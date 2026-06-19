"""Rule Evaluation Engine — evaluates policy rules against contract data.

Core capabilities:
- Conditional rule evaluation (AND/OR nesting, field comparison, regex, threshold)
- Deviation detection with severity scoring
- Approval threshold matching
- Clause recommendation generation
- Risk scoring from evaluation results
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.domains.playbook.models import (
    PolicyRule,
    RuleEffect,
    DeviationSeverity,
    ClauseStandard,
    ApprovalThreshold,
    ClauseCategory,
)

logger = logging.getLogger(__name__)


def _resolve_effect(effect: Any) -> str:
    """Safely resolve a rule effect to its string value.

    Handles both SQLAlchemy enum objects (with .value) and plain strings
    (from raw SQL inserts or deserialization).
    """
    if isinstance(effect, str):
        return effect
    if hasattr(effect, 'value'):
        return effect.value
    return str(effect)


@dataclass
class EvaluationContext:
    """Context for evaluating rules against a contract."""
    upload_id: str
    tenant_id: str
    review_id: Optional[str] = None

    # Contract data extracted from AI analysis
    contract_value: Optional[float] = None
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    counterparty: Optional[str] = None

    # Clause data — extracted clauses from the contract
    clauses: list[ExtractedClause] = field(default_factory=list)

    # AI findings that may trigger rules
    risk_score: Optional[float] = None
    findings: list[dict] = field(default_factory=list)

    # Metadata
    correlation_id: Optional[str] = None


@dataclass
class ExtractedClause:
    """A clause extracted from a contract during AI analysis."""
    category: str
    text: str
    text_snippet: str
    confidence: float = 1.0
    page_numbers: list[int] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a single rule against the context."""
    rule_id: str
    rule_name: str
    rule_type: str
    effect: str
    violation_triggered: bool
    priority: int
    details: Optional[str] = None
    deviation_severity: Optional[str] = None
    matched_clause_category: Optional[str] = None
    matched_clause_text: Optional[str] = None

    @property
    def matched(self) -> bool:
        """Alias for violation_triggered — backward compatibility."""
        return self.violation_triggered

    @matched.setter
    def matched(self, value: bool) -> None:
        self.violation_triggered = value


@dataclass
class DeviationResult:
    """A detected deviation between contract clause and standard."""
    clause_category: str
    clause_text_snippet: str
    expected: str
    actual: str
    severity: str
    score: float
    rule_id: Optional[str] = None
    recommendation: Optional[str] = None
    fallback_clause_id: Optional[str] = None


@dataclass
class EvaluationResult:
    """Complete evaluation result for a contract against a playbook."""
    total_rules: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    deviations: list[DeviationResult] = field(default_factory=list)
    rule_results: list[RuleEvaluationResult] = field(default_factory=list)
    approval_requirements: list[ApprovalRequirement] = field(default_factory=list)
    recommendations: list[ClauseRecommendation] = field(default_factory=list)
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    mandatory_blocks: int = 0
    approval_required: int = 0


@dataclass
class ApprovalRequirement:
    """An approval requirement triggered by a rule or threshold."""
    threshold_id: Optional[str] = None
    rule_id: Optional[str] = None
    approval_role: str = ""
    approval_level: int = 1
    reason: str = ""
    clause_category: Optional[str] = None
    auto_approve: bool = False


@dataclass
class ClauseRecommendation:
    """A recommended clause from the playbook for a deviation."""
    clause_id: Optional[str] = None
    clause_category: str = ""
    clause_type: str = ""
    title: str = ""
    body: str = ""
    rationale: Optional[str] = None
    confidence_score: Optional[float] = None
    risk_reduction: Optional[str] = None
    priority: int = 50
    deviation_id: Optional[str] = None
    replaces_clause_text: Optional[str] = None


