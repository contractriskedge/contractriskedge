"""
Integration Telemetry — OpenTelemetry instrumentation for the integration subsystem.

Records metrics and traces for:
- Sync operations (latency, items, status)
- Webhook events (volume, processing time, status)
- OAuth flows (success/failure, refresh rates)
- Rate limit events
- Connector health checks
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.metrics import Counter, Histogram
from structlog import get_logger

logger = get_logger(__name__)

# Meter and tracer for integration subsystem
_meter = metrics.get_meter("contractriskedge.integration")
_tracer = trace.get_tracer("contractriskedge.integration")


@dataclass
class IntegrationMetrics:
    """Container for all integration-related metric instruments."""

    # Sync metrics
    sync_duration: Histogram = field(default_factory=lambda: _meter.create_histogram(
        name="integration.sync.duration",
        description="Duration of sync operations",
        unit="ms",
    ))
    sync_items: Histogram = field(default_factory=lambda: _meter.create_histogram(
        name="integration.sync.items",
        description="Number of items synced per operation",
        unit="items",
    ))
    sync_total: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.sync.total",
        description="Total sync operations",
    ))
    sync_errors: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.sync.errors",
        description="Total sync errors",
    ))

    # Webhook metrics
    webhook_events: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.webhook.events",
        description="Total webhook events received",
    ))
    webhook_duration: Histogram = field(default_factory=lambda: _meter.create_histogram(
        name="integration.webhook.duration",
        description="Webhook processing duration",
        unit="ms",
    ))
    webhook_errors: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.webhook.errors",
        description="Total webhook processing errors",
    ))

    # OAuth metrics
    oauth_flows: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.oauth.flows",
        description="Total OAuth authorization flows",
    ))
    oauth_refresh: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.oauth.refresh",
        description="Total OAuth token refreshes",
    ))
    oauth_errors: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.oauth.errors",
        description="Total OAuth errors",
    ))

    # Rate limit metrics
    rate_limit_hits: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.ratelimit.hits",
        description="Total rate limit hits",
    ))

    # Connector health metrics
    connector_health: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.connector.health",
        description="Connector health check results",
    ))

    # Retry metrics
    retry_attempts: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.retry.attempts",
        description="Total retry attempts",
    ))
    dead_letter_events: Counter = field(default_factory=lambda: _meter.create_counter(
        name="integration.retry.dead_letter",
        description="Total dead-lettered events",
    ))


class IntegrationTelemetry:
    """
    Telemetry instrumentation for the integration subsystem.

    Records OpenTelemetry metrics and traces for all integration operations.
    """

    def __init__(self):
        self.metrics = IntegrationMetrics()

    # ---- Sync telemetry ----

    def record_sync_completion(
        self,
        provider: str,
        status: str,
        duration_ms: float,
        items_synced: int = 0,
    ) -> None:
        """Record sync completion metrics."""
        attrs = {"provider": provider, "status": status}

        self.metrics.sync_duration.record(duration_ms, attributes=attrs)
        self.metrics.sync_total.add(1, attributes=attrs)

        if items_synced > 0:
            self.metrics.sync_items.record(items_synced, attributes=attrs)

        if status in ("failed", "error"):
            self.metrics.sync_errors.add(1, attributes=attrs)

    def record_sync_retry(
        self,
        provider: str,
        attempt: int,
        max_retries: int,
    ) -> None:
        """Record a sync retry attempt."""
        self.metrics.retry_attempts.add(
            1,
            attributes={
                "provider": provider,
                "attempt": str(attempt),
                "max_retries": str(max_retries),
            },
        )

    def record_dead_letter(
        self,
        provider: str,
        resource_type: str,
    ) -> None:
        """Record a dead-letter event."""
        self.metrics.dead_letter_events.add(
            1,
            attributes={"provider": provider, "resource_type": resource_type},
        )

    # ---- Webhook telemetry ----

    def record_webhook_event(
        self,
        provider: str,
        event_type: str,
        status: str,
    ) -> None:
        """Record a webhook event."""
        self.metrics.webhook_events.add(
            1,
            attributes={
                "provider": provider,
                "event_type": event_type,
                "status": status,
            },
        )

    def record_webhook_processing(
        self,
        provider: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record webhook processing duration."""
        self.metrics.webhook_duration.record(
            duration_ms,
            attributes={"provider": provider, "success": str(success)},
        )
        if not success:
            self.metrics.webhook_errors.add(
                1, attributes={"provider": provider}
            )

    # ---- OAuth telemetry ----

    def record_oauth_flow(
        self,
        provider: str,
        success: bool,
    ) -> None:
        """Record an OAuth authorization flow."""
        self.metrics.oauth_flows.add(
            1,
            attributes={"provider": provider, "success": str(success)},
        )
        if not success:
            self.metrics.oauth_errors.add(
                1, attributes={"provider": provider, "flow": "authorization"}
            )

    def record_oauth_refresh(
        self,
        provider: str,
        success: bool,
    ) -> None:
        """Record an OAuth token refresh."""
        self.metrics.oauth_refresh.add(
            1,
            attributes={"provider": provider, "success": str(success)},
        )
        if not success:
            self.metrics.oauth_errors.add(
                1, attributes={"provider": provider, "flow": "refresh"}
            )

    # ---- Rate limit telemetry ----

    def record_rate_limit_hit(
        self,
        provider: str,
        integration_id: str,
    ) -> None:
        """Record a rate limit hit."""
        self.metrics.rate_limit_hits.add(
            1,
            attributes={
                "provider": provider,
                "integration_id": integration_id,
            },
        )

    # ---- Connector health telemetry ----

    def record_connector_health(
        self,
        provider: str,
        healthy: bool,
        latency_ms: Optional[float] = None,
    ) -> None:
        """Record a connector health check result."""
        self.metrics.connector_health.add(
            1,
            attributes={
                "provider": provider,
                "healthy": str(healthy),
            },
        )

    # ---- Trace helpers ----

    @staticmethod
    def start_trace(name: str, attributes: Optional[dict] = None):
        """Start a new trace span for an integration operation."""
        return _tracer.start_as_current_span(
            name,
            attributes=attributes or {},
        )


# Global telemetry singleton
_global_telemetry: Optional[IntegrationTelemetry] = None


def get_telemetry() -> IntegrationTelemetry:
    """Get the global telemetry singleton."""
    global _global_telemetry
    if _global_telemetry is None:
        _global_telemetry = IntegrationTelemetry()
    return _global_telemetry
