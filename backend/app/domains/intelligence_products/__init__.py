"""Enterprise Intelligence Products — Vendor Risk, Negotiation, Renewal, Compliance, Obligation, Workflow Efficiency.

Each product provides: scoring, trends, forecasting, recommendations, benchmarking, executive summaries.
These are sellable intelligence products, not just engines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IntelligenceProduct(str, Enum):
    VENDOR_RISK = "vendor_risk"
    NEGOTIATION = "negotiation"
    RENEWAL = "renewal"
    COMPLIANCE_EXPOSURE = "compliance_exposure"
    OBLIGATION = "obligation"
    WORKFLOW_EFFICIENCY = "workflow_efficiency"


@dataclass
class ProductScore:
    """A score from an intelligence product."""
    product: IntelligenceProduct
    score: float  # 0.0-1.0
    trend: str  # improving, stable, declining
    percentile: float = 0.0
    sample_size: int = 0


@dataclass
class ProductRecommendation:
    """A recommendation from an intelligence product."""
    priority: str  # critical, high, medium, low
    category: str
    title: str
    description: str
    expected_impact: str = ""
    action_url: str = ""


@dataclass
class ProductReport:
    """A complete intelligence product report."""
    product: IntelligenceProduct
    title: str
    summary: str
    score: ProductScore
    recommendations: list[ProductRecommendation] = field(default_factory=list)
    trends: list[dict[str, Any]] = field(default_factory=list)
    benchmarks: dict[str, float] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VendorRiskProduct:
    """Vendor Risk Intelligence — concentration, performance, compliance risk per vendor."""

    def assess(self, vendor_name: str, contracts: list[dict]) -> ProductReport:
        """Assess vendor risk across all contracts."""
        count = len(contracts)
        if count == 0:
            return ProductReport(
                product=IntelligenceProduct.VENDOR_RISK,
                title=f"Vendor Risk: {vendor_name}",
                summary="No contract data available",
                score=ProductScore(IntelligenceProduct.VENDOR_RISK, 0.5, "stable"),
            )

        avg_risk = sum(c.get("risk_score", 0.5) for c in contracts) / count
        total_value = sum(c.get("value", 0) for c in contracts)
        overdue_obligations = sum(1 for c in contracts if c.get("obligations_overdue", 0) > 0)

        concentration_score = min(1.0, count * 0.05 + total_value * 0.0000001)
        risk_score = (avg_risk * 0.4 + concentration_score * 0.3 + min(1.0, overdue_obligations * 0.1) * 0.3)

        recommendations = []
        if risk_score > 0.7:
            recommendations.append(ProductRecommendation(
                priority="critical", category="diversification",
                title=f"Reduce {vendor_name} concentration",
                description=f"{count} contracts, ${total_value:,.0f} total — consider diversifying",
            ))
        if overdue_obligations > 0:
            recommendations.append(ProductRecommendation(
                priority="high", category="compliance",
                title=f"Resolve {overdue_obligations} overdue obligations with {vendor_name}",
                description="Overdue obligations may create legal exposure",
            ))

        return ProductReport(
            product=IntelligenceProduct.VENDOR_RISK,
            title=f"Vendor Risk: {vendor_name}",
            summary=f"{count} contracts, avg risk {avg_risk:.2f}, ${total_value:,.0f} total exposure",
            score=ProductScore(IntelligenceProduct.VENDOR_RISK, round(risk_score, 4), "stable"),
            recommendations=recommendations,
            benchmarks={"contract_count": count, "total_value": total_value, "avg_risk": avg_risk},
        )


@dataclass
class NegotiationProduct:
    """Negotiation Intelligence — effectiveness, cycle time, concession patterns."""

    def analyze(self, negotiations: list[dict]) -> ProductReport:
        """Analyze negotiation effectiveness."""
        total = len(negotiations)
        if total == 0:
            return ProductReport(
                product=IntelligenceProduct.NEGOTIATION,
                title="Negotiation Intelligence",
                summary="No negotiation data available",
                score=ProductScore(IntelligenceProduct.NEGOTIATION, 0.5, "stable"),
            )

        successful = sum(1 for n in negotiations if n.get("outcome") == "successful")
        avg_cycle_days = sum(n.get("cycle_days", 30) for n in negotiations) / total
        avg_concessions = sum(n.get("concessions_made", 0) for n in negotiations) / total

        success_rate = successful / total
        efficiency_score = min(1.0, success_rate * 0.5 + (1.0 - min(1.0, avg_cycle_days / 90)) * 0.3 + (1.0 - min(1.0, avg_concessions / 10)) * 0.2)

        recommendations = []
        if avg_cycle_days > 60:
            recommendations.append(ProductRecommendation(
                priority="high", category="cycle_time",
                title=f"Reduce negotiation cycle ({avg_cycle_days:.0f} days avg)",
                description="Long cycles increase legal costs and delay revenue",
            ))
        if success_rate < 0.7:
            recommendations.append(ProductRecommendation(
                priority="high", category="outcomes",
                title=f"Improve negotiation success rate ({success_rate:.0%})",
                description="Review negotiation playbook and approval thresholds",
            ))

        return ProductReport(
            product=IntelligenceProduct.NEGOTIATION,
            title="Negotiation Intelligence",
            summary=f"{successful}/{total} successful, avg {avg_cycle_days:.0f} days cycle",
            score=ProductScore(IntelligenceProduct.NEGOTIATION, round(efficiency_score, 4), "stable"),
            recommendations=recommendations,
            benchmarks={"success_rate": success_rate, "avg_cycle_days": avg_cycle_days, "avg_concessions": avg_concessions},
        )


@dataclass
class RenewalProduct:
    """Renewal Intelligence — risk forecasting, optimization opportunities."""

    def forecast(self, renewals: list[dict]) -> ProductReport:
        """Forecast renewal risks and opportunities."""
        total = len(renewals)
        if total == 0:
            return ProductReport(
                product=IntelligenceProduct.RENEWAL,
                title="Renewal Intelligence",
                summary="No renewal data available",
                score=ProductScore(IntelligenceProduct.RENEWAL, 0.5, "stable"),
            )

        at_risk = sum(1 for r in renewals if r.get("risk_score", 0) or 0 > 0.6)
        imminent = sum(1 for r in renewals if r.get("days_until_renewal", 365) <= 30)
        avg_risk = sum(r.get("risk_score", 0.5) or 0.5 for r in renewals) / total

        health_score = 1.0 - (at_risk / total * 0.5 + avg_risk * 0.3 + (imminent / total) * 0.2)

        recommendations = []
        if imminent > 0:
            recommendations.append(ProductRecommendation(
                priority="critical", category="imminent_renewals",
                title=f"{imminent} contracts renewing within 30 days",
                description="Begin renewal negotiations immediately",
            ))
        if at_risk > 0:
            recommendations.append(ProductRecommendation(
                priority="high", category="at_risk_renewals",
                title=f"{at_risk} renewals at high risk of unfavorable terms",
                description="Review risk factors and prepare counter-strategies",
            ))

        return ProductReport(
            product=IntelligenceProduct.RENEWAL,
            title="Renewal Intelligence",
            summary=f"{total} renewals tracked, {at_risk} at risk, {imminent} imminent",
            score=ProductScore(IntelligenceProduct.RENEWAL, round(health_score, 4), "stable"),
            recommendations=recommendations,
            benchmarks={"at_risk_pct": at_risk / total, "imminent_pct": imminent / total, "avg_risk": avg_risk},
        )


@dataclass
class ComplianceExposureProduct:
    """Compliance Exposure Intelligence — regulatory risk assessment."""

    def assess(self, regulations: list[dict]) -> ProductReport:
        """Assess compliance exposure across regulations."""
        total = len(regulations)
        if total == 0:
            return ProductReport(
                product=IntelligenceProduct.COMPLIANCE_EXPOSURE,
                title="Compliance Exposure",
                summary="No compliance data available",
                score=ProductScore(IntelligenceProduct.COMPLIANCE_EXPOSURE, 0.5, "stable"),
            )

        compliant = sum(1 for r in regulations if r.get("compliant", False))
        avg_gaps = sum(len(r.get("gaps", [])) for r in regulations) / total
        compliance_rate = compliant / total

        exposure_score = 1.0 - (compliance_rate * 0.6 + (1.0 - min(1.0, avg_gaps / 5)) * 0.4)

        recommendations = []
        if exposure_score > 0.5:
            regulations_with_gaps = [r for r in regulations if not r.get("compliant", False)]
            for reg in regulations_with_gaps[:3]:
                recommendations.append(ProductRecommendation(
                    priority="critical" if exposure_score > 0.7 else "high",
                    category="compliance_gap",
                    title=f"Address {reg.get('name', 'unknown')} compliance gaps",
                    description=f"{len(reg.get('gaps', []))} gaps detected",
                ))

        return ProductReport(
            product=IntelligenceProduct.COMPLIANCE_EXPOSURE,
            title="Compliance Exposure Assessment",
            summary=f"{compliant}/{total} regulations compliant, avg {avg_gaps:.1f} gaps per regulation",
            score=ProductScore(IntelligenceProduct.COMPLIANCE_EXPOSURE, round(exposure_score, 4), "stable"),
            recommendations=recommendations,
            benchmarks={"compliance_rate": compliance_rate, "avg_gaps": avg_gaps},
        )


@dataclass
class ObligationProduct:
    """Obligation Intelligence — tracking, aging, risk analysis."""

    def analyze(self, obligations: list[dict]) -> ProductReport:
        """Analyze obligation portfolio health."""
        total = len(obligations)
        if total == 0:
            return ProductReport(
                product=IntelligenceProduct.OBLIGATION,
                title="Obligation Intelligence",
                summary="No obligation data available",
                score=ProductScore(IntelligenceProduct.OBLIGATION, 0.5, "stable"),
            )

        overdue = sum(1 for o in obligations if o.get("status") == "overdue")
        at_risk = sum(1 for o in obligations if o.get("status") == "at_risk")
        fulfilled = total - overdue - at_risk

        health_score = fulfilled / total if total > 0 else 1.0

        recommendations = []
        if overdue > 0:
            recommendations.append(ProductRecommendation(
                priority="critical" if overdue > 5 else "high",
                category="overdue_obligations",
                title=f"{overdue} overdue obligations require immediate action",
                description="Overdue obligations may create legal and compliance exposure",
            ))

        return ProductReport(
            product=IntelligenceProduct.OBLIGATION,
            title="Obligation Intelligence",
            summary=f"{fulfilled} fulfilled, {overdue} overdue, {at_risk} at risk of {total} total",
            score=ProductScore(IntelligenceProduct.OBLIGATION, round(health_score, 4), "stable"),
            recommendations=recommendations,
            benchmarks={"fulfillment_rate": health_score, "overdue_pct": overdue / total, "at_risk_pct": at_risk / total},
        )


@dataclass
class WorkflowEfficiencyProduct:
    """Workflow Efficiency Intelligence — bottlenecks, cycle times, optimization opportunities."""

    def analyze(self, workflows: list[dict]) -> ProductReport:
        """Analyze workflow efficiency across the organization."""
        total = len(workflows)
        if total == 0:
            return ProductReport(
                product=IntelligenceProduct.WORKFLOW_EFFICIENCY,
                title="Workflow Efficiency",
                summary="No workflow data available",
                score=ProductScore(IntelligenceProduct.WORKFLOW_EFFICIENCY, 0.5, "stable"),
            )

        completed = sum(1 for w in workflows if w.get("status") == "completed")
        breached = sum(1 for w in workflows if w.get("sla_breached", False))
        avg_cycle_hours = sum(w.get("cycle_hours", 24) for w in workflows) / total

        completion_rate = completed / total
        sla_compliance = 1.0 - (breached / total)
        efficiency = completion_rate * 0.5 + sla_compliance * 0.3 + max(0, 1.0 - avg_cycle_hours / 168) * 0.2

        recommendations = []
        if breached > 0:
            recommendations.append(ProductRecommendation(
                priority="high" if breached > total * 0.1 else "medium",
                category="sla_breaches",
                title=f"{breached} workflows breached SLA ({breached/total:.0%})",
                description="Review bottleneck stages and adjust capacity",
            ))
        if avg_cycle_hours > 72:
            recommendations.append(ProductRecommendation(
                priority="medium", category="cycle_time",
                title=f"Average workflow cycle is {avg_cycle_hours:.0f} hours",
                description="Target: under 48 hours for standard reviews",
            ))

        return ProductReport(
            product=IntelligenceProduct.WORKFLOW_EFFICIENCY,
            title="Workflow Efficiency Intelligence",
            summary=f"{completed}/{total} completed, {breached} SLA breaches, avg {avg_cycle_hours:.0f}h cycle",
            score=ProductScore(IntelligenceProduct.WORKFLOW_EFFICIENCY, round(efficiency, 4), "stable"),
            recommendations=recommendations,
            benchmarks={"completion_rate": completion_rate, "sla_compliance": sla_compliance, "avg_cycle_hours": avg_cycle_hours},
        )


# ── Intelligence Products Factory ─────────────────────────────────

@dataclass
class IntelligenceProductsFactory:
    """Factory for all intelligence products."""

    vendor_risk: VendorRiskProduct = field(default_factory=VendorRiskProduct)
    negotiation: NegotiationProduct = field(default_factory=NegotiationProduct)
    renewal: RenewalProduct = field(default_factory=RenewalProduct)
    compliance: ComplianceExposureProduct = field(default_factory=ComplianceExposureProduct)
    obligation: ObligationProduct = field(default_factory=ObligationProduct)
    workflow_efficiency: WorkflowEfficiencyProduct = field(default_factory=WorkflowEfficiencyProduct)

    def get_product(self, product_type: IntelligenceProduct):
        """Get an intelligence product by type."""
        mapping = {
            IntelligenceProduct.VENDOR_RISK: self.vendor_risk,
            IntelligenceProduct.NEGOTIATION: self.negotiation,
            IntelligenceProduct.RENEWAL: self.renewal,
            IntelligenceProduct.COMPLIANCE_EXPOSURE: self.compliance,
            IntelligenceProduct.OBLIGATION: self.obligation,
            IntelligenceProduct.WORKFLOW_EFFICIENCY: self.workflow_efficiency,
        }
        return mapping.get(product_type)

    def generate_all_reports(self, data: dict[str, Any]) -> dict[str, ProductReport]:
        """Generate reports from all intelligence products."""
        reports = {}
        if "vendor_contracts" in data:
            for vendor, contracts in data["vendor_contracts"].items():
                reports[f"vendor_risk:{vendor}"] = self.vendor_risk.assess(vendor, contracts)
        if "negotiations" in data:
            reports["negotiation"] = self.negotiation.analyze(data["negotiations"])
        if "renewals" in data:
            reports["renewal"] = self.renewal.forecast(data["renewals"])
        if "regulations" in data:
            reports["compliance"] = self.compliance.assess(data["regulations"])
        if "obligations" in data:
            reports["obligation"] = self.obligation.analyze(data["obligations"])
        if "workflows" in data:
            reports["workflow_efficiency"] = self.workflow_efficiency.analyze(data["workflows"])
        return reports


# ── Global singleton ───────────────────────────────────────────────

intelligence_products = IntelligenceProductsFactory()