class RuleEvaluator:
    """Evaluates policy rules against contract context.

    Supports:
    - Nested AND/OR conditions
    - Field comparison (equals, contains, greater_than, etc.)
    - Regex matching
    - Threshold evaluation
    - Clause existence checks
    """

    @staticmethod
    def evaluate_rule(rule: PolicyRule, ctx: EvaluationContext) -> RuleEvaluationResult:
        """Evaluate a single rule against the evaluation context."""
        try:
            conditions = rule.conditions or {}
            violation_triggered = RuleEvaluator._evaluate_conditions(conditions, rule, ctx)

            severity = None
            details = None
            matched_category = None
            matched_text = None

            if violation_triggered:
                # Determine deviation severity from effect config
                if rule.effect in (RuleEffect.FLAG_FOR_REVIEW, RuleEffect.BLOCK, RuleEffect.REQUIRE_APPROVAL,
                                    RuleEffect.REQUIRE_MANDATORY_CLAUSE, RuleEffect.ESCALATE):
                    severity = RuleEvaluator._determine_severity(rule, ctx)
                    details = f"Rule '{rule.name}' triggered: {_resolve_effect(rule.effect)}"

                # Find matching clause context
                if rule.target_category:
                    for clause in ctx.clauses:
                        if clause.category == rule.target_category:
                            matched_category = clause.category
                            matched_text = clause.text_snippet[:200]
                            break

            return RuleEvaluationResult(
                rule_id=str(rule.rule_id),
                rule_name=rule.name,
                rule_type=rule.rule_type,
                effect=_resolve_effect(rule.effect),
                violation_triggered=violation_triggered,
                priority=rule.priority,
                details=details,
                deviation_severity=severity,
                matched_clause_category=matched_category,
                matched_clause_text=matched_text,
            )
        except Exception as exc:
            logger.error("Rule evaluation failed for rule %s: %s", rule.rule_id, exc)
            return RuleEvaluationResult(
                rule_id=str(rule.rule_id),
                rule_name=rule.name,
                rule_type=rule.rule_type,
                effect=_resolve_effect(rule.effect),
                violation_triggered=False,
                priority=rule.priority,
                details=f"Evaluation error: {exc}",
            )

    @staticmethod
    def _evaluate_conditions(conditions: dict, rule: PolicyRule, ctx: EvaluationContext) -> bool:
        """Recursively evaluate nested conditions."""
        operator = conditions.get("operator", "and")
        field = conditions.get("field")
        value = conditions.get("value")
        nested = conditions.get("conditions", [])

        # If there are nested conditions, evaluate as AND/OR group
        if nested:
            results = [RuleEvaluator._evaluate_conditions(c, rule, ctx) for c in nested]
            if operator.lower() == "or":
                return any(results)
            return all(results)

        # Leaf condition — evaluate against context
        if not field:
            return True

        return RuleEvaluator._evaluate_leaf_condition(operator, field, value, rule, ctx)

    @staticmethod
    def _evaluate_leaf_condition(operator: str, field: str, value: Any,
                                  rule: PolicyRule, ctx: EvaluationContext) -> bool:
        """Evaluate a single leaf condition."""
        # Resolve field value from context
        field_value = RuleEvaluator._resolve_field(field, ctx, rule)

        if field_value is None and operator not in ("not_exists", "exists"):
            return False

        op = operator.lower()

        if op == "equals":
            return str(field_value) == str(value)
        elif op == "not_equals":
            return str(field_value) != str(value)
        elif op == "contains":
            return str(value).lower() in str(field_value).lower()
        elif op == "not_contains":
            return str(value).lower() not in str(field_value).lower()
        elif op == "greater_than":
            try:
                return float(field_value) > float(value)
            except (TypeError, ValueError):
                return False
        elif op == "less_than":
            try:
                return float(field_value) < float(value)
            except (TypeError, ValueError):
                return False
        elif op == "in":
            if isinstance(value, list):
                return str(field_value) in [str(v) for v in value]
            return False
        elif op == "not_in":
            if isinstance(value, list):
                return str(field_value) not in [str(v) for v in value]
            return False
        elif op == "matches_regex":
            try:
                return bool(re.search(str(value), str(field_value), re.IGNORECASE))
            except re.error:
                return False
        elif op == "exists":
            if isinstance(field_value, bool):
                return field_value
            return field_value is not None
        elif op == "not_exists":
            if isinstance(field_value, bool):
                return not field_value
            return field_value is None
        elif op == "meets_threshold":
            try:
                return float(field_value) >= float(value)
            except (TypeError, ValueError):
                return False

        return False

    @staticmethod
    def _resolve_field(field: str, ctx: EvaluationContext, rule: PolicyRule) -> Any:
        """Resolve a field path from the evaluation context."""
        # Contract-level fields
        if field == "contract.value":
            return ctx.contract_value
        elif field == "contract.jurisdiction":
            return ctx.jurisdiction
        elif field == "contract.industry":
            return ctx.industry
        elif field == "contract.counterparty":
            return ctx.counterparty
        elif field == "contract.risk_score":
            return ctx.risk_score

        # Clause-level fields
        elif field == "clause.category":
            if rule.target_category and ctx.clauses:
                for c in ctx.clauses:
                    if c.category == rule.target_category:
                        return c.category
            return rule.target_category
        elif field == "clause.exists":
            if rule.target_category:
                return any(c.category == rule.target_category for c in ctx.clauses)
            return bool(ctx.clauses)
        elif field == "clause.count":
            if rule.target_category:
                return sum(1 for c in ctx.clauses if c.category == rule.target_category)
            return len(ctx.clauses)

        # Finding-level fields
        elif field.startswith("finding."):
            finding_field = field.replace("finding.", "")
            if ctx.findings:
                return RuleEvaluator._find_in_findings(finding_field, ctx.findings)
            return None

        # Rule metadata
        elif field == "rule.effect":
            return _resolve_effect(rule.effect)
        elif field == "rule.rule_type":
            return rule.rule_type
        elif field.startswith("rule.metadata."):
            meta_key = field.replace("rule.metadata.", "")
            return rule.metadata.get(meta_key) if rule.metadata else None

        return None

    @staticmethod
    def _find_in_findings(field: str, findings: list[dict]) -> Any:
        """Search for a field across all findings."""
        if field == "count":
            return len(findings)
        elif field == "max_severity":
            severities = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
            max_sev = "info"
            for f in findings:
                sev = f.get("severity", "info")
                if severities.get(sev, 0) > severities.get(max_sev, 0):
                    max_sev = sev
            return max_sev
        elif field == "high_count":
            return sum(1 for f in findings if f.get("severity") in ("critical", "high"))

        # Return first finding's field match
        for f in findings:
            if field in f:
                return f[field]
        return None

    @staticmethod
    def _determine_severity(rule: PolicyRule, ctx: EvaluationContext) -> str:
        """Determine deviation severity based on rule config and context."""
        config = rule.effect_config or {}

        # Check for explicit severity in config
        if "severity" in config:
            return config["severity"]

        # Derive from rule type
        severity_map = {
            "clause_forbidden": "critical",
            "clause_required": "high",
            "deviation": "medium",
            "risk_threshold": "high",
            "value_threshold": "medium",
            "approval": "medium",
        }
        return severity_map.get(rule.rule_type, "medium")


