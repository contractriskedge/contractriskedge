"""AI provider abstraction package."""

from __future__ import annotations

from app.domains.ai.providers.capabilities import ProviderCapabilities, ProviderHealth

__all__ = [
    "BaseLLMProvider",
    "LLMProviderRegistry",
    "llm_registry",
    "ProviderCapabilities",
    "ProviderHealth",
]

_LAZY_EXPORTS = frozenset({"BaseLLMProvider", "LLMProviderRegistry", "llm_registry"})


def __getattr__(name: str):
    if name == "BaseLLMProvider":
        from app.domains.ai.llm import BaseLLMProvider

        return BaseLLMProvider
    if name in ("LLMProviderRegistry", "llm_registry"):
        from app.domains.ai.providers.registry import LLMProviderRegistry, llm_registry

        return {"LLMProviderRegistry": LLMProviderRegistry, "llm_registry": llm_registry}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _LAZY_EXPORTS)
