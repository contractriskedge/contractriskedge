"""Prompt caching for Anthropic Claude API.

Implements semantic caching for LLM prompts, leveraging Anthropic's
prompt caching feature to save up to 90% on repeated calls. Supports
TTL-based expiration, LRU eviction, and configurable cache backends.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""

    key: str
    response: LLMResponse
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0.0


class PromptCache:
    """Semantic prompt cache for LLM responses.

    Caches LLM responses keyed by a hash of the prompt content.
    Supports TTL-based expiration, LRU eviction when the cache
    exceeds max size, and configurable backends (memory or Redis).

    Usage:
        cache = PromptCache(ttl_seconds=3600, max_entries=1000)
        await cache.set("my-key", response)
        cached = await cache.get("my-key")
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_entries: int = 1000,
        redis_client: Optional[Any] = None,
    ) -> None:
        """Initialize the prompt cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds.
            max_entries: Maximum number of entries before LRU eviction.
            redis_client: Optional Redis client for distributed caching.
                          If None, uses in-memory dictionary.
        """
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._redis_client = redis_client
        self._cache: Dict[str, CacheEntry] = {}
        self._hits: int = 0
        self._misses: int = 0

    def _generate_key(self, messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
        """Generate a cache key from prompt content.

        Creates a deterministic hash from the serialized messages
        and optional system prompt.

        Args:
            messages: List of message dicts with role and content.
            system: Optional system prompt text.

        Returns:
            SHA-256 hash string used as cache key.
        """
        content = json.dumps(messages, sort_keys=True)
        if system:
            content += system
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def build_key(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        """Build a deterministic cache key from request parameters.

        Only caches deterministic requests (temperature near 0).

        Args:
            messages: List of message dicts.
            system: Optional system prompt.
            temperature: Sampling temperature.

        Returns:
            Cache key string, or empty string if request is non-deterministic.
        """
        if temperature > 0.2:
            logger.debug("Skipping cache for non-deterministic request (t=%f)", temperature)
            return ""
        return self._generate_key(messages, system)

    async def get(self, key: str) -> Optional[LLMResponse]:
        """Retrieve a cached response.

        Args:
            key: The cache key to look up.

        Returns:
            Cached LLM response if found and not expired, None otherwise.
        """
        if self._redis_client is not None:
            return await self._get_from_redis(key)

        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None

        # Check expiration
        if time.monotonic() > entry.expires_at:
            del self._cache[key]
            self._misses += 1
            logger.debug("Cache entry expired for key=%s", key[:16])
            return None

        # Update access stats
        entry.access_count += 1
        entry.last_accessed = time.monotonic()

        self._hits += 1
        logger.debug("Cache HIT for key=%s (hits=%d)", key[:16], self._hits)
        return entry.response

    async def set(self, key: str, response: LLMResponse) -> None:
        """Store a response in the cache.

        Args:
            key: The cache key.
            response: The LLM response to cache.
        """
        if self._redis_client is not None:
            await self._set_in_redis(key, response)
            return

        # Evict if at capacity
        if len(self._cache) >= self._max_entries:
            self._evict_lru()

        now = time.monotonic()
        entry = CacheEntry(
            key=key,
            response=response,
            created_at=now,
            expires_at=now + self._ttl_seconds,
        )
        self._cache[key] = entry
        logger.debug("Cache SET for key=%s (size=%d)", key[:16], len(self._cache))

    async def _get_from_redis(self, key: str) -> Optional[LLMResponse]:
        """Get a cached response from Redis.

        Args:
            key: The cache key.

        Returns:
            Cached response or None.
        """
        try:
            data = await self._redis_client.get(f"llm_cache:{key}")
            if data is None:
                self._misses += 1
                return None

            response_dict = json.loads(data)
            self._hits += 1
            return LLMResponse(**response_dict)
        except Exception as exc:
            logger.warning("Redis cache get failed: %s", exc)
            self._misses += 1
            return None

    async def _set_in_redis(self, key: str, response: LLMResponse) -> None:
        """Store a response in Redis cache.

        Args:
            key: The cache key.
            response: The response to cache.
        """
        try:
            response_dict = response.model_dump()
            await self._redis_client.setex(
                f"llm_cache:{key}",
                self._ttl_seconds,
                json.dumps(response_dict, default=str),
            )
        except Exception as exc:
            logger.warning("Redis cache set failed: %s", exc)

    def _evict_lru(self) -> None:
        """Evict the least recently used cache entry."""
        if not self._cache:
            return

        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed,
        )
        evicted = self._cache.pop(lru_key)
        logger.debug(
            "LRU evicted key=%s (accessed=%d times)",
            lru_key[:16],
            evicted.access_count,
        )

    async def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry.

        Args:
            key: The cache key to invalidate.
        """
        if self._redis_client is not None:
            await self._redis_client.delete(f"llm_cache:{key}")
        else:
            self._cache.pop(key, None)
        logger.debug("Cache invalidated for key=%s", key[:16])

    async def clear(self) -> None:
        """Clear all cache entries."""
        if self._redis_client is not None:
            await self._redis_client.delete_pattern("llm_cache:*")
        else:
            self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate as a float between 0 and 1.
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of entries in the cache.
        """
        if self._redis_client is not None:
            return 0  # Redis size not tracked locally
        return len(self._cache)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hit count, miss count, hit rate, and size.
        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
            "size": self.size,
            "max_entries": self._max_entries,
            "ttl_seconds": self._ttl_seconds,
        }

    async def close(self) -> None:
        """Close any backend connections."""
        # Redis client lifecycle is managed externally
        self._cache.clear()
        logger.info("Prompt cache closed")
