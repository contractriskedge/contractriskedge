"""Production-grade embedding service using OpenAI embeddings API.

Provides async embedding generation with retry logic, exponential backoff,
structured logging, input validation, and pgvector-compatible output.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import openai
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.domains.vectors.embedding_throttle import embedding_slot

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

EMBEDDING_DIMENSION: int = 1536
"""Expected output dimension for text-embedding-3-small."""

DEFAULT_MODEL: str = "text-embedding-3-small"
"""Default OpenAI embedding model."""

MAX_RETRIES: int = 3
"""Maximum number of retry attempts for failed API calls."""

TIMEOUT_SECONDS: int = 30
"""Request timeout in seconds for OpenAI API calls."""

MAX_BATCH_SIZE: int = 20
"""Maximum texts per batch request (OpenAI limit)."""

CONTROL_CHAR_PATTERN: re.Pattern = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
"""Regex to strip control characters (preserves tabs, newlines, carriage returns)."""


# ── Exceptions ────────────────────────────────────────────────────────────────


class EmbeddingError(Exception):
    """Base exception for embedding service failures."""


class EmptyTextError(EmbeddingError):
    """Raised when input text is empty after cleaning."""


class DimensionMismatchError(EmbeddingError):
    """Raised when API returns embedding with unexpected dimension."""


class EmbeddingTimeoutError(EmbeddingError):
    """Raised when the embedding request times out."""


class EmbeddingRateLimitError(EmbeddingError):
    """Raised when OpenAI rate limit is hit (transient — retryable)."""


class EmbeddingQuotaExceededError(EmbeddingError):
    """Raised when OpenAI billing quota is exhausted (not retryable)."""


class EmbeddingAPIError(EmbeddingError):
    """Raised for unexpected OpenAI API errors."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _clean_text(text: str) -> str:
    """Strip whitespace and remove control characters from input text.

    Preserves tabs (``\\t``), newlines (``\\n``), and carriage returns (``\\r``).
    """
    cleaned = CONTROL_CHAR_PATTERN.sub("", text).strip()
    return cleaned


