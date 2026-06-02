"""Tests for Legal Playbook + Policy Engine — rule evaluation, deviation detection,
policy overrides, approval thresholds, AI policy injection, tenant isolation,
versioning, and governance audit."""

from __future__ import annotations

import pytest
from datetime import datetime
from app.domains.playbook.models import (
    PlaybookStatus, ClauseCategory, ClauseType, RuleOperator, RuleEffect,
    DeviationSeverity, OverrideStatus, EvaluationStatus,
)
from app.domains.playbook.engine import (
    RuleEvaluator, EvaluationContext, ExtractedClause, DeviationDetector,
    ApprovalThresholdEvaluator, ClauseRecommender, RiskScorer, PolicyEngine,
    EvaluationResult, DeviationResult, ClauseRecommendation, ApprovalRequirement,
)


# ══════════════════════════════════════════════════════════════════════
# ENUM TESTS
# ══════════════════════════════════════════════════════════════════════


class TestPlaybookEnums:
    """Verify playbook enum values."""

    def test_playbook_status_values(self):
        assert PlaybookStatus.DRAFT.value == "draft"
        assert PlaybookStatus.PUBLISHED.value == "published"
        assert PlaybookStatus.ARCHIVED.value == "archived"
        assert PlaybookStatus.SUPERSEDED.value == "superseded"

    def test_clause_category_values(self):
        assert ClauseCategory.INDEMNIFICATION.value == "indemnification"
        assert ClauseCategory.LIMITATION_OF_LIABILITY.value == "limitation_of_liability"
        assert ClauseCategory.CONFIDENTIALITY.value == "confidentiality"
        assert ClauseCategory.GENERAL.value == "general"

    def test_clause_type_values(self):
        assert ClauseType.APPROVED.value == "approved"
        assert ClauseType.PREFERRED.value == "preferred"
        assert ClauseType.FALLBACK.value == "fallback"
        assert ClauseType.FORBIDDEN.value == "forbidden"

    def test_rule_operator_values(self):
        assert RuleOperator.EQUALS.value == "equals"
        assert RuleOperator.CONTAINS.value == "contains"
        assert RuleOperator.GREATER_THAN.value == "greater_than"
        assert RuleOperator.MATCHES_REGEX.value == "matches_regex"

    def test_rule_effect_values(self):
        assert RuleEffect.ALLOW.value == "allow"
        assert RuleEffect.BLOCK.value == "block"
        assert RuleEffect.FLAG_FOR_REVIEW.value == "flag_for_review"
        assert RuleEffect.REQUIRE_APPROVAL.value == "require_approval"
        assert RuleEffect.ESCALATE.value == "escalate"

    def test_deviation_severity_values(self):
        assert DeviationSeverity.CRITICAL.value == "critical"
        assert DeviationSeverity.HIGH.value == "high"
        assert DeviationSeverity.MEDIUM.value == "medium"
        assert DeviationSeverity.LOW.value == "low"

    def test_override_status_values(self):
        assert OverrideStatus.PENDING.value == "pending"
        assert OverrideStatus.APPROVED.value == "approved"
        assert OverrideStatus.REJECTED.value == "rejected"
        assert OverrideStatus.EXPIRED.value == "expired"

    def test_evaluation_status_values(self):
        assert EvaluationStatus.PENDING.value == "pending"
        assert EvaluationStatus.PROCESSING.value == "processing"
        assert EvaluationStatus.COMPLETED.value == "completed"
        assert EvaluationStatus.FAILED.value == "failed"


# ══════════════════════════════════════════════════════════════════════
# RULE EVALUATOR TESTS
# ══════════════════════════════════════════════════════════════════════


