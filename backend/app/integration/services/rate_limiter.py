"""
Rate Limiter — token-bucket rate limiting for external API calls.

Tracks per-integration and per-tenant rate usage with configurable
windows and burst allowances.
"""

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from structlog import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitState:
    """Tracks rate limit state for a single integration."""

    max_requests: int
    window_seconds: int
    tokens: float
    last_refill: float
    remaining: int
    reset_at: float


class RateLimiter:
    """
    Token-bucket rate limiter for external API integrations.

    Supports per-integration rate limits with configurable windows.
    Uses in-memory state by default; can be backed by Redis for distributed use.
    """

    def __init__(self, use_redis: bool = False, redis_client=None):
        self._use_redis = use_redis
        self._redis = redis_client
        self._local_buckets: dict[str, RateLimitState] = {}
        self._lock = Lock()

    async def check_sync_rate_limit(
        self,
        integration_id: uuid.UUID,
        max_requests: Optional[int] = None,
        window_seconds: int = 60,
    ) -> bool:
        """
        Check if a sync operation is allowed under the rate limit.

        Returns True if allowed, False if rate limited.
        """
        if max_requests is None:
            return True  # No rate limit configured

        key = str(integration_id)
        now = time.time()

        if self._use_redis and self._redis:
            return await self._check_redis(key, max_requests, window_seconds, now)

        return self._check_local(key, max_requests, window_seconds, now)

    def _check_local(
        self, key: str, max_requests: int, window_seconds: int, now: float
    ) -> bool:
        """Check rate limit using local in-memory state."""
        with self._lock:
            state = self._local_buckets.get(key)

            if state is None:
                state = RateLimitState(
                    max_requests=max_requests,
                    window_seconds=window_seconds,
                    tokens=float(max_requests),
                    last_refill=now,
                    remaining=max_requests,
                    reset_at=now + window_seconds,
                )
                self._local_buckets[key] = state

            # Refill tokens
            elapsed = now - state.last_refill
            refill = (elapsed / state.window_seconds) * state.max_requests
            state.tokens = min(state.max_requests, state.tokens + refill)
            state.last_refill = now

            if state.tokens >= 1.0:
                state.tokens -= 1.0
                state.remaining = int(state.tokens)
                state.reset_at = now + state.window_seconds
                return True
            else:
                state.remaining = 0
                logger.warning(
                    "rate_limit_exceeded",
                    key=key,
                    max_requests=max_requests,
                    window_seconds=window_seconds,
                )
                return False

    async def _check_redis(
        self, key: str, max_requests: int, window_seconds: int, now: float
    ) -> bool:
        """Check rate limit using Redis-backed sliding window."""
        redis_key = f"ratelimit:integration:{key}"
        current = int(now)
        window_start = current - window_seconds

        # Remove old entries
        await self._redis.zremrangebyscore(redis_key, 0, window_start)

        # Count current entries
        count = await self._redis.zcard(redis_key)

        if count >= max_requests:
            logger.warning(
                "rate_limit_exceeded_redis",
                key=key,
                count=count,
                max_requests=max_requests,
            )
            return False

        # Add current request
        await self._redis.zadd(redis_key, {str(current): current})
        await self._redis.expire(redis_key, window_seconds * 2)

        return True

    def get_remaining(self, integration_id: uuid.UUID) -> Optional[int]:
        """Get remaining requests for an integration."""
        key = str(integration_id)
        with self._lock:
            state = self._local_buckets.get(key)
            if state:
                return state.remaining
        return None

    def get_reset_at(self, integration_id: uuid.UUID) -> Optional[float]:
        """Get the timestamp when the rate limit resets."""
        key = str(integration_id)
        with self._lock:
            state = self._local_buckets.get(key)
            if state:
                return state.reset_at
        return None

    def reset(self, integration_id: uuid.UUID) -> None:
        """Reset rate limit for an integration."""
        key = str(integration_id)
        with self._lock:
            self._local_buckets.pop(key, None)
        logger.info("rate_limit_reset", integration_id=str(integration_id))


class RateLimitTracker:
    """
    Tracks and records rate limit headers from external API responses.

    Useful for adapting to provider-enforced rate limits dynamically.
    """

    def __init__(self):
        self._tracked: dict[str, dict] = {}

    def record_response(
        self,
        provider: str,
        remaining: Optional[int],
        limit: Optional[int],
        reset_at: Optional[float],
    ) -> None:
        """Record rate limit info from an API response."""
        key = f"{provider}"
        self._tracked[key] = {
            "remaining": remaining,
            "limit": limit,
            "reset_at": reset_at,
            "recorded_at": time.time(),
        }

    def get_status(self, provider: str) -> Optional[dict]:
        """Get the latest rate limit status for a provider."""
        return self._tracked.get(provider)

    def is_throttled(self, provider: str, min_remaining: int = 5) -> bool:
        """Check if a provider is close to being rate limited."""
        status = self._tracked.get(provider)
        if not status:
            return False
        remaining = status.get("remaining")
        if remaining is None:
            return False
        return remaining <= min_remaining
