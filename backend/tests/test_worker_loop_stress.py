"""Integration stress test for WorkerLoop — validates no cross-loop asyncpg failures.

Tests
-----
1. **Single-task execution** — basic sanity: one coroutine runs on the loop.
2. **Concurrent execution** — multiple coroutines run simultaneously via
   ``run_coroutine_threadsafe``, simulating Celery prefetch.
3. **Session lifecycle** — sessions are created, used, and closed without
   ``Event loop is closed`` or ``Future attached to a different loop``.
4. **Retry resilience** — tasks that fail and are retried do not exhibit
   cross-loop connection errors.
5. **Shutdown cleanliness** — ``WorkerLoop.shutdown()`` disposes the engine
   and closes the loop without errors.

Run::

    cd backend
    pytest tests/test_worker_loop_stress.py -v --timeout=120
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from sqlalchemy import text

from workers.worker_loop import WorkerLoop

logger = logging.getLogger(__name__)

# How many concurrent "tasks" to simulate
CONCURRENCY_LEVELS = [1, 5, 10, 20]


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def worker_loop():
    """Provide a fresh WorkerLoop for each test, then shut it down."""
    loop = WorkerLoop()
    loop.start()
    yield loop
    loop.shutdown()


# ── Helpers ────────────────────────────────────────────────────────


async def _ping_db(loop_ref: WorkerLoop, task_id: int) -> dict[str, Any]:
    """Execute a simple DB query and return diagnostics."""
    start = time.monotonic()
    session = await loop_ref.create_session("system", f"stress-test-{task_id}", "admin")
    try:
        result = await session.execute(text("SELECT 1 AS ok"))
        row = result.one()
        elapsed = time.monotonic() - start
        return {
            "task_id": task_id,
            "ok": row.ok,
            "elapsed_s": round(elapsed, 4),
            "session_id": id(session),
        }
    finally:
        await session.close()


async def _ping_db_with_scope(loop_ref: WorkerLoop, task_id: int) -> dict[str, Any]:
    """Same as _ping_db but uses session_scope for lifecycle."""
    start = time.monotonic()
    session = await loop_ref.create_session("system", f"stress-test-{task_id}", "admin")
    async with loop_ref.session_scope(session):
        result = await session.execute(text("SELECT 1 AS ok"))
        row = result.one()
        elapsed = time.monotonic() - start
        return {
            "task_id": task_id,
            "ok": row.ok,
            "elapsed_s": round(elapsed, 4),
            "session_id": id(session),
        }


async def _failing_query(loop_ref: WorkerLoop, task_id: int) -> None:
    """Execute a query that will fail (invalid SQL)."""
    session = await loop_ref.create_session("system", f"stress-test-{task_id}", "admin")
    async with loop_ref.session_scope(session):
        await session.execute(text("SELECT invalid_sql"))


# ── Tests ──────────────────────────────────────────────────────────


class TestWorkerLoopStress:
    """Stress tests for WorkerLoop stability under concurrent load."""

    def test_single_execution(self, worker_loop):
        """A single coroutine executes successfully on the worker loop."""
        result = worker_loop.run(_ping_db(worker_loop, 0))
        assert result["ok"] == 1
        assert result["elapsed_s"] < 10

    def test_multiple_sequential(self, worker_loop):
        """Multiple coroutines execute sequentially without errors."""
        for i in range(10):
            result = worker_loop.run(_ping_db(worker_loop, i))
            assert result["ok"] == 1
            logger.info("Sequential task %d: session=%s elapsed=%.4fs", i, result["session_id"], result["elapsed_s"])

    @pytest.mark.parametrize("concurrency", CONCURRENCY_LEVELS)
    def test_concurrent_from_thread_pool(self, worker_loop, concurrency):
        """Simulate Celery prefork: tasks from different threads share the same loop.

        This is the critical test.  If the engine is bound to the loop thread
        and ``run_coroutine_threadsafe`` is used correctly, all tasks should
        succeed.  If not, we get ``Future attached to a different loop``.
        """
        def _task(task_id: int) -> dict[str, Any]:
            """This runs in a worker thread — simulates a Celery task."""
            return worker_loop.run(_ping_db(worker_loop, task_id))

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(_task, i) for i in range(concurrency * 3)]

        results = [f.result(timeout=30) for f in futures]
        assert len(results) == concurrency * 3
        for r in results:
            assert r["ok"] == 1, f"Task {r['task_id']} failed: {r}"
        logger.info(
            "Concurrent %d: %d tasks completed, avg %.4fs",
            concurrency,
            len(results),
            sum(r["elapsed_s"] for r in results) / len(results),
        )

    @pytest.mark.parametrize("concurrency", [5, 10])
    def test_concurrent_with_session_scope(self, worker_loop, concurrency):
        """Concurrent tasks using session_scope for lifecycle management."""
        def _task(task_id: int) -> dict[str, Any]:
            return worker_loop.run(_ping_db_with_scope(worker_loop, task_id))

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(_task, i) for i in range(concurrency * 2)]

        results = [f.result(timeout=30) for f in futures]
        assert len(results) == concurrency * 2
        for r in results:
            assert r["ok"] == 1

    def test_session_isolation(self, worker_loop):
        """Each task gets its own session (no cross-task connection reuse)."""
        session_ids = set()
        for i in range(20):
            result = worker_loop.run(_ping_db(worker_loop, i))
            session_ids.add(result["session_id"])
        # With pool_size=10, we should see at most 10 unique session IDs
        # (the pool recycles connections, but each create_session returns a new session object)
        assert len(session_ids) == 20, "Each call should create a new session wrapper"

    def test_error_recovery(self, worker_loop):
        """A failing task does not corrupt the loop for subsequent tasks."""
        # Run a failing task
        with pytest.raises(Exception, match="invalid_sql"):
            worker_loop.run(_failing_query(worker_loop, 0))

        # The loop should still be usable
        result = worker_loop.run(_ping_db(worker_loop, 1))
        assert result["ok"] == 1

    def test_shutdown_cleanliness(self):
        """Shutdown disposes the engine and closes the loop without errors."""
        loop = WorkerLoop()
        loop.start()

        # Run a few tasks
        for i in range(5):
            loop.run(_ping_db(loop, i))

        # Shutdown should not raise
        loop.shutdown()

        # After shutdown, the loop should be closed
        assert loop._loop is None or loop._loop.is_closed()

    def test_loop_not_recreated(self, worker_loop):
        """The same event loop is reused across multiple run() calls."""
        loop_ids = set()
        for _ in range(10):
            worker_loop.run(_ping_db(worker_loop, 0))
            loop_ids.add(id(worker_loop._loop))
        assert len(loop_ids) == 1, "Loop should not be recreated"

    @pytest.mark.parametrize("concurrency", [5, 10])
    def test_mixed_success_failure(self, worker_loop, concurrency):
        """Mix of successful and failing tasks — failures don't affect others."""
        def _mixed_task(task_id: int) -> dict[str, Any]:
            if task_id % 3 == 0:
                # Every 3rd task fails
                return worker_loop.run(_failing_query(worker_loop, task_id))
            return worker_loop.run(_ping_db(worker_loop, task_id))

        results: list[dict | Exception] = []
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(_mixed_task, i) for i in range(concurrency * 3)]
            for f in futures:
                try:
                    results.append(f.result(timeout=30))
                except Exception as e:
                    results.append(e)

        successes = [r for r in results if isinstance(r, dict) and r.get("ok") == 1]
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(successes) > 0, "Some tasks should succeed"
        assert len(failures) > 0, "Some tasks should fail (expected)"
        logger.info("Mixed: %d successes, %d failures", len(successes), len(failures))

    def test_long_running_queries(self, worker_loop):
        """Simulate a longer-running query to ensure no timeout issues."""
        async def _slow_query(task_id: int) -> dict[str, Any]:
            session = await worker_loop.create_session("system", f"slow-{task_id}", "admin")
            async with worker_loop.session_scope(session):
                await asyncio.sleep(0.5)
                result = await session.execute(text("SELECT 1 AS ok"))
                row = result.one()
                return {"task_id": task_id, "ok": row.ok}

        results = []
        for i in range(5):
            results.append(worker_loop.run(_slow_query(i)))

        assert all(r["ok"] == 1 for r in results)

    def test_engine_pool_reuse(self, worker_loop):
        """The same engine pool is used across all tasks (no new engine per task)."""
        engine_ids = set()
        for _ in range(20):
            worker_loop.run(_ping_db(worker_loop, 0))
            engine_ids.add(id(worker_loop._factory._engine))

        assert len(engine_ids) == 1, "A single engine should be reused across all tasks"
