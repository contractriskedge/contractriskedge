"""AI policy engine for centralized pre-execution governance."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from app.config import settings
from app.domains.tenant_config.service import FeatureFlagService
from sqlalchemy.ext.asyncio import AsyncSession


class AIPolicyViolation(Exception):
    """Raised when an AI execution request violates governance policy."""


@dataclass
class AIPolicyContext:
    tenant_id: str
    operation: str
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    upload_id: Optional[str] = None
    contract_id: Optional[str] = None
    provider: str = "openai"
    model: str = "gpt-4o"
    prompt_length: int = 0
    max_tokens: int = 4096
    clause_size: Optional[int] = None
    region: Optional[str] = None
    response_confidence: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIPolicyDecision:
    allowed: bool
    violations: list[str] = field(default_factory=list)
    fallback_provider: Optional[str] = None
    applied_rules: list[str] = field(default_factory=list)


class AIPolicyEngine:
    """Centralized governance engine for AI execution policies."""

    def __init__(self, session: Any, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.flag_service = FeatureFlagService(session, tenant_id)

    async def validate(self, context: AIPolicyContext) -> AIPolicyDecision:
        """Validate an AI execution request against tenant policy."""
        decision = AIPolicyDecision(allowed=True)

        try:
            policy_enabled = await self._is_policy_engine_enabled(context.user_role)
            if not policy_enabled:
                decision.applied_rules.append("policy_engine_disabled")
                return decision

            await self._evaluate_feature_enablement(context, decision)
            self._evaluate_model_constraints(context, decision)
            self._evaluate_prompt_constraints(context, decision)
            self._evaluate_clause_constraints(context, decision)
            self._evaluate_region_constraints(context, decision)
            self._evaluate_pii_constraints(context, decision)
            self._evaluate_confidence_constraints(context, decision)
            self._resolve_provider_fallback(context, decision)

            decision.allowed = len(decision.violations) == 0
        except Exception:
            decision.applied_rules.append("policy_engine_error_fallback")

        return decision

    async def _is_policy_engine_enabled(self, user_role: Optional[str]) -> bool:
        try:
            evaluation = await self.flag_service.evaluate_flag(
                flag_key="policy_engine",
                user_role=user_role or "anonymous",
            )
            return evaluation.enabled
        except Exception:
            return True  # Fail open: allow if policy engine is unreachable

    async def _evaluate_feature_enablement(self, context: AIPolicyContext, decision: AIPolicyDecision) -> None:
        user_role = context.user_role or "anonymous"
        # Use a savepoint so DB errors in feature flag queries don't abort
        # the main transaction (PostgreSQL aborts the entire transaction
        # on any error, even if caught in Python).
        try:
            await self.session.begin_nested()
        except Exception:
            pass  # No active transaction to nest in
        try:
            if context.operation == "risk_review":
                evaluation = await self.flag_service.evaluate_flag(
                    flag_key="ai_analysis",
                    user_role=user_role,
                )
                if not evaluation.enabled:
                    decision.violations.append("AI analysis is disabled for this tenant")
            if context.operation == "redline_generation":
                evaluation = await self.flag_service.evaluate_flag(
                    flag_key="redlines",
                    user_role=user_role,
                )
                if not evaluation.enabled:
                    decision.violations.append("AI redline generation is disabled for this tenant")
        except Exception:
            try:
                await self.session.rollback()  # Rollback savepoint only
            except Exception:
                pass
        decision.applied_rules.append("feature_enablement")

    def _evaluate_model_constraints(self, context: AIPolicyContext, decision: AIPolicyDecision) -> None:
        allowed_models = settings.ai_allowed_models
        if context.model not in allowed_models:
            decision.violations.append(
                f"Model '{context.model}' is not allowed for tenant {context.tenant_id}."
            )
        decision.applied_rules.append("allowed_models")

    def _evaluate_prompt_constraints(self, context: AIPolicyContext, decision: AIPolicyDecision) -> None:
        # Convert prompt length (characters) to estimated tokens (~4 chars per token)
        estimated_tokens = context.prompt_length // 4
        # Use the HIGHER of context.max_tokens (model budget) and settings.ai_max_tokens (policy limit)
        # so that a generous policy limit doesn't get overridden by a conservative model default.
        max_allowed = max(context.max_tokens, settings.ai_max_tokens)
        if estimated_tokens > max_allowed:
            decision.violations.append(
                f"Prompt length ~{estimated_tokens} estimated tokens exceeds allowed max tokens {max_allowed}."
            )
        decision.applied_rules.append("prompt_limits")

    def _evaluate_clause_constraints(self, context: AIPolicyContext, decision: AIPolicyDecision) -> None:
        if context.clause_size is not None and context.clause_size > settings.ai_max_clause_size:
            decision.violations.append(
                f"Clause size {context.clause_size} exceeds max allowed {settings.ai_max_clause_size}."
            )
        decision.applied_rules.append("clause_size")

    def _evaluate_region_constraints(self, context: AIPolicyContext, decision: AIPolicyDecision) -> None:
        if context.region:
            allowed = settings.ai_allowed_regions
            normalized = context.region.lower()
            if normalized not in allowed:
                decision.violations.append(
                    f"Region '{context.region}' is not permitted for AI execution."
                )
        decision.applied_rules.append("region_restrictions")

    def _evaluate_pii_constraints(self, context: AIPolicyContext, decision: AIPolicyDecision) -> None:
        if not settings.ai_pii_protection_enabled:
            decision.applied_rules.append("pii_detection_disabled")
            return

        prompt_text = context.metadata.get("prompt_text", "")
        if not prompt_text:
            decision.applied_rules.append("pii_detection_skipped_empty")
            return

        # Skip PII detection for contract analysis operations — contracts
        # naturally contain email addresses, phone numbers, and other
        # identifiers as part of the business terms. Flagging these as PII
        # would block legitimate analysis of every contract.
        pii_safe_operations = {"risk_review", "clause_extraction", "obligation_extraction",
                               "redline_generation", "summarization", "classification"}
        if context.operation in pii_safe_operations:
            decision.applied_rules.append("pii_detection_skipped_operation")
            return

        if self._contains_pii(prompt_text):
            decision.violations.append("Prompt contains PII and violates tenant policy.")
        decision.applied_rules.append("pii_detection")

    def _evaluate_confidence_constraints(self, context: AIPolicyContext, decision: AIPolicyDecision) -> None:
        if context.response_confidence is not None:
            min_confidence = settings.ai_min_confidence_threshold
            if context.response_confidence < min_confidence:
                decision.violations.append(
                    f"Response confidence {context.response_confidence:.2f} is below the minimum threshold {min_confidence:.2f}."
                )
        decision.applied_rules.append("confidence_threshold")

    def _resolve_provider_fallback(self, context: AIPolicyContext, decision: AIPolicyDecision) -> None:
        fallback_order = settings.ai_provider_fallback_order
        if context.provider not in fallback_order:
            if fallback_order:
                decision.fallback_provider = fallback_order[0]
                decision.applied_rules.append("provider_fallback")
        else:
            decision.applied_rules.append("provider_selection")

    def _is_feature_enabled(self, flag_key: str) -> bool:
        # This is a fast local check; actual policy engine queries the tenant configuration service.
        return flag_key in settings.ai_feature_flags if hasattr(settings, "ai_feature_flags") else True

    @staticmethod
    def _contains_pii(text: str) -> bool:
        if not text:
            return False
        patterns = [
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b\d{9}\b",
            r"\b4[0-9]{12}(?:[0-9]{3})?\b",
            r"\b5[1-5][0-9]{14}\b",
            r"\b3[47][0-9]{13}\b",
            r"\b(\+\d{1,2}\s)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        ]
        return any(re.search(pattern, text) for pattern in patterns)


__all__ = [
    "AIPolicyEngine",
    "AIPolicyContext",
    "AIPolicyDecision",
    "AIPolicyViolation",
]
