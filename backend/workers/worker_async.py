"""DEPRECATED — Use ``workers.worker_loop`` instead.

This module is kept for backward compatibility during migration.
All new code should use ``workers.worker_loop.worker_loop`` which provides
a **single persistent event loop** per worker process instead of creating
a new loop per task.

Legacy ``WorkerAsyncHelper`` and ``run_async`` now delegate to the global
``WorkerLoop`` singleton to avoid the ``RuntimeError: got Future attached
to a different loop`` and ``Event loop is closed`` errors caused by
creating/closing an event loop on every task invocation.
"""

from __future__ import annotations

import logging
from typing import Awaitable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

T = TypeVar("T")


class WorkerAsyncHelper:
    """DEPRECATED — Delegates to ``WorkerLoop``.

    Instead of creating a new event loop per task (which caused cross-loop
    asyncpg connection errors), this now runs coroutines on the single
    persistent ``WorkerLoop``.

    Usage remains the same::

        helper = WorkerAsyncHelper()
        return helper.run(_my_async_func(...))

    But under the hood it uses the global ``worker_loop`` singleton.
    """

    __slots__ = ()

    def run(self, coro: Awaitable[T]) -> T:
        """Execute a coroutine on the persistent worker loop.

        Unlike the old implementation, this does NOT create a new event
        loop — it reuses the single ``WorkerLoop`` that lives for the
        entire lifetime of the worker process.
        """
        return worker_loop.run(coro)

    def session_scope(self, session: AsyncSession) -> "_SessionScope":
        """Register an AsyncSession for automatic lifecycle management.

        Delegates to ``WorkerLoop.session_scope``.
        """
        return worker_loop.session_scope(session)


class _SessionScope:
    """DEPRECATED — Delegates to ``WorkerLoop._SessionScope``.

    Kept for backward compatibility with existing ``async with
    helper.session_scope(session)`` usage.
    """

    __slots__ = ("_scope",)

    def __init__(self, session: AsyncSession) -> None:
        self._scope = worker_loop.session_scope(session)

    async def __aenter__(self) -> AsyncSession:
        return await self._scope.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._scope.__aexit__(exc_type, exc_val, exc_tb)


# ── Module-level convenience ───────────────────────────────────────


def run_async(coro: Awaitable[T]) -> T:
    """Run an async coroutine on the persistent worker loop.

    DEPRECATED — Use ``worker_loop.run(coro)`` directly instead.

    Usage::

        from workers.worker_async import run_async

        def my_task(self, ...):
            return run_async(_my_async_func(...))
    """
    return worker_loop.run(coro)