class DeviationDetector:
    """Detects deviations between contract clauses and playbook standards."""

    def __init__(self, deviation_thresholds: Optional[dict] = None):
        """Configure with playbook-level thresholds.

        Args:
            deviation_thresholds: Dict with keys ``similarity`` (default 0.5)
                and ``forbidden_similarity`` (default 0.3). Pass ``None`` to
                use defaults.
        """
        self.similarity_threshold = (
            deviation_thresholds.get("similarity", 0.5)
            if deviation_thresholds else 0.5
        )
        self.forbidden_similarity_threshold = (
            deviation_thresholds.get("forbidden_similarity", 0.3)
            if deviation_thresholds else 0.3
        )

    def detect_deviations(
        self,
        clauses: list[ExtractedClause],
        standards: list[ClauseStandard],
        rule_results: list[RuleEvaluationResult],
    ) -> list[DeviationResult]:
        """Compare extracted clauses against playbook standards to find deviations."""
        deviations: list[DeviationResult] = []

        def _clause_type(std: ClauseStandard) -> str:
            ct = std.clause_type
            return ct.value if hasattr(ct, "value") else str(ct)

        def _category(std: ClauseStandard) -> str:
            cat = std.category
            return cat.value if hasattr(cat, "value") else str(cat)

        # Build standard lookup by category (approved / preferred)
        standards_by_category: dict[str, list[ClauseStandard]] = {}
        for std in standards:
            if _clause_type(std) in ("approved", "preferred") and std.is_active:
                cat = _category(std)
                standards_by_category.setdefault(cat, []).append(std)

        # Check each extracted clause against standards
        for clause in clauses:
            cat = clause.category
            if cat in standards_by_category:
                for std in standards_by_category[cat]:
                    deviation = self._compare_clause(clause, std)
                    if deviation:
                        deviations.append(deviation)

            for std in standards:
                if not std.is_active or _clause_type(std) != "forbidden":
                    continue
                if _category(std) != cat:
                    continue
                deviation = self._compare_clause(clause, std)
                if deviation:
                    deviations.append(deviation)

        # Add deviations from rule results
        for result in rule_results:
            if result.violation_triggered and result.deviation_severity:
                if not any(d.rule_id == result.rule_id for d in deviations):
                    deviations.append(DeviationResult(
                        clause_category=result.matched_clause_category or "",
                        clause_text_snippet=result.matched_clause_text or "",
                        expected=f"Rule: {result.rule_name}",
                        actual=f"Violation: {result.details or 'Rule conditions matched'}",
                        severity=result.deviation_severity,
                        score=self._severity_to_score(result.deviation_severity),
                        rule_id=result.rule_id,
                    ))

        return deviations

    def _compare_clause(self, clause: ExtractedClause, standard: ClauseStandard) -> Optional[DeviationResult]:
        """Compare an extracted clause against a clause standard."""
        # Simple text overlap comparison
        clause_text = clause.text.lower()
        standard_text = standard.body.lower()

        # Token overlap score
        clause_tokens = set(clause_text.split())
        standard_tokens = set(standard_text.split())

        if not standard_tokens:
            return None

        overlap = len(clause_tokens & standard_tokens)
        total = len(clause_tokens | standard_tokens)
        jaccard = overlap / total if total > 0 else 0

        std_type = (
            standard.clause_type.value
            if hasattr(standard.clause_type, "value")
            else str(standard.clause_type)
        )

        # Check for forbidden language
        if std_type == "forbidden":
            if jaccard > self.forbidden_similarity_threshold:  # Configurable threshold
                return DeviationResult(
                    clause_category=clause.category,
                    clause_text_snippet=clause.text_snippet[:200],
                    expected=f"Forbidden clause type: {standard.title}",
                    actual=f"Contract contains forbidden language (similarity: {jaccard:.2f})",
                    severity="critical",
                    score=1.0 - jaccard,
                    fallback_clause_id=str(standard.clause_id) if standard.fallback_clause_ids else None,
                    recommendation=f"Remove forbidden language. {standard.summary or ''}",
                )
            return None

        # For approved/preferred clauses — check if contract clause matches
        if std_type in ("approved", "preferred"):
            if jaccard < self.similarity_threshold:  # Configurable threshold
                severity = "high" if standard.clause_type == "approved" else "medium"
                return DeviationResult(
                    clause_category=clause.category,
                    clause_text_snippet=clause.text_snippet[:200],
                    expected=f"{(standard.clause_type.value if hasattr(standard.clause_type, 'value') else standard.clause_type).title()} clause: {standard.title}",
                    actual=f"Contract clause deviates from standard (similarity: {jaccard:.2f})",
                    severity=severity,
                    score=1.0 - jaccard,
                    fallback_clause_id=str(standard.clause_id),
                    recommendation=f"Consider using approved language. {standard.summary or ''}",
                )

        return None

    def _severity_to_score(self, severity: str) -> float:
        mapping = {"critical": 0.9, "high": 0.7, "medium": 0.5, "low": 0.3, "info": 0.1}
        return mapping.get(severity, 0.5)


