"""AI execution plan abstractions for policy-driven orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from app.domains.ai.providers.capabilities import ProviderCapabilities


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 2.0
    max_backoff_seconds: float = 30.0
    retry_on_error: bool = True


@dataclass
class TimeoutPolicy:
    request_timeout_seconds: int = 60
    total_timeout_seconds: int = 120


@dataclass
class GuardrailProfile:
    profile_id: str
    enforcement_level: str = "strict"
    allowed_violation_severity: list[str] = field(default_factory=lambda: ["low", "medium"])


@dataclass
class RetrievalStrategy:
    name: str = "semantic_search"
    max_documents: int = 10
    rerank: bool = True
    vector_similarity_threshold: float = 0.75


@dataclass
class FallBackChain:
    providers: list[str] = field(default_factory=list)
    max_fallbacks: int = 2


@dataclass
class AIExecutionPlan:
    provider_name: str
    model: str
    temperature: float
    token_budget: int
    retry_policy: RetryPolicy
    timeout_policy: TimeoutPolicy
    guardrail_profile: GuardrailProfile
    policy_pack_version: str
    retrieval_strategy: RetrievalStrategy
    fallback_chain: FallBackChain
    provider_capabilities: ProviderCapabilities
    prompt_template_version: int
    operation_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
