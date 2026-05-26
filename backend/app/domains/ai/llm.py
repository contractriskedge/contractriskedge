"""LLM provider abstraction layer with OpenAI implementation, structured output parsing, and retry-safe inference."""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


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


class LLMProviderError(Exception):
    """Base error for LLM provider failures."""


class RateLimitError(LLMProviderError):
    """Provider rate limit exceeded."""


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

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


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider with retry-safe inference and cost tracking."""

    RATES = {
        "gpt-4o": {"input": 0.0000025, "output": 0.00001},
        "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
        "gpt-4-turbo": {"input": 0.00001, "output": 0.00003},
    }
    DEFAULT_MODEL = "gpt-4o"
    MAX_RETRIES = 3

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = None

    @property
    def provider_name(self) -> str: return "openai"

    @property
    def supported_models(self) -> list[str]:
        return list(self.RATES.keys())

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((RateLimitError,)),
    )
    async def complete(self, request: LLMRequest) -> LLMResponse:
        client = await self._get_client()
        start = time.monotonic()

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        kwargs = {
            "model": request.model or self.DEFAULT_MODEL,
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
            if "rate" in error and "limit" in error:
                raise RateLimitError(str(exc))
            raise LLMProviderError(f"OpenAI call failed: {exc}")

        latency_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        model = response.model

        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            provider=self.provider_name,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
            cost_usd=self._estimate_cost(model, usage.prompt_tokens, usage.completion_tokens),
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


class LLMProviderRegistry:
    """Registry of available LLM providers."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider):
        self._providers[provider.provider_name] = provider

    def get(self, name: str = "openai") -> LLMProvider:
        provider = self._providers.get(name)
        if not provider:
            raise ValueError(f"LLM provider '{name}' not registered")
        return provider


llm_registry = LLMProviderRegistry()
