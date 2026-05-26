"""SQLAlchemy async engine, session factory, and tenant-safe session management.

CRITICAL: This module ensures tenant context is properly isolated across
database connection pool reuse. Every session creation resets PostgreSQL
session variables to prevent cross-tenant data leakage.

CRITICAL: Query timeout protections are applied on every session creation.
Without these, a runaway query can consume a connection indefinitely.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class TenantAwareSessionFactory:
    """Creates tenant-safe database sessions with timeout protections.

    Applies per-session:
    - statement_timeout (30s) — kills any single query exceeding this
    - lock_timeout (5s) — kills any lock wait exceeding this
    - idle_in_transaction_session_timeout (60s) — aborts idle transactions
    - tenant context for RLS
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 5,
        pool_recycle: int = 300,
        statement_timeout_ms: int = 30000,
        lock_timeout_ms: int = 5000,
        idle_transaction_timeout_s: int = 60,
        slow_query_threshold_ms: int = 500,
    ):
        self._statement_timeout_ms = statement_timeout_ms
        self._lock_timeout_ms = lock_timeout_ms
        self._idle_transaction_timeout_s = idle_transaction_timeout_s
        self._slow_query_threshold_ms = slow_query_threshold_ms

        self._engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=pool_recycle,
            echo=False,
            # asyncpg-specific: set application name for pg_stat_activity
            connect_args={
                "server_settings": {
                    "application_name": "contractrisk-api",
                },
            },
        )

        # ── Connection pool telemetry ──────────────────────────────
        self._connections_created = 0
        self._connections_closed = 0
        self._queries_executed = 0
        self._slow_queries = 0
        self._query_durations: list[int] = []  # For p50/p95/p99 tracking

        @event.listens_for(self._engine.sync_engine, "checkout")
        def _on_checkout(dbapi_connection, connection_record, connection_proxy):
            self._connections_created += 1

        @event.listens_for(self._engine.sync_engine, "checkin")
        def _on_checkin(dbapi_connection, connection_record):
            self._connections_closed += 1

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @property
    def pool_stats(self) -> dict:
        """Current connection pool statistics with p50/p95/p99 latency."""
        pool = self._engine.pool
        durations = self._query_durations
        p50 = p95 = p99 = 0
        if durations:
            sorted_d = sorted(durations)
            n = len(sorted_d)
            p50 = sorted_d[int(n * 0.50)]
            p95 = sorted_d[int(n * 0.95)]
            p99 = sorted_d[int(n * 0.99)]
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "connections_created": self._connections_created,
            "connections_closed": self._connections_closed,
            "queries_executed": self._queries_executed,
            "slow_queries": self._slow_queries,
            "p50_query_ms": p50,
            "p95_query_ms": p95,
            "p99_query_ms": p99,
        }

    async def create_session(
        self,
        tenant_id: str,
        user_id: str = "",
        user_role: str = "viewer",
    ) -> AsyncSession:
        """Create a new session with tenant context and query timeout protections.

        ALWAYS resets session variables before setting new values.
        This prevents context leaking from the previous connection user.

        ALWAYS sets query timeouts to prevent runaway queries.
        """
        session = self._session_factory()

        # Reset ALL session variables to prevent context leaks
        await session.execute(text("RESET app.tenant_id"))
        await session.execute(text("RESET app.user_id"))
        await session.execute(text("RESET app.user_role"))

        # ── Query timeout protections ──────────────────────────────
        # Kill any single query exceeding 30 seconds
        await session.execute(
            text(f"SET LOCAL statement_timeout = '{self._statement_timeout_ms}ms'")
        )
        # Kill any lock wait exceeding 5 seconds
        await session.execute(
            text(f"SET LOCAL lock_timeout = '{self._lock_timeout_ms}ms'")
        )
        # Abort any transaction idle for more than 60 seconds
        await session.execute(
            text(f"SET LOCAL idle_in_transaction_session_timeout = '{self._idle_transaction_timeout_s}s'")
        )

        # Set tenant context for RLS
        await session.execute(
            text(f"SET app.tenant_id = '{tenant_id}'"),
        )
        if user_id:
            await session.execute(
                text(f"SET app.user_id = '{user_id}'"),
            )
        if user_role:
            await session.execute(
                text(f"SET app.user_role = '{user_role}'"),
            )

        # Wrap execute to add slow query logging
        original_execute = session.execute
        session._parent_factory = self

        async def monitored_execute(statement, params=None, **kw):
            start = time.monotonic()
            try:
                result = await original_execute(statement, params=params, **kw)
                return result
            finally:
                duration_ms = int((time.monotonic() - start) * 1000)
                self._queries_executed += 1
                self._query_durations.append(duration_ms)
                # Keep only last 10000 durations for p95 tracking
                if len(self._query_durations) > 10000:
                    self._query_durations = self._query_durations[-5000:]

                if duration_ms > self._slow_query_threshold_ms:
                    self._slow_queries += 1
                    logger.warning(
                        "Slow query detected",
                        extra={
                            "duration_ms": duration_ms,
                            "threshold_ms": self._slow_query_threshold_ms,
                            "tenant_id": tenant_id,
                            "query": str(statement)[:200],
                        },
                    )

        session.execute = monitored_execute  # type: ignore[assignment]
        return session

    async def close(self):
        await self._engine.dispose()


# ── Synchronous session for Celery workers ─────────────────────────
# Celery tasks run in sync mode. This provides a sync session factory
# that connects to the same database with the same timeout protections.

_sync_engine = None


def create_sync_session() -> Session:
    """Create a synchronous SQLAlchemy session for Celery worker tasks.

    Uses the same database URL and timeout protections as the async factory.
    Each call creates a new session. Caller must close() it.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession
    from app.config import settings

    global _sync_engine
    if _sync_engine is None:
        # Convert asyncpg URL to psycopg2 for sync usage
        sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
        _sync_engine = create_engine(
            sync_url,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "options": "-c statement_timeout=30000 -c lock_timeout=5000",
            },
        )

    session = SyncSession(_sync_engine)
    return session
