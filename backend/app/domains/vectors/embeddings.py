"""Embedding provider abstraction layer with OpenAI implementation and retry-safe batching."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingRequest:
    """Request to generate an embedding for a text input."""
    text: str
    model: str = "text-embedding-3-large"
    dimensions: int = 1536


@dataclass
class EmbeddingResponse:
    """Response from an embedding provider."""
    embedding: list[float]
    model: str
    provider: str
    token_count: int
    latency_ms: int
    cost_usd: float = 0.0


class EmbeddingProviderError(Exception):
    """Base error for embedding provider failures."""


class RateLimitError(EmbeddingProviderError):
    """Provider rate limit exceeded (transient)."""


class QuotaExceededError(EmbeddingProviderError):
    """Provider billing quota exhausted (not retryable)."""


class TimeoutError(EmbeddingProviderError):
    """Provider request timed out."""


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface.

    Implementations:
    - OpenAIEmbeddingProvider (V1)
    - CustomEmbeddingProvider (future)
    """

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        ...

    @abstractmethod
    async def embed_batch(self, requests: list[EmbeddingRequest]) -> list[EmbeddingResponse]:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        ...


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider with retry-safe batching and cost tracking."""

    RATES = {
        "text-embedding-3-large": 0.00000013,   # $0.13 per 1M tokens
        "text-embedding-3-small": 0.00000002,   # $0.02 per 1M tokens
        "text-embedding-ada-002": 0.00000010,   # $0.10 per 1M tokens
    }

    MAX_BATCH_SIZE = 20       # OpenAI max batch size
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30

    def __init__(self, api_key: str, default_model: str = "text-embedding-3-large", tenant_id: str = "global"):
        self._api_key = api_key
        self._default_model = default_model
        self._tenant_id = tenant_id
        self._client = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supported_models(self) -> list[str]:
        return ["text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"]

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            from httpx import AsyncClient, Timeout
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                http_client=AsyncClient(timeout=Timeout(self.TIMEOUT_SECONDS, connect=10.0)),
                max_retries=0,
            )
        return self._client

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=2, min=5, max=90),
        retry=retry_if_exception_type((RateLimitError, TimeoutError)),
    )
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        from app.domains.vectors.embedding_throttle import embedding_slot

        client = await self._get_client()
        start = time.monotonic()

        async with embedding_slot(self._tenant_id):
            try:
                response = await client.embeddings.create(
                    model=request.model or self._default_model,
                    input=request.text,
                    dimensions=request.dimensions,
                )
            except Exception as exc:
                error_str = str(exc).lower()
                if "insufficient_quota" in error_str or "exceeded your current quota" in error_str:
                    raise QuotaExceededError(f"OpenAI quota exceeded: {exc}")
                if "rate" in error_str and "limit" in error_str:
                    raise RateLimitError(f"OpenAI rate limit: {exc}")
                raise EmbeddingProviderError(f"OpenAI embedding failed: {exc}")

        latency_ms = int((time.monotonic() - start) * 1000)
        data = response.data[0]
        usage = response.usage

        cost = self._estimate_cost(request.model or self._default_model, usage.total_tokens)

        return EmbeddingResponse(
            embedding=data.embedding,
            model=response.model,
            provider=self.provider_name,
            token_count=usage.total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )

    async def embed_batch(self, requests: list[EmbeddingRequest]) -> list[EmbeddingResponse]:
        """Embed multiple texts in batches, respecting OpenAI limits."""
        results: list[EmbeddingResponse] = []

        for i in range(0, len(requests), self.MAX_BATCH_SIZE):
            batch = requests[i:i + self.MAX_BATCH_SIZE]
            batch_results = await self._embed_batch_single(batch)
            results.extend(batch_results)

        return results

    async def _embed_batch_single(self, requests: list[EmbeddingRequest]) -> list[EmbeddingResponse]:
        from app.domains.vectors.embedding_throttle import embedding_slot

        client = await self._get_client()
        start = time.monotonic()
        texts = [r.text for r in requests]
        model = requests[0].model if requests else self._default_model
        dims = requests[0].dimensions if requests else 1536

        async with embedding_slot(self._tenant_id):
            try:
                response = await client.embeddings.create(
                    model=model,
                    input=texts,
                    dimensions=dims,
                )
            except Exception as exc:
                error_str = str(exc).lower()
                if "insufficient_quota" in error_str or "exceeded your current quota" in error_str:
                    raise QuotaExceededError(f"OpenAI quota exceeded: {exc}")
                if "rate" in error_str and "limit" in error_str:
                    raise RateLimitError(f"OpenAI rate limit: {exc}")
                raise EmbeddingProviderError(f"OpenAI batch embedding failed: {exc}")

        latency_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        total_tokens = usage.total_tokens
        cost = self._estimate_cost(model, total_tokens)

        results = []
        for i, data in enumerate(response.data):
            results.append(EmbeddingResponse(
                embedding=data.embedding,
                model=response.model,
                provider=self.provider_name,
                token_count=total_tokens // len(requests),
                latency_ms=latency_ms,
                cost_usd=cost / len(requests),
            ))

        return results

    def _estimate_cost(self, model: str, total_tokens: int) -> float:
        rate = self.RATES.get(model, self.RATES["text-embedding-3-large"])
        return total_tokens * rate


class EmbeddingProviderRegistry:
    """Registry of available embedding providers with factory method."""

    def __init__(self):
        self._providers: dict[str, EmbeddingProvider] = {}

    def register(self, provider: EmbeddingProvider):
        self._providers[provider.provider_name] = provider

    def get(self, name: str = "openai") -> EmbeddingProvider:
        provider = self._providers.get(name)
        if not provider:
            raise ValueError(f"Embedding provider '{name}' not registered")
        return provider

    def get_default(self) -> EmbeddingProvider:
        return self.get("openai")


embedding_registry = EmbeddingProviderRegistry()
