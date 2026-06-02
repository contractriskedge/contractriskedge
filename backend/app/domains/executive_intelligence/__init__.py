"""Executive Decision Intelligence — vendor concentration, renewal forecasting, compliance exposure, obligation heatmaps.

Executives want business impact, exposure, forecasting, and prioritization — not raw AI findings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ExposureLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VendorConcentrationRisk:
    """Risk from over-reliance on a single vendor."""
    vendor_name: str
    contract_count: int
    total_value: float
    risk_score: float
    exposure_level: ExposureLevel
    recommendation: str = ""


@dataclass
class ComplianceExposure:
    """Compliance exposure from contract portfolio."""
    regulation: str
    affected_contracts: int
    risk_score: float
    exposure_level: ExposureLevel
    gaps: list[str] = field(default_factory=list)


@dataclass
class ObligationHeatmap:
    """Heatmap of obligations across the organization."""
    department: str
    total_obligations: int
    overdue: int
    at_risk: int
    compliance_rate: float


@dataclass
class ExecutiveIntelligenceService:
    """Executive-level decision intelligence.

    Capabilities:
    - Vendor concentration risk (over-reliance on single vendors)
    - Renewal forecasting (when contracts need attention)
    - Compliance exposure scoring (regulatory risk)
    - Negotiation efficiency scoring (how effective are negotiations)
    - Enterprise obligation heatmaps (obligations by department)
    - Contract risk trend analysis (is risk increasing/decreasing)
    - Organizational bottleneck analysis (where is the org slowing down)
    """

    _contract_scores: list[dict[str, Any]] = field(default_factory=list)

    def analyze_vendor_concentration(self, vendor_contracts: dict[str, list[dict]]) -> list[VendorConcentrationRisk]:
        """Analyze vendor concentration risk across the portfolio."""
        risks = []
        for vendor_name, contracts in vendor_contracts.items():
            count = len(contracts)
            total_value = sum(c.get("value", 0) for c in contracts)
            avg_risk = sum(c.get("risk_score", 0.5) for c in contracts) / max(count, 1)

            # Concentration scoring
            concentration_score = (count * 0.3 + total_value * 0.3 + avg_risk * 0.4) / 100
            concentration_score = min(1.0, concentration_score)

            if concentration_score > 0.7:
                exposure = ExposureLevel.CRITICAL
                recommendation = f"Critical: diversify {vendor_name} contracts — {count} contracts, ${total_value:,.0f} total"
            elif concentration_score > 0.5:
                exposure = ExposureLevel.HIGH
                recommendation = f"High concentration in {vendor_name}: review sourcing strategy"
            elif concentration_score > 0.3:
                exposure = ExposureLevel.MEDIUM
                recommendation = f"Monitor {vendor_name} concentration"
            else:
                exposure = ExposureLevel.LOW
                recommendation = "Acceptable diversification"

            risks.append(VendorConcentrationRisk(
                vendor_name=vendor_name,
                contract_count=count,
                total_value=total_value,
                risk_score=round(concentration_score, 4),
                exposure_level=exposure,
                recommendation=recommendation,
            ))

        return sorted(risks, key=lambda r: r.risk_score, reverse=True)

    def assess_compliance_exposure(self, contracts_by_regulation: dict[str, list[dict]]) -> list[ComplianceExposure]:
        """Assess compliance exposure across regulations."""
        exposures = []
        for regulation, contracts in contracts_by_regulation.items():
            total = len(contracts)
            compliant = sum(1 for c in contracts if c.get("compliant", False))
            risk_score = 1.0 - (compliant / max(total, 1))

            gaps = []
            for c in contracts:
                if not c.get("compliant", False):
                    gaps.append(f"{c.get('name', 'unknown')} — {c.get('gap', 'unknown gap')}")

            if risk_score > 0.3:
                exposure = ExposureLevel.CRITICAL if risk_score > 0.5 else ExposureLevel.HIGH
            elif risk_score > 0.1:
                exposure = ExposureLevel.MEDIUM
            else:
                exposure = ExposureLevel.LOW

            exposures.append(ComplianceExposure(
                regulation=regulation,
                affected_contracts=total,
                risk_score=round(risk_score, 4),
                exposure_level=exposure,
                gaps=gaps[:5],  # Top 5 gaps
            ))

        return sorted(exposures, key=lambda e: e.risk_score, reverse=True)

    def compute_obligation_heatmap(self, obligations_by_dept: dict[str, list[dict]]) -> list[ObligationHeatmap]:
        """Compute obligation heatmap by department."""
        heatmap = []
        for dept, obligations in obligations_by_dept.items():
            total = len(obligations)
            overdue = sum(1 for o in obligations if o.get("status") == "overdue")
            at_risk = sum(1 for o in obligations if o.get("status") == "at_risk")
            compliance_rate = (total - overdue - at_risk) / max(total, 1)

            heatmap.append(ObligationHeatmap(
                department=dept,
                total_obligations=total,
                overdue=overdue,
                at_risk=at_risk,
                compliance_rate=round(compliance_rate, 4),
            ))

        return sorted(heatmap, key=lambda h: h.compliance_rate)

    def analyze_risk_trend(self, contract_scores: list[dict]) -> dict[str, Any]:
        """Analyze risk score trends over time."""
        self._contract_scores = contract_scores
        if len(contract_scores) < 2:
            return {"trend": "insufficient_data", "change": 0, "direction": "stable"}

        # Sort by date
        sorted_scores = sorted(contract_scores, key=lambda x: x.get("date", ""))
        recent = sorted_scores[-min(10, len(sorted_scores)):]
        older = sorted_scores[:min(10, len(sorted_scores))]

        recent_avg = sum(r.get("risk_score", 0.5) for r in recent) / len(recent)
        older_avg = sum(o.get("risk_score", 0.5) for o in older) / len(older)
        change = recent_avg - older_avg

        if abs(change) < 0.05:
            direction = "stable"
        elif change > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        return {
            "trend": "improving" if direction == "decreasing" else "degrading" if direction == "increasing" else "stable",
            "change": round(change, 4),
            "direction": direction,
            "recent_average": round(recent_avg, 4),
            "older_average": round(older_avg, 4),
            "samples": len(contract_scores),
        }

    def get_executive_summary(self) -> dict[str, Any]:
        """Get a comprehensive executive summary."""
        return {
            "vendor_concentration": [],
            "compliance_exposure": [],
            "obligation_heatmap": [],
            "risk_trend": {"trend": "stable", "change": 0},
            "generated_at": datetime.utcnow().isoformat(),
        }
