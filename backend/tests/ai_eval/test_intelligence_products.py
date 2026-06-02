"""Enterprise Intelligence Products & ROI Layer Tests.

Validates:
- Intelligence Products (Vendor Risk, Negotiation, Renewal, Compliance, Obligation, Workflow Efficiency)
- ROI Measurement Engine (review time, negotiation, SLA, reviewer efficiency, false positives, contract cycle)
- Recommendation Orchestration (prioritized action plans, workflow/vendor/renewal/staffing recommendations)
- Simulation & Scenario Engine (workflow what-if, reviewer load, vendor risk, compliance exposure)
- Commercial Packaging (5 tiers with graduated limits, upgrade paths, feature access)
- AI Governance Certification (governance, explainability, replay audit, model usage, provider transparency)
"""

from __future__ import annotations

import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. ENTERPRISE INTELLIGENCE PRODUCTS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestIntelligenceProducts:
    """Validate enterprise intelligence products."""

    def test_product_types_defined(self) -> None:
        """All intelligence product types must be defined."""
        from app.domains.intelligence_products import IntelligenceProduct

        required = ["VENDOR_RISK", "NEGOTIATION", "RENEWAL", "COMPLIANCE_EXPOSURE", "OBLIGATION", "WORKFLOW_EFFICIENCY"]
        for p in required:
            assert hasattr(IntelligenceProduct, p), f"Missing product: {p}"

    def test_vendor_risk_product(self) -> None:
        """Vendor risk product must assess concentration and compliance."""
        from app.domains.intelligence_products import VendorRiskProduct

        product = VendorRiskProduct()
        report = product.assess("Test Vendor", [
            {"risk_score": 0.6, "value": 100000, "obligations_overdue": 2},
            {"risk_score": 0.7, "value": 200000, "obligations_overdue": 1},
        ])
        assert report.product.value == "vendor_risk"
        assert len(report.recommendations) > 0

    def test_negotiation_product(self) -> None:
        """Negotiation product must analyze effectiveness."""
        from app.domains.intelligence_products import NegotiationProduct

        product = NegotiationProduct()
        report = product.analyze([
            {"outcome": "successful", "cycle_days": 30, "concessions_made": 2},
            {"outcome": "successful", "cycle_days": 45, "concessions_made": 3},
            {"outcome": "failed", "cycle_days": 60, "concessions_made": 5},
        ])
        assert report.product.value == "negotiation"
        assert report.score.score > 0

    def test_renewal_product(self) -> None:
        """Renewal product must forecast risks."""
        from app.domains.intelligence_products import RenewalProduct

        product = RenewalProduct()
        report = product.forecast([
            {"risk_score": 0.8, "days_until_renewal": 15},
            {"risk_score": 0.3, "days_until_renewal": 120},
        ])
        assert report.product.value == "renewal"
        assert len(report.recommendations) > 0  # Imminent renewal detected

    def test_compliance_exposure_product(self) -> None:
        """Compliance exposure product must assess regulatory risk."""
        from app.domains.intelligence_products import ComplianceExposureProduct

        product = ComplianceExposureProduct()
        report = product.assess([
            {"name": "GDPR", "compliant": True, "gaps": []},
            {"name": "SOC2", "compliant": False, "gaps": ["Missing access review", "Incomplete audit trail"]},
        ])
        assert report.product.value == "compliance_exposure"
        # At least one recommendation if there are compliance gaps
        if not report.recommendations:
            assert report.score.score < 0.5  # Should have low score

    def test_obligation_product(self) -> None:
        """Obligation product must analyze portfolio health."""
        from app.domains.intelligence_products import ObligationProduct

        product = ObligationProduct()
        report = product.analyze([
            {"status": "fulfilled"}, {"status": "fulfilled"}, {"status": "overdue"},
        ])
        assert report.product.value == "obligation"
        assert report.score.score < 1.0  # Not perfect due to overdue

    def test_workflow_efficiency_product(self) -> None:
        """Workflow efficiency product must analyze cycle times."""
        from app.domains.intelligence_products import WorkflowEfficiencyProduct

        product = WorkflowEfficiencyProduct()
        report = product.analyze([
            {"status": "completed", "sla_breached": False, "cycle_hours": 24},
            {"status": "completed", "sla_breached": True, "cycle_hours": 48},
        ])
        assert report.product.value == "workflow_efficiency"

    def test_intelligence_products_factory(self) -> None:
        """Factory must generate reports from all products."""
        from app.domains.intelligence_products import IntelligenceProductsFactory, IntelligenceProduct

        factory = IntelligenceProductsFactory()
        assert factory.get_product(IntelligenceProduct.VENDOR_RISK) is not None
        assert factory.get_product(IntelligenceProduct.NEGOTIATION) is not None
        assert factory.get_product(IntelligenceProduct.RENEWAL) is not None


