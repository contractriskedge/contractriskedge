"""Customer Success Intelligence — tenant health score, adoption score, workflow maturity, reviewer efficiency, AI trust trends, expansion opportunities, underutilized features.

Critical for commercial success — understanding how customers use the platform.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CHURN_RISK = "churn_risk"


@dataclass
class TenantHealthScore:
    """Overall health score for a tenant."""
    tenant_id: str
    tenant_name: str
    overall_score: float  # 0.0-1.0
    status: HealthStatus
    adoption_score: float = 0.0
    workflow_maturity: float = 0.0
    reviewer_efficiency: float = 0.0
    ai_trust_trend: str = "stable"
    days_since_last_active: int = 0
    expansion_opportunities: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class FeatureAdoption:
    """Feature adoption metrics for a tenant."""
    feature_name: str
    category: str
    enabled: bool = False
    times_used: int = 0
    last_used: str = ""
    power_user_count: int = 0
    adoption_rate: float = 0.0  # 0.0-1.0


@dataclass
class CustomerSuccessService:
    """Customer success intelligence — understanding and improving tenant outcomes.

    Tracks:
    - Tenant health score (composite of adoption, maturity, efficiency, trust)
    - Adoption score (which features are being used)
    - Workflow maturity (how advanced are their workflows)
    - Reviewer efficiency (how productive are their reviewers)
    - AI trust trends (is trust improving or declining)
    - Expansion opportunities (which features could add value)
    - Underutilized features (features they're paying for but not using)
    """

    def calculate_health_score(self, tenant_data: dict[str, Any]) -> TenantHealthScore:
        """Calculate comprehensive tenant health score."""
        tenant_id = tenant_data.get("tenant_id", "unknown")
        tenant_name = tenant_data.get("tenant_name", "Unknown")

        # Adoption score
        features = tenant_data.get("features", {})
        enabled_features = sum(1 for f in features.values() if f.get("enabled", False))
        used_features = sum(1 for f in features.values() if f.get("times_used", 0) > 0)
        total_features = max(len(features), 1)
        adoption_score = used_features / total_features

        # Workflow maturity
        workflows = tenant_data.get("workflows", [])
        custom_workflows = sum(1 for w in workflows if w.get("is_custom", False))
        workflow_maturity = min(1.0, len(workflows) * 0.1 + custom_workflows * 0.2)

        # Reviewer efficiency
        reviewers = tenant_data.get("reviewers", [])
        if reviewers:
            avg_completion = sum(r.get("avg_review_time_hours", 4) for r in reviewers) / len(reviewers)
            sla_compliance = sum(r.get("sla_compliance_rate", 0.9) for r in reviewers) / len(reviewers)
            reviewer_efficiency = (1.0 - min(1.0, avg_completion / 8)) * 0.5 + sla_compliance * 0.5
        else:
            reviewer_efficiency = 0.5

        # AI trust
        execution_history = tenant_data.get("execution_history", [])
        if execution_history:
            accepted = sum(1 for e in execution_history if e.get("reviewer_action") == "accepted")
            total = len(execution_history)
            ai_trust = accepted / max(total, 1)
        else:
            ai_trust = 0.85

        # Days since last active
        last_active_str = tenant_data.get("last_active", "")
        days_since = 0
        if last_active_str:
            try:
                last_active = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
                days_since = (datetime.utcnow() - last_active).days
            except (ValueError, TypeError):
                days_since = 0

        # Composite score
        overall = adoption_score * 0.25 + workflow_maturity * 0.2 + reviewer_efficiency * 0.2 + ai_trust * 0.25 + max(0, 1.0 - days_since / 30) * 0.1

        # Status
        if overall < 0.3 or days_since > 14:
            status = HealthStatus.CHURN_RISK
        elif overall < 0.5 or days_since > 7:
            status = HealthStatus.AT_RISK
        else:
            status = HealthStatus.HEALTHY

        # Risk factors
        risk_factors = []
        if days_since > 7:
            risk_factors.append(f"Not active in {days_since} days")
        if adoption_score < 0.3:
            risk_factors.append("Low feature adoption")
        if reviewer_efficiency < 0.4:
            risk_factors.append("Low reviewer efficiency")
        if ai_trust < 0.6:
            risk_factors.append("Declining AI trust")

        # Expansion opportunities
        expansion = []
        if not features.get("benchmarks", {}).get("enabled", False):
            expansion.append("Benchmark Intelligence")
        if not features.get("simulation", {}).get("enabled", False):
            expansion.append("What-If Simulation")
        if not features.get("forecasting", {}).get("enabled", False):
            expansion.append("Forecasting & Predictions")

        # Recommendations
        recommendations = []
        if status == HealthStatus.CHURN_RISK:
            recommendations.append("Schedule executive business review immediately")
            recommendations.append("Offer personalized onboarding session")
        elif status == HealthStatus.AT_RISK:
            recommendations.append("Schedule check-in call")
            recommendations.append("Share best practices for underutilized features")
        if expansion:
            recommendations.append(f"Introduce {expansion[0]} — high relevance for this tenant")

        return TenantHealthScore(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            overall_score=round(overall, 4),
            status=status,
            adoption_score=round(adoption_score, 4),
            workflow_maturity=round(workflow_maturity, 4),
            reviewer_efficiency=round(reviewer_efficiency, 4),
            ai_trust_trend="improving" if ai_trust > 0.85 else "stable" if ai_trust > 0.7 else "declining",
            days_since_last_active=days_since,
            expansion_opportunities=expansion,
            risk_factors=risk_factors,
            recommendations=recommendations,
        )

    def analyze_feature_adoption(self, usage_data: dict[str, Any]) -> list[FeatureAdoption]:
        """Analyze feature adoption across the tenant."""
        features = []
        for feature_name, data in usage_data.get("features", {}).items():
            category = data.get("category", "uncategorized")
            features.append(FeatureAdoption(
                feature_name=feature_name,
                category=category,
                enabled=data.get("enabled", False),
                times_used=data.get("times_used", 0),
                last_used=data.get("last_used", ""),
                power_user_count=data.get("power_user_count", 0),
                adoption_rate=data.get("times_used", 0) / max(usage_data.get("total_actions", 1), 1),
            ))

        return sorted(features, key=lambda f: f.adoption_rate)

    def get_underutilized_features(self, usage_data: dict[str, Any], threshold: float = 0.1) -> list[FeatureAdoption]:
        """Get features that are underutilized by the tenant."""
        all_features = self.analyze_feature_adoption(usage_data)
        return [f for f in all_features if f.enabled and f.adoption_rate < threshold]

    def get_tenant_segment(self, health_scores: list[TenantHealthScore]) -> dict[str, Any]:
        """Segment tenants by health status for portfolio analysis."""
        healthy = [t for t in health_scores if t.status == HealthStatus.HEALTHY]
        at_risk = [t for t in health_scores if t.status == HealthStatus.AT_RISK]
        churn_risk = [t for t in health_scores if t.status == HealthStatus.CHURN_RISK]

        return {
            "total_tenants": len(health_scores),
            "healthy": len(healthy),
            "at_risk": len(at_risk),
            "churn_risk": len(churn_risk),
            "health_rate": round(len(healthy) / max(len(health_scores), 1), 4),
            "expansion_revenue": sum(
                len(t.expansion_opportunities) * 5000 for t in healthy + at_risk
            ),
        }


# ── Global singleton ───────────────────────────────────────────────

customer_success = CustomerSuccessService()