class ApprovalThresholdEvaluator:
    """Evaluates approval thresholds against contract context."""

    @staticmethod
    def evaluate(
        thresholds: list[ApprovalThreshold],
        ctx: EvaluationContext,
        deviations: list[DeviationResult],
        rule_results: list[RuleEvaluationResult],
    ) -> list[ApprovalRequirement]:
        """Evaluate which approval thresholds are triggered."""
        requirements: list[ApprovalRequirement] = []

        for threshold in thresholds:
            if not threshold.is_active:
                continue

            triggered = False
            reason = ""

            if threshold.threshold_type == "risk_score" and ctx.risk_score is not None:
                triggered = ApprovalThresholdEvaluator._compare_value(
                    ctx.risk_score, threshold.operator, threshold.min_value, threshold.max_value,
                )
                reason = f"Risk score {ctx.risk_score} triggered threshold '{threshold.name}'"

            elif threshold.threshold_type == "contract_value" and ctx.contract_value is not None:
                triggered = ApprovalThresholdEvaluator._compare_value(
                    ctx.contract_value, threshold.operator, threshold.min_value, threshold.max_value,
                )
                reason = f"Contract value {ctx.contract_value} triggered threshold '{threshold.name}'"

            elif threshold.threshold_type == "clause_category":
                if threshold.target_category:
                    for deviation in deviations:
                        if deviation.clause_category == threshold.target_category:
                            triggered = True
                            reason = f"Deviation in clause '{threshold.target_category}' triggered threshold '{threshold.name}'"
                            break
                    if not triggered:
                        for result in rule_results:
                            if result.violation_triggered and result.matched_clause_category == threshold.target_category:
                                triggered = True
                                reason = f"Rule match in clause '{threshold.target_category}' triggered threshold '{threshold.name}'"
                                break

            elif threshold.threshold_type == "deviation_severity":
                for deviation in deviations:
                    if ApprovalThresholdEvaluator._compare_severity(deviation.severity, threshold):
                        triggered = True
                        reason = f"Deviation severity '{deviation.severity}' triggered threshold '{threshold.name}'"
                        break

            elif threshold.threshold_type == "override":
                # Override thresholds are checked when an override is requested
                pass

            if triggered:
                requirements.append(ApprovalRequirement(
                    threshold_id=str(threshold.threshold_id),
                    approval_role=threshold.approval_role,
                    approval_level=threshold.approval_level,
                    reason=reason,
                    auto_approve=threshold.auto_approve,
                    clause_category=threshold.target_category,
                ))

        return requirements

    @staticmethod
    def _compare_value(value: float, operator: str, min_val: Optional[float],
                        max_val: Optional[float]) -> bool:
        op = operator.lower()
        if op == "greater_than" and min_val is not None:
            return value > min_val
        elif op == "less_than" and min_val is not None:
            return value < min_val
        elif op == "equals" and min_val is not None:
            return value == min_val
        elif op == "in_range" and min_val is not None and max_val is not None:
            return min_val <= value <= max_val
        return False

    @staticmethod
    def _compare_severity(severity: str, threshold: ApprovalThreshold) -> bool:
        severity_order = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
        sev_val = severity_order.get(severity, 0)
        threshold_val = severity_order.get(threshold.target_category or "medium", 3)

        op = threshold.operator.lower()
        if op == "greater_than":
            return sev_val > threshold_val
        elif op == "less_than":
            return sev_val < threshold_val
        elif op == "equals":
            return sev_val == threshold_val
        elif op == "in_range":
            min_v = severity_order.get(str(threshold.min_value or "low"), 1)
            max_v = severity_order.get(str(threshold.max_value or "critical"), 5)
            return min_v <= sev_val <= max_v
        return sev_val >= threshold_val


