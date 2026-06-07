"""Rate limiting middleware for FastAPI.

Provides Redis-backed sliding window rate limiting with tenant-aware limits.
Supports different rate tiers for authenticated vs anonymous users,
and per-endpoint rate limit overrides.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.kernel.middleware.excluded_paths import is_path_excluded
from app.kernel.middleware.ai_rate_limits import match_ai_endpoint

logger = logging.getLogger(__name__)

# Default rate limits (requests per window)
DEFAULT_RATE_LIMITS: dict[str, int] = {
    "anonymous": 20,       # 20 req/min for unauthenticated users
    "authenticated": 100,  # 100 req/min for authenticated users
    "admin": 500,          # 500 req/min for admin users
}

# Stricter limits for sensitive endpoints
ENDPOINT_OVERIDES: dict[str, int] = {
    "/api/v1/auth/token": 10,           # 10 req/min for login
    "/api/v1/integration/webhooks/ingest": 200,  # 200 req/min for webhook ingestion
    "/api/v1/ingestion/upload": 30,     # 30 req/min for uploads
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis-backed sliding window counters.

    Falls back to in-memory counters if Redis is unavailable.
    Applies per-tenant and per-user rate limits.
    """

    def __init__(self, app):
        super().__init__(app)
        self._redis = None
        self._local_counters: dict[str, list[float]] = {}

    async def _get_redis(self):
        """Lazy-init Redis client from app state."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                client = aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_keepalive=False,
                )
                await client.ping()
                self._redis = client
            except Exception:
                self._redis = False  # Sentinel — skip Redis for this session
        return self._redis if self._redis else None

    def _get_client_key(self, request: Request) -> str:
        """Derive a unique rate limit key for the client.

        Priority: user ID > tenant ID > IP address.
        """
        user = getattr(request.state, "user", None)
        if user and getattr(user, "id", None):
            return f"user:{user.id}"
        if user and getattr(user, "tenant_id", None):
            return f"tenant:{user.tenant_id}"
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client = request.client
        if client:
            return f"ip:{client.host}"
        return "ip:unknown"

    def _get_rate_limit(self, request: Request) -> int:
        """Determine the rate limit for this request based on user role and endpoint."""
        path = request.url.path

        # Check regex-based AI endpoint patterns first (handles UUID segments)
        ai_match = match_ai_endpoint(path)
        if ai_match is not None:
            pattern, user_limit, tenant_limit = ai_match
            # Store tenant limit on request state for dispatch() to check
            request.state._ai_tenant_limit = tenant_limit
            request.state._ai_operation = pattern.pattern
            return user_limit

        # Check prefix-based endpoint overrides
        for endpoint_path, limit in ENDPOINT_OVERIDES.items():
            if path.startswith(endpoint_path):
                return limit

        # Role-based limits
        user = getattr(request.state, "user", None)
        if user and getattr(user, "role", None):
            role = user.role.lower()
            if role in ("admin", "tenant_admin", "superadmin"):
                return DEFAULT_RATE_LIMITS["admin"]
            return DEFAULT_RATE_LIMITS["authenticated"]

        return DEFAULT_RATE_LIMITS["anonymous"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for excluded paths and OPTIONS
        if is_path_excluded(request.url.path) or request.method == "OPTIONS":
            return await call_next(request)

        try:
            client_key = self._get_client_key(request)
            rate_limit = self._get_rate_limit(request)
            window_seconds = 60  # 1-minute sliding window

            redis_client = await self._get_redis()
            if redis_client:
                allowed = await self._check_redis(redis_client, client_key, rate_limit, window_seconds)
            else:
                allowed = self._check_local(client_key, rate_limit, window_seconds)

            if not allowed:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_key": client_key,
                        "rate_limit": rate_limit,
                        "path": request.url.path,
                        "method": request.method,
                    },
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Too many requests. Limit: {rate_limit} per {window_seconds}s. Try again later.",
                    },
                    headers={
                        "Retry-After": str(window_seconds),
                        "X-RateLimit-Limit": str(rate_limit),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            # Tenant-level AI rate limit check (after per-user check passes)
            tenant_limit = getattr(request.state, "_ai_tenant_limit", None)
            if tenant_limit is not None:
                tenant_id = getattr(request.state.user, "tenant_id", None) if hasattr(request.state, "user") else None
                if tenant_id:
                    operation = getattr(request.state, "_ai_operation", "unknown")
                    tenant_key = f"ai_tenant:{tenant_id}:{operation}"
                    tenant_window = settings.ai_rate_limit_tenant_window_seconds
                    if redis_client:
                        tenant_allowed = await self._check_redis(
                            redis_client, tenant_key, tenant_limit, tenant_window
                        )
                    else:
                        tenant_allowed = self._check_local(
                            tenant_key, tenant_limit, tenant_window
                        )
                    if not tenant_allowed:
                        logger.warning(
                            "Tenant AI rate limit exceeded",
                            extra={
                                "tenant_id": tenant_id,
                                "tenant_limit": tenant_limit,
                                "path": request.url.path,
                                "operation": operation,
                            },
                        )
                        return JSONResponse(
                            status_code=429,
                            content={
                                "error": "tenant_rate_limit_exceeded",
                                "message": f"Tenant AI request limit ({tenant_limit}) reached. Try again later.",
                            },
                            headers={
                                "Retry-After": str(tenant_window),
                                "X-RateLimit-Limit": str(rate_limit),
                                "X-RateLimit-Remaining": "0",
                            },
                        )

            response = await call_next(request)
            # Add rate limit headers
            try:
                remaining = (
                    await self._get_remaining(redis_client, client_key, rate_limit, window_seconds)
                    if redis_client
                    else self._get_remaining_local(client_key, rate_limit, window_seconds)
                )
                response.headers["X-RateLimit-Limit"] = str(rate_limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
            except Exception:
                pass  # Non-critical: rate limit headers are informational
            return response
        except Exception:
            # If rate limiting itself fails, allow the request through
            return await call_next(request)

    async def _check_redis(self, redis_client, key: str, limit: int, window: int) -> bool:
        """Sliding window rate check via Redis sorted set."""
        redis_key = f"ratelimit:{key}"
        now = time.time()
        window_start = now - window

        # Remove old entries outside the window
        await redis_client.zremrangebyscore(redis_key, 0, window_start)
        # Count current entries
        count = await redis_client.zcard(redis_key)

        if count >= limit:
            return False

        # Add current request timestamp
        await redis_client.zadd(redis_key, {str(now): now})
        await redis_client.expire(redis_key, window * 2)
        return True

    def _check_local(self, key: str, limit: int, window: int) -> bool:
        """In-memory fallback rate check."""
        now = time.time()
        timestamps = self._local_counters.get(key, [])
        # Prune old entries
        timestamps = [t for t in timestamps if now - t < window]
        if len(timestamps) >= limit:
            return False
        timestamps.append(now)
        self._local_counters[key] = timestamps
        return True

    async def _get_remaining(self, redis_client, key: str, limit: int, window: int) -> int:
        """Get remaining requests for Redis-backed rate limit."""
        try:
            redis_key = f"ratelimit:{key}"
            now = time.time()
            window_start = now - window
            await redis_client.zremrangebyscore(redis_key, 0, window_start)
            count = await redis_client.zcard(redis_key)
            return max(0, limit - count)
        except Exception:
            return limit

    def _get_remaining_local(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests for in-memory rate limit."""
        now = time.time()
        timestamps = self._local_counters.get(key, [])
        timestamps = [t for t in timestamps if now - t < window]
        return max(0, limit - len(timestamps))
