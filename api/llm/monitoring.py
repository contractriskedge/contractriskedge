"""OpenTelemetry tracing for LLM operations with Datadog export.

Provides distributed tracing, metrics collection, and monitoring
for all LLM operations including request latency, token usage,
error rates, and provider failover events.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from .models import ProviderType

logger = logging.getLogger(__name__)

# Conditional import for OpenTelemetry - works without it installed
try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Status, StatusCode

    _HAS_OPENTELEMETRY = True
except ImportError:
    _HAS_OPENTELEMETRY = False

    # Stub types for type checking
    class Span:  # type: ignore
        """Stub Span for when OpenTelemetry is not installed."""
        pass


class LLMMonitoring:
    """OpenTelemetry-based monitoring for LLM operations.

    Provides tracing spans for LLM requests, metrics collection,
    and Datadog-compatible export. Gracefully degrades when
    OpenTelemetry is not installed.

    Usage:
        monitoring = LLMMonitoring(service_name="contract-risk-analyzer")
        with monitoring.trace_request("llm_complete") as span:
            response = await client.complete(request)
    """

    def __init__(
        self,
        service_name: str = "contract-risk-analyzer",
        datadog_agent_url: Optional[str] = None,
        sample_rate: float = 1.0,
    ) -> None:
        """Initialize the LLM monitoring.

        Args:
            service_name: Name of the service for tracing.
            datadog_agent_url: Optional Datadog agent URL for direct export.
            sample_rate: Trace sampling rate (0.0 to 1.0).
        """
        self._service_name = service_name
        self._datadog_agent_url = datadog_agent_url
        self._sample_rate = sample_rate
        self._tracer = None

        if _HAS_OPENTELEMETRY:
            self._setup_opentelemetry()
        else:
            logger.info(
                "OpenTelemetry not installed. Monitoring will use fallback logging."
            )

        # In-memory metrics for when OpenTelemetry is unavailable
        self._metrics: Dict[str, Any] = {
            "total_requests": 0,
            "total_errors": 0,
            "total_failovers": 0,
            "cache_hits": 0,
            "provider_requests": {},
            "latency_buckets": {},
        }

    def _setup_opentelemetry(self) -> None:
        """Configure OpenTelemetry with Datadog exporter."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create(
                attributes={
                    "service.name": self._service_name,
                    "service.version": "1.0.0",
                }
            )

            provider = TracerProvider(resource=resource)

            # Configure Datadog exporter if agent URL is provided
            if self._datadog_agent_url:
                try:
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                        OTLPSpanExporter,
                    )

                    exporter = OTLPSpanExporter(
                        endpoint=f"{self._datadog_agent_url}/v1/traces",
                    )
                    provider.add_span_processor(
                        BatchSpanProcessor(exporter)
                    )
                    logger.info("Datadog OTLP exporter configured")
                except ImportError:
                    logger.warning(
                        "OTLP exporter not installed. Install opentelemetry-exporter-otlp-proto-http"
                    )

            # Always add a console exporter for debugging
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )

            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(__name__)

            logger.info("OpenTelemetry tracing initialized for %s", self._service_name)

        except Exception as exc:
            logger.warning("Failed to setup OpenTelemetry: %s", exc)
            self._tracer = None

    def _should_sample(self) -> bool:
        """Determine if a trace should be sampled.

        Returns:
            True if the trace should be recorded.
        """
        if self._sample_rate >= 1.0:
            return True
        return (hash(time.monotonic()) % 100) < (self._sample_rate * 100)

    def record_request(
        self,
        provider: ProviderType,
        duration_ms: float,
        token_count: int,
        request_id: str,
    ) -> None:
        """Record an LLM request completion.

        Args:
            provider: The provider used.
            duration_ms: Request duration in milliseconds.
            token_count: Total tokens used.
            request_id: Unique request identifier.
        """
        self._metrics["total_requests"] += 1

        provider_key = provider.value
        if provider_key not in self._metrics["provider_requests"]:
            self._metrics["provider_requests"][provider_key] = {
                "count": 0,
                "total_duration_ms": 0.0,
                "total_tokens": 0,
            }

        prov_metrics = self._metrics["provider_requests"][provider_key]
        prov_metrics["count"] += 1
        prov_metrics["total_duration_ms"] += duration_ms
        prov_metrics["total_tokens"] += token_count

        # Track latency distribution
        bucket = self._get_latency_bucket(duration_ms)
        self._metrics["latency_buckets"][bucket] = (
            self._metrics["latency_buckets"].get(bucket, 0) + 1
        )

        if _HAS_OPENTELEMETRY and self._tracer and self._should_sample():
            with self._tracer.start_as_current_span("llm_request") as span:
                span.set_attribute("llm.provider", provider.value)
                span.set_attribute("llm.duration_ms", duration_ms)
                span.set_attribute("llm.token_count", token_count)
                span.set_attribute("llm.request_id", request_id)

    def record_provider_failover(
        self, failed_provider: ProviderType, error: str
    ) -> None:
        """Record a provider failover event.

        Args:
            failed_provider: The provider that failed.
            error: Error message from the failure.
        """
        self._metrics["total_failovers"] += 1

        logger.warning(
            "Provider failover from %s: %s",
            failed_provider.value,
            error,
        )

        if _HAS_OPENTELEMETRY and self._tracer:
            with self._tracer.start_as_current_span("llm_failover") as span:
                span.set_attribute("llm.failed_provider", failed_provider.value)
                span.set_attribute("llm.error", error)
                span.set_status(Status(StatusCode.ERROR, error))

    def record_request_failure(self, request_id: str, error: str) -> None:
        """Record an LLM request failure.

        Args:
            request_id: The failed request identifier.
            error: Error description.
        """
        self._metrics["total_errors"] += 1

        if _HAS_OPENTELEMETRY and self._tracer:
            with self._tracer.start_as_current_span("llm_request_failure") as span:
                span.set_attribute("llm.request_id", request_id)
                span.set_attribute("llm.error", error)
                span.set_status(Status(StatusCode.ERROR, error))

    def record_cache_hit(self, request_id: str) -> None:
        """Record a cache hit event.

        Args:
            request_id: The request that had a cache hit.
        """
        self._metrics["cache_hits"] += 1

    def _get_latency_bucket(self, duration_ms: float) -> str:
        """Get the latency bucket for a duration.

        Args:
            duration_ms: Duration in milliseconds.

        Returns:
            Bucket label string.
        """
        if duration_ms < 100:
            return "0-100ms"
        elif duration_ms < 500:
            return "100-500ms"
        elif duration_ms < 1000:
            return "500-1000ms"
        elif duration_ms < 3000:
            return "1-3s"
        elif duration_ms < 10000:
            return "3-10s"
        else:
            return "10s+"

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of current metrics.

        Returns:
            Dict with all accumulated metrics.
        """
        metrics = dict(self._metrics)

        # Add computed metrics
        total = metrics["total_requests"]
        if total > 0:
            metrics["error_rate"] = round(
                metrics["total_errors"] / total, 4
            )
            metrics["failover_rate"] = round(
                metrics["total_failovers"] / total, 4
            )
            metrics["cache_hit_rate"] = round(
                metrics["cache_hits"] / total, 4
            )
        else:
            metrics["error_rate"] = 0.0
            metrics["failover_rate"] = 0.0
            metrics["cache_hit_rate"] = 0.0

        return metrics

    def create_span(
        self, name: str, attributes: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create a new tracing span.

        Args:
            name: Span name.
            attributes: Optional span attributes.

        Returns:
            A span context manager, or a no-op context if tracing is unavailable.
        """
        if _HAS_OPENTELEMETRY and self._tracer:
            return self._tracer.start_as_current_span(
                name, attributes=attributes
            )

        # Return no-op context manager
        class _NoOpSpan:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def set_attribute(self, key, value):
                pass
            def set_status(self, status):
                pass

        return _NoOpSpan()

    def close(self) -> None:
        """Close the monitoring and flush any pending traces."""
        if _HAS_OPENTELEMETRY:
            try:
                from opentelemetry import trace
                provider = trace.get_tracer_provider()
                if hasattr(provider, "shutdown"):
                    provider.shutdown()
                    logger.info("OpenTelemetry tracer provider shut down")
            except Exception as exc:
                logger.warning("Error shutting down tracer: %s", exc)
