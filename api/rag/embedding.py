"""Text embedding pipeline using OpenAI text-embedding-3-large.

Provides high-quality text embeddings for semantic search and
retrieval. Supports batch processing, caching, and configurable
embedding dimensions.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Text embedding pipeline using OpenAI's text-embedding-3-large.

    Generates embeddings for text chunks with support for batching,
    caching, dimension reduction, and error handling with retries.

    Usage:
        pipeline = EmbeddingPipeline(api_key="sk-...")
        embeddings = await pipeline.embed_texts(["text1", "text2"])
        embedding = await pipeline.embed_text("single text")
    """

    MODEL_NAME = "text-embedding-3-large"
    DEFAULT_DIMENSIONS = 1536  # text-embedding-3-large supports up to 3072
    MAX_BATCH_SIZE = 100
    MAX_RETRIES = 3

    def __init__(
        self,
        api_key: str,
        dimensions: int = DEFAULT_DIMENSIONS,
        cache_size: int = 10_000,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        """Initialize the embedding pipeline.

        Args:
            api_key: OpenAI API key.
            dimensions: Embedding dimensions (up to 3072).
            cache_size: Maximum number of cached embeddings.
            base_url: OpenAI API base URL.
        """
        self._api_key = api_key
        self._dimensions = min(dimensions, 3072)
        self._base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, List[float]] = {}
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            Configured async HTTP client.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client

    def _make_cache_key(self, text: str) -> str:
        """Generate a cache key for a text string.

        Args:
            text: The text to key.

        Returns:
            SHA-256 hash of the text.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def embed_text(self, text: str) -> List[float]:
        """Generate an embedding for a single text.

        Args:
            text: The text to embed.

        Returns:
            Embedding vector as a list of floats.
        """
        results = await self.embed_texts([text])
        return results[0]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts.

        Processes texts in batches, checking cache first.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        # Check cache
        for i, text in enumerate(texts):
            cache_key = self._make_cache_key(text)
            cached = self._cache.get(cache_key)
            if cached is not None:
                results[i] = cached
                self._cache_hits += 1
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                self._cache_misses += 1

        if not uncached_texts:
            return [r for r in results if r is not None]

        # Process uncached texts in batches
        for batch_start in range(0, len(uncached_texts), self.MAX_BATCH_SIZE):
            batch = uncached_texts[batch_start:batch_start + self.MAX_BATCH_SIZE]
            batch_embeddings = await self._call_embedding_api(batch)

            for j, embedding in enumerate(batch_embeddings):
                original_idx = uncached_indices[batch_start + j]
                results[original_idx] = embedding
                # Cache the result
                cache_key = self._make_cache_key(uncached_texts[batch_start + j])
                self._add_to_cache(cache_key, embedding)

        return [r for r in results if r is not None]

    async def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """Call the OpenAI embedding API.

        Args:
            texts: Batch of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            RuntimeError: If API call fails after retries.
        """
        client = await self._get_client()

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.post(
                    "/embeddings",
                    json={
                        "model": self.MODEL_NAME,
                        "input": texts,
                        "dimensions": self._dimensions,
                    },
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

                # Sort by index to preserve order
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in sorted_data]

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "Rate limited, retrying in %ds (attempt %d/%d)",
                        wait,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(
                    f"Embedding API error after {attempt + 1} attempts: {exc}"
                )

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "Network error, retrying in %ds: %s", wait, exc
                    )
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(
                    f"Embedding API network error: {exc}"
                )

        raise RuntimeError("Embedding API call failed after all retries")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for OpenAI API.

        Returns:
            Header dictionary.
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _add_to_cache(self, key: str, embedding: List[float]) -> None:
        """Add an embedding to the cache with LRU eviction.

        Args:
            key: Cache key.
            embedding: Embedding vector.
        """
        if len(self._cache) >= self._cache_size:
            # Remove a random entry (approximate LRU)
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = embedding

    async def embed_with_retry(
        self, text: str, max_retries: int = 3
    ) -> List[float]:
        """Embed a single text with explicit retry control.

        Args:
            text: Text to embed.
            max_retries: Maximum retry attempts.

        Returns:
            Embedding vector.
        """
        for attempt in range(max_retries):
            try:
                return await self.embed_text(text)
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    "Embedding retry %d/%d: %s", attempt + 1, max_retries, exc
                )
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError("Embedding failed after all retries")

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache hit/miss counts and rate.
        """
        total = self._cache_hits + self._cache_misses
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "size": len(self._cache),
            "max_size": self._cache_size,
            "hit_rate": round(self._cache_hits / total, 4) if total > 0 else 0.0,
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
