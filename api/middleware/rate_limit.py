"""Rate limiting middleware for FastAPI using Redis.

Provides configurable rate limiting per user/IP with Redis-backed
token bucket algorithm. Supports different rate limits for
authenticated vs anonymous users.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional, Set, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-backed token bucket rate limiter.

    Supports per-user and per-IP rate limiting with configurable
    rates and burst allowances.

    Attributes:
        redis_url: Redis connection URL.
        default_rate: Default requests per window (default 100).
        default_window: Window size in seconds (default 60).
        burst_multiplier: Burst allowance multiplier (default 2).
    """

    def __init__(
        self,
        redis_url: str = "",
        default_rate: int = 100,
        default_window: int = 60,
        burst_multiplier: int = 2,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            redis_url: Redis connection URL.
            default_rate: Default max requests per window.
            default_window: Window size in seconds.
            burst_multiplier: How many times the rate to allow as burst.
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.default_rate = default_rate
        self.default_window = default_window
        self.burst_multiplier = burst_multiplier
        self._redis: Any = None
        self._local_buckets: Dict[str, Tuple[int, float]] = {}  # key -> (tokens, last_refill)

    async def _get_redis(self) -> Any:
        """Get the Redis client (lazy init).

        Returns:
            Redis client or None if unavailable.
        """
        if self._redis is not None:
            return self._redis

        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await self._redis.ping()
            return self._redis
        except Exception:
            logger.warning("Redis unavailable for rate limiting; using local fallback")
            self._redis = False  # Sentinel for "no redis"
            return None

    def _get_client_key(self, request: Request) -> str:
        """Get a unique key for the client (user ID or IP).

        Args:
            request: The incoming request.

        Returns:
            A string key for rate limiting.
        """
        # Prefer authenticated user ID
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "sub"):
            return f"user:{user.sub}"

        # Fall back to IP
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _get_rate_for_client(self, client_key: str) -> Tuple[int, int]:
        """Get the rate limit for a specific client.

        Authenticated users get higher limits than anonymous IPs.

        Args:
            client_key: The client identifier key.

        Returns:
            Tuple of (rate, window_seconds).
        """
        if client_key.startswith("user:"):
            return (self.default_rate, self.default_window)
        return (self.default_rate // 2, self.default_window)

    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict[str, Any]]:
        """Check if a request should be rate limited.

        Args:
            request: The incoming request.

        Returns:
            Tuple of (allowed, headers_dict).
            headers_dict contains X-RateLimit-* headers.
        """
        client_key = self._get_client_key(request)
        rate, window = self._get_rate_for_client(client_key)

        redis = await self._get_redis()
        now = time.time()

        if redis:
            # Redis-backed rate limiting with sliding window
            window_key = f"ratelimit:{client_key}:{int(now / window)}"
            pipe = redis.pipeline()
            pipe.incr(window_key)
            pipe.expire(window_key, window * 2)
            result = await pipe.execute()
            current_count = result[0]
        else:
            # Local in-memory fallback with token bucket
            current_count, headers = await self._local_token_bucket(client_key, rate, window, now)
            return current_count, headers

        allowed = current_count <= rate
        remaining = max(0, rate - current_count)
        reset_time = int((int(now / window) + 1) * window)

        headers = {
            "X-RateLimit-Limit": str(rate),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }

        return allowed, headers

    async def _local_token_bucket(
        self,
        client_key: str,
        rate: int,
        window: int,
        now: float,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Local in-memory token bucket fallback.

        Args:
            client_key: Client identifier.
            rate: Max tokens.
            window: Window in seconds.
            now: Current timestamp.

        Returns:
            Tuple of (allowed, headers).
        """
        tokens_per_second = rate / window
        max_burst = rate * self.burst_multiplier

        if client_key not in self._local_buckets:
            self._local_buckets[client_key] = (max_burst, now)

        tokens, last_refill = self._local_buckets[client_key]
        elapsed = now - last_refill
        tokens = min(max_burst, tokens + elapsed * tokens_per_second)

        if tokens >= 1:
            tokens -= 1
            self._local_buckets[client_key] = (tokens, now)
            remaining_tokens = int(tokens)
            return True, {
                "X-RateLimit-Limit": str(rate),
                "X-RateLimit-Remaining": str(remaining_tokens),
                "X-RateLimit-Reset": str(int(now + window)),
            }

        self._local_buckets[client_key] = (tokens, now)
        retry_after = int(1 / tokens_per_second) if tokens_per_second > 0 else 1
        return False, {
            "X-RateLimit-Limit": str(rate),
            "X-RateLimit-Remaining": "0",
            "Retry-After": str(retry_after),
        }


def _canonical_request_path(path: str) -> str:
    stripped = path.rstrip("/")
    return stripped if stripped else "/"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting.

    Applies rate limits to all requests and returns 429 when
    limits are exceeded.
    """

    def __init__(
        self,
        app: Any,
        exclude_paths: Optional[Set[str]] = None,
    ) -> None:
        """Initialize the rate limit middleware.

        Args:
            app: The ASGI application.
            exclude_paths: Paths to exclude from rate limiting.
        """
        super().__init__(app)
        raw_exclude = exclude_paths or {
            "/api/v1/health",
            "/health",
            "/ready",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        }
        self.exclude_paths = raw_exclude
        self.exclude_paths_canonical = {_canonical_request_path(p) for p in raw_exclude}
        self.limiter = RateLimiter()

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process the request through rate limiting.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response, possibly with 429 status.
        """
        req_path = request.url.path
        if req_path in self.exclude_paths or _canonical_request_path(req_path) in self.exclude_paths_canonical:
            return await call_next(request)

        try:
            allowed, headers = await self.limiter.check_rate_limit(request)
        except Exception as exc:
            logger.error("Rate limit check failed: %s", exc)
            # Allow the request on rate limiter failure
            return await call_next(request)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for %s on %s",
                request.client.host if request.client else "unknown",
                request.url.path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                },
                headers={
                    **headers,
                    "Content-Type": "application/json",
                },
            )

        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value

        return response
