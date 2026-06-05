"""Tests for LLM resilience hardening — provider fallback chain and selection."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.ai.llm import BaseLLMProvider, LLMResponse
from app.domains.ai.providers.capabilities import ProviderCapabilities
from app.domains.ai.providers.registry import llm_registry
from app.domains.ai.orchestration.plan import AIExecutionPlan, FallBackChain, RetryPolicy, TimeoutPolicy, GuardrailProfile, RetrievalStrategy
from app.domains.ai.orchestration.envelope import AIRequestEnvelope
from app.domains.ai.orchestration.orchestrator import AIExecutionOrchestrator


# ── Mock Providers ────────────────────────────────────────────────


class MockProvider(BaseLLMProvider):
    """A mock LLM provider for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        self._name = name
        self._should_fail = should_fail
        super().__init__()

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def supported_models(self) -> list[str]:
        return ["gpt-4o"]

    async def complete(self, request: "LLMRequest") -> LLMResponse:
        if self._should_fail:
            raise RuntimeError(f"{self._name} failed")
        return LLMResponse(
            content='{"risk_score": 0.5, "summary": "test", "findings": []}',
            model="gpt-4o",
            provider=self._name,
            prompt_tokens=10,
            completion_tokens=10,
            total_tokens=20,
            cost_usd=0.0,
            latency_ms=10,
        )


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the registry before each test and restore after."""
    original_providers = dict(llm_registry._providers)
    original_health = dict(llm_registry._health)
    llm_registry._providers.clear()
    llm_registry._health.clear()
    yield
    llm_registry._providers = original_providers
    llm_registry._health = original_health


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def orchestrator(mock_session):
    return AIExecutionOrchestrator(mock_session, "tenant-001")


@pytest.fixture
def base_envelope():
    return AIRequestEnvelope(
        tenant_id="tenant-001",
        user_id="user-001",
        contract_id="contract-001",
        upload_id="upload-001",
        operation_type="risk_review",
        execution_plan=AIExecutionPlan(
            provider_name="openai",
            model="gpt-4o",
            temperature=0.1,
            token_budget=4096,
            retry_policy=RetryPolicy(),
            timeout_policy=TimeoutPolicy(),
            guardrail_profile=GuardrailProfile(profile_id="default"),
            policy_pack_version="default",
            retrieval_strategy=RetrievalStrategy(name="semantic_search"),
            fallback_chain=FallBackChain(providers=[], max_fallbacks=2),
            provider_capabilities=ProviderCapabilities(provider_name="openai", max_response_tokens=4096),
            prompt_template_version=1,
            operation_type="risk_review",
        ),
        audit_context={
            "prompt_text": "Analyze this contract.",
            "system_prompt": "You are a contract analyst.",
            "user_role": "admin",
        },
    )


# ── Provider Registry Tests ───────────────────────────────────────


class TestProviderRegistry:
    def test_register_and_select(self):
        """A registered provider should be selectable."""
        provider = MockProvider("test_provider")
        llm_registry.register(provider)
        selected = llm_registry.select_provider(preferred=["test_provider"])
        assert selected.provider_name == "test_provider"

    def test_select_fallback_chain(self):
        """When primary is not in registry, fallback should be selected."""
        primary = MockProvider("primary")
        fallback = MockProvider("fallback")
        llm_registry.register(primary)
        llm_registry.register(fallback)
        selected = llm_registry.select_provider(preferred=["nonexistent", "fallback", "primary"])
        assert selected.provider_name == "fallback"

    def test_select_healthy_provider(self):
        """select_provider should skip unhealthy providers."""
        unhealthy = MockProvider("unhealthy")
        unhealthy.health.record_failure(latency_ms=100, cost_usd=0.0)
        unhealthy.health.record_failure(latency_ms=100, cost_usd=0.0)
        unhealthy.health.record_failure(latency_ms=100, cost_usd=0.0)
        # failure_rate = 1.0, health_score = 0.0, is_available = False
        healthy = MockProvider("healthy")
        llm_registry.register(unhealthy)
        llm_registry.register(healthy)
        selected = llm_registry.select_provider(preferred=["unhealthy", "healthy"])
        assert selected.provider_name == "healthy"

    def test_no_healthy_providers_raises(self):
        """With no healthy providers, select_provider should raise."""
        with pytest.raises(ValueError, match="No healthy LLM providers"):
            llm_registry.select_provider(preferred=["nonexistent"])


# ── Provider Fallback Chain Tests ─────────────────────────────────


class TestProviderFallbackChain:
    async def test_primary_succeeds_no_fallback(self, orchestrator, base_envelope, mock_session):
        """When the primary provider succeeds, no fallback should be attempted."""
        primary = MockProvider("openai")
        fallback = MockProvider("anthropic")
        llm_registry.register(primary)
        llm_registry.register(fallback)

        # Mock policy engine to allow
        with patch.object(orchestrator.policy_engine, "validate", return_value=MagicMock(allowed=True, violations=[])):
            with patch.object(orchestrator.guardrail_engine, "evaluate_prompt", return_value=[]):
                with patch.object(orchestrator.guardrail_engine, "has_critical_violation", return_value=False):
                    with patch.object(orchestrator.guardrail_engine, "evaluate_response", return_value=[]):
                        outcome = await orchestrator.execute(base_envelope)

        assert outcome is not None
        assert outcome.response.provider == "openai"

    async def test_primary_fails_fallback_succeeds(self, orchestrator, base_envelope, mock_session):
        """When the primary provider fails, the fallback should be used."""
        primary = MockProvider("openai", should_fail=True)
        fallback = MockProvider("anthropic")
        llm_registry.register(primary)
        llm_registry.register(fallback)

        # Add fallback to the envelope's plan
        base_envelope.execution_plan.fallback_chain.providers = ["anthropic"]

        with patch.object(orchestrator.policy_engine, "validate", return_value=MagicMock(allowed=True, violations=[])):
            with patch.object(orchestrator.guardrail_engine, "evaluate_prompt", return_value=[]):
                with patch.object(orchestrator.guardrail_engine, "has_critical_violation", return_value=False):
                    with patch.object(orchestrator.guardrail_engine, "evaluate_response", return_value=[]):
                        outcome = await orchestrator.execute(base_envelope)

        assert outcome is not None
        assert outcome.response.provider == "anthropic"

    async def test_all_providers_fail_raises(self, orchestrator, base_envelope, mock_session):
        """When all providers in the chain fail, the last exception should propagate."""
        primary = MockProvider("openai", should_fail=True)
        fallback = MockProvider("anthropic", should_fail=True)
        llm_registry.register(primary)
        llm_registry.register(fallback)

        base_envelope.execution_plan.fallback_chain.providers = ["anthropic"]

        with patch.object(orchestrator.policy_engine, "validate", return_value=MagicMock(allowed=True, violations=[])):
            with patch.object(orchestrator.guardrail_engine, "evaluate_prompt", return_value=[]):
                with patch.object(orchestrator.guardrail_engine, "has_critical_violation", return_value=False):
                    with pytest.raises(RuntimeError, match="anthropic failed"):
                        await orchestrator.execute(base_envelope)

    async def test_fallback_not_in_registry_skipped(self, orchestrator, base_envelope, mock_session):
        """A fallback provider not in the registry should be skipped, raising the original error."""
        primary = MockProvider("openai", should_fail=True)
        llm_registry.register(primary)
        # Don't register "anthropic" — it should be skipped

        base_envelope.execution_plan.fallback_chain.providers = ["anthropic"]

        with patch.object(orchestrator.policy_engine, "validate", return_value=MagicMock(allowed=True, violations=[])):
            with patch.object(orchestrator.guardrail_engine, "evaluate_prompt", return_value=[]):
                with patch.object(orchestrator.guardrail_engine, "has_critical_violation", return_value=False):
                    with pytest.raises((RuntimeError, ValueError)):
                        await orchestrator.execute(base_envelope)

    async def test_provider_chain_order_respected(self, orchestrator, base_envelope, mock_session):
        """Providers should be tried in the order specified by the chain."""
        call_order = []

        class TrackingProvider(MockProvider):
            async def complete(self, request):
                call_order.append(self._name)
                return await super().complete(request)

        primary = TrackingProvider("openai", should_fail=True)
        fallback1 = TrackingProvider("anthropic")
        fallback2 = TrackingProvider("google")
        llm_registry.register(primary)
        llm_registry.register(fallback1)
        llm_registry.register(fallback2)

        base_envelope.execution_plan.fallback_chain.providers = ["anthropic", "google"]

        with patch.object(orchestrator.policy_engine, "validate", return_value=MagicMock(allowed=True, violations=[])):
            with patch.object(orchestrator.guardrail_engine, "evaluate_prompt", return_value=[]):
                with patch.object(orchestrator.guardrail_engine, "has_critical_violation", return_value=False):
                    with patch.object(orchestrator.guardrail_engine, "evaluate_response", return_value=[]):
                        outcome = await orchestrator.execute(base_envelope)

        assert call_order == ["openai", "anthropic"]
        assert outcome.response.provider == "anthropic"


# ── Provider Health Tracking Tests ────────────────────────────────


class TestProviderHealthTracking:
    def test_success_updates_health(self):
        """A successful call should increment success_count."""
        provider = MockProvider("test")
        llm_registry.register(provider)
        llm_registry.report_outcome("test", success=True, latency_ms=100, cost_usd=0.01)
        assert provider.health.success_count == 1
        assert provider.health.failure_count == 0

    def test_failure_updates_health(self):
        """A failed call should increment failure_count."""
        provider = MockProvider("test")
        llm_registry.register(provider)
        llm_registry.report_outcome("test", success=False, latency_ms=100, cost_usd=0.0)
        assert provider.health.failure_count == 1
        assert provider.health.success_count == 0

    def test_high_failure_rate_triggers_unavailable(self):
        """After 3 failures, the provider should become unavailable."""
        provider = MockProvider("test")
        llm_registry.register(provider)
        for _ in range(3):
            llm_registry.report_outcome("test", success=False, latency_ms=100, cost_usd=0.0)
        assert provider.health.is_available() is False
        assert provider.health.circuit_breaker_open is True
