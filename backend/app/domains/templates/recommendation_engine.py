"""Clause Recommendation Engine — evaluates template/contract variables against
rules and returns suggested clauses from the clause library.

Architected as a platform service (not template-specific) so it works for:
- Create from Template
- Upload Existing Contract (after AI extraction)
- Future metadata import

The engine is deterministic (rule-based). An AI provider can be added later
without changing the generation workflow.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.templates.recommendation_models import (
    ClauseRecommendationRule,
    RecommendationAudit,
    RecommendationType,
    ConditionOperator,
)
from app.domains.templates.recommendation_schemas import (
    RecommendationContext,
    RecommendationResult,
    SuggestedClause,
)

logger = logging.getLogger(__name__)


class ConditionEvaluationError(Exception):
    """Raised when a condition cannot be evaluated."""


class RecommendationEngine:
    """Evaluates rules against variable values and returns suggested clauses.

    Usage:
        engine = RecommendationEngine(session, tenant_id)
        result = await engine.evaluate(context)
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def evaluate(
        self,
        context: RecommendationContext,
    ) -> RecommendationResult:
        """Evaluate all active rules against the given context.

        Args:
            context: Variable values, optional template/business unit scope.

        Returns:
            Sorted list of suggested clauses with reasons.
        """
        # Build query for active rules
        query = select(ClauseRecommendationRule).where(
            ClauseRecommendationRule.tenant_id == self.tenant_id,
            ClauseRecommendationRule.is_active == True,
        )

        # Apply optional template scope
        if context.template_id:
            query = query.where(
                or_(
                    ClauseRecommendationRule.template_id == context.template_id,
                    ClauseRecommendationRule.template_id.is_(None),
                )
            )

        # Apply effective date filter
        now = datetime.now(timezone.utc)
        query = query.where(
            or_(
                ClauseRecommendationRule.effective_from.is_(None),
                ClauseRecommendationRule.effective_from <= now,
            )
        ).where(
            or_(
                ClauseRecommendationRule.effective_to.is_(None),
                ClauseRecommendationRule.effective_to >= now,
            )
        )

        query = query.order_by(
            ClauseRecommendationRule.priority.desc(),
            ClauseRecommendationRule.created_at.asc(),
        )

        result = await self.session.execute(query)
        rules = result.scalars().all()

        variables = context.variable_values or {}
        matched: list[SuggestedClause] = []

        for rule in rules:
            try:
                if self._evaluate_condition(rule, variables):
                    clause = await self._build_suggested_clause(rule, variables)
                    if clause:
                        matched.append(clause)
                else:
                    # For IS_EMPTY and IS_NOT_EMPTY, also check if the key exists
                    if rule.operator in (ConditionOperator.IS_EMPTY.value, ConditionOperator.IS_NOT_EMPTY.value):
                        if rule.variable_key not in variables:
                            continue
            except ConditionEvaluationError as exc:
                logger.warning(
                    "Failed to evaluate rule %s (%s): %s",
                    rule.id, rule.name, exc,
                )
                continue
            except Exception as exc:
                logger.exception(
                    "Unexpected error evaluating rule %s (%s): %s",
                    rule.id, rule.name, exc,
                )
                continue

        # Sort by priority then recommendation type
        type_order = {"required": 0, "recommended": 1, "optional": 2}
        matched.sort(key=lambda c: (type_order.get(c.recommendation_type, 99), c.clause_title))

        return RecommendationResult(
            suggested_clauses=matched,
            rules_evaluated=len(rules),
            rules_matched=len(matched),
        )

    def _evaluate_condition(
        self,
        rule: ClauseRecommendationRule,
        variables: dict[str, Any],
    ) -> bool:
        """Evaluate a single rule's condition against the variable values."""
        var_value = variables.get(rule.variable_key)
        op = rule.operator
        raw_cond_values = rule.condition_value or []

        # Normalize condition_value: asyncpg returns JSONB string arrays as a
        # Python string like '["Germany"]' instead of a list. Handle both cases.
        cond_values: list[Any] = []
        if isinstance(raw_cond_values, list):
            cond_values = raw_cond_values
        elif isinstance(raw_cond_values, str):
            try:
                import json
                parsed = json.loads(raw_cond_values)
                cond_values = parsed if isinstance(parsed, list) else [raw_cond_values]
            except (json.JSONDecodeError, TypeError):
                cond_values = [raw_cond_values]
        else:
            cond_values = [raw_cond_values]

        # IS_EMPTY / IS_NOT_EMPTY
        if op == ConditionOperator.IS_EMPTY.value:
            return var_value is None or var_value == "" or var_value == [] or var_value == {}
        if op == ConditionOperator.IS_NOT_EMPTY.value:
            return var_value is not None and var_value != "" and var_value != [] and var_value != {}

        # If the variable isn't provided, no match (unless IS_EMPTY handled above)
        if var_value is None:
            return False

        str_val = str(var_value).strip().lower()
        num_val = self._to_number(var_value)

        # Get the first condition value for single-value comparisons
        first_val = cond_values[0] if cond_values else ""
        first_str = str(first_val).strip().lower() if first_val else ""
        first_num = self._to_number(first_val)

        if op == ConditionOperator.EQ.value:
            return str_val == first_str

        if op == ConditionOperator.NEQ.value:
            return str_val != first_str

        if op in (ConditionOperator.GT.value, ConditionOperator.GTE.value,
                   ConditionOperator.LT.value, ConditionOperator.LTE.value):
            if num_val is None or first_num is None:
                # Try string comparison as fallback
                try:
                    if op == ConditionOperator.GT.value:
                        return str_val > first_str
                    if op == ConditionOperator.GTE.value:
                        return str_val >= first_str
                    if op == ConditionOperator.LT.value:
                        return str_val < first_str
                    if op == ConditionOperator.LTE.value:
                        return str_val <= first_str
                except Exception:
                    return False
            if op == ConditionOperator.GT.value:
                return num_val > first_num
            if op == ConditionOperator.GTE.value:
                return num_val >= first_num
            if op == ConditionOperator.LT.value:
                return num_val < first_num
            if op == ConditionOperator.LTE.value:
                return num_val <= first_num

        if op == ConditionOperator.IN.value:
            return any(str(v).strip().lower() == str_val for v in cond_values)

        if op == ConditionOperator.NOT_IN.value:
            return all(str(v).strip().lower() != str_val for v in cond_values)

        if op == ConditionOperator.CONTAINS.value:
            return first_str in str_val

        if op == ConditionOperator.BETWEEN.value:
            if len(cond_values) < 2:
                return False
            low = self._to_number(cond_values[0])
            high = self._to_number(cond_values[1])
            if num_val is not None and low is not None and high is not None:
                return low <= num_val <= high
            return False

        if op == ConditionOperator.MATCHES.value:
            try:
                return bool(re.search(first_str, str_val, re.IGNORECASE))
            except re.error:
                return False

        return False

    async def _build_suggested_clause(
        self,
        rule: ClauseRecommendationRule,
        variables: dict[str, Any],
    ) -> Optional[SuggestedClause]:
        """Build a SuggestedClause from a matched rule by fetching clause details."""
        from app.domains.templates.models import TemplateClause

        result = await self.session.execute(
            select(TemplateClause).where(
                TemplateClause.id == rule.clause_id,
                TemplateClause.tenant_id == self.tenant_id,
            )
        )
        clause = result.scalar_one_or_none()
        if not clause:
            logger.warning(
                "Rule %s references non-existent clause %s",
                rule.id, rule.clause_id,
            )
            return None

        # Build a human-readable reason
        var_label = rule.variable_key
        op_label = self._operator_label(rule.operator)
        val_label = self._format_condition_value(rule.condition_value)
        reason = f"{var_label} {op_label} {val_label}"

        is_checked = rule.recommendation_type in (
            RecommendationType.REQUIRED.value,
            RecommendationType.RECOMMENDED.value,
        )

        return SuggestedClause(
            clause_id=rule.clause_id,
            clause_title=clause.title,
            clause_type=clause.clause_type,
            clause_content=clause.content,
            risk_level=clause.risk_level,
            recommendation_type=rule.recommendation_type,
            reason=reason.strip(),
            rule_id=rule.id,
            rule_name=rule.name,
            is_checked=is_checked,
        )

    def _to_number(self, value: Any) -> Optional[float]:
        """Try to convert a value to a number."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            # Strip currency symbols and commas
            cleaned = str(value).replace("$", "").replace("€", "").replace("£", "").replace(",", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _operator_label(self, op: str) -> str:
        """Convert operator to human-readable label."""
        labels = {
            "=": "is",
            "!=": "is not",
            ">": ">",
            ">=": "≥",
            "<": "<",
            "<=": "≤",
            "IN": "in",
            "NOT_IN": "not in",
            "CONTAINS": "contains",
            "BETWEEN": "between",
            "IS_EMPTY": "is empty",
            "IS_NOT_EMPTY": "is not empty",
            "MATCHES": "matches",
        }
        return labels.get(op, op)

    def _format_condition_value(self, values: list[Any]) -> str:
        """Format condition values for human-readable reason."""
        if not values:
            return ""
        if len(values) == 1:
            return str(values[0])
        return ", ".join(str(v) for v in values)

    async def record_audit(
        self,
        context: RecommendationContext,
        result: RecommendationResult,
        accepted_ids: list[str] | None = None,
        rejected_ids: list[str] | None = None,
        review_id: str | None = None,
        generated_contract_id: str | None = None,
        created_by: str = "system",
    ) -> None:
        """Record a recommendation audit trail."""
        suggested = [
            {
                "clause_id": c.clause_id,
                "clause_title": c.clause_title,
                "recommendation_type": c.recommendation_type,
                "reason": c.reason,
                "is_checked": c.is_checked,
            }
            for c in result.suggested_clauses
        ]
        audit = RecommendationAudit(
            tenant_id=self.tenant_id,
            review_id=review_id,
            generated_contract_id=generated_contract_id,
            template_id=context.template_id,
            variable_values=context.variable_values,
            rules_evaluated=result.rules_evaluated,
            rules_matched=result.rules_matched,
            suggested_clauses=suggested,
            accepted_clause_ids=accepted_ids or [],
            rejected_clause_ids=rejected_ids or [],
            created_by=created_by,
        )
        self.session.add(audit)
        await self.session.flush()