# ═══════════════════════════════════════════════════════════════════
# 2. ROI MEASUREMENT ENGINE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestROIMeasurement:
    """Validate ROI measurement engine."""

    def test_review_time_reduction(self) -> None:
        """Review time reduction must calculate savings."""
        from app.domains.roi import ROIMeasurementEngine

        engine = ROIMeasurementEngine()
        metric = engine.measure_review_time_reduction(
            baseline_hours=8, current_hours=3, reviews_per_year=1000
        )
        assert metric.improvement == 5  # 8 - 3 = 5 hours saved
        assert metric.estimated_annual_savings > 0
        assert metric.trend == "improving"

    def test_negotiation_acceleration(self) -> None:
        """Negotiation acceleration must calculate savings."""
        from app.domains.roi import ROIMeasurementEngine

        engine = ROIMeasurementEngine()
        metric = engine.measure_negotiation_acceleration(
            baseline_days=60, current_days=30, negotiations_per_year=100
        )
        assert metric.improvement == 30
        assert metric.estimated_annual_savings > 0

    def test_sla_improvement(self) -> None:
        """SLA improvement must calculate breach reduction."""
        from app.domains.roi import ROIMeasurementEngine

        engine = ROIMeasurementEngine()
        metric = engine.measure_sla_improvement(
            baseline_breach_rate=0.15, current_breach_rate=0.05, workflows_per_year=1000
        )
        assert metric.improvement == 10  # 10 percentage points
        assert metric.estimated_annual_savings > 0

    def test_reviewer_efficiency(self) -> None:
        """Reviewer efficiency must calculate capacity gains."""
        from app.domains.roi import ROIMeasurementEngine

        engine = ROIMeasurementEngine()
        metric = engine.measure_reviewer_efficiency(
            baseline_reviews_per_day=3, current_reviews_per_day=5, reviewers=10
        )
        assert metric.improvement == 2
        assert metric.estimated_annual_savings > 0

    def test_false_positive_reduction(self) -> None:
        """False positive reduction must calculate time saved."""
        from app.domains.roi import ROIMeasurementEngine

        engine = ROIMeasurementEngine()
        metric = engine.measure_false_positive_reduction(
            baseline_fp_rate=0.20, current_fp_rate=0.10, findings_per_year=10000
        )
        assert metric.improvement == 10
        assert metric.estimated_annual_savings > 0

    def test_full_roi_report(self) -> None:
        """Full ROI report must aggregate all metrics."""
        from app.domains.roi import roi_engine

        roi_engine.set_baseline("review_time_hours", 8)
        roi_engine.set_current("review_time_hours", 3)
        roi_engine.set_baseline("negotiation_days", 60)
        roi_engine.set_current("negotiation_days", 30)
        roi_engine.set_baseline("sla_breach_rate", 0.15)
        roi_engine.set_current("sla_breach_rate", 0.05)
        roi_engine.set_baseline("reviews_per_day", 3)
        roi_engine.set_current("reviews_per_day", 5)
        roi_engine.set_baseline("fp_rate", 0.20)
        roi_engine.set_current("fp_rate", 0.10)

        report = roi_engine.generate_full_report(annual_contracts=1000)
        assert report.total_annual_savings > 0
        assert len(report.roi_metrics) > 0
        assert report.confidence_score > 0


