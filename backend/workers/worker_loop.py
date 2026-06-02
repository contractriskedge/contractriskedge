"""Single persistent event loop per worker process for async Celery tasks.

Architecture
------------
Every Celery worker process runs in a **sync** context.  When a task needs
to call async code (SQLAlchemy async sessions, HTTP clients, etc.) we need
a persistent event loop that lives for the entire lifetime of the worker
process, *not* a new loop per task.

**The problem with per-task loops:**

1. ``RuntimeError: Event loop is closed`` — asyncpg's connection cleanup
   tries to schedule work on the loop after it has been closed.

2. ``RuntimeError: got Future attached to a different loop`` — if an
   ``AsyncEngine`` was created on loop A, then a retry creates a new
   engine on loop B, asyncpg connections from loop A's pool leak and get
   reused on loop B.

3. ``TenantAwareSessionFactory`` creates a new ``AsyncEngine`` each time,
   each with its own connection pool — wasteful and dangerous.

**Solution — :class:`WorkerLoop`:**

- Creates a **single** ``asyncio.AbstractEventLoop`` when the module is
  first loaded (i.e. once per worker process).
- Provides :meth:`run` to execute a coroutine on that persistent loop via
  ``run_coroutine_threadsafe`` (if called from a non-main thread) or
  ``run_until_complete`` (if called from the loop's own thread).
- Provides :meth:`session_scope` for automatic ``AsyncSession`` lifecycle
  management (rollback + close).
- Holds a **single** shared ``AsyncEngine`` / ``TenantAwareSessionFactory``
  so all tasks in the same worker process reuse the same connection pool.
- Registers a Celery worker-shutdown signal handler that disposes the
  engine and closes the loop gracefully.

Usage::

    from workers.worker_loop import worker_loop

    def my_celery_task(self, ...):
        return worker_loop.run(_my_async_func(...))

    async def _my_async_func(...):
        session = await worker_loop.create_session(tenant_id, user_id, role)
        async with worker_loop.session_scope(session):
            ...
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import signal
import threading
from contextvars import ContextVar
from typing import Awaitable, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.kernel.database.session import TenantAwareSessionFactory

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Track the active task for diagnostics
_current_task_id: ContextVar[str | None] = ContextVar("_current_task_id", default=None)


class WorkerLoop:
    """Persistent event loop + shared engine for a Celery worker process.

    Thread safety
    -------------
    - ``run()`` is thread-safe — it uses ``run_coroutine_threadsafe`` when
      called from a thread other than the loop's own thread.
    - The loop runs in a dedicated background thread (the "loop thread").
    - ``create_session()`` is *not* thread-safe — it must be called from
      within a coroutine running on the loop thread.

    Lifecycle
    ---------
    - The loop and engine are created when :meth:`start` is called (or on
      first use via :meth:`run`).
    - :meth:`shutdown` disposes the engine and closes the loop.
    - A Celery ``worker_shutting_down`` signal handler calls :meth:`shutdown`.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._factory: TenantAwareSessionFactory | None = None
        self._started = False
        self._lock = threading.Lock()

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background event loop thread and create the shared engine.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._started:
            return
        with self._lock:
            if self._started:
                return
            self._loop = asyncio.new_event_loop()
            # Python 3.11+ requires a ThreadPoolExecutor instance, not None
            try:
                self._loop.set_default_executor(concurrent.futures.ThreadPoolExecutor())
            except TypeError:
                pass  # Older Python versions may not accept this either

            # Start the loop in a daemon thread so it doesn't block shutdown
            self._loop_thread = threading.Thread(
                target=self._run_loop_forever,
                name="worker-asyncio",
                daemon=True,
            )
            self._loop_thread.start()

            # Create the shared engine factory on the loop thread
            future = asyncio.run_coroutine_threadsafe(
                self._create_factory(),
                self._loop,
            )
            future.result(timeout=30)  # Wait for engine creation

            self._started = True
            logger.info(
                "WorkerLoop started (thread=%s, loop=%s)",
                self._loop_thread.name,
                id(self._loop),
            )

    def shutdown(self) -> None:
        """Shut down the event loop and dispose the database engine.

        Safe to call multiple times.
        """
        if not self._started:
            return
        with self._lock:
            if not self._started:
                return
            self._started = False
            loop = self._loop

            if loop is not None and not loop.is_closed():
                # Dispose the engine on the loop thread first
                if self._factory is not None:
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self._factory.close(),
                            loop,
                        )
                        future.result(timeout=15)
                    except Exception:
                        logger.exception("Error disposing engine during shutdown")
                    self._factory = None

                # Stop the loop
                loop.call_soon_threadsafe(loop.stop)

            self._loop = None
            self._loop_thread = None
            logger.info("WorkerLoop shut down")

    # ── Execute a coroutine on the persistent loop ────────────────

    def run(self, coro: Awaitable[T], task_id: str | None = None) -> T:
        """Execute an async coroutine on the persistent worker loop.

        Thread-safe.  If called from the loop's own thread, uses
        ``run_until_complete``.  Otherwise uses ``run_coroutine_threadsafe``.
        """
        self.start()  # Ensure started

        loop = self._loop
        assert loop is not None

        current_thread = threading.current_thread()
        is_loop_thread = current_thread is self._loop_thread

        if is_loop_thread:
            # Already on the loop thread — run directly
            token = _current_task_id.set(task_id)
            try:
                return loop.run_until_complete(coro)
            finally:
                _current_task_id.reset(token)
        else:
            # Called from a Celery worker thread — use thread-safe dispatch
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()

    # ── Session management ────────────────────────────────────────

    async def create_session(
        self,
        tenant_id: str,
        user_id: str = "",
        user_role: str = "viewer",
    ) -> AsyncSession:
        """Create a new tenant-scoped AsyncSession from the shared engine.

        Must be called from within a coroutine running on the loop thread.
        """
        assert self._factory is not None, "WorkerLoop not started"
        return await self._factory.create_session(tenant_id, user_id, user_role)

    def session_scope(self, session: AsyncSession) -> "_SessionScope":
        """Register an AsyncSession for automatic lifecycle management.

        The session is closed (rolled back first if active) when the
        context manager exits — *without* closing the event loop.
        """
        return _SessionScope(session)

    # ── Internal helpers ──────────────────────────────────────────

    async def _shutdown_engine(self) -> None:
        """Dispose the shared engine without shutting down the loop.

        Used after fork to discard the parent process's connection pool.
        """
        if self._factory is not None:
            try:
                await self._factory.close()
            except Exception:
                logger.exception("Error disposing engine after fork")
            self._factory = None

    def _run_loop_forever(self) -> None:
        """Run the event loop forever (daemon thread target)."""
        loop = self._loop
        assert loop is not None
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        except Exception:
            logger.exception("Worker event loop crashed")
        finally:
            # Clean up any remaining tasks
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass
            logger.info("Worker event loop exited")

    async def _create_factory(self) -> None:
        """Create the shared TenantAwareSessionFactory on the loop thread."""
        self._factory = TenantAwareSessionFactory(
            database_url=settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle,
            statement_timeout_ms=settings.db_statement_timeout_ms,
            lock_timeout_ms=settings.db_lock_timeout_ms,
            idle_transaction_timeout_s=settings.db_idle_transaction_timeout_s,
            slow_query_threshold_ms=settings.db_slow_query_threshold_ms,
        )
        logger.info(
            "Shared TenantAwareSessionFactory created (pool=%d, overflow=%d)",
            settings.db_pool_size,
            settings.db_max_overflow,
        )


