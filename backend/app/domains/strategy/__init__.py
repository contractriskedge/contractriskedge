"""Strategic Recommendation System — contract portfolio optimization, vendor diversification strategy, reviewer staffing strategy, negotiation prioritization, renewal sequencing.

Moves the platform upward into executive operations and enterprise strategy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StrategicPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class StrategicRecommendation:
    """A high-level strategic recommendation for enterprise operations."""
    recommendation_id: str
    domain: str  # portfolio, vendor, staffing, negotiation, renewal, compliance
    priority: StrategicPriority
    title: str
    description: str
    expected_impact: str = ""
    effort_level: str = "medium"  # low, medium, high
    roi_estimate: float = 0.0
    time_horizon: str = "short_term"  # short_term, medium_term, long_term
    dependencies: list[str] = field(default_factory=list)


@dataclass
class StrategicPlan:
    """A complete strategic plan with prioritized recommendations."""
    plan_id: str
    title: str
    summary: str
    recommendations: list[StrategicRecommendation] = field(default_factory=list)
    total_roi: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class StrategyService:
    """Strategic recommendation system — enterprise strategy orchestration.

    Capabilities:
    - Contract portfolio optimization (which contracts to prioritize)
    - Vendor diversification strategy (how to reduce concentration)
    - Reviewer staffing strategy (optimal team composition)
    - Negotiation prioritization (which negotiations to prioritize)
    - Renewal sequencing (optimal order for renewals)
    - Compliance remediation prioritization (which gaps to fix first)
    """

    def optimize_portfolio(self, contracts: list[dict]) -> list[StrategicRecommendation]:
        """Generate contract portfolio optimization recommendations."""
        recs = []

        # Find high-risk, high-value contracts
        high_priority = [c for c in contracts if (c.get("risk_score", 0) or 0) > 0.6 and (c.get("value", 0) or 0) > 100000]
        if high_priority:
            recs.append(StrategicRecommendation(
                recommendation_id="portfolio_high_risk",
                domain="portfolio",
                priority=StrategicPriority.CRITICAL,
                title=f"Review {len(high_priority)} High-Risk, High-Value Contracts",
                description=f"{len(high_priority)} contracts with risk > 0.6 and value > $100K need immediate attention",
                expected_impact="Mitigate significant financial and legal exposure",
                effort_level="high",
                roi_estimate=len(high_priority) * 50000,
                time_horizon="short_term",
            ))

        # Find contracts approaching renewal
        from datetime import datetime as dt
        approaching = [c for c in contracts if c.get("days_until_renewal", 365) <= 60]
        if approaching:
            recs.append(StrategicRecommendation(
                recommendation_id="portfolio_renewals",
                domain="portfolio",
                priority=StrategicPriority.HIGH,
                title=f"Prepare {len(approaching)} Contracts for Renewal",
                description=f"{len(approaching)} contracts renewing within 60 days",
                expected_impact="Secure favorable renewal terms, prevent auto-renewal",
                effort_level="medium",
                roi_estimate=len(approaching) * 25000,
                time_horizon="short_term",
            ))

        return recs

    def optimize_vendor_diversification(self, vendor_contracts: dict[str, list[dict]]) -> list[StrategicRecommendation]:
        """Generate vendor diversification strategy recommendations."""
        recs = []
        for vendor, contracts in vendor_contracts.items():
            count = len(contracts)
            total_value = sum(c.get("value", 0) for c in contracts)
            if count >= 5 or total_value > 500000:
                recs.append(StrategicRecommendation(
                    recommendation_id=f"vendor_div_{vendor.lower().replace(' ', '_')}",
                    domain="vendor",
                    priority=StrategicPriority.HIGH if total_value > 1000000 else StrategicPriority.MEDIUM,
                    title=f"Diversify {vendor} concentration ({count} contracts, ${total_value:,.0f})",
                    description=f"Over-reliance on {vendor} creates supply chain risk",
                    expected_impact="Reduce single-vendor failure impact by 60%",
                    effort_level="high",
                    roi_estimate=min(total_value * 0.1, 500000),
                    time_horizon="medium_term",
                    dependencies=["vendor_discovery", "contract_migration"],
                ))
        return recs

    def optimize_staffing(self, reviewer_workloads: list[dict]) -> list[StrategicRecommendation]:
        """Generate reviewer staffing strategy recommendations."""
        recs = []
        overloaded = [r for r in reviewer_workloads if r.get("utilization", 0) > 0.8]
        if overloaded:
            recs.append(StrategicRecommendation(
                recommendation_id="staffing_overload",
                domain="staffing",
                priority=StrategicPriority.HIGH,
                title=f"Address {len(overloaded)} Overloaded Reviewers",
                description=f"{len(overloaded)} reviewers above 80% capacity — SLA risk increasing",
                expected_impact="Reduce SLA breaches by 40%, improve reviewer satisfaction",
                effort_level="medium",
                roi_estimate=len(overloaded) * 25000,
                time_horizon="short_term",
                dependencies=["hiring", "workload_redistribution"],
            ))

        underloaded = [r for r in reviewer_workloads if r.get("utilization", 0) < 0.3]
        if underloaded and overloaded:
            recs.append(StrategicRecommendation(
                recommendation_id="staffing_rebalance",
                domain="staffing",
                priority=StrategicPriority.MEDIUM,
                title="Rebalance Reviewer Workload",
                description=f"Move work from {len(overloaded)} overloaded to {len(underloaded)} underloaded reviewers",
                expected_impact="Immediate SLA improvement without hiring",
                effort_level="low",
                roi_estimate=10000,
                time_horizon="short_term",
            ))

        return recs

    def prioritize_negotiations(self, negotiations: list[dict]) -> list[StrategicRecommendation]:
        """Generate negotiation prioritization recommendations."""
        recs = []
        urgent = [n for n in negotiations if n.get("days_until_deadline", 365) <= 30 and (n.get("value", 0) or 0) > 50000]
        if urgent:
            recs.append(StrategicRecommendation(
                recommendation_id="neg_urgent",
                domain="negotiation",
                priority=StrategicPriority.CRITICAL,
                title=f"Prioritize {len(urgent)} Urgent Negotiations",
                description=f"{len(urgent)} negotiations with >$50K value expiring within 30 days",
                expected_impact="Capture $X in value before deadline",
                effort_level="high",
                roi_estimate=sum(n.get("value", 0) * 0.1 for n in urgent),
                time_horizon="short_term",
            ))
        return recs

    def generate_strategic_plan(self, data: dict[str, Any]) -> StrategicPlan:
        """Generate a complete strategic plan from all data sources."""
        all_recs = []
        all_recs.extend(self.optimize_portfolio(data.get("contracts", [])))
        all_recs.extend(self.optimize_vendor_diversification(data.get("vendor_contracts", {})))
        all_recs.extend(self.optimize_staffing(data.get("reviewer_workloads", [])))
        all_recs.extend(self.prioritize_negotiations(data.get("negotiations", [])))

        critical = [r for r in all_recs if r.priority == StrategicPriority.CRITICAL]
        total_roi = sum(r.roi_estimate for r in all_recs)

        import uuid
        return StrategicPlan(
            plan_id=str(uuid.uuid4()),
            title="Enterprise Strategic Operations Plan",
            summary=f"{len(critical)} critical actions, {len(all_recs)} total recommendations, ${total_roi:,.0f} estimated ROI",
            recommendations=all_recs,
            total_roi=total_roi,
        )


# ── Global singleton ───────────────────────────────────────────────

strategy_service = StrategyService()