class ClauseRecommender:
    """Generates clause recommendations based on deviations and standards."""

    @staticmethod
    def recommend(
        deviations: list[DeviationResult],
        standards: list[ClauseStandard],
    ) -> list[ClauseRecommendation]:
        """Generate clause recommendations for detected deviations."""
        recommendations: list[ClauseRecommendation] = []

        # Build standard lookup
        standards_by_id: dict[str, ClauseStandard] = {}
        for std in standards:
            standards_by_id[str(std.clause_id)] = std

        for deviation in deviations:
            # If a fallback clause is specified, recommend it
            if deviation.fallback_clause_id and deviation.fallback_clause_id in standards_by_id:
                std = standards_by_id[deviation.fallback_clause_id]
                recommendations.append(ClauseRecommendation(
                    clause_id=str(std.clause_id),
                    clause_category=std.category.value if hasattr(std.category, 'value') else str(std.category),
                    clause_type=std.clause_type.value if hasattr(std.clause_type, 'value') else str(std.clause_type),
                    title=std.title,
                    body=std.body,
                    rationale=deviation.recommendation or f"Recommended alternative for {deviation.clause_category} deviation",
                    confidence_score=1.0 - deviation.score,
                    risk_reduction=deviation.severity,
                    priority=ClauseRecommender._severity_to_priority(deviation.severity),
                    replaces_clause_text=deviation.clause_text_snippet,
                ))

            # Also recommend approved/preferred standards for the same category
            elif deviation.clause_category:
                for std in standards:
                    cat = std.category.value if hasattr(std.category, 'value') else str(std.category)
                    if cat == deviation.clause_category and std.clause_type in ("approved", "preferred"):
                        if not any(r.clause_id == str(std.clause_id) for r in recommendations):
                            recommendations.append(ClauseRecommendation(
                                clause_id=str(std.clause_id),
                                clause_category=cat,
                                clause_type=std.clause_type.value if hasattr(std.clause_type, 'value') else str(std.clause_type),
                                title=std.title,
                                body=std.body,
                                rationale=deviation.recommendation or f"Standard clause for {deviation.clause_category}",
                                confidence_score=0.7,
                                risk_reduction=deviation.severity,
                                priority=ClauseRecommender._severity_to_priority(deviation.severity),
                                replaces_clause_text=deviation.clause_text_snippet,
                            ))

        # Sort by priority (lower = more important)
        recommendations.sort(key=lambda r: r.priority)
        return recommendations

    @staticmethod
    def _severity_to_priority(severity: str) -> int:
        mapping = {"critical": 10, "high": 20, "medium": 50, "low": 80, "info": 100}
        return mapping.get(severity, 50)


