"""Enterprise Strategy Engine — vendor portfolio optimization, renewal strategy sequencing, risk reduction roadmaps, staffing optimization, compliance prioritization, negotiation sequencing.

Moves the platform into executive operational strategy infrastructure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StrategyHorizon(str, Enum):
    IMMEDIATE = "immediate"       # 0-30 days
    SHORT_TERM = "short_term"     # 30-90 days
    MEDIUM_TERM = "medium_term"   # 90-180 days
    LONG_TERM = "long_term"       # 180+ days


@dataclass
class StrategicInitiative:
    """A strategic initiative with timeline and expected impact."""
    initiative_id: str
    domain: str
    title: str
    description: str
    horizon: StrategyHorizon
    priority: int  # 1 (highest) to 10
    expected_roi: float = 0.0
    effort_hours: int = 0
    dependencies: list[str] = field(default_factory=list)
    status: str = "proposed"  # proposed, active, completed, blocked


@dataclass
class EnterpriseRoadmap:
    """A complete enterprise strategy roadmap."""
    roadmap_id: str
    title: str
    summary: str
    initiatives: list[StrategicInitiative] = field(default_factory=list)
    total_roi: float = 0.0
    total_effort_hours: int = 0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class StrategyEngineService:
    """Enterprise strategy engine — executive operational strategy infrastructure.

    Capabilities:
    - Vendor portfolio optimization (which vendors to prioritize, diversify, or replace)
    - Renewal strategy sequencing (optimal order for renewals)
    - Risk reduction roadmaps (step-by-step risk mitigation)
    - Staffing optimization (optimal team structure)
    - Compliance prioritization (which compliance gaps to fix first)
    - Negotiation sequencing (optimal order for negotiations)
    """

    def optimize_vendor_portfolio(self, vendors: list[dict]) -> list[StrategicInitiative]:
        """Generate vendor portfolio optimization initiatives."""
        initiatives = []
        high_risk = [v for v in vendors if v.get("risk_score", 0) > 0.6]
        high_concentration = [v for v in vendors if v.get("portfolio_pct", 0) > 30]

        if high_concentration:
            for v in high_concentration:
                initiatives.append(StrategicInitiative(
                    initiative_id=f"vendor_div_{v.get('name', 'unknown')[:8]}",
                    domain="vendor_portfolio",
                    title=f"Diversify {v.get('name', 'unknown')} concentration ({v.get('portfolio_pct', 0):.0f}% of portfolio)",
                    description=f"Reduce {v.get('name', 'unknown')} concentration from {v.get('portfolio_pct', 0):.0f}% to below 25%",
                    horizon=StrategyHorizon.MEDIUM_TERM,
                    priority=2,
                    expected_roi=v.get("total_value", 0) * 0.05,
                    effort_hours=80,
                ))

        if high_risk:
            initiatives.append(StrategicInitiative(
                initiative_id="vendor_risk_review",
                domain="vendor_portfolio",
                title=f"Review {len(high_risk)} High-Risk Vendor Relationships",
                description=f"Complete risk assessment for {len(high_risk)} vendors with risk score > 0.6",
                horizon=StrategyHorizon.SHORT_TERM,
                priority=1,
                expected_roi=sum(v.get("total_value", 0) * 0.1 for v in high_risk),
                effort_hours=40 * len(high_risk),
            ))

        return initiatives

    def sequence_renewals(self, renewals: list[dict]) -> list[StrategicInitiative]:
        """Generate optimal renewal sequencing initiatives."""
        initiatives = []
        now = datetime.utcnow()

        urgent = [r for r in renewals if r.get("days_until_renewal", 365) <= 30]
        high_value = [r for r in renewals if (r.get("value", 0) or 0) > 100000]
        high_risk = [r for r in renewals if (r.get("risk_score", 0) or 0) > 0.6]

        if urgent:
            initiatives.append(StrategicInitiative(
                initiative_id="renewal_urgent",
                domain="renewal_strategy",
                title=f"Complete {len(urgent)} Urgent Renewals",
                description=f"{len(urgent)} contracts renewing within 30 days — prioritize immediate action",
                horizon=StrategyHorizon.IMMEDIATE,
                priority=1,
                expected_roi=sum(r.get("value", 0) * 0.15 for r in urgent),
                effort_hours=20 * len(urgent),
            ))

        if high_value and not urgent:
            initiatives.append(StrategicInitiative(
                initiative_id="renewal_high_value",
                domain="renewal_strategy",
                title=f"Prepare {len(high_value)} High-Value Renewal Strategies",
                description=f"Develop negotiation strategies for {len(high_value)} contracts with value > $100K",
                horizon=StrategyHorizon.SHORT_TERM,
                priority=3,
                expected_roi=sum(r.get("value", 0) * 0.1 for r in high_value),
                effort_hours=16 * len(high_value),
            ))

        return initiatives

    def build_risk_reduction_roadmap(self, risks: list[dict]) -> list[StrategicInitiative]:
        """Generate a step-by-step risk reduction roadmap."""
        initiatives = []
        critical = [r for r in risks if r.get("severity") == "critical"]
        high = [r for r in risks if r.get("severity") == "high"]

        if critical:
            initiatives.append(StrategicInitiative(
                initiative_id="risk_critical",
                domain="risk_reduction",
                title=f"Remediate {len(critical)} Critical Risks",
                description=f"Immediate action required for {len(critical)} critical-risk items",
                horizon=StrategyHorizon.IMMEDIATE,
                priority=1,
                expected_roi=sum(r.get("potential_loss", 100000) for r in critical),
                effort_hours=40 * len(critical),
            ))

        if high:
            initiatives.append(StrategicInitiative(
                initiative_id="risk_high",
                domain="risk_reduction",
                title=f"Address {len(high)} High-Risk Items",
                description=f"Schedule remediation for {len(high)} high-risk items within 90 days",
                horizon=StrategyHorizon.SHORT_TERM,
                priority=4,
                expected_roi=sum(r.get("potential_loss", 50000) for r in high),
                effort_hours=20 * len(high),
            ))

        return initiatives

    def generate_enterprise_roadmap(self, data: dict[str, Any]) -> EnterpriseRoadmap:
        """Generate a complete enterprise strategy roadmap."""
        all_initiatives = []
        all_initiatives.extend(self.optimize_vendor_portfolio(data.get("vendors", [])))
        all_initiatives.extend(self.sequence_renewals(data.get("renewals", [])))
        all_initiatives.extend(self.build_risk_reduction_roadmap(data.get("risks", [])))

        all_initiatives.sort(key=lambda i: (i.priority, list(StrategyHorizon).index(i.horizon)))

        import uuid
        return EnterpriseRoadmap(
            roadmap_id=str(uuid.uuid4()),
            title="Enterprise Strategy Roadmap",
            summary=f"{len(all_initiatives)} strategic initiatives across vendor, renewal, and risk domains",
            initiatives=all_initiatives,
            total_roi=sum(i.expected_roi for i in all_initiatives),
            total_effort_hours=sum(i.effort_hours for i in all_initiatives),
        )


# ── Global singleton ───────────────────────────────────────────────

strategy_engine = StrategyEngineService()
