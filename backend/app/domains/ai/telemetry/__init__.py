"""Structured AI telemetry — centralized metrics for AI execution observability.

Tracks:
- Provider latency and cost
- Retrieval latency
- Guardrail rejection rate
- Hallucination rate
- Retry count
- Timeout rate
- Cost per execution
- Token usage
- Model distribution
- Fallback frequency
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics for a single AI execution."""
    execution_id: str
    tenant_id: str
    operation_type: str
    provider: str
    model: str

    # Timing
    started_at: float = 0.0  # monotonic timestamp
    completed_at: float = 0.0
    total_latency_ms: int = 0

    # Breakdown latencies
    retrieval_latency_ms: int = 0
    guardrail_latency_ms: int = 0
    provider_latency_ms: int = 0
    validation_latency_ms: int = 0
    persistence_latency_ms: int = 0

    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Cost
    cost_usd: float = 0.0

    # Quality
    confidence: float = 0.0
    findings_count: int = 0
    guardrail_violations: int = 0
    guardrail_rejected: bool = False
    validation_score: float = 1.0
    hallucination_flags: int = 0

    # Reliability
    retry_count: int = 0
    timed_out: bool = False
    fallback_used: bool = False
    fallback_provider: str | None = None
    error_message: str | None = None

    # Retrieval
    chunks_retrieved: int = 0
    snapshot_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tenant_id": self.tenant_id,
            "operation_type": self.operation_type,
            "provider": self.provider,
            "model": self.model,
            "total_latency_ms": self.total_latency_ms,
            "retrieval_latency_ms": self.retrieval_latency_ms,
            "guardrail_latency_ms": self.guardrail_latency_ms,
            "provider_latency_ms": self.provider_latency_ms,
            "validation_latency_ms": self.validation_latency_ms,
            "persistence_latency_ms": self.persistence_latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "confidence": self.confidence,
            "findings_count": self.findings_count,
            "guardrail_violations": self.guardrail_violations,
            "guardrail_rejected": self.guardrail_rejected,
            "validation_score": self.validation_score,
            "hallucination_flags": self.hallucination_flags,
            "retry_count": self.retry_count,
            "timed_out": self.timed_out,
            "fallback_used": self.fallback_used,
            "fallback_provider": self.fallback_provider,
            "error_message": self.error_message,
            "chunks_retrieved": self.chunks_retrieved,
            "snapshot_used": self.snapshot_used,
        }