class RiskScorer:
    """Calculates overall risk score from evaluation results.

    Uses configurable severity weights and risk level thresholds from the
    playbook configuration. Falls back to sensible defaults if not provided.
    """

    def __init__(self, risk_weights: Optional[dict] = None,
                 risk_levels: Optional[dict] = None):
        self.weights = dict(risk_weights or {
            "critical": 5.0, "high": 3.0, "medium": 2.0,
            "low": 1.0, "info": 0.1,
        })
        self.levels = dict(risk_levels or {
            "critical": 8.0, "high": 5.0, "medium": 3.0,
        })

    def calculate(
        self,
        rule_results: list[RuleEvaluationResult],
        deviations: list[DeviationResult],
    ) -> tuple[Optional[float], Optional[str]]:
        """Calculate risk score and level from evaluation results."""
        if not rule_results and not deviations:
            return None, None

        total_score = 0.0
        weights = 0.0

        # Prefer explicit deviations when present (avoids double-counting rule + deviation)
        if deviations:
            rule_results = []

        # Score from rule results
        for result in rule_results:
            if result.violation_triggered:
                sev = (result.deviation_severity or "low").lower()
                weight = self.weights.get(sev, 1.0)
                total_score += weight * 10.0  # Base score per violation
                weights += weight

        # Score from deviations
        for deviation in deviations:
            sev = (deviation.severity or "low").lower()
            weight = self.weights.get(sev, 1.0)
            total_score += weight * deviation.score * 10.0
            weights += weight

        if weights == 0:
            return 0.0, "low"

        normalized = total_score / weights

        # Determine risk level from configurable thresholds
        crit = self.levels.get("critical", 8.0)
        hi = self.levels.get("high", 5.0)
        med = self.levels.get("medium", 3.0)
        if normalized >= crit:
            level = "critical"
        elif normalized >= hi:
            level = "high"
        elif normalized >= med:
            level = "medium"
        else:
            level = "low"

        return round(normalized, 2), level