def _estimate_tokens(text: str) -> int:
    """Roughly estimate token count for a text string.

    Uses a simple heuristic (~4 chars per token for English text).
    For production accuracy, use ``tiktoken`` with the appropriate model.
    """
    return max(1, len(text) // 4)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec_a: First embedding vector.
        vec_b: Second embedding vector.

    Returns:
        Cosine similarity in range ``[-1.0, 1.0]``.

    Raises:
        ValueError: If vectors have different lengths or are empty.
    """
    if len(vec_a) != len(vec_b):
        raise ValueError(
            f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}"
        )
    if not vec_a or not vec_b:
        raise ValueError("Vectors must not be empty")

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


# ── Embedding Service ─────────────────────────────────────────────────────────


@dataclass
class EmbeddingResult:
    """Result of a single embedding generation."""

    vector: list[float]
    model: str
    dimension: int
    token_count: int
    latency_ms: int


@dataclass
class EmbeddingBatchResult:
    """Result of a batch embedding generation."""

    vectors: list[list[float]]
    model: str
    dimension: int
    total_tokens: int
    total_latency_ms: int
    items_requested: int
    items_succeeded: int
    items_failed: int


class EmbeddingService:
    """Production-grade embedding service using OpenAI's embedding API.

    Features:
        - Async-first implementation with ``asyncio``
        - Retry with exponential backoff via ``tenacity``
        - Configurable timeout handling
        - Structured logging (latency, tokens, failures, retries)
        - Input validation (empty text, control chars, dimension checks)
        - OpenAI API error classification
        - pgvector-compatible ``list[float]`` output (1536 dimensions)

    Usage::

        service = EmbeddingService(api_key="sk-...")
        vector = await service.generate_embedding("Your contract text here")
        vectors = await service.generate_embeddings_batch(["text1", "text2"])
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Initialize the embedding service.

        Args:
            api_key: OpenAI API key. Falls back to ``OPENAI_API_KEY`` env var.
            model: Embedding model name. Falls back to ``DEFAULT_EMBEDDING_MODEL``
                env var, then ``text-embedding-3-small``.
            timeout_seconds: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
        """
        if api_key is not None:
            self._api_key = api_key
        else:
            self._api_key = settings.openai_api_key
        if not self._api_key:
            raise EmbeddingError("OPENAI_API_KEY is required")
        self._model = (
            model
            or settings.default_embedding_model
            or DEFAULT_MODEL
        )
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._tenant_id = tenant_id or "global"
        self._client: Optional[openai.AsyncOpenAI] = None

        logger.info(
            "EmbeddingService initialized",
            extra={
                "model": self._model,
                "timeout_seconds": self._timeout,
                "max_retries": self._max_retries,
            },
        )

    # ── Client ────────────────────────────────────────────────────────────

    async def _get_client(self) -> openai.AsyncOpenAI:
        """Lazy-initialize and return the async OpenAI client."""
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=0,  # We handle retries ourselves
            )
        return self._client

    # ── Public API ────────────────────────────────────────────────────────

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text input.

        Args:
            text: Input text to embed.

        Returns:
            A ``list[float]`` of length 1536, compatible with pgvector ``Vector(1536)``.

        Raises:
            EmptyTextError: If the text is empty after cleaning.
            DimensionMismatchError: If the API returns unexpected dimension.
            EmbeddingTimeoutError: If the request times out.
            EmbeddingRateLimitError: If OpenAI rate limit is exceeded.
            EmbeddingAPIError: For other OpenAI API errors.
        """
        cleaned = _clean_text(text)
        if not cleaned:
            raise EmptyTextError("Input text is empty after cleaning")

        estimated_tokens = _estimate_tokens(cleaned)
        logger.debug(
            "Generating embedding",
            extra={
                "text_length": len(cleaned),
                "estimated_tokens": estimated_tokens,
                "model": self._model,
            },
        )

        start = time.monotonic()
        vector = await self._embed_with_retry(cleaned)
        latency_ms = int((time.monotonic() - start) * 1000)

        self._validate_dimension(vector)

        logger.info(
            "Embedding generated",
            extra={
                "latency_ms": latency_ms,
                "estimated_tokens": estimated_tokens,
                "model": self._model,
                "dimension": len(vector),
            },
        )

        return vector

    async def generate_embeddings_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embedding vectors for a batch of text inputs.

        Automatically splits into sub-batches respecting OpenAI's max batch size.
        Failed items are retried individually.

        Args:
            texts: List of input texts to embed.

        Returns:
            A list of ``list[float]`` vectors (one per input), each of length 1536.

        Raises:
            EmptyTextError: If the input list is empty.
            EmbeddingError: If all items fail after retries.
        """
        if not texts:
            raise EmptyTextError("Input text list is empty")

        # Clean and validate all texts
        cleaned_texts: list[str] = []
        valid_indices: list[int] = []
        for i, t in enumerate(texts):
            cleaned = _clean_text(t)
            if cleaned:
                cleaned_texts.append(cleaned)
                valid_indices.append(i)

        if not cleaned_texts:
            raise EmptyTextError("All input texts are empty after cleaning")

        logger.info(
            "Batch embedding requested",
            extra={
                "total_input": len(texts),
                "valid_input": len(cleaned_texts),
                "filtered_empty": len(texts) - len(cleaned_texts),
                "model": self._model,
            },
        )

        start = time.monotonic()
        total_tokens_est = sum(_estimate_tokens(t) for t in cleaned_texts)
        vectors: list[list[float]] = []
        total_latency = 0
        succeeded = 0
        failed = 0

        # Process in sub-batches with a short pause to avoid TPM bursts
        for batch_start in range(0, len(cleaned_texts), MAX_BATCH_SIZE):
            batch = cleaned_texts[batch_start : batch_start + MAX_BATCH_SIZE]
            batch_vectors, batch_latency, batch_succeeded, batch_failed = (
                await self._process_sub_batch(batch)
            )
            vectors.extend(batch_vectors)
            total_latency += batch_latency
            succeeded += batch_succeeded
            failed += batch_failed
            if batch_start + MAX_BATCH_SIZE < len(cleaned_texts):
                await asyncio.sleep(0.5)

        total_latency_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "Batch embedding completed",
            extra={
                "total_latency_ms": total_latency_ms,
                "estimated_tokens": total_tokens_est,
                "succeeded": succeeded,
                "failed": failed,
                "model": self._model,
            },
        )

        if not vectors:
            raise EmbeddingError(
                "All embedding requests failed after retries"
            )

        return vectors

    # ── Internal: Retry Logic ─────────────────────────────────────────────

    async def _embed_with_retry(self, text: str) -> list[float]:
        """Call OpenAI embedding API with retry and exponential backoff."""
        attempt = 0
        last_exception: Optional[Exception] = None

        async for attempt_data in AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=2, min=5, max=90),
            retry=retry_if_exception_type(
                (EmbeddingTimeoutError, EmbeddingRateLimitError)
            ),
            reraise=True,
        ):
            with attempt_data:
                attempt += 1
                try:
                    return await self._call_embedding_api(text)
                except (EmbeddingTimeoutError, EmbeddingRateLimitError) as exc:
                    last_exception = exc
                    logger.warning(
                        "Embedding retry",
                        extra={
                            "attempt": attempt,
                            "max_retries": self._max_retries,
                            "error": str(exc),
                            "model": self._model,
                        },
                    )
                    raise
                except EmbeddingError:
                    # Non-retryable errors propagate immediately
                    raise

        # Should not reach here due to reraise=True, but safety net
        raise EmbeddingError(
            f"Embedding failed after {self._max_retries} retries"
        ) from last_exception

    async def _call_embedding_api(self, text: str) -> list[float]:
        """Execute the actual OpenAI API call with timeout handling."""
        client = await self._get_client()

        async with embedding_slot(self._tenant_id):
            try:
                response = await asyncio.wait_for(
                    client.embeddings.create(
                        model=self._model,
                        input=text,
                        dimensions=EMBEDDING_DIMENSION,
                    ),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError as exc:
                raise EmbeddingTimeoutError(
                    f"OpenAI embedding request timed out after {self._timeout}s"
                ) from exc
            except openai.APIConnectionError as exc:
                raise EmbeddingTimeoutError(
                    f"OpenAI connection error: {exc}"
                ) from exc
            except openai.RateLimitError as exc:
                err = str(exc).lower()
                if "insufficient_quota" in err or "exceeded your current quota" in err:
                    raise EmbeddingQuotaExceededError(
                        f"OpenAI embedding quota exceeded: {exc}"
                    ) from exc
                raise EmbeddingRateLimitError(
                    f"OpenAI rate limit exceeded: {exc}"
                ) from exc
            except openai.APIError as exc:
                err = str(exc).lower()
                if "insufficient_quota" in err or "exceeded your current quota" in err:
                    raise EmbeddingQuotaExceededError(
                        f"OpenAI embedding quota exceeded: {exc}"
                    ) from exc
                raise EmbeddingAPIError(
                    f"OpenAI API error: {exc}"
                ) from exc
            except Exception as exc:
                err = str(exc).lower()
                if "insufficient_quota" in err or "exceeded your current quota" in err:
                    raise EmbeddingQuotaExceededError(
                        f"OpenAI embedding quota exceeded: {exc}"
                    ) from exc
                raise EmbeddingAPIError(
                    f"Unexpected embedding error: {exc}"
                ) from exc

        vector: list[float] = response.data[0].embedding
        return vector

    # ── Internal: Batch Processing ────────────────────────────────────────

    async def _process_sub_batch(
        self,
        texts: list[str],
    ) -> tuple[list[list[float]], int, int, int]:
        """Process a sub-batch of texts, falling back to individual retries."""
        vectors: list[list[float]] = []
        batch_latency = 0
        succeeded = 0
        failed = 0

        start = time.monotonic()

        try:
            batch_vectors = await self._embed_batch_with_retry(texts)
            for vec in batch_vectors:
                self._validate_dimension(vec)
                vectors.append(vec)
                succeeded += 1
            batch_latency = int((time.monotonic() - start) * 1000)
            return vectors, batch_latency, succeeded, failed
        except EmbeddingQuotaExceededError:
            raise
        except EmbeddingError:
            # Fall back to individual embedding with retry
            logger.info(
                "Batch request failed, falling back to individual requests",
                extra={"batch_size": len(texts)},
            )
            for text in texts:
                try:
                    vec = await self._embed_with_retry(text)
                    self._validate_dimension(vec)
                    vectors.append(vec)
                    succeeded += 1
                except EmbeddingError as exc:
                    logger.error(
                        "Individual embedding failed",
                        extra={"error": str(exc), "model": self._model},
                    )
                    failed += 1

            batch_latency = int((time.monotonic() - start) * 1000)
            return vectors, batch_latency, succeeded, failed

    async def _embed_batch_with_retry(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Call batch embedding API with retry logic."""
        attempt = 0

        async for attempt_data in AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=2, min=5, max=90),
            retry=retry_if_exception_type(
                (EmbeddingTimeoutError, EmbeddingRateLimitError)
            ),
            reraise=True,
        ):
            with attempt_data:
                attempt += 1
                try:
                    return await self._call_batch_embedding_api(texts)
                except (EmbeddingTimeoutError, EmbeddingRateLimitError) as exc:
                    logger.warning(
                        "Batch embedding retry",
                        extra={
                            "attempt": attempt,
                            "max_retries": self._max_retries,
                            "error": str(exc),
                            "batch_size": len(texts),
                        },
                    )
                    raise

        raise EmbeddingError(
            f"Batch embedding failed after {self._max_retries} retries"
        )

    async def _call_batch_embedding_api(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Execute batch OpenAI API call with timeout."""
        client = await self._get_client()

        async with embedding_slot(self._tenant_id):
            try:
                response = await asyncio.wait_for(
                    client.embeddings.create(
                        model=self._model,
                        input=texts,
                        dimensions=EMBEDDING_DIMENSION,
                    ),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError as exc:
                raise EmbeddingTimeoutError(
                    f"Batch embedding timed out after {self._timeout}s"
                ) from exc
            except openai.APIConnectionError as exc:
                raise EmbeddingTimeoutError(
                    f"OpenAI connection error on batch: {exc}"
                ) from exc
            except openai.RateLimitError as exc:
                err = str(exc).lower()
                if "insufficient_quota" in err or "exceeded your current quota" in err:
                    raise EmbeddingQuotaExceededError(
                        f"OpenAI embedding quota exceeded on batch: {exc}"
                    ) from exc
                raise EmbeddingRateLimitError(
                    f"OpenAI rate limit exceeded on batch: {exc}"
                ) from exc
            except openai.APIError as exc:
                err = str(exc).lower()
                if "insufficient_quota" in err or "exceeded your current quota" in err:
                    raise EmbeddingQuotaExceededError(
                        f"OpenAI embedding quota exceeded on batch: {exc}"
                    ) from exc
                raise EmbeddingAPIError(
                    f"OpenAI API error on batch: {exc}"
                ) from exc
            except Exception as exc:
                err = str(exc).lower()
                if "insufficient_quota" in err or "exceeded your current quota" in err:
                    raise EmbeddingQuotaExceededError(
                        f"OpenAI embedding quota exceeded on batch: {exc}"
                    ) from exc
                raise EmbeddingAPIError(
                    f"Unexpected batch embedding error: {exc}"
                ) from exc

        # Sort by index to preserve input order
        sorted_data = sorted(response.data, key=lambda d: d.index)
        vectors = [d.embedding for d in sorted_data]
        return vectors

    # ── Validation ────────────────────────────────────────────────────────

    def _validate_dimension(self, vector: list[float]) -> None:
        """Validate that the embedding vector has the expected dimension."""
        if len(vector) != EMBEDDING_DIMENSION:
            raise DimensionMismatchError(
                f"Expected embedding dimension {EMBEDDING_DIMENSION}, "
                f"got {len(vector)}"
            )

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def model(self) -> str:
        """The configured embedding model name."""
        return self._model

    @property
    def timeout_seconds(self) -> int:
        """The configured request timeout."""
        return self._timeout