# ═══════════════════════════════════════════════════════════════════
# 3. RECOMMENDATION ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestRecommendationEngine:
    """Validate recommendation orchestration."""

    def test_priority_levels_defined(self) -> None:
        """All priority levels must be defined."""
        from app.domains.recommendation_engine import RecommendationPriority

        assert RecommendationPriority.CRITICAL
        assert RecommendationPriority.HIGH
        assert RecommendationPriority.MEDIUM
        assert RecommendationPriority.LOW

    def test_workflow_recommendations(self) -> None:
        """Workflow bottlenecks must generate recommendations."""
        from app.domains.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        recs = engine.generate_workflow_recommendations([
            {"stage": "legal_review", "severity": "high", "avg_completion_hours": 32, "breach_rate": 0.4},
        ])
        assert len(recs) == 1
        assert recs[0].priority.value == "high"

    def test_vendor_recommendations(self) -> None:
        """Vendor risks must generate recommendations."""
        from app.domains.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        recs = engine.generate_vendor_recommendations([
            {"vendor_name": "High Risk Vendor", "risk_score": 0.85, "contract_count": 15},
        ])
        assert len(recs) == 1
        assert recs[0].priority.value == "critical"

    def test_renewal_recommendations(self) -> None:
        """Imminent renewals must generate critical recommendations."""
        from app.domains.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        recs = engine.generate_renewal_recommendations([
            {"contract_id": "c_001", "contract_name": "Test", "days_until_renewal": 15, "risk_score": 0.8},
        ])
        assert len(recs) == 1
        assert recs[0].priority.value == "critical"

    def test_staffing_recommendations(self) -> None:
        """Reviewer overload must generate staffing recommendations."""
        from app.domains.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        recs = engine.generate_staffing_recommendations([
            {"reviewer_id": "reviewer_001", "overload_risk": "high", "recommendation": "Add capacity"},
        ])
        assert len(recs) == 1
        assert recs[0].priority.value == "critical"

    def test_action_plan_creation(self) -> None:
        """Action plans must prioritize critical recommendations first."""
        from app.domains.recommendation_engine import RecommendationEngine, ActionableRecommendation, RecommendationPriority, RecommendationCategory

        engine = RecommendationEngine()
        recs = [
            ActionableRecommendation(recommendation_id="r1", priority=RecommendationPriority.LOW, category=RecommendationCategory.OPTIMIZATION, title="Low priority", description="Low impact task"),
            ActionableRecommendation(recommendation_id="r2", priority=RecommendationPriority.CRITICAL, category=RecommendationCategory.RISK, title="Critical priority", description="Critical risk needs immediate attention"),
            ActionableRecommendation(recommendation_id="r3", priority=RecommendationPriority.HIGH, category=RecommendationCategory.COMPLIANCE, title="High priority", description="Compliance gap needs resolution"),
        ]
        plan = engine.create_action_plan(recs)
        assert plan.recommendations[0].recommendation_id == "r2"  # Critical first


