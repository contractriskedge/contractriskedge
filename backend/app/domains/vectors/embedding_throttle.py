"""Redis-backed concurrency gate for OpenAI embedding API calls."""

from __future__ import annotations

import asyncio
import logging
import random
import time

from app.config import settings

logger = logging.getLogger(__name__)

_EMBED_ACTIVE_KEY = "embed_active:{}"
_EMBED_SLOT_TTL = 300


async def _redis_client():
    import redis.asyncio as aioredis

    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=2,
    )


async def try_acquire_embedding_slot(tenant_id: str) -> bool:
    """Try to acquire an embedding concurrency slot. Fail-open if Redis is down."""
    try:
        r = await _redis_client()
        key = _EMBED_ACTIVE_KEY.format(tenant_id)
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, _EMBED_SLOT_TTL)
        count = (await pipe.execute())[0]
        max_concurrent = settings.embedding_max_concurrent
        if count > max_concurrent:
            await r.decr(key)
            await r.close()
            return False
        await r.close()
        return True
    except Exception as exc:
        logger.warning("Redis unavailable for embedding throttle: %s — allowing through", exc)
        return True


async def release_embedding_slot(tenant_id: str) -> None:
    try:
        r = await _redis_client()
        await r.decr(_EMBED_ACTIVE_KEY.format(tenant_id))
        await r.close()
    except Exception:
        pass


class embedding_slot:
    """Async context manager that waits for and releases an embedding slot."""

    def __init__(self, tenant_id: str, max_wait_seconds: float = 120):
        self.tenant_id = tenant_id
        self.max_wait_seconds = max_wait_seconds
        self._acquired = False

    async def __aenter__(self) -> bool:
        deadline = time.monotonic() + self.max_wait_seconds
        attempts = 0
        while time.monotonic() < deadline:
            if await try_acquire_embedding_slot(self.tenant_id):
                self._acquired = True
                return True
            attempts += 1
            if attempts >= 30:
                logger.warning(
                    "Embedding slots saturated for tenant %s — proceeding without throttle",
                    self.tenant_id,
                )
                return True
            delay = random.uniform(2, 6)
            logger.info(
                "Embedding slot full for tenant %s (max=%d). Waiting %.1fs.",
                self.tenant_id,
                settings.embedding_max_concurrent,
                delay,
            )
            await asyncio.sleep(delay)
        logger.warning(
            "Timed out waiting for embedding slot for tenant %s — proceeding without throttle",
            self.tenant_id,
        )
        return True

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            await release_embedding_slot(self.tenant_id)