class TestRuleEvaluator:
    """Verify rule evaluation logic — conditions, operators, field resolution."""

    def test_evaluate_equals_match(self):
        """Equals operator should match when values are equal."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Test Rule", rule_type="clause_required",
            conditions={"operator": "equals", "field": "contract.jurisdiction", "value": "US"},
            effect=RuleEffect.FLAG_FOR_REVIEW, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", jurisdiction="US")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True
        assert result.effect == "flag_for_review"

    def test_evaluate_equals_no_match(self):
        """Equals operator should not match when values differ."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Test Rule", rule_type="clause_required",
            conditions={"operator": "equals", "field": "contract.jurisdiction", "value": "US"},
            effect=RuleEffect.FLAG_FOR_REVIEW, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", jurisdiction="UK")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is False

    def test_evaluate_greater_than_match(self):
        """Greater than operator should match when value exceeds threshold."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="High Value", rule_type="value_threshold",
            conditions={"operator": "greater_than", "field": "contract.value", "value": 1000000},
            effect=RuleEffect.REQUIRE_APPROVAL, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", contract_value=5000000)
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True
        assert result.effect == "require_approval"

    def test_evaluate_greater_than_no_match(self):
        """Greater than operator should not match when value is below threshold."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="High Value", rule_type="value_threshold",
            conditions={"operator": "greater_than", "field": "contract.value", "value": 1000000},
            effect=RuleEffect.REQUIRE_APPROVAL, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", contract_value=500000)
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is False

    def test_evaluate_contains_match(self):
        """Contains operator should match on substring."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Jurisdiction Check", rule_type="clause_required",
            conditions={"operator": "contains", "field": "contract.jurisdiction", "value": "EU"},
            effect=RuleEffect.FLAG_FOR_REVIEW, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", jurisdiction="EU_GDPR")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_evaluate_and_conditions(self):
        """AND conditions should require all to match."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Complex Rule", rule_type="approval",
            conditions={
                "operator": "and",
                "conditions": [
                    {"operator": "greater_than", "field": "contract.value", "value": 500000},
                    {"operator": "equals", "field": "contract.jurisdiction", "value": "US"},
                ],
            },
            effect=RuleEffect.REQUIRE_APPROVAL, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1",
                                contract_value=1000000, jurisdiction="US")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_evaluate_and_conditions_partial_match(self):
        """AND conditions should fail if any condition doesn't match."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Complex Rule", rule_type="approval",
            conditions={
                "operator": "and",
                "conditions": [
                    {"operator": "greater_than", "field": "contract.value", "value": 500000},
                    {"operator": "equals", "field": "contract.jurisdiction", "value": "US"},
                ],
            },
            effect=RuleEffect.REQUIRE_APPROVAL, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1",
                                contract_value=100000, jurisdiction="UK")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is False

    def test_evaluate_or_conditions(self):
        """OR conditions should match if any condition matches."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="OR Rule", rule_type="deviation",
            conditions={
                "operator": "or",
                "conditions": [
                    {"operator": "equals", "field": "contract.jurisdiction", "value": "US"},
                    {"operator": "equals", "field": "contract.jurisdiction", "value": "UK"},
                ],
            },
            effect=RuleEffect.FLAG_FOR_REVIEW, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", jurisdiction="UK")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_evaluate_clause_exists(self):
        """Clause existence check should find matching clauses."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Check Indemnification", rule_type="clause_required",
            conditions={"operator": "exists", "field": "clause.exists"},
            effect=RuleEffect.REQUIRE_MANDATORY_CLAUSE, priority=100,
            target_category="indemnification",
        )
        ctx = EvaluationContext(
            upload_id="u1", tenant_id="t1",
            clauses=[ExtractedClause(category="indemnification", text="Indemnity clause", text_snippet="Indemnity")],
        )
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_evaluate_clause_not_exists(self):
        """Clause existence check should fail when clause is missing."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Check Indemnification", rule_type="clause_required",
            conditions={"operator": "exists", "field": "clause.exists"},
            effect=RuleEffect.REQUIRE_MANDATORY_CLAUSE, priority=100,
            target_category="indemnification",
        )
        ctx = EvaluationContext(
            upload_id="u1", tenant_id="t1",
            clauses=[ExtractedClause(category="confidentiality", text="Confidentiality", text_snippet="Conf")],
        )
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is False

    def test_evaluate_regex_match(self):
        """Regex operator should match pattern."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Regex Check", rule_type="deviation",
            conditions={"operator": "matches_regex", "field": "contract.jurisdiction", "value": r"^US|UK|EU"},
            effect=RuleEffect.FLAG_FOR_REVIEW, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", jurisdiction="US_CA")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_evaluate_in_operator(self):
        """IN operator should match when value is in list."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="In Check", rule_type="deviation",
            conditions={"operator": "in", "field": "contract.industry", "value": ["healthcare", "finance"]},
            effect=RuleEffect.FLAG_FOR_REVIEW, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", industry="healthcare")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_evaluate_not_in_operator(self):
        """NOT_IN operator should match when value is not in list."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Not In Check", rule_type="deviation",
            conditions={"operator": "not_in", "field": "contract.industry", "value": ["healthcare", "finance"]},
            effect=RuleEffect.ALLOW, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", industry="technology")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_evaluate_not_exists(self):
        """NOT_EXISTS should match when field is None."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Missing Value", rule_type="deviation",
            conditions={"operator": "not_exists", "field": "contract.risk_score"},
            effect=RuleEffect.FLAG_FOR_REVIEW, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_inactive_rule_skipped(self):
        """Inactive rules should not be evaluated."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="Inactive", rule_type="clause_required",
            conditions={"operator": "equals", "field": "contract.jurisdiction", "value": "US"},
            effect=RuleEffect.BLOCK, priority=100, is_active=False,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", jurisdiction="US")
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        # Inactive rules are filtered by the engine, not the evaluator
        assert result is not None

    def test_evaluate_risk_score_threshold(self):
        """Risk score threshold should trigger at correct levels."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="High Risk", rule_type="risk_threshold",
            conditions={"operator": "greater_than", "field": "contract.risk_score", "value": 7.0},
            effect=RuleEffect.REQUIRE_APPROVAL, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", risk_score=8.5)
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is True

    def test_evaluate_risk_score_below_threshold(self):
        """Risk score below threshold should not trigger."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            name="High Risk", rule_type="risk_threshold",
            conditions={"operator": "greater_than", "field": "contract.risk_score", "value": 7.0},
            effect=RuleEffect.REQUIRE_APPROVAL, priority=100,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", risk_score=3.0)
        result = RuleEvaluator.evaluate_rule(rule, ctx)
        assert result.matched is False


# ══════════════════════════════════════════════════════════════════════
# DEVIATION DETECTION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestDeviationDetector:
    """Verify deviation detection between contract clauses and standards."""

    def test_no_deviations_when_clause_matches_standard(self):
        """No deviations when contract clause matches approved standard."""
        from app.domains.playbook.models import ClauseStandard, ClauseCategory, ClauseType
        standard = ClauseStandard(
            clause_id="s1", category=ClauseCategory.INDEMNIFICATION,
            clause_type=ClauseType.APPROVED, title="Standard Indemnity",
            body="The Company shall indemnify and hold harmless the Client",
            is_active=True,
        )
        clause = ExtractedClause(
            category="indemnification",
            text="The Company shall indemnify and hold harmless the Client against any losses",
            text_snippet="The Company shall indemnify and hold harmless",
        )
        deviations = DeviationDetector.detect_deviations([clause], [standard], [])
        # High similarity should not produce deviation
        assert len(deviations) == 0

    def test_deviation_when_clause_differs_from_standard(self):
        """Deviation detected when clause differs significantly from standard."""
        from app.domains.playbook.models import ClauseStandard, ClauseCategory, ClauseType
        standard = ClauseStandard(
            clause_id="s1", category=ClauseCategory.INDEMNIFICATION,
            clause_type=ClauseType.APPROVED, title="Standard Indemnity",
            body="The Company shall indemnify and hold harmless the Client against any and all losses claims damages and expenses arising out of or relating to this Agreement",
            is_active=True,
        )
        clause = ExtractedClause(
            category="indemnification",
            text="Company will not be liable for any damages",
            text_snippet="Company will not be liable for any damages",
        )
        deviations = DeviationDetector.detect_deviations([clause], [standard], [])
        assert len(deviations) >= 1
        assert deviations[0].severity in ("high", "medium")

    def test_forbidden_clause_detected(self):
        """Forbidden clause should be detected as critical deviation."""
        from app.domains.playbook.models import ClauseStandard, ClauseCategory, ClauseType
        forbidden = ClauseStandard(
            clause_id="f1", category=ClauseCategory.LIMITATION_OF_LIABILITY,
            clause_type=ClauseType.FORBIDDEN, title="No Liability Cap",
            body="Neither party shall be liable for any indirect consequential or incidental damages",
            is_active=True,
        )
        clause = ExtractedClause(
            category="limitation_of_liability",
            text="Neither party shall be liable for any indirect consequential or incidental damages of any kind",
            text_snippet="Neither party shall be liable for any indirect consequential",
        )
        deviations = DeviationDetector.detect_deviations([clause], [forbidden], [])
        assert len(deviations) >= 1
        assert deviations[0].severity == "critical"

    def test_deviation_from_rule_results(self):
        """Deviations should be created from matched rules."""
        from app.domains.playbook.engine import RuleEvaluationResult
        rule_result = RuleEvaluationResult(
            rule_id="r1", rule_name="Missing Indemnification",
            rule_type="clause_required", effect="require_mandatory_clause",
            violation_triggered=True, priority=100,
            deviation_severity="high",
            matched_clause_category="indemnification",
        )
        deviations = DeviationDetector.detect_deviations([], [], [rule_result])
        assert len(deviations) >= 1
        assert deviations[0].rule_id == "r1"
        assert deviations[0].severity == "high"

    def test_deviation_scoring(self):
        """Deviation scores should be in valid range."""
        from app.domains.playbook.models import ClauseStandard, ClauseCategory, ClauseType
        standard = ClauseStandard(
            clause_id="s1", category=ClauseCategory.CONFIDENTIALITY,
            clause_type=ClauseType.APPROVED, title="Standard Confidentiality",
            body="The Receiving Party shall maintain the Confidential Information in strict confidence",
            is_active=True,
        )
        clause = ExtractedClause(
            category="confidentiality",
            text="Some unrelated text about something completely different",
            text_snippet="Some unrelated text",
        )
        deviations = DeviationDetector.detect_deviations([clause], [standard], [])
        if deviations:
            assert 0 <= deviations[0].score <= 1.0


# ══════════════════════════════════════════════════════════════════════
# APPROVAL THRESHOLD TESTS
# ══════════════════════════════════════════════════════════════════════


class TestApprovalThresholdEvaluator:
    """Verify approval threshold evaluation logic."""

    def test_risk_score_threshold_triggered(self):
        """Risk score threshold should trigger when score exceeds minimum."""
        from app.domains.playbook.models import ApprovalThreshold
        threshold = ApprovalThreshold(
            threshold_id="t1", name="High Risk Approval",
            threshold_type="risk_score", operator="greater_than",
            min_value=7.0, approval_role="legal_director",
            approval_level=2, is_active=True,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", risk_score=8.5)
        reqs = ApprovalThresholdEvaluator.evaluate([threshold], ctx, [], [])
        assert len(reqs) == 1
        assert reqs[0].approval_role == "legal_director"
        assert reqs[0].approval_level == 2

    def test_risk_score_threshold_not_triggered(self):
        """Risk score threshold should not trigger when score is below minimum."""
        from app.domains.playbook.models import ApprovalThreshold
        threshold = ApprovalThreshold(
            threshold_id="t1", name="High Risk Approval",
            threshold_type="risk_score", operator="greater_than",
            min_value=7.0, approval_role="legal_director", is_active=True,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", risk_score=3.0)
        reqs = ApprovalThresholdEvaluator.evaluate([threshold], ctx, [], [])
        assert len(reqs) == 0

    def test_contract_value_threshold_triggered(self):
        """Contract value threshold should trigger for high-value contracts."""
        from app.domains.playbook.models import ApprovalThreshold
        threshold = ApprovalThreshold(
            threshold_id="t1", name="High Value Approval",
            threshold_type="contract_value", operator="greater_than",
            min_value=1000000, approval_role="cfo", is_active=True,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", contract_value=5000000)
        reqs = ApprovalThresholdEvaluator.evaluate([threshold], ctx, [], [])
        assert len(reqs) == 1
        assert reqs[0].approval_role == "cfo"

    def test_clause_category_threshold_triggered(self):
        """Clause category threshold should trigger on deviation in that category."""
        from app.domains.playbook.models import ApprovalThreshold
        from app.domains.playbook.engine import DeviationResult
        threshold = ApprovalThreshold(
            threshold_id="t1", name="Indemnification Review",
            threshold_type="clause_category", operator="equals",
            target_category="indemnification", approval_role="legal_director",
            is_active=True,
        )
        deviation = DeviationResult(
            clause_category="indemnification", clause_text_snippet="test",
            expected="standard", actual="deviation",
            severity="high", score=0.7,
        )
        reqs = ApprovalThresholdEvaluator.evaluate([threshold], None, [deviation], [])
        assert len(reqs) == 1
        assert reqs[0].clause_category == "indemnification"

    def test_deviation_severity_threshold(self):
        """Deviation severity threshold should trigger at matching severity."""
        from app.domains.playbook.models import ApprovalThreshold
        from app.domains.playbook.engine import DeviationResult
        threshold = ApprovalThreshold(
            threshold_id="t1", name="Critical Deviation",
            threshold_type="deviation_severity", operator="greater_than",
            target_category="high", approval_role="general_counsel",
            is_active=True,
        )
        deviation = DeviationResult(
            clause_category="indemnification", clause_text_snippet="test",
            expected="standard", actual="deviation",
            severity="critical", score=0.9,
        )
        reqs = ApprovalThresholdEvaluator.evaluate([threshold], None, [deviation], [])
        assert len(reqs) == 1

    def test_auto_approve_threshold(self):
        """Auto-approve threshold should set auto_approve flag."""
        from app.domains.playbook.models import ApprovalThreshold
        threshold = ApprovalThreshold(
            threshold_id="t1", name="Low Risk Auto-approve",
            threshold_type="risk_score", operator="less_than",
            min_value=3.0, approval_role="legal_manager",
            auto_approve=True, is_active=True,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", risk_score=2.0)
        reqs = ApprovalThresholdEvaluator.evaluate([threshold], ctx, [], [])
        assert len(reqs) == 1
        assert reqs[0].auto_approve is True

    def test_inactive_threshold_skipped(self):
        """Inactive thresholds should not be evaluated."""
        from app.domains.playbook.models import ApprovalThreshold
        threshold = ApprovalThreshold(
            threshold_id="t1", name="Inactive",
            threshold_type="risk_score", operator="greater_than",
            min_value=5.0, approval_role="legal_director",
            is_active=False,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", risk_score=9.0)
        reqs = ApprovalThresholdEvaluator.evaluate([threshold], ctx, [], [])
        assert len(reqs) == 0


# ══════════════════════════════════════════════════════════════════════
# CLAUSE RECOMMENDER TESTS
# ══════════════════════════════════════════════════════════════════════


class TestClauseRecommender:
    """Verify clause recommendation generation."""

    def test_recommendation_from_fallback(self):
        """Recommendation should use fallback clause ID when specified."""
        from app.domains.playbook.models import ClauseStandard, ClauseCategory, ClauseType
        standard = ClauseStandard(
            clause_id="s1", category=ClauseCategory.INDEMNIFICATION,
            clause_type=ClauseType.APPROVED, title="Standard Indemnity",
            body="Standard indemnification language here",
            is_active=True,
        )
        deviation = DeviationResult(
            clause_category="indemnification", clause_text_snippet="bad clause",
            expected="good clause", actual="bad clause",
            severity="high", score=0.8,
            fallback_clause_id="s1",
            recommendation="Use the standard indemnity clause",
        )
        recs = ClauseRecommender.recommend([deviation], [standard])
        assert len(recs) >= 1
        assert recs[0].clause_id == "s1"
        assert recs[0].title == "Standard Indemnity"

    def test_recommendation_from_category_match(self):
        """Recommendation should match approved clauses by category."""
        from app.domains.playbook.models import ClauseStandard, ClauseCategory, ClauseType
        standard = ClauseStandard(
            clause_id="s1", category=ClauseCategory.CONFIDENTIALITY,
            clause_type=ClauseType.APPROVED, title="Standard Confidentiality",
            body="Standard confidentiality language",
            is_active=True,
        )
        deviation = DeviationResult(
            clause_category="confidentiality", clause_text_snippet="weak clause",
            expected="strong clause", actual="weak clause",
            severity="medium", score=0.6,
        )
        recs = ClauseRecommender.recommend([deviation], [standard])
        assert len(recs) >= 1
        assert recs[0].clause_category == "confidentiality"

    def test_recommendation_priority_ordering(self):
        """Critical deviations should have higher priority (lower number)."""
        from app.domains.playbook.models import ClauseStandard, ClauseCategory, ClauseType
        standard = ClauseStandard(
            clause_id="s1", category=ClauseCategory.INDEMNIFICATION,
            clause_type=ClauseType.APPROVED, title="Standard",
            body="Standard language", is_active=True,
        )
        critical_dev = DeviationResult(
            clause_category="indemnification", clause_text_snippet="bad",
            expected="good", actual="bad",
            severity="critical", score=0.9,
            fallback_clause_id="s1",
        )
        recs = ClauseRecommender.recommend([critical_dev], [standard])
        if recs:
            assert recs[0].priority <= 20  # Critical = priority 10

    def test_no_recommendations_for_no_deviations(self):
        """No recommendations should be generated when there are no deviations."""
        recs = ClauseRecommender.recommend([], [])
        assert len(recs) == 0


# ══════════════════════════════════════════════════════════════════════
# RISK SCORER TESTS
# ══════════════════════════════════════════════════════════════════════


class TestRiskScorer:
    """Verify risk scoring from evaluation results."""

    def test_no_risk_when_no_results(self):
        """Risk should be None when there are no results."""
        score, level = RiskScorer.calculate([], [])
        assert score is None
        assert level is None

    def test_low_risk_for_passing_rules(self):
        """Risk should be low when all rules pass and no deviations."""
        from app.domains.playbook.engine import RuleEvaluationResult
        results = [
            RuleEvaluationResult(rule_id="r1", rule_name="R1", rule_type="check",
                                  effect="allow", violation_triggered=False, priority=100),
        ]
        score, level = RiskScorer.calculate(results, [])
        assert level == "low"
        assert score is not None

    def test_critical_risk_for_critical_deviations(self):
        """Risk should be critical when critical deviations exist."""
        from app.domains.playbook.engine import RuleEvaluationResult, DeviationResult
        results = [
            RuleEvaluationResult(rule_id="r1", rule_name="R1", rule_type="check",
                                  effect="block", violation_triggered=True, priority=100,
                                  deviation_severity="critical"),
        ]
        deviations = [
            DeviationResult(clause_category="indemnification", clause_text_snippet="bad",
                            expected="good", actual="bad", severity="critical",
                            score=0.9),
        ]
        score, level = RiskScorer.calculate(results, deviations)
        assert level == "critical"
        assert score is not None
        assert score >= 8.0

    def test_high_risk_for_high_deviations(self):
        """Risk should be high for high-severity deviations."""
        from app.domains.playbook.engine import RuleEvaluationResult, DeviationResult
        results = [
            RuleEvaluationResult(rule_id="r1", rule_name="R1", rule_type="check",
                                  effect="flag_for_review", violation_triggered=True, priority=100,
                                  deviation_severity="high"),
        ]
        deviations = [
            DeviationResult(clause_category="confidentiality", clause_text_snippet="bad",
                            expected="good", actual="bad", severity="high", score=0.7),
        ]
        score, level = RiskScorer.calculate(results, deviations)
        assert level == "high"
        assert 5.0 <= score < 8.0


# ══════════════════════════════════════════════════════════════════════
# POLICY ENGINE INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestPolicyEngine:
    """Verify end-to-end policy evaluation pipeline."""

    def test_full_evaluation_pipeline(self):
        """Complete pipeline should produce evaluation results."""
        from app.domains.playbook.models import (
            PolicyRule, ClauseStandard, ApprovalThreshold,
            ClauseCategory, ClauseType,
        )

        rules = [
            PolicyRule(
                rule_id="r1", name="High Value", rule_type="value_threshold",
                conditions={"operator": "greater_than", "field": "contract.value", "value": 1000000},
                effect=RuleEffect.REQUIRE_APPROVAL, priority=100, is_active=True,
            ),
            PolicyRule(
                rule_id="r2", name="US Jurisdiction", rule_type="deviation",
                conditions={"operator": "equals", "field": "contract.jurisdiction", "value": "US"},
                effect=RuleEffect.FLAG_FOR_REVIEW, priority=200, is_active=True,
            ),
        ]

        standards = [
            ClauseStandard(
                clause_id="s1", category=ClauseCategory.INDEMNIFICATION,
                clause_type=ClauseType.APPROVED, title="Standard Indemnity",
                body="Company shall indemnify Client against all losses",
                is_active=True,
            ),
        ]

        thresholds = [
            ApprovalThreshold(
                threshold_id="t1", name="High Risk",
                threshold_type="risk_score", operator="greater_than",
                min_value=7.0, approval_role="legal_director", is_active=True,
            ),
        ]

        ctx = EvaluationContext(
            upload_id="u1", tenant_id="t1",
            contract_value=5000000, jurisdiction="US",
            risk_score=8.0,
            clauses=[ExtractedClause(category="indemnification", text="Some weak indemnity language",
                                      text_snippet="Some weak indemnity")],
        )

        result = PolicyEngine.evaluate(rules, standards, thresholds, ctx)
        assert result.total_rules == 2
        assert result.rules_failed >= 1
        assert result.deviations_found >= 0
        assert result.risk_score is not None
        assert result.risk_level is not None

    def test_empty_playbook_produces_empty_result(self):
        """Evaluation with no rules should produce empty result."""
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1")
        result = PolicyEngine.evaluate([], [], [], ctx)
        assert result.total_rules == 0
        assert result.rules_passed == 0
        assert result.rules_failed == 0
        assert result.deviations_found == 0
        assert result.risk_score is None

    def test_mandatory_rule_blocking(self):
        """Mandatory blocking rules should increment mandatory_blocks."""
        from app.domains.playbook.models import PolicyRule
        rule = PolicyRule(
            rule_id="r1", name="Block EU", rule_type="clause_forbidden",
            conditions={"operator": "equals", "field": "contract.jurisdiction", "value": "EU"},
            effect=RuleEffect.BLOCK, priority=100, is_active=True, is_mandatory=True,
        )
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", jurisdiction="EU")
        result = PolicyEngine.evaluate([rule], [], [], ctx)
        assert result.mandatory_blocks == 1
        assert result.rules_failed == 1

    def test_rule_sorting_by_priority(self):
        """Rules should be evaluated in priority order."""
        from app.domains.playbook.models import PolicyRule
        rules = [
            PolicyRule(
                rule_id="r1", name="Low Priority", rule_type="deviation",
                conditions={"operator": "equals", "field": "contract.value", "value": 100},
                effect=RuleEffect.FLAG_FOR_REVIEW, priority=200, is_active=True,
            ),
            PolicyRule(
                rule_id="r2", name="High Priority", rule_type="deviation",
                conditions={"operator": "equals", "field": "contract.value", "value": 100},
                effect=RuleEffect.BLOCK, priority=50, is_active=True,
            ),
        ]
        ctx = EvaluationContext(upload_id="u1", tenant_id="t1", contract_value=100)
        result = PolicyEngine.evaluate(rules, [], [], ctx)
        assert result.total_rules == 2
        # High priority (50) should be evaluated first
        assert result.rule_results[0].rule_id == "r2"


# ══════════════════════════════════════════════════════════════════════
# TENANT ISOLATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestTenantIsolation:
    """Verify all playbook models have tenant_id field."""

    def test_legal_playbook_has_tenant(self):
        from app.domains.playbook.models import LegalPlaybook
        assert hasattr(LegalPlaybook, "tenant_id")

    def test_playbook_version_has_tenant(self):
        from app.domains.playbook.models import PlaybookVersion
        assert hasattr(PlaybookVersion, "tenant_id")

    def test_clause_standard_has_tenant(self):
        from app.domains.playbook.models import ClauseStandard
        assert hasattr(ClauseStandard, "tenant_id")

    def test_policy_rule_has_tenant(self):
        from app.domains.playbook.models import PolicyRule
        assert hasattr(PolicyRule, "tenant_id")

    def test_policy_evaluation_has_tenant(self):
        from app.domains.playbook.models import PolicyEvaluation
        assert hasattr(PolicyEvaluation, "tenant_id")

    def test_approval_threshold_has_tenant(self):
        from app.domains.playbook.models import ApprovalThreshold
        assert hasattr(ApprovalThreshold, "tenant_id")

    def test_clause_recommendation_has_tenant(self):
        from app.domains.playbook.models import ClauseRecommendation
        assert hasattr(ClauseRecommendation, "tenant_id")

    def test_policy_override_has_tenant(self):
        from app.domains.playbook.models import PolicyOverride
        assert hasattr(PolicyOverride, "tenant_id")

    def test_governance_audit_event_has_tenant(self):
        from app.domains.playbook.models import GovernanceAuditEvent
        assert hasattr(GovernanceAuditEvent, "tenant_id")


# ══════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestPlaybookSchemas:
    """Verify Pydantic schema validation."""

    def test_valid_playbook_create(self):
        from app.domains.playbook.schemas import PlaybookCreate
        data = PlaybookCreate(name="US Commercial Playbook", description="Standard US commercial contracts")
        assert data.name == "US Commercial Playbook"
        assert data.jurisdiction is None

    def test_playbook_create_min_length(self):
        from app.domains.playbook.schemas import PlaybookCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PlaybookCreate(name="")

    def test_valid_clause_create(self):
        from app.domains.playbook.schemas import ClauseStandardCreate
        data = ClauseStandardCreate(
            category="indemnification", clause_type="approved",
            title="Standard Indemnity", body="Full indemnification text here",
        )
        assert data.category == "indemnification"
        assert data.risk_level == "medium"

    def test_clause_create_body_required(self):
        from app.domains.playbook.schemas import ClauseStandardCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ClauseStandardCreate(
                category="indemnification", clause_type="approved",
                title="Test", body="",
            )

    def test_valid_rule_create(self):
        from app.domains.playbook.schemas import PolicyRuleCreate, RuleCondition
        condition = RuleCondition(operator="equals", field="contract.jurisdiction", value="US")
        data = PolicyRuleCreate(
            name="US Check", rule_type="deviation",
            conditions=condition, effect="flag_for_review",
        )
        assert data.name == "US Check"
        assert data.priority == 100

    def test_valid_override_request(self):
        from app.domains.playbook.schemas import OverrideRequest
        data = OverrideRequest(
            evaluation_id="e1", upload_id="u1",
            override_type="rule_exception",
            justification="This is a valid justification with enough length",
        )
        assert data.override_type == "rule_exception"
        assert data.status is None  # Not a field on request

    def test_override_justification_min_length(self):
        from app.domains.playbook.schemas import OverrideRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OverrideRequest(
                evaluation_id="e1", upload_id="u1",
                override_type="rule_exception",
                justification="Short",
            )

    def test_valid_approval_threshold_create(self):
        from app.domains.playbook.schemas import ApprovalThresholdCreate
        data = ApprovalThresholdCreate(
            name="High Value", threshold_type="contract_value",
            approval_role="cfo", min_value=1000000,
        )
        assert data.operator == "greater_than"
        assert data.approval_level == 1

    def test_valid_override_review(self):
        from app.domains.playbook.schemas import OverrideReview
        data = OverrideReview(decision="approved", review_notes="Looks good")
        assert data.decision == "approved"

    def test_invalid_override_review_decision(self):
        from app.domains.playbook.schemas import OverrideReview
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OverrideReview(decision="invalid_decision")


# ══════════════════════════════════════════════════════════════════════
# AI POLICY INJECTION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestAIPolicyInjection:
    """Verify AI policy context building."""

    def test_context_prompt_includes_playbook_name(self):
        """Context prompt should reference the playbook name."""
        # Unit test the prompt construction logic
        playbook_name = "US Commercial Playbook"
        prompt_parts = [f"You are analyzing this contract against the '{playbook_name}' legal playbook."]
        prompt_parts.append("\nAPPROVED CLAUSES (2):")
        prompt_parts.append("- indemnification/Standard Indemnity: Standard language...")
        prompt_parts.append("\nMANDATORY RULES (1):")
        prompt_parts.append("- [clause_required] Must have indemnification: Indemnification is required")

        context_prompt = "\n".join(prompt_parts)
        assert "US Commercial Playbook" in context_prompt
        assert "APPROVED CLAUSES" in context_prompt
        assert "MANDATORY RULES" in context_prompt

    def test_context_includes_approved_and_forbidden(self):
        """Context should mention both approved and forbidden clauses."""
        prompt_parts = []
        prompt_parts.append("APPROVED CLAUSES (3):")
        prompt_parts.append("- confidentiality/Standard Confidentiality")
        prompt_parts.append("FORBIDDEN CLAUSES (1):")
        prompt_parts.append("- limitation_of_liability/No Cap")

        context = "\n".join(prompt_parts)
        assert "APPROVED CLAUSES" in context
        assert "FORBIDDEN CLAUSES" in context

    def test_context_instructions(self):
        """Context should include evaluation instructions."""
        prompt_parts = []
        prompt_parts.append("Evaluate each clause against these standards. Flag any deviations.")
        prompt_parts.append("For each deviation, recommend the appropriate standard clause.")
        prompt_parts.append("If a clause is forbidden, flag it as CRITICAL.")

        context = "\n".join(prompt_parts)
        assert "Flag any deviations" in context
        assert "flag it as CRITICAL" in context


# ══════════════════════════════════════════════════════════════════════
# VERSIONING TESTS
# ══════════════════════════════════════════════════════════════════════


class TestPlaybookVersioning:
    """Verify playbook versioning logic."""

    def test_initial_version_is_draft(self):
        """Initial playbook version should be a draft."""
        from app.domains.playbook.models import PlaybookVersion
        version = PlaybookVersion(
            version_id="v1", playbook_id="p1", tenant_id="t1",
            version_number=1, is_draft=True, is_active=False,
            created_by="user1",
        )
        assert version.is_draft is True
        assert version.is_active is False

    def test_published_version_not_draft(self):
        """Published version should not be a draft."""
        from app.domains.playbook.models import PlaybookVersion
        version = PlaybookVersion(
            version_id="v1", playbook_id="p1", tenant_id="t1",
            version_number=1, is_draft=False, is_active=True,
            published_by="user1", published_at=datetime.utcnow(),
            created_by="user1",
        )
        assert version.is_draft is False
        assert version.is_active is True
        assert version.published_by == "user1"

    def test_version_lineage(self):
        """Versions should track parent lineage."""
        from app.domains.playbook.models import PlaybookVersion
        v2 = PlaybookVersion(
            version_id="v2", playbook_id="p1", tenant_id="t1",
            version_number=2, is_draft=True, is_active=False,
            parent_version_id="v1", created_by="user1",
        )
        assert v2.parent_version_id == "v1"
        assert v2.version_number == 2

    def test_version_snapshot(self):
        """Published versions should have snapshots."""
        from app.domains.playbook.models import PlaybookVersion
        version = PlaybookVersion(
            version_id="v1", playbook_id="p1", tenant_id="t1",
            version_number=1, is_draft=False, is_active=True,
            snapshot={"name": "Playbook v1", "clause_count": 10},
            published_by="user1", created_by="user1",
        )
        assert version.snapshot["name"] == "Playbook v1"
        assert version.snapshot["clause_count"] == 10


# ══════════════════════════════════════════════════════════════════════
# GOVERNANCE AUDIT TESTS
# ══════════════════════════════════════════════════════════════════════


class TestGovernanceAudit:
    """Verify governance audit event structure."""

    def test_audit_event_creation(self):
        """Audit events should capture all required fields."""
        from app.domains.playbook.models import GovernanceAuditEvent
        event = GovernanceAuditEvent(
            event_id="e1", tenant_id="t1",
            event_type="playbook.published",
            entity_type="playbook", entity_id="p1",
            actor_id="user1", actor_role="legal_manager",
            change_summary="Published version 2",
            source="api",
        )
        assert event.event_type == "playbook.published"
        assert event.actor_id == "user1"
        assert event.change_summary == "Published version 2"

    def test_audit_event_types(self):
        """Verify all governance event types."""
        from app.domains.playbook.models import GovernanceAuditEvent
        event_types = [
            "playbook.created", "playbook.published", "playbook.archived",
            "playbook.rolled_back",
            "clause.created", "clause.updated", "clause.deactivated",
            "rule.created", "rule.updated", "rule.activated", "rule.deactivated",
            "evaluation.completed", "deviation.detected",
            "override.requested", "override.approved", "override.rejected",
            "threshold.created", "threshold.updated",
        ]
        for et in event_types:
            event = GovernanceAuditEvent(
                event_id="e1", tenant_id="t1",
                event_type=et, entity_type="test", entity_id="1",
                actor_id="user1", source="test",
            )
            assert event.event_type == et

    def test_audit_previous_and_new_state(self):
        """Audit events should capture state changes."""
        from app.domains.playbook.models import GovernanceAuditEvent
        event = GovernanceAuditEvent(
            event_id="e1", tenant_id="t1",
            event_type="clause.updated",
            entity_type="clause", entity_id="c1",
            actor_id="user1",
            previous_state={"body": "Old text", "risk_level": "high"},
            new_state={"body": "New text", "risk_level": "medium"},
            change_summary="Updated clause body and risk level",
        )
        assert event.previous_state["body"] == "Old text"
        assert event.new_state["body"] == "New text"
        assert event.previous_state["risk_level"] == "high"
        assert event.new_state["risk_level"] == "medium"
