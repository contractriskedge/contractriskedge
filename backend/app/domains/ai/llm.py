"""LLM provider abstraction layer with OpenAI implementation, provider selection, and retry-safe inference."""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, ValidationError

from app.domains.ai.providers.capabilities import ProviderHealth

logger = logging.getLogger(__name__)

_LAZY_EXPORTS = frozenset({"LLMProviderRegistry", "llm_registry"})


@dataclass
class LLMRequest:
    """Request to an LLM provider."""
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    response_format: Optional[dict] = None  # {"type": "json_object"}


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float = 0.0


class BaseLLMProvider(ABC):
    """Abstract LLM provider interface for pluggable AI providers."""

    def __init__(self):
        self._health = ProviderHealth(provider_name=self.provider_name)

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        ...

    @property
    def supported_regions(self) -> list[str]:
        return ["us", "eu", "apac", "latam", "uk", "global"]

    @property
    def health(self) -> ProviderHealth:
        return self._health

    @property
    def health_score(self) -> float:
        return self._health.health_score

    def record_metrics(self, latency_ms: int, cost_usd: float, success: bool = True) -> None:
        if success:
            self._health.record_success(latency_ms=latency_ms, cost_usd=cost_usd)
        else:
            self._health.record_failure(latency_ms=latency_ms, cost_usd=cost_usd)

    def is_available(self) -> bool:
        return self._health.is_available()


class LLMProviderError(Exception):
    """Base error for LLM provider failures."""


class RateLimitError(LLMProviderError):
    """Provider rate limit exceeded (transient — safe to retry)."""

    def __init__(self, message: str, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def parse_openai_retry_after(error: str) -> float | None:
    """Extract 'try again in Xs' hint from OpenAI rate-limit error messages."""
    import re
    match = re.search(r"try again in ([\d.]+)\s*s", error, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


class QuotaExceededError(LLMProviderError):
    """Provider billing/quota exhausted (not retryable)."""


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider with retry-safe inference and cost tracking."""

    RATES = {
        "gpt-4o": {"input": 0.0000025, "output": 0.00001},
        "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
        "gpt-4-turbo": {"input": 0.00001, "output": 0.00003},
    }
    DEFAULT_MODEL = "gpt-4o"
    MAX_RETRIES = 3
    # OpenAI completion token limits (not context window size).
    MAX_COMPLETION_TOKENS: dict[str, int] = {
        "gpt-4o": 16384,
        "gpt-4o-mini": 16384,
        "gpt-4-turbo": 4096,
    }

    def __init__(self, api_key: str):
        super().__init__()
        self._api_key = api_key
        self._client = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supported_models(self) -> list[str]:
        return list(self.RATES.keys())

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            # Celery task layer handles retries; in-process SDK retries would hold
            # DB connections open during backoff (idle_in_transaction timeout).
            self._client = AsyncOpenAI(api_key=self._api_key, max_retries=0)
        return self._client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Execute an LLM completion with the provider.

        Note: Retry-on-rate-limit is handled by the Celery task layer
        (``autoretry_for`` + ``retry_backoff``) so the worker is released
        back to the pool during backoff instead of blocking.
        """
        client = await self._get_client()
        start = time.monotonic()

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        model = request.model or self.DEFAULT_MODEL
        max_tokens = request.max_tokens
        model_cap = self.MAX_COMPLETION_TOKENS.get(model, 4096)
        if max_tokens > model_cap:
            logger.warning(
                "Capping max_tokens from %s to %s for model %s",
                max_tokens,
                model_cap,
                model,
            )
            max_tokens = model_cap

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": max_tokens,
        }
        if request.response_format:
            kwargs["response_format"] = request.response_format

        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as exc:
            error = str(exc).lower()
            if "insufficient_quota" in error or "exceeded your current quota" in error:
                raise QuotaExceededError(str(exc))
            if "rate" in error and "limit" in error:
                raise RateLimitError(str(exc), retry_after_seconds=parse_openai_retry_after(str(exc)))
            raise LLMProviderError(f"OpenAI call failed: {exc}")

        latency_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        model = response.model
        self.record_metrics(latency_ms=latency_ms, cost_usd=0.0, success=True)

        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            provider=self.provider_name,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
        )

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = self.RATES.get(model, self.RATES[self.DEFAULT_MODEL])
        return (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])