class AIExecutionMetrics:
    """Centralized telemetry collector for AI execution observability.

    This is an in-memory aggregator. For production, metrics should be
    exported to Prometheus/OpenTelemetry as well.
    """

    def __init__(self):
        self._executions: list[ExecutionMetrics] = []
        self._aggregates: dict[str, Any] = self._empty_aggregates()

    @staticmethod
    def _empty_aggregates() -> dict[str, Any]:
        return {
            "total_executions": 0,
            "total_errors": 0,
            "total_timeouts": 0,
            "total_fallbacks": 0,
            "total_guardrail_rejections": 0,
            "total_hallucination_flags": 0,
            "total_cost_usd": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_latency_ms": 0,
            "avg_latency_ms": 0,
            "avg_confidence": 0.0,
            "avg_validation_score": 1.0,
            "avg_cost_per_execution": 0.0,
            "provider_breakdown": {},
            "model_breakdown": {},
            "operation_breakdown": {},
            "error_breakdown": {},
        }

    def record_execution(self, metrics: ExecutionMetrics) -> None:
        """Record metrics for a single execution."""
        self._executions.append(metrics)
        self._update_aggregates(metrics)

    def record_execution_sync(
        self,
        execution_id: str,
        tenant_id: str,
        operation_type: str,
        provider: str,
        model: str,
        **kwargs: Any,
    ) -> ExecutionMetrics:
        """Create and record execution metrics from kwargs."""
        metrics = ExecutionMetrics(
            execution_id=execution_id,
            tenant_id=tenant_id,
            operation_type=operation_type,
            provider=provider,
            model=model,
            **kwargs,
        )
        self.record_execution(metrics)
        return metrics

    def _update_aggregates(self, m: ExecutionMetrics) -> None:
        """Update running aggregates with a new execution's metrics."""
        agg = self._aggregates
        agg["total_executions"] += 1

        if m.error_message:
            agg["total_errors"] += 1
            error_key = m.error_message.split(":")[0][:100]
            agg["error_breakdown"][error_key] = agg["error_breakdown"].get(error_key, 0) + 1

        if m.timed_out:
            agg["total_timeouts"] += 1
        if m.fallback_used:
            agg["total_fallbacks"] += 1
        if m.guardrail_rejected:
            agg["total_guardrail_rejections"] += 1

        agg["total_hallucination_flags"] += m.hallucination_flags
        agg["total_cost_usd"] += m.cost_usd
        agg["total_prompt_tokens"] += m.prompt_tokens
        agg["total_completion_tokens"] += m.completion_tokens
        agg["total_tokens"] += m.total_tokens
        agg["total_latency_ms"] += m.total_latency_ms

        n = agg["total_executions"]
        agg["avg_latency_ms"] = agg["total_latency_ms"] // n
        agg["avg_confidence"] = (
            (agg["avg_confidence"] * (n - 1) + m.confidence) / n
        )
        agg["avg_validation_score"] = (
            (agg["avg_validation_score"] * (n - 1) + m.validation_score) / n
        )
        agg["avg_cost_per_execution"] = agg["total_cost_usd"] / n

        # Provider breakdown
        if m.provider not in agg["provider_breakdown"]:
            agg["provider_breakdown"][m.provider] = {"count": 0, "total_cost": 0.0, "total_latency": 0}
        agg["provider_breakdown"][m.provider]["count"] += 1
        agg["provider_breakdown"][m.provider]["total_cost"] += m.cost_usd
        agg["provider_breakdown"][m.provider]["total_latency"] += m.provider_latency_ms

        # Model breakdown
        model_key = f"{m.provider}/{m.model}"
        agg["model_breakdown"][model_key] = agg["model_breakdown"].get(model_key, 0) + 1

        # Operation breakdown
        agg["operation_breakdown"][m.operation_type] = (
            agg["operation_breakdown"].get(m.operation_type, 0) + 1
        )

    def get_aggregates(self) -> dict[str, Any]:
        """Get current aggregate metrics."""
        return dict(self._aggregates)

    def get_recent_executions(self, limit: int = 100) -> list[ExecutionMetrics]:
        """Get the most recent executions."""
        return list(self._executions[-limit:])

    def get_provider_summary(self) -> dict[str, dict[str, Any]]:
        """Get per-provider summary metrics."""
        return dict(self._aggregates.get("provider_breakdown", {}))

    def get_error_rate(self) -> float:
        """Get the overall error rate (0.0-1.0)."""
        agg = self._aggregates
        if agg["total_executions"] == 0:
            return 0.0
        return agg["total_errors"] / agg["total_executions"]

    def get_guardrail_rejection_rate(self) -> float:
        """Get guardrail rejection rate (0.0-1.0)."""
        agg = self._aggregates
        if agg["total_executions"] == 0:
            return 0.0
        return agg["total_guardrail_rejections"] / agg["total_executions"]

    def get_hallucination_rate(self) -> float:
        """Get hallucination flag rate (flags per execution)."""
        agg = self._aggregates
        if agg["total_executions"] == 0:
            return 0.0
        return agg["total_hallucination_flags"] / agg["total_executions"]

    def get_fallback_frequency(self) -> float:
        """Get fallback frequency (0.0-1.0)."""
        agg = self._aggregates
        if agg["total_executions"] == 0:
            return 0.0
        return agg["total_fallbacks"] / agg["total_executions"]

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._executions.clear()
        self._aggregates = self._empty_aggregates()


# ── Global singleton ───────────────────────────────────────────────

ai_execution_metrics = AIExecutionMetrics()