# ═══════════════════════════════════════════════════════════════════
# 4. SIMULATION & SCENARIO ENGINE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestSimulationEngine:
    """Validate simulation and scenario engine."""

    def test_simulation_types_defined(self) -> None:
        """All simulation types must be defined."""
        from app.domains.simulation import SimulationType

        required = ["WORKFLOW_WHAT_IF", "SLA_IMPACT", "REVIEWER_LOAD", "VENDOR_RISK", "COMPLIANCE_EXPOSURE", "NEGOTIATION_STRATEGY"]
        for s in required:
            assert hasattr(SimulationType, s), f"Missing simulation type: {s}"

    def test_workflow_what_if_simulation(self) -> None:
        """Workflow what-if must show impact of SLA changes."""
        from app.domains.simulation import SimulationEngine

        engine = SimulationEngine()
        result = engine.simulate_workflow_what_if({
            "scenario_name": "Optimize Legal Review",
            "stages": [
                {"name": "AI Analysis", "sla_hours": 1},
                {"name": "Legal Review", "sla_hours": 48},
                {"name": "Approval", "sla_hours": 8},
            ],
            "sla_changes": {"Legal Review": 24},
        })
        assert result.baseline["total_hours"] == 57
        assert result.projected["total_hours"] == 33
        assert result.delta["hours_saved"] == 24

    def test_reviewer_load_simulation(self) -> None:
        """Reviewer load must show backlog impact."""
        from app.domains.simulation import SimulationEngine

        engine = SimulationEngine()
        result = engine.simulate_reviewer_load({
            "scenario_name": "Add Reviewers",
            "current_reviewers": 5,
            "current_backlog": 200,
            "avg_review_time_hours": 4,
            "new_reviews_per_day": 10,
            "add_reviewers": 3,
        })
        assert result.projected["reviewers"] == 8
        assert len(result.recommendations) > 0

    def test_vendor_risk_simulation(self) -> None:
        """Vendor failure simulation must show financial impact."""
        from app.domains.simulation import SimulationEngine

        engine = SimulationEngine()
        result = engine.simulate_vendor_risk({
            "vendor_name": "Critical Vendor",
            "contract_count": 20,
            "total_value": 500000,
            "disruption_pct": 1.0,
            "has_alternative": False,
        })
        assert result.projected["financial_impact"] == 500000
        assert len(result.recommendations) > 0

    def test_compliance_simulation(self) -> None:
        """Regulatory change simulation must show compliance impact."""
        from app.domains.simulation import SimulationEngine

        engine = SimulationEngine()
        result = engine.simulate_compliance_exposure({
            "regulation": "GDPR Update",
            "compliance_rate": 0.8,
            "new_requirement_severity": 0.3,
            "affected_contracts": 100,
        })
        assert result.projected["compliance_rate"] == 0.5
        assert result.projected["newly_non_compliant"] == 30


# ═══════════════════════════════════════════════════════════════════
# 5. COMMERCIAL PACKAGING
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestCommercialPackaging:
    """Validate commercial packaging and tier management."""

    def test_all_tiers_defined(self) -> None:
        """All product tiers must be defined with limits."""
        from app.domains.intelligence_products.packaging import ProductTier, TIER_CONFIGS

        required = ["DEVELOPER", "TEAM", "BUSINESS", "ENTERPRISE", "ENTERPRISE_PLUS"]
        for t in required:
            assert hasattr(ProductTier, t), f"Missing tier: {t}"
        assert len(TIER_CONFIGS) == 5

    def test_tier_limits_graduated(self) -> None:
        """Tier limits must increase with each tier."""
        from app.domains.intelligence_products.packaging import ProductTier, TIER_CONFIGS

        tiers = [ProductTier.DEVELOPER, ProductTier.TEAM, ProductTier.BUSINESS, ProductTier.ENTERPRISE, ProductTier.ENTERPRISE_PLUS]
        for i in range(len(tiers) - 1):
            current = TIER_CONFIGS[tiers[i]]
            next_tier = TIER_CONFIGS[tiers[i + 1]]
            assert next_tier.max_contracts > current.max_contracts
            assert next_tier.ai_executions_per_month > current.ai_executions_per_month

    def test_tier_for_contract_count(self) -> None:
        """Tier resolution must match contract volume."""
        from app.domains.intelligence_products.packaging import commercial_packaging, ProductTier

        assert commercial_packaging.get_tier_for_contract_count(10) == ProductTier.DEVELOPER
        assert commercial_packaging.get_tier_for_contract_count(100) == ProductTier.TEAM
        assert commercial_packaging.get_tier_for_contract_count(1000) == ProductTier.BUSINESS
        assert commercial_packaging.get_tier_for_contract_count(50000) == ProductTier.ENTERPRISE

    def test_upgrade_path(self) -> None:
        """Upgrade paths must show new features."""
        from app.domains.intelligence_products.packaging import commercial_packaging, ProductTier

        upgrades = commercial_packaging.get_upgrade_path(ProductTier.DEVELOPER)
        assert len(upgrades) == 4  # 4 tiers above developer
        assert len(upgrades[0]["new_features"]) > 0

    def test_feature_access(self) -> None:
        """Feature access must match tier."""
        from app.domains.intelligence_products.packaging import commercial_packaging, ProductTier

        assert commercial_packaging.check_feature_access(ProductTier.ENTERPRISE, "simulation") is True
        assert commercial_packaging.check_feature_access(ProductTier.DEVELOPER, "simulation") is False
        assert commercial_packaging.check_feature_access(ProductTier.BUSINESS, "forecasting") is True

    def test_tier_summary(self) -> None:
        """Tier summary must include all tiers."""
        from app.domains.intelligence_products.packaging import commercial_packaging

        summary = commercial_packaging.get_tier_summary()
        assert len(summary) == 5
        for s in summary:
            assert "tier" in s
            assert "price" in s
            assert "features" in s


