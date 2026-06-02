"""OpenTelemetry integration for AI execution tracing.

Provides distributed tracing with span hierarchy across the entire
AI orchestration pipeline:

API Request
  -> AI Orchestrator
      -> Retrieval
      -> Guardrails
      -> Provider
      -> Validation
      -> Audit Persistence

Usage::
    from app.domains.ai.telemetry.tracing import (
        AIExecutionTracer, trace_ai_execution, get_tracer
    )

    tracer = AIExecutionTracer()
    with tracer.execution_span(execution_id, tenant_id, operation_type) as span:
        with tracer.retrieval_span():
            ...
        with tracer.provider_span(provider, model):
            ...
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry — gracefully degrade if not installed
try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, SpanKind, Status, StatusCode
    from opentelemetry.trace.propagation import set_span_in_context
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    # Stub types for type checking
    class Span:  # type: ignore
        pass
    class SpanKind:
        INTERNAL = 0
        CLIENT = 1
        SERVER = 2
    class StatusCode:
        OK = 0
        ERROR = 1
    class Status:
        def __init__(self, status_code, description=""):
            self.status_code = status_code
            self.description = description


# ── Span Names ─────────────────────────────────────────────────────

SPAN_EXECUTION = "ai.execution"
SPAN_RETRIEVAL = "ai.retrieval"
SPAN_GUARDRAIL_PRE = "ai.guardrail.pre"
SPAN_GUARDRAIL_POST = "ai.guardrail.post"
SPAN_PROVIDER = "ai.provider"
SPAN_VALIDATION = "ai.validation"
SPAN_PERSISTENCE = "ai.persistence"
SPAN_POLICY = "ai.policy"
SPAN_REPLAY = "ai.replay"
SPAN_SNAPSHOT = "ai.snapshot"


class SpanRecorder:
    """Fallback span recorder when OpenTelemetry is not available.

    Records span start/end times and attributes in memory.
    """

    def __init__(self):
        self.spans: list[dict[str, Any]] = []

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
        span = {
            "name": name,
            "attributes": attributes or {},
            "start_time": time.monotonic(),
            "end_time": None,
            "status": "ok",
        }
        self.spans.append(span)
        return span

    def end_span(self, span: dict[str, Any], status: str = "ok") -> None:
        span["end_time"] = time.monotonic()
        span["duration_ms"] = int((span["end_time"] - span["start_time"]) * 1000)
        span["status"] = status

    def get_trace(self) -> dict[str, Any]:
        return {
            "spans": list(self.spans),
            "total_duration_ms": sum(
                s.get("duration_ms", 0) for s in self.spans if s.get("duration_ms")
            ),
        }


# ── AI Execution Tracer ────────────────────────────────────────────

@dataclass
class AIExecutionTracer:
    """Tracer for AI execution pipelines with OpenTelemetry support.

    Falls back to in-memory SpanRecorder if OpenTelemetry is not installed.
    """

    service_name: str = "contractriskedge-ai"
    _recorder: SpanRecorder = field(default_factory=SpanRecorder)

    def __post_init__(self):
        if _OTEL_AVAILABLE:
            self._tracer = trace.get_tracer(self.service_name)
        else:
            self._tracer = None
            logger.info("OpenTelemetry not available, using in-memory span recorder")

    # ── Context Managers ───────────────────────────────────────────

    @contextmanager
    def execution_span(
        self,
        execution_id: str,
        tenant_id: str,
        operation_type: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | dict[str, Any], None, None]:
        """Create the top-level execution span."""
        attrs = {
            "ai.execution_id": execution_id,
            "ai.tenant_id": tenant_id,
            "ai.operation_type": operation_type,
            "ai.service": self.service_name,
            **(attributes or {}),
        }

        if self._tracer:
            with self._tracer.start_as_current_span(
                SPAN_EXECUTION,
                kind=SpanKind.SERVER,
                attributes=attrs,
            ) as span:
                yield span
        else:
            span = self._recorder.start_span(SPAN_EXECUTION, attrs)
            try:
                yield span
            finally:
                self._recorder.end_span(span)

    @contextmanager
    def retrieval_span(
        self,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | dict[str, Any], None, None]:
        """Span for retrieval operations."""
        attrs = {"ai.component": "retrieval", **(attributes or {})}
        with self._child_span(SPAN_RETRIEVAL, attrs) as span:
            yield span

    @contextmanager
    def guardrail_span(
        self,
        phase: str = "pre",
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | dict[str, Any], None, None]:
        """Span for guardrail evaluation."""
        span_name = SPAN_GUARDRAIL_PRE if phase == "pre" else SPAN_GUARDRAIL_POST
        attrs = {"ai.component": "guardrail", "ai.guardrail_phase": phase, **(attributes or {})}
        with self._child_span(span_name, attrs) as span:
            yield span

    @contextmanager
    def provider_span(
        self,
        provider: str,
        model: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | dict[str, Any], None, None]:
        """Span for LLM provider execution."""
        attrs = {
            "ai.component": "provider",
            "ai.provider": provider,
            "ai.model": model,
            **(attributes or {}),
        }
        with self._child_span(SPAN_PROVIDER, attrs) as span:
            yield span

    @contextmanager
    def validation_span(
        self,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | dict[str, Any], None, None]:
        """Span for response validation."""
        attrs = {"ai.component": "validation", **(attributes or {})}
        with self._child_span(SPAN_VALIDATION, attrs) as span:
            yield span

    @contextmanager
    def persistence_span(
        self,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | dict[str, Any], None, None]:
        """Span for audit persistence."""
        attrs = {"ai.component": "persistence", **(attributes or {})}
        with self._child_span(SPAN_PERSISTENCE, attrs) as span:
            yield span

    @contextmanager
    def policy_span(
        self,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | dict[str, Any], None, None]:
        """Span for policy engine evaluation."""
        attrs = {"ai.component": "policy", **(attributes or {})}
        with self._child_span(SPAN_POLICY, attrs) as span:
            yield span

    @contextmanager
    def _child_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | dict[str, Any], None, None]:
        """Create a child span under the current execution span."""
        if self._tracer:
            with self._tracer.start_as_current_span(
                name,
                kind=SpanKind.INTERNAL,
                attributes=attributes or {},
            ) as span:
                yield span
        else:
            span = self._recorder.start_span(name, attributes)
            try:
                yield span
            finally:
                self._recorder.end_span(span)

    # ── Manual Span Control ────────────────────────────────────────

    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Span | dict[str, Any] | None:
        """Start a span manually (for use outside context managers)."""
        if self._tracer:
            return self._tracer.start_span(name, attributes=attributes)
        return self._recorder.start_span(name, attributes)

    def end_span(
        self,
        span: Span | dict[str, Any] | None,
        status: str = "ok",
    ) -> None:
        """End a manually started span."""
        if span is None:
            return
        if _OTEL_AVAILABLE and isinstance(span, Span):
            span.set_status(Status(
                StatusCode.OK if status == "ok" else StatusCode.ERROR,
                description=status,
            ))
            span.end()
        elif isinstance(span, dict):
            self._recorder.end_span(span, status)

    def set_span_attribute(
        self, span: Span | dict[str, Any] | None, key: str, value: Any
    ) -> None:
        """Set an attribute on an active span."""
        if span is None:
            return
        if _OTEL_AVAILABLE and isinstance(span, Span):
            span.set_attribute(key, value)
        elif isinstance(span, dict):
            span.setdefault("attributes", {})[key] = value

    def record_exception(
        self, span: Span | dict[str, Any] | None, exception: Exception
    ) -> None:
        """Record an exception on a span."""
        if span is None:
            return
        if _OTEL_AVAILABLE and isinstance(span, Span):
            span.record_exception(exception)
            span.set_status(Status(StatusCode.ERROR, str(exception)))
        elif isinstance(span, dict):
            span["status"] = "error"
            span["error"] = str(exception)

    # ── Trace Export ───────────────────────────────────────────────

    def get_trace(self) -> dict[str, Any] | None:
        """Get the current trace data (only for in-memory recorder)."""
        if not _OTEL_AVAILABLE:
            return self._recorder.get_trace()
        return None

    def get_recorder_spans(self) -> list[dict[str, Any]]:
        """Get all recorded spans from the in-memory recorder."""
        return list(self._recorder.spans)


# ── Global tracer singleton ────────────────────────────────────────

_global_tracer: AIExecutionTracer | None = None


def get_tracer() -> AIExecutionTracer:
    """Get or create the global AI execution tracer."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = AIExecutionTracer()
    return _global_tracer


def trace_ai_execution(
    execution_id: str,
    tenant_id: str,
    operation_type: str,
) -> AIExecutionTracer:
    """Convenience function to get a tracer and start an execution span.

    Usage::
        tracer = trace_ai_execution(exec_id, tenant_id, "risk_analysis")
        with tracer.execution_span(exec_id, tenant_id, "risk_analysis"):
            ...
    """
    return get_tracer()
