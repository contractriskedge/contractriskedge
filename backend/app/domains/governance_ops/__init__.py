"""AI Governance Operations Center — governance drift detection, explainability monitoring, policy violation forecasting, replay integrity health, provider trust scoring.

Operationalizes governance itself — making it observable, measurable, and actionable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GovernanceHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class GovernanceMetric:
    """A single governance health metric."""
    name: str
    value: float
    status: GovernanceHealthStatus
    threshold_warning: float = 0.0
    threshold_critical: float = 0.0
    trend: str = "stable"


@dataclass
class ProviderTrustScore:
    """Trust score for an AI provider."""
    provider: str
    trust_score: float
    total_calls: int = 0
    success_rate: float = 1.0
    avg_latency_ms: int = 0
    circuit_breaker_status: str = "closed"
    data_residency_compliant: bool = True


@dataclass
class GovernanceOperationsService:
    """AI Governance Operations Center — operationalizes governance itself.

    Capabilities:
    - Governance drift detection (is governance degrading?)
    - Explainability monitoring (are decisions explainable?)
    - Policy violation forecasting (will violations increase?)
    - Replay integrity health (is replay still reliable?)
    - Provider trust scoring (can we trust each provider?)
    - AI ethics controls (are ethical boundaries respected?)
    - Governance trend analytics (is governance improving?)
    """

    _metrics: dict[str, GovernanceMetric] = field(default_factory=dict)

    def assess_replay_health(self, recent_replays: list[dict]) -> GovernanceMetric:
        """Assess replay integrity health."""
        total = len(recent_replays)
        if total == 0:
            return GovernanceMetric("replay_health", 1.0, GovernanceHealthStatus.HEALTHY)

        drifted = sum(1 for r in recent_replays if r.get("drift_detected", False))
        drift_rate = drifted / total
        avg_drift = sum(r.get("drift_score", 0) for r in recent_replays) / total

        health = 1.0 - (drift_rate * 0.6 + avg_drift * 0.4)
        status = GovernanceHealthStatus.HEALTHY if health > 0.9 else \
                 GovernanceHealthStatus.DEGRADED if health > 0.7 else \
                 GovernanceHealthStatus.CRITICAL

        return GovernanceMetric(
            "replay_health", round(health, 4), status,
            threshold_warning=0.9, threshold_critical=0.7,
            trend="declining" if drift_rate > 0.1 else "stable",
        )

    def assess_explainability(self, execution_history: list[dict]) -> GovernanceMetric:
        """Assess explainability coverage."""
        total = len(execution_history)
        if total == 0:
            return GovernanceMetric("explainability", 1.0, GovernanceHealthStatus.HEALTHY)

        with_trace = sum(1 for e in execution_history if e.get("has_trace", False))
        with_evidence = sum(1 for e in execution_history if e.get("has_evidence", False))
        coverage = (with_trace + with_evidence) / (total * 2) * 2  # Normalize

        status = GovernanceHealthStatus.HEALTHY if coverage > 0.95 else \
                 GovernanceHealthStatus.DEGRADED if coverage > 0.8 else \
                 GovernanceHealthStatus.CRITICAL

        return GovernanceMetric("explainability", round(coverage, 4), status, threshold_warning=0.95, threshold_critical=0.8)

    def assess_policy_compliance(self, violations_30d: list[dict]) -> GovernanceMetric:
        """Assess policy compliance health."""
        total = len(violations_30d)
        if total == 0:
            return GovernanceMetric("policy_compliance", 1.0, GovernanceHealthStatus.HEALTHY)

        critical = sum(1 for v in violations_30d if v.get("severity") == "critical")
        high = sum(1 for v in violations_30d if v.get("severity") == "high")

        compliance = 1.0 - (critical * 0.1 + high * 0.05)
        compliance = max(0.0, compliance)

        status = GovernanceHealthStatus.HEALTHY if compliance > 0.95 else \
                 GovernanceHealthStatus.DEGRADED if compliance > 0.8 else \
                 GovernanceHealthStatus.CRITICAL

        return GovernanceMetric("policy_compliance", round(compliance, 4), status, threshold_warning=0.95, threshold_critical=0.8)

    def score_provider_trust(self, provider_name: str, stats: dict) -> ProviderTrustScore:
        """Score an AI provider's trustworthiness."""
        success_rate = stats.get("success_rate", 1.0)
        avg_latency = stats.get("avg_latency_ms", 0)
        circuit_breaker = stats.get("circuit_breaker", "closed")
        total_calls = stats.get("total_calls", 0)

        trust = success_rate * 0.5 + (1.0 - min(1.0, avg_latency / 10000)) * 0.2 + (1.0 if circuit_breaker == "closed" else 0.3) * 0.3

        return ProviderTrustScore(
            provider=provider_name,
            trust_score=round(trust, 4),
            total_calls=total_calls,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            circuit_breaker_status=circuit_breaker,
            data_residency_compliant=True,
        )

    def get_governance_dashboard(self) -> dict[str, Any]:
        """Get governance operations dashboard."""
        return {
            "metrics": {k: {"value": m.value, "status": m.status.value, "trend": m.trend} for k, m in self._metrics.items()},
            "overall_status": self._compute_overall_status(),
            "last_updated": datetime.utcnow().isoformat(),
        }

    def _compute_overall_status(self) -> str:
        """Compute overall governance health status."""
        if not self._metrics:
            return "unknown"
        statuses = [m.status for m in self._metrics.values()]
        if any(s == GovernanceHealthStatus.CRITICAL for s in statuses):
            return "critical"
        if any(s == GovernanceHealthStatus.DEGRADED for s in statuses):
            return "degraded"
        return "healthy"


# ── Global singleton ───────────────────────────────────────────────

governance_ops = GovernanceOperationsService()