# ═══════════════════════════════════════════════════════════════════
# 6. AI GOVERNANCE CERTIFICATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestAIGovernance:
    """Validate AI governance certification."""

    def test_governance_report_types_defined(self) -> None:
        """All governance report types must be defined."""
        from app.domains.intelligence_products.governance import GovernanceReportType

        required = ["AI_GOVERNANCE", "EXPLAINABILITY", "REPLAY_AUDIT", "MODEL_USAGE", "PROVIDER_TRANSPARENCY", "POLICY_ENFORCEMENT"]
        for r in required:
            assert hasattr(GovernanceReportType, r), f"Missing report type: {r}"

    def test_ai_governance_report(self) -> None:
        """AI governance report must show control status."""
        from app.domains.intelligence_products.governance import ai_governance

        report = ai_governance.generate_ai_governance_report("tenant_001")
        assert report.status == "compliant"
        assert len(report.findings) > 0

    def test_explainability_report(self) -> None:
        """Explainability report must trace execution stages."""
        from app.domains.intelligence_products.governance import ai_governance

        report = ai_governance.generate_explainability_report("exec_001", {
            "timeline_events": [
                {"event_type": "policy_check", "component": "policy_engine", "duration_ms": 50},
                {"event_type": "retrieval", "component": "search_engine", "duration_ms": 200},
            ],
            "prompt_version": "2.1.0",
            "provider": "openai",
            "model": "gpt-4o",
        })
        assert report.status == "compliant"
        assert len(report.findings) == 2

    def test_replay_audit_report(self) -> None:
        """Replay audit report must verify reproducibility."""
        from app.domains.intelligence_products.governance import ai_governance

        report = ai_governance.generate_replay_audit_report("exec_001", {
            "drift_score": 0.02,
            "drift_detected": False,
            "retrieval_snapshot_matched": True,
            "prompt_version_changed": False,
        })
        assert report.status == "compliant"

    def test_replay_audit_drift_detected(self) -> None:
        """Replay audit must detect and report drift."""
        from app.domains.intelligence_products.governance import ai_governance

        report = ai_governance.generate_replay_audit_report("exec_002", {
            "drift_score": 0.35,
            "drift_detected": True,
            "retrieval_snapshot_matched": False,
            "prompt_version_changed": True,
        })
        assert report.status == "needs_review"
        assert len(report.recommendations) > 0

    def test_model_usage_report(self) -> None:
        """Model usage report must show distribution."""
        from app.domains.intelligence_products.governance import ai_governance

        report = ai_governance.generate_model_usage_report([
            {"model": "gpt-4o", "provider": "openai"},
            {"model": "gpt-4o", "provider": "openai"},
            {"model": "gpt-4o-mini", "provider": "openai"},
            {"model": "claude-3-sonnet", "provider": "anthropic"},
        ])
        assert report.status == "compliant"
        assert len(report.findings) == 5

    def test_provider_transparency_report(self) -> None:
        """Provider transparency report must show performance."""
        from app.domains.intelligence_products.governance import ai_governance

        report = ai_governance.generate_provider_transparency_report([
            {"provider": "openai", "total_calls": 5000, "success_rate": 0.99, "avg_latency_ms": 2000, "total_cost": 150.0},
        ])
        assert report.status == "compliant"

    def test_policy_enforcement_report(self) -> None:
        """Policy enforcement report must track violations."""
        from app.domains.intelligence_products.governance import ai_governance

        report = ai_governance.generate_policy_enforcement_report([
            {"policy": "data_residency", "violation": "EU data processed in US"},
        ])
        assert report.status == "needs_review"