class AnthropicProvider(BaseLLMProvider):
    """Placeholder Anthropic provider abstraction."""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def supported_models(self) -> list[str]:
        return ["claude-3.5", "claude-4"]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("AnthropicProvider is not implemented yet.")


class AzureOpenAIProvider(BaseLLMProvider):
    """Placeholder Azure OpenAI provider abstraction."""

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    @property
    def supported_models(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("AzureOpenAIProvider is not implemented yet.")


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek Chat provider — uses OpenAI-compatible API at a fraction of GPT-4o cost.

    Pricing (per 1M tokens):
      - deepseek-v4-flash:  ~$0.30 input / $1.10 output
      - deepseek-v4-pro:    ~$0.50 input / $2.00 output

    Suitable for bulk ingestion (risk analysis, chunking) where cost matters.
    Uses deepseek-v4-flash as default for speed/cost.
    """

    RATES = {
        "deepseek-v4-flash": {"input": 0.00000030, "output": 0.0000011},
        "deepseek-v4-pro": {"input": 0.00000050, "output": 0.0000020},
    }
    DEFAULT_MODEL = "deepseek-v4-flash"
    BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key: str):
        super().__init__()
        self._api_key = api_key
        self._client = None

    @property
    def provider_name(self) -> str:
        return "deepseek"

    @property
    def supported_models(self) -> list[str]:
        return list(self.RATES.keys())

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self.BASE_URL,
                max_retries=0,  # Celery handles retries
            )
        return self._client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Execute an LLM completion via DeepSeek's OpenAI-compatible API.

        Retry-on-rate-limit is handled by the Celery task layer so the worker
        is released back to the pool during backoff.
        """
        client = await self._get_client()
        start = time.monotonic()

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        model = request.model or self.DEFAULT_MODEL
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_format:
            kwargs["response_format"] = request.response_format

        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as exc:
            error = str(exc).lower()
            if "insufficient_quota" in error or "exceeded your current quota" in error:
                raise QuotaExceededError(str(exc))
            if "rate" in error and "limit" in error:
                raise RateLimitError(str(exc))
            raise LLMProviderError(f"DeepSeek call failed: {exc}")

        latency_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        model_used = response.model
        self.record_metrics(latency_ms=latency_ms, cost_usd=0.0, success=True)

        return LLMResponse(
            content=response.choices[0].message.content,
            model=model_used,
            provider=self.provider_name,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
        )

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = self.RATES.get(model, self.RATES[self.DEFAULT_MODEL])
        return (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])


class StructuredOutputParser:
    """Parses and validates structured JSON outputs from LLM responses.

    Handles:
    - Malformed JSON (repair attempts)
    - Schema validation via Pydantic
    - Partial response handling
    - Confidence scoring
    """

    @staticmethod
    def parse_json(content: str, max_repair_attempts: int = 2) -> Optional[dict]:
        """Parse JSON from LLM response with repair attempts."""
        # Direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON object boundaries
        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            try:
                return json.loads(content[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def validate_model(data: dict, model_class: type[BaseModel]) -> Optional[BaseModel]:
        """Validate parsed data against a Pydantic model."""
        try:
            return model_class(**data)
        except ValidationError as exc:
            logger.warning("Schema validation failed: %s", exc)
            return None

    @staticmethod
    def calculate_confidence(parsed: Optional[dict], model: Optional[BaseModel]) -> float:
        """Calculate confidence score based on parse and validation success."""
        if parsed is None:
            return 0.0
        if model is not None:
            return 0.95  # Successfully parsed and validated
        return 0.5  # Parsed but failed schema validation


def __getattr__(name: str):
    """Lazy re-exports so registry can import BaseLLMProvider without a circular import."""
    if name in _LAZY_EXPORTS:
        from app.domains.ai.providers.registry import LLMProviderRegistry, llm_registry

        return {"LLMProviderRegistry": LLMProviderRegistry, "llm_registry": llm_registry}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _LAZY_EXPORTS)
