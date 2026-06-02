"""Executive Command Center — portfolio risk heatmaps, vendor concentration, renewal timelines, bottleneck maps, SLA dashboards, AI trust metrics, ROI visualization.

Executives need visibility, forecasting, prioritization, and risk posture — not raw findings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PortfolioRiskHeatmap:
    """Heatmap data for portfolio risk visualization."""
    segments: list[dict[str, Any]] = field(default_factory=list)
    overall_risk: float = 0.0
    total_contracts: int = 0
    high_risk_count: int = 0
    critical_risk_count: int = 0


@dataclass
class VendorConcentrationMap:
    """Vendor concentration visualization data."""
    vendors: list[dict[str, Any]] = field(default_factory=list)
    concentration_score: float = 0.0
    top_vendor_pct: float = 0.0
    recommendation: str = ""


@dataclass
class RenewalTimeline:
    """Renewal timeline visualization data."""
    renewals: list[dict[str, Any]] = field(default_factory=list)
    imminent_count: int = 0
    at_risk_count: int = 0
    total_value_at_risk: float = 0.0


@dataclass
class ExecutiveDashboard:
    """Complete executive dashboard with all visualizations."""
    risk_heatmap: PortfolioRiskHeatmap = field(default_factory=PortfolioRiskHeatmap)
    vendor_concentration: VendorConcentrationMap = field(default_factory=VendorConcentrationMap)
    renewal_timeline: RenewalTimeline = field(default_factory=RenewalTimeline)
    bottlenecks: list[dict[str, Any]] = field(default_factory=list)
    sla_dashboard: dict[str, Any] = field(default_factory=dict)
    ai_trust_metrics: dict[str, Any] = field(default_factory=dict)
    roi_visualization: dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ExecutiveCommandCenter:
    """Generates executive-level dashboards and visualizations.

    Provides:
    - Portfolio risk heatmaps by segment
    - Vendor concentration maps
    - Renewal timelines with risk indicators
    - Organizational bottleneck maps
    - SLA exposure dashboards
    - AI trust metrics with trends
    - ROI trend visualization
    """

    def build_portfolio_risk_heatmap(self, contracts: list[dict]) -> PortfolioRiskHeatmap:
        """Build portfolio risk heatmap from contract data."""
        segments: dict[str, list[float]] = {}
        total = len(contracts)
        high_risk = 0
        critical_risk = 0

        for c in contracts:
            segment = c.get("segment", "Uncategorized")
            risk = c.get("risk_score", 0.5)
            if segment not in segments:
                segments[segment] = []
            segments[segment].append(risk)
            if risk > 0.7:
                high_risk += 1
            if risk > 0.9:
                critical_risk += 1

        segment_data = []
        for seg_name, risks in segments.items():
            avg_risk = sum(risks) / len(risks)
            segment_data.append({
                "name": seg_name,
                "count": len(risks),
                "avg_risk": round(avg_risk, 4),
                "max_risk": round(max(risks), 4),
                "risk_level": "critical" if avg_risk > 0.7 else "high" if avg_risk > 0.5 else "medium" if avg_risk > 0.3 else "low",
            })

        overall = sum(c.get("risk_score", 0.5) for c in contracts) / max(total, 1)

        return PortfolioRiskHeatmap(
            segments=sorted(segment_data, key=lambda s: s["avg_risk"], reverse=True),
            overall_risk=round(overall, 4),
            total_contracts=total,
            high_risk_count=high_risk,
            critical_risk_count=critical_risk,
        )

    def build_vendor_concentration_map(self, vendor_contracts: dict[str, list[dict]]) -> VendorConcentrationMap:
        """Build vendor concentration visualization."""
        vendors = []
        total_value = 0

        for vendor_name, contracts in vendor_contracts.items():
            count = len(contracts)
            value = sum(c.get("value", 0) for c in contracts)
            avg_risk = sum(c.get("risk_score", 0.5) for c in contracts) / max(count, 1)
            total_value += value
            vendors.append({
                "name": vendor_name,
                "contract_count": count,
                "total_value": value,
                "avg_risk": round(avg_risk, 4),
                "pct_of_portfolio": 0.0,  # Calculated below
            })

        # Calculate percentages
        for v in vendors:
            v["pct_of_portfolio"] = round(v["total_value"] / max(total_value, 1) * 100, 1)

        vendors.sort(key=lambda v: v["total_value"], reverse=True)
        top_pct = vendors[0]["pct_of_portfolio"] if vendors else 0

        concentration = top_pct / 100
        recommendation = "Healthy diversification" if concentration < 0.3 else \
                         "Monitor concentration" if concentration < 0.5 else \
                         "Critical: diversify top vendor"

        return VendorConcentrationMap(
            vendors=vendors,
            concentration_score=round(concentration, 4),
            top_vendor_pct=top_pct,
            recommendation=recommendation,
        )

    def build_renewal_timeline(self, renewals: list[dict]) -> RenewalTimeline:
        """Build renewal timeline with risk indicators."""
        now = datetime.utcnow()
        timeline = []
        imminent = 0
        at_risk = 0
        value_at_risk = 0.0

        for r in renewals:
            try:
                renewal_date = datetime.fromisoformat(r.get("renewal_date", "").replace("Z", "+00:00"))
                days_until = (renewal_date - now).days
            except (ValueError, TypeError):
                days_until = 365

            risk = r.get("risk_score", 0.5)
            value = r.get("value", 0)

            if days_until <= 30:
                imminent += 1
            if risk > 0.6:
                at_risk += 1
                value_at_risk += value

            timeline.append({
                "contract_id": r.get("contract_id", "")[:8],
                "contract_name": r.get("contract_name", "Unknown"),
                "counterparty": r.get("counterparty", ""),
                "days_until_renewal": days_until,
                "risk_score": risk,
                "value": value,
                "needs_attention": days_until <= 60 or risk > 0.6,
            })

        return RenewalTimeline(
            renewals=sorted(timeline, key=lambda t: t["days_until_renewal"]),
            imminent_count=imminent,
            at_risk_count=at_risk,
            total_value_at_risk=value_at_risk,
        )

    def build_ai_trust_metrics(self, execution_history: list[dict]) -> dict[str, Any]:
        """Build AI trust metrics with trends."""
        total = len(execution_history)
        if total == 0:
            return {"trust_score": 0.85, "trend": "stable", "total_executions": 0}

        accepted = sum(1 for e in execution_history if e.get("reviewer_action") == "accepted")
        rejected = sum(1 for e in execution_history if e.get("reviewer_action") == "rejected")
        acceptance_rate = accepted / max(total, 1)

        drift_scores = [e.get("drift_score", 0) for e in execution_history if "drift_score" in e]
        avg_drift = sum(drift_scores) / max(len(drift_scores), 1) if drift_scores else 0

        trust_score = acceptance_rate * 0.6 + (1.0 - avg_drift) * 0.4
        trust_score = max(0.0, min(1.0, trust_score))

        return {
            "trust_score": round(trust_score, 4),
            "acceptance_rate": round(acceptance_rate, 4),
            "avg_drift_score": round(avg_drift, 4),
            "total_executions": total,
            "accepted": accepted,
            "rejected": rejected,
            "trend": "improving" if trust_score > 0.85 else "stable" if trust_score > 0.7 else "declining",
        }

    def build_full_dashboard(self, data: dict[str, Any]) -> ExecutiveDashboard:
        """Build complete executive dashboard from all data sources."""
        return ExecutiveDashboard(
            risk_heatmap=self.build_portfolio_risk_heatmap(data.get("contracts", [])),
            vendor_concentration=self.build_vendor_concentration_map(data.get("vendor_contracts", {})),
            renewal_timeline=self.build_renewal_timeline(data.get("renewals", [])),
            bottlenecks=data.get("bottlenecks", []),
            sla_dashboard=data.get("sla_metrics", {}),
            ai_trust_metrics=self.build_ai_trust_metrics(data.get("execution_history", [])),
            roi_visualization=data.get("roi_metrics", {}),
        )


# ── Global singleton ───────────────────────────────────────────────

executive_command_center = ExecutiveCommandCenter()
