"""Workflow Intelligence Layer — bottleneck detection, approval delay prediction, escalation forecasting.

Turns workflow execution data into operational intelligence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BottleneckSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Bottleneck:
    """A detected workflow bottleneck."""
    stage_name: str
    severity: BottleneckSeverity
    avg_completion_hours: float
    sla_hours: int
    breach_rate: float  # 0.0-1.0
    reviewer_load: int
    recommendation: str = ""


@dataclass
class ApprovalDelayPrediction:
    """Predicted delay for an approval stage."""
    stage_name: str
    predicted_hours: float
    confidence: float  # 0.0-1.0
    risk_factors: list[str] = field(default_factory=list)
    recommended_action: str = ""


@dataclass
class ReviewerOverloadPrediction:
    """Prediction of reviewer overload."""
    reviewer_id: str
    current_load: int
    max_capacity: int
    predicted_load_7d: int
    overload_risk: str  # low, medium, high
    recommendation: str = ""


@dataclass
class WorkflowIntelligenceService:
    """Operational intelligence for workflow execution.

    Capabilities:
    - Bottleneck detection (which stages slow things down)
    - Approval delay prediction (how long will approval take)
    - Escalation forecasting (will this need escalation)
    - Reviewer overload prediction (who is overworked)
    - Negotiation cycle prediction (how long will negotiation take)
    - SLA breach forecasting (will we miss SLA deadlines)
    """

    _stage_history: list[dict[str, Any]] = field(default_factory=list)

    def record_stage_completion(self, stage_name: str, sla_hours: int, actual_hours: float, breached: bool) -> None:
        """Record a stage completion for analysis."""
        self._stage_history.append({
            "stage_name": stage_name,
            "sla_hours": sla_hours,
            "actual_hours": actual_hours,
            "breached": breached,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def detect_bottlenecks(self, min_samples: int = 5) -> list[Bottleneck]:
        """Detect workflow bottlenecks from stage history."""
        stage_stats: dict[str, list[float]] = {}
        stage_slas: dict[str, int] = {}
        stage_breaches: dict[str, int] = {}
        stage_total: dict[str, int] = {}

        for record in self._stage_history:
            name = record["stage_name"]
            if name not in stage_stats:
                stage_stats[name] = []
                stage_slas[name] = record["sla_hours"]
                stage_breaches[name] = 0
                stage_total[name] = 0
            stage_stats[name].append(record["actual_hours"])
            stage_total[name] += 1
            if record["breached"]:
                stage_breaches[name] += 1

        bottlenecks = []
        for name, times in stage_stats.items():
            if len(times) < min_samples:
                continue
            avg_time = sum(times) / len(times)
            sla = stage_slas.get(name, 24)
            breach_rate = stage_breaches.get(name, 0) / max(stage_total.get(name, 1), 1)

            if avg_time > sla * 1.5 or breach_rate > 0.3:
                severity = BottleneckSeverity.CRITICAL if (avg_time > sla * 2 or breach_rate > 0.5) else \
                           BottleneckSeverity.HIGH if (avg_time > sla * 1.5 or breach_rate > 0.3) else \
                           BottleneckSeverity.MEDIUM
                bottlenecks.append(Bottleneck(
                    stage_name=name,
                    severity=severity,
                    avg_completion_hours=round(avg_time, 1),
                    sla_hours=sla,
                    breach_rate=round(breach_rate, 2),
                    reviewer_load=0,
                    recommendation=self._recommend_bottleneck_fix(name, severity),
                ))

        return sorted(bottlenecks, key=lambda b: b.severity.value, reverse=True)

    def _recommend_bottleneck_fix(self, stage_name: str, severity: BottleneckSeverity) -> str:
        """Generate recommendation for bottleneck resolution."""
        if severity == BottleneckSeverity.CRITICAL:
            return f"Immediate intervention needed at '{stage_name}': add reviewer capacity or automate"
        elif severity == BottleneckSeverity.HIGH:
            return f"Review '{stage_name}' workflow: consider parallel review or SLA adjustment"
        return f"Monitor '{stage_name}' — consider minor optimization"

    def predict_approval_delay(self, stage_name: str, current_load: int) -> ApprovalDelayPrediction:
        """Predict how long an approval will take based on historical data."""
        relevant = [r for r in self._stage_history if r["stage_name"] == stage_name]
        if not relevant:
            return ApprovalDelayPrediction(
                stage_name=stage_name,
                predicted_hours=8.0,
                confidence=0.5,
                risk_factors=["Insufficient historical data"],
                recommended_action="Monitor first few approvals to establish baseline",
            )

        avg_hours = sum(r["actual_hours"] for r in relevant) / len(relevant)
        breach_rate = sum(1 for r in relevant if r["breached"]) / len(relevant)

        # Adjust for current load
        load_factor = 1.0 + (current_load * 0.1)
        predicted = avg_hours * load_factor

        risk_factors = []
        if breach_rate > 0.2:
            risk_factors.append(f"Historical breach rate: {breach_rate:.0%}")
        if current_load > 5:
            risk_factors.append(f"Reviewer currently handling {current_load} items")

        return ApprovalDelayPrediction(
            stage_name=stage_name,
            predicted_hours=round(predicted, 1),
            confidence=round(0.9 - (breach_rate * 0.3), 2),
            risk_factors=risk_factors,
            recommended_action="Add backup reviewer" if predicted > 24 else "Monitor normally",
        )

    def predict_reviewer_overload(self, reviewer_id: str, current_load: int, max_capacity: int, trend_7d: int = 0) -> ReviewerOverloadPrediction:
        """Predict if a reviewer is heading toward overload."""
        predicted_load = current_load + trend_7d
        utilization = current_load / max(max_capacity, 1)

        if utilization > 0.9 or predicted_load > max_capacity:
            risk = "high"
            recommendation = f"Immediate action: redistribute workload from {reviewer_id[:8]}"
        elif utilization > 0.7 or predicted_load > max_capacity * 0.8:
            risk = "medium"
            recommendation = f"Monitor {reviewer_id[:8]} — approaching capacity"
        else:
            risk = "low"
            recommendation = "Adequate capacity"

        return ReviewerOverloadPrediction(
            reviewer_id=reviewer_id,
            current_load=current_load,
            max_capacity=max_capacity,
            predicted_load_7d=predicted_load,
            overload_risk=risk,
            recommendation=recommendation,
        )

    def forecast_sla_breach(self, elapsed_hours: float, sla_hours: int, stage_name: str) -> dict[str, Any]:
        """Forecast whether a workflow stage will breach its SLA."""
        remaining = sla_hours - elapsed_hours
        progress_pct = (elapsed_hours / sla_hours) * 100

        if remaining <= 0:
            return {"stage": stage_name, "breach": True, "status": "breached", "severity": "critical"}
        elif remaining <= sla_hours * 0.1:
            return {"stage": stage_name, "breach": True, "status": "at_risk", "severity": "high"}
        elif remaining <= sla_hours * 0.25:
            return {"stage": stage_name, "breach": False, "status": "warning", "severity": "medium"}
        else:
            return {"stage": stage_name, "breach": False, "status": "on_track", "severity": "low"}

    def get_intelligence_summary(self) -> dict[str, Any]:
        """Get workflow intelligence summary."""
        bottlenecks = self.detect_bottlenecks()
        return {
            "total_stages_tracked": len(set(r["stage_name"] for r in self._stage_history)),
            "total_completions": len(self._stage_history),
            "bottlenecks": [
                {"stage": b.stage_name, "severity": b.severity.value, "avg_hours": b.avg_completion_hours, "breach_rate": b.breach_rate}
                for b in bottlenecks
            ],
            "critical_bottlenecks": sum(1 for b in bottlenecks if b.severity == BottleneckSeverity.CRITICAL),
        }


# ── Global singleton ───────────────────────────────────────────────

workflow_intelligence = WorkflowIntelligenceService()
