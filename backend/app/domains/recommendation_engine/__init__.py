"""Recommendation Orchestration — prioritized action plans, workflow optimization, escalation, vendor negotiation, renewal strategy, staffing.

Turns intelligence into prioritized operational actions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RecommendationPriority(str, Enum):
    CRITICAL = "critical"  # Act within 24 hours
    HIGH = "high"          # Act within 1 week
    MEDIUM = "medium"      # Act within 1 month
    LOW = "low"            # Act within 1 quarter


class RecommendationCategory(str, Enum):
    WORKFLOW = "workflow"
    VENDOR = "vendor"
    RENEWAL = "renewal"
    COMPLIANCE = "compliance"
    STAFFING = "staffing"
    NEGOTIATION = "negotiation"
    OPTIMIZATION = "optimization"
    RISK = "risk"


@dataclass
class ActionableRecommendation:
    """A single actionable recommendation with context and expected impact."""
    recommendation_id: str
    priority: RecommendationPriority
    category: RecommendationCategory
    title: str
    description: str
    expected_impact: str = ""
    effort_hours: int = 0
    roi_estimate: float = 0.0
    source_data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ActionPlan:
    """A prioritized action plan with grouped recommendations."""
    plan_id: str
    title: str
    summary: str
    recommendations: list[ActionableRecommendation] = field(default_factory=list)
    total_roi_estimate: float = 0.0
    total_effort_hours: int = 0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class RecommendationEngine:
    """Orchestrates intelligence into prioritized, actionable recommendations.

    Generates:
    - Workflow optimization recommendations (bottleneck resolution)
    - Escalation recommendations (when to escalate)
    - Vendor negotiation recommendations (when and how to negotiate)
    - Renewal strategy recommendations (optimize renewal timing)
    - Staffing recommendations (capacity planning)
    - Compliance remediation recommendations
    """

    def generate_workflow_recommendations(self, bottlenecks: list[dict]) -> list[ActionableRecommendation]:
        """Generate recommendations from workflow bottlenecks."""
        recs = []
        for b in bottlenecks:
            severity = b.get("severity", "medium")
            priority = RecommendationPriority.CRITICAL if severity == "critical" else \
                       RecommendationPriority.HIGH if severity == "high" else \
                       RecommendationPriority.MEDIUM

            recs.append(ActionableRecommendation(
                recommendation_id=f"wf_opt_{b.get('stage', 'unknown')}",
                priority=priority,
                category=RecommendationCategory.WORKFLOW,
                title=f"Optimize '{b.get('stage', 'unknown')}' workflow stage",
                description=b.get("recommendation", f"Bottleneck at {b.get('stage', 'unknown')} stage"),
                expected_impact=f"Reduce cycle time by up to {b.get('avg_completion_hours', 0):.0f}h",
                effort_hours=8 if severity == "low" else 16,
                roi_estimate=b.get("breach_rate", 0) * 50000,
                source_data=b,
            ))
        return recs

    def generate_vendor_recommendations(self, vendor_risks: list[dict]) -> list[ActionableRecommendation]:
        """Generate recommendations from vendor risk analysis."""
        recs = []
        for v in vendor_risks:
            risk_score = v.get("risk_score", 0.5)
            priority = RecommendationPriority.CRITICAL if risk_score > 0.7 else \
                       RecommendationPriority.HIGH if risk_score > 0.5 else \
                       RecommendationPriority.MEDIUM

            recs.append(ActionableRecommendation(
                recommendation_id=f"vendor_{v.get('vendor_name', 'unknown')}",
                priority=priority,
                category=RecommendationCategory.VENDOR,
                title=f"Review {v.get('vendor_name', 'unknown')} concentration risk",
                description=f"{v.get('contract_count', 0)} contracts, score: {risk_score:.2f}",
                expected_impact=f"Reduce vendor concentration risk by diversifying",
                effort_hours=40,
                roi_estimate=risk_score * 100000,
                source_data=v,
            ))
        return recs

    def generate_renewal_recommendations(self, renewals: list[dict]) -> list[ActionableRecommendation]:
        """Generate recommendations from renewal forecasting."""
        recs = []
        for r in renewals:
            days_until = r.get("days_until_renewal", 365)
            risk = r.get("risk_score", 0.5)

            if days_until <= 30:
                priority = RecommendationPriority.CRITICAL
            elif days_until <= 60:
                priority = RecommendationPriority.HIGH
            elif risk > 0.6:
                priority = RecommendationPriority.HIGH
            else:
                priority = RecommendationPriority.MEDIUM

            recs.append(ActionableRecommendation(
                recommendation_id=f"renewal_{r.get('contract_id', 'unknown')[:8]}",
                priority=priority,
                category=RecommendationCategory.RENEWAL,
                title=f"Prepare {r.get('contract_name', 'Unknown')} renewal strategy",
                description=f"Renewal in {days_until} days, risk score: {risk:.2f}",
                expected_impact=f"Secure favorable renewal terms, avoid auto-renewal",
                effort_hours=8 if days_until > 60 else 24,
                roi_estimate=risk * 50000,
                source_data=r,
            ))
        return recs

    def generate_staffing_recommendations(self, overload_predictions: list[dict]) -> list[ActionableRecommendation]:
        """Generate staffing/capacity recommendations."""
        recs = []
        for p in overload_predictions:
            risk = p.get("overload_risk", "low")
            priority = RecommendationPriority.CRITICAL if risk == "high" else \
                       RecommendationPriority.HIGH if risk == "medium" else \
                       RecommendationPriority.LOW

            recs.append(ActionableRecommendation(
                recommendation_id=f"staff_{p.get('reviewer_id', 'unknown')[:8]}",
                priority=priority,
                category=RecommendationCategory.STAFFING,
                title=f"Reviewer {p.get('reviewer_id', 'unknown')[:8]} approaching capacity",
                description=p.get("recommendation", "Reviewer may be overloaded"),
                expected_impact="Prevent SLA breaches from reviewer overload",
                effort_hours=4,
                roi_estimate=5000,
                source_data=p,
            ))
        return recs

    def create_action_plan(self, all_recs: list[ActionableRecommendation]) -> ActionPlan:
        """Create a prioritized action plan from recommendations."""
        critical = [r for r in all_recs if r.priority == RecommendationPriority.CRITICAL]
        high = [r for r in all_recs if r.priority == RecommendationPriority.HIGH]
        medium = [r for r in all_recs if r.priority == RecommendationPriority.MEDIUM]
        low = [r for r in all_recs if r.priority == RecommendationPriority.LOW]

        sorted_recs = critical + high + medium + low
        total_roi = sum(r.roi_estimate for r in sorted_recs)
        total_effort = sum(r.effort_hours for r in sorted_recs)

        import uuid
        return ActionPlan(
            plan_id=str(uuid.uuid4()),
            title="Enterprise Intelligence Action Plan",
            summary=f"{len(critical)} critical, {len(high)} high, {len(medium)} medium, {len(low)} low priority actions — ${total_roi:,.0f} estimated ROI",
            recommendations=sorted_recs,
            total_roi_estimate=total_roi,
            total_effort_hours=total_effort,
        )


# ── Global singleton ───────────────────────────────────────────────

recommendation_engine = RecommendationEngine()
