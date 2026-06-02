"""Predictive Enterprise Operations — SLA breach, approval bottleneck, negotiation failure, compliance exposure, reviewer burnout, vendor instability, renewal risk forecasting.

Moving from reactive intelligence to predictive operational intelligence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """A single prediction with confidence and time horizon."""
    prediction_id: str
    metric: str
    predicted_value: float
    confidence: float  # 0.0-1.0
    time_horizon_days: int
    risk_factors: list[str] = field(default_factory=list)
    recommended_action: str = ""


@dataclass
class PredictiveService:
    """Predictive enterprise operations — forecasts operational outcomes before they occur.

    Predictions:
    - SLA breach prediction (will this workflow breach SLA?)
    - Approval bottleneck forecasting (where will approvals get stuck?)
    - Negotiation failure forecasting (will this negotiation fail?)
    - Compliance exposure forecasting (will compliance gaps emerge?)
    - Reviewer burnout forecasting (is a reviewer heading for burnout?)
    - Vendor instability forecasting (is a vendor becoming unstable?)
    - Renewal risk forecasting (will renewal be unfavorable?)
    """

    _prediction_history: list[Prediction] = field(default_factory=list)

    def predict_sla_breach(self, workflow_data: dict) -> Prediction:
        """Predict if a workflow will breach its SLA."""
        elapsed_pct = workflow_data.get("elapsed_sla_pct", 0)
        complexity = workflow_data.get("complexity", 0.5)
        reviewer_load = workflow_data.get("reviewer_load", 0.5)
        stage_count = workflow_data.get("remaining_stages", 3)

        risk_score = (elapsed_pct * 0.3 + complexity * 0.25 + reviewer_load * 0.25 + min(1.0, stage_count * 0.1) * 0.2)
        will_breach = risk_score > 0.6

        risk_factors = []
        if elapsed_pct > 70:
            risk_factors.append(f"{elapsed_pct:.0f}% of SLA already elapsed")
        if reviewer_load > 0.7:
            risk_factors.append("Reviewer near capacity")
        if stage_count > 3:
            risk_factors.append(f"{stage_count} stages remaining")

        return Prediction(
            prediction_id=f"sla_{workflow_data.get('workflow_id', 'unknown')[:8]}_{datetime.utcnow().timestamp()}",
            metric="sla_breach",
            predicted_value=1.0 if will_breach else 0.0,
            confidence=min(0.95, risk_score),
            time_horizon_days=0,
            risk_factors=risk_factors,
            recommended_action="Expedite review, add reviewer capacity" if will_breach else "On track — monitor normally",
        )

    def predict_approval_bottleneck(self, approval_data: dict) -> Prediction:
        """Predict if an approval will become a bottleneck."""
        required_approvers = approval_data.get("required_approvers", 1)
        available_approvers = approval_data.get("available_approvers", 1)
        avg_approval_time = approval_data.get("avg_approval_hours", 24)
        sla_remaining = approval_data.get("sla_remaining_hours", 48)

        approver_shortage = max(0, required_approvers - available_approvers)
        time_risk = avg_approval_time / max(sla_remaining, 1)
        bottleneck_risk = min(1.0, approver_shortage * 0.4 + time_risk * 0.6)

        risk_factors = []
        if approver_shortage > 0:
            risk_factors.append(f"Need {required_approvers} approvers, {available_approvers} available")
        if time_risk > 0.7:
            risk_factors.append(f"Avg approval time ({avg_approval_time}h) consumes {time_risk:.0%} of SLA")

        return Prediction(
            prediction_id=f"bn_{approval_data.get('approval_id', 'unknown')[:8]}_{datetime.utcnow().timestamp()}",
            metric="approval_bottleneck",
            predicted_value=round(bottleneck_risk, 4),
            confidence=min(0.9, bottleneck_risk + 0.1),
            time_horizon_days=1,
            risk_factors=risk_factors,
            recommended_action="Add backup approvers" if bottleneck_risk > 0.5 else "Adequate coverage",
        )

    def predict_negotiation_failure(self, negotiation_data: dict) -> Prediction:
        """Predict if a negotiation will fail."""
        historical_success = negotiation_data.get("historical_success_rate", 0.7)
        counterparty_risk = negotiation_data.get("counterparty_risk", 0.3)
        complexity = negotiation_data.get("complexity", 0.5)
        concession_gap = negotiation_data.get("concession_gap", 0.3)

        failure_risk = (1.0 - historical_success) * 0.3 + counterparty_risk * 0.25 + complexity * 0.25 + concession_gap * 0.2

        risk_factors = []
        if counterparty_risk > 0.6:
            risk_factors.append("High-risk counterparty")
        if concession_gap > 0.5:
            risk_factors.append("Significant concession gap")
        if historical_success < 0.5:
            risk_factors.append("Low historical success rate for this type")

        return Prediction(
            prediction_id=f"neg_{negotiation_data.get('negotiation_id', 'unknown')[:8]}_{datetime.utcnow().timestamp()}",
            metric="negotiation_failure",
            predicted_value=round(failure_risk, 4),
            confidence=min(0.85, 1.0 - historical_success + 0.2),
            time_horizon_days=30,
            risk_factors=risk_factors,
            recommended_action="Engage executive sponsor, prepare fallback positions" if failure_risk > 0.5 else "Standard approach likely sufficient",
        )

    def predict_reviewer_burnout(self, reviewer_data: dict) -> Prediction:
        """Predict if a reviewer is heading for burnout."""
        current_load = reviewer_data.get("current_reviews", 0)
        max_capacity = reviewer_data.get("max_capacity", 10)
        trend_7d = reviewer_data.get("trend_7d", 0)
        avg_hours = reviewer_data.get("avg_review_hours", 4)
        sla_breaches = reviewer_data.get("sla_breaches_30d", 0)

        utilization = current_load / max(max_capacity, 1)
        growth_risk = min(1.0, trend_7d / max_capacity * 2)
        quality_risk = min(1.0, sla_breaches / 10)

        burnout_risk = utilization * 0.4 + growth_risk * 0.3 + quality_risk * 0.3

        risk_factors = []
        if utilization > 0.8:
            risk_factors.append(f"At {utilization:.0%} capacity")
        if trend_7d > 0:
            risk_factors.append(f"Load growing by {trend_7d}/week")
        if sla_breaches > 3:
            risk_factors.append(f"{sla_breaches} SLA breaches in 30 days")

        return Prediction(
            prediction_id=f"bo_{reviewer_data.get('reviewer_id', 'unknown')[:8]}_{datetime.utcnow().timestamp()}",
            metric="reviewer_burnout",
            predicted_value=round(burnout_risk, 4),
            confidence=min(0.9, burnout_risk + 0.15),
            time_horizon_days=14,
            risk_factors=risk_factors,
            recommended_action="Reduce workload, add backup reviewer" if burnout_risk > 0.6 else "Monitor workload trend",
        )

    def predict_renewal_risk(self, renewal_data: dict) -> Prediction:
        """Predict renewal risk."""
        current_risk = renewal_data.get("current_risk_score", 0.5)
        days_until = renewal_data.get("days_until_renewal", 365)
        negotiation_history = renewal_data.get("negotiation_history_score", 0.5)
        market_volatility = renewal_data.get("market_volatility", 0.3)

        time_risk = max(0, 1.0 - days_until / 90) if days_until < 90 else 0
        risk_score = current_risk * 0.3 + time_risk * 0.25 + (1.0 - negotiation_history) * 0.25 + market_volatility * 0.2

        risk_factors = []
        if days_until < 30:
            risk_factors.append(f"Only {days_until} days until renewal")
        if current_risk > 0.6:
            risk_factors.append(f"Current risk score: {current_risk:.2f}")
        if negotiation_history < 0.4:
            risk_factors.append("Poor negotiation history")

        return Prediction(
            prediction_id=f"ren_{renewal_data.get('contract_id', 'unknown')[:8]}_{datetime.utcnow().timestamp()}",
            metric="renewal_risk",
            predicted_value=round(risk_score, 4),
            confidence=min(0.85, 1.0 - days_until / 365 + 0.3),
            time_horizon_days=days_until,
            risk_factors=risk_factors,
            recommended_action="Begin renewal negotiation immediately" if risk_score > 0.6 else "Standard renewal process",
        )

    def get_prediction_summary(self) -> dict[str, Any]:
        """Get summary of all predictions."""
        return {
            "total_predictions": len(self._prediction_history),
            "high_confidence": sum(1 for p in self._prediction_history if p.confidence > 0.8),
            "critical_predictions": sum(1 for p in self._prediction_history if p.predicted_value > 0.7),
            "recent": [
                {"metric": p.metric, "value": p.predicted_value, "confidence": p.confidence, "action": p.recommended_action}
                for p in self._prediction_history[-10:]
            ],
        }


# ── Global singleton ───────────────────────────────────────────────

predictive_service = PredictiveService()