class _SessionScope:
    """Async context manager that rolls back on exception and closes on exit.

    Unlike the old ``WorkerAsyncHelper.session_scope``, this does NOT rely
    on the helper to close sessions — it closes them directly in ``__aexit__``
    because the loop is persistent and never closed between tasks.
    """

    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type is not None and self._session.is_active:
            try:
                await self._session.rollback()
            except Exception:
                logger.exception("Error rolling back session")
        try:
            await self._session.close()
        except Exception:
            logger.exception("Error closing session")


# ── Module-level singleton ─────────────────────────────────────────

worker_loop = WorkerLoop()

# Register Celery worker lifecycle handlers
try:
    from celery.signals import worker_process_init, worker_shutting_down

    @worker_process_init.connect
    def _on_worker_process_init(**kwargs) -> None:  # type: ignore[misc]
        """Dispose the inherited async engine after fork.

        When Celery forks worker processes (ForkPoolWorker), the async
        engine's connection pool from the parent process is inherited.
        Child processes must create their own fresh pool to avoid
        ``non-checked-in connection`` warnings from asyncpg.

        This handler runs in each child process after fork, before any
        tasks are executed. It resets the WorkerLoop state so the next
        call to ``start()`` creates a new engine on the child's event loop.
        """
        logger.info(
            "Celery worker process initialized (PID=%s) — resetting WorkerLoop engine",
            os.getpid(),
        )
        # Reset the factory so a new engine is created in this child process
        worker_loop._factory = None
        worker_loop._started = False
        # Dispose the inherited engine if it exists
        if worker_loop._loop is not None and not worker_loop._loop.is_closed():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    worker_loop._shutdown_engine(),
                    worker_loop._loop,
                )
                future.result(timeout=10)
            except Exception:
                logger.debug("Inherited engine already disposed or loop not ready")
        worker_loop._loop = None
        worker_loop._loop_thread = None

    @worker_shutting_down.connect
    def _on_worker_shutdown(**kwargs) -> None:  # type: ignore[misc]
        logger.info("Celery worker shutting down — cleaning up WorkerLoop")
        worker_loop.shutdown()

except ImportError:
    # Celery not available (e.g. during tests or API process)
    pass