class PolicyEngine:
    """Orchestrates the full policy evaluation pipeline.

    Pipeline:
    1. Load active rules and standards for the playbook
    2. Evaluate each rule against contract context
    3. Detect clause deviations
    4. Evaluate approval thresholds
    5. Generate clause recommendations
    6. Calculate risk score
    """

    @staticmethod
    def evaluate(
        rules: list[PolicyRule],
        standards: list[ClauseStandard],
        thresholds: list[ApprovalThreshold],
        ctx: EvaluationContext,
        deviation_thresholds: Optional[dict] = None,
        risk_weights: Optional[dict] = None,
        risk_levels: Optional[dict] = None,
    ) -> EvaluationResult:
        """Run full policy evaluation pipeline.

        Args:
            rules: Active policy rules to evaluate.
            standards: Clause standards for deviation detection.
            thresholds: Approval thresholds.
            ctx: Evaluation context with contract data.
            deviation_thresholds: Optional playbook config for similarity
                thresholds (keys: ``similarity``, ``forbidden_similarity``).
            risk_weights: Optional playbook config for severity weights
                (keys: ``critical``, ``high``, ``medium``, ``low``, ``info``).
            risk_levels: Optional playbook config for risk level boundaries
                (keys: ``critical``, ``high``, ``medium``).
        """
        result = EvaluationResult()

        # 1. Sort rules by priority
        sorted_rules = sorted(rules, key=lambda r: r.priority)

        # 2. Evaluate each rule
        for rule in sorted_rules:
            if not rule.is_active:
                continue

            rule_result = RuleEvaluator.evaluate_rule(rule, ctx)
            result.rule_results.append(rule_result)
            result.total_rules += 1

            if rule_result.violation_triggered:
                result.rules_failed += 1
                if _resolve_effect(rule.effect) == "block":
                    result.mandatory_blocks += 1
                if _resolve_effect(rule.effect) == "require_approval":
                    result.approval_required += 1
            else:
                result.rules_passed += 1

        # 3. Detect deviations with configurable thresholds
        detector = DeviationDetector(deviation_thresholds)
        result.deviations = detector.detect_deviations(
            ctx.clauses, standards, result.rule_results,
        )

        # 4. Evaluate approval thresholds
        approval_reqs = ApprovalThresholdEvaluator.evaluate(
            thresholds, ctx, result.deviations, result.rule_results,
        )
        result.approval_requirements = approval_reqs
        result.approval_required += len(approval_reqs)

        # 5. Generate clause recommendations
        result.recommendations = ClauseRecommender.recommend(result.deviations, standards)

        # 6. Calculate risk score with configurable weights
        scorer = RiskScorer(risk_weights, risk_levels)
        result.risk_score, result.risk_level = scorer.calculate(
            result.rule_results, result.deviations,
        )

        # 7. Summary counts
        result.deviations_found = len(result.deviations)

        return result
