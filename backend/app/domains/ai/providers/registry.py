"""Health-aware LLM provider registry and selection logic."""

from __future__ import annotations

from typing import Iterable, Optional

from app.domains.ai.llm import BaseLLMProvider
from app.domains.ai.providers.capabilities import ProviderHealth


class LLMProviderRegistry:
    """Registry and selector for pluggable LLM providers."""

    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._health: dict[str, ProviderHealth] = {}

    def register(self, provider: BaseLLMProvider) -> None:
        self._providers[provider.provider_name] = provider
        self._health[provider.provider_name] = provider.health

    def get(self, name: str = "openai") -> BaseLLMProvider:
        provider = self._providers.get(name)
        if not provider:
            raise ValueError(f"LLM provider '{name}' not registered")
        return provider

    def select_provider(self, preferred: Optional[Iterable[str]] = None) -> BaseLLMProvider:
        if preferred:
            for name in preferred:
                provider = self._providers.get(name)
                if provider and provider.health.is_available():
                    return provider
        healthy_providers = [p for p in self._providers.values() if p.health.is_available()]
        if not healthy_providers:
            raise ValueError("No healthy LLM providers are available")
        return max(healthy_providers, key=lambda p: p.health.health_score)

    def report_outcome(self, provider_name: str, success: bool, latency_ms: int, cost_usd: float, timeout: bool = False) -> None:
        health = self._health.get(provider_name)
        if not health:
            return
        if success:
            health.record_success(latency_ms=latency_ms, cost_usd=cost_usd)
        else:
            health.record_failure(latency_ms=latency_ms, cost_usd=cost_usd, timeout=timeout)


llm_registry = LLMProviderRegistry()
