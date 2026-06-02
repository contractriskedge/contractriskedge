"""Execution planning for AI orchestration and provider routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.config import settings
from app.domains.ai.orchestration.plan import (
    AIExecutionPlan,
    RetryPolicy,
    TimeoutPolicy,
    GuardrailProfile,
    RetrievalStrategy,
    FallBackChain,
)
from app.domains.ai.providers.capabilities import ProviderCapabilities
from app.domains.ai.policy import AIPolicyDecision


@dataclass
class AIExecutionPlanner:
    tenant_id: str
    policy_pack_version: str = "default"
    prompt_template_version: int = 1

    def build(
        self,
        operation_type: str,
        model: str,
        provider_name: str,
        preferred_fallbacks: Iterable[str] | None = None,
        policy_decision: AIPolicyDecision | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AIExecutionPlan:
        return AIExecutionPlan(
            provider_name=provider_name,
            model=model,
            temperature=getattr(settings, "ai_default_temperature", 0.1),
            token_budget=min(
                settings.ai_default_token_budget,
                settings.ai_max_response_tokens,
            ),
            retry_policy=RetryPolicy(
                max_attempts=getattr(settings, "ai_retry_attempts", 3),
                backoff_seconds=getattr(settings, "ai_retry_backoff", 2.0),
                max_backoff_seconds=getattr(settings, "ai_retry_max_backoff", 30.0),
                retry_on_error=True,
            ),
            timeout_policy=TimeoutPolicy(
                request_timeout_seconds=getattr(settings, "ai_request_timeout", 60),
                total_timeout_seconds=getattr(settings, "ai_total_timeout", 120),
            ),
            guardrail_profile=GuardrailProfile(
                profile_id=getattr(settings, "ai_guardrail_profile", "default"),
                enforcement_level=getattr(settings, "ai_guardrail_enforcement", "strict"),
                allowed_violation_severity=getattr(settings, "ai_guardrail_allowed_severity", ["low", "medium"]),
            ),
            policy_pack_version=self.policy_pack_version,
            retrieval_strategy=RetrievalStrategy(
                name=getattr(settings, "ai_retrieval_strategy", "semantic_search"),
                max_documents=getattr(settings, "ai_retrieval_max_documents", 10),
                rerank=getattr(settings, "ai_retrieval_rerank", True),
                vector_similarity_threshold=getattr(settings, "ai_retrieval_similarity_threshold", 0.75),
            ),
            fallback_chain=FallBackChain(
                providers=list(preferred_fallbacks) if preferred_fallbacks else [],
                max_fallbacks=getattr(settings, "ai_max_fallbacks", 2),
            ),
            provider_capabilities=ProviderCapabilities(
                provider_name=provider_name,
                supports_json_mode=True,
                supports_tool_calling=False,
                supports_streaming=False,
                supports_vision=False,
                supports_retrieval=False,
                max_context_tokens=getattr(settings, "ai_max_context_tokens", 32768),
                max_response_tokens=settings.ai_max_response_tokens,
                supports_reasoning_depth=True,
            ),
            prompt_template_version=self.prompt_template_version,
            operation_type=operation_type,
            metadata=metadata or {},
        )
