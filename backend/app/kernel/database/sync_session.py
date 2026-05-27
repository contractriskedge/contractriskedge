"""Synchronous session factory for Celery workers with tenant-safe RLS context.

Celery workers run in sync mode. This factory provides tenant-isolated
sync database sessions with the same timeout protections and RLS context
as the async TenantAwareSessionFactory.

Usage:
    factory = SyncSessionFactory()
    session = factory.create_session(tenant_id="...", user_id="...", user_role="admin")
    try:
        # ... work ...
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
"""

from __future__ import annotations

import logging
from threading import Lock

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)


class SyncSessionFactory:
    """Thread-safe synchronous session factory for Celery workers.

    Maintains a single shared engine per process (thread-safe via connection pool).
    Each call to create_session() returns a new session bound to that engine
    with tenant context and timeout protections applied.
    """

    def __init__(self):
        self._engine = None
        self._lock = Lock()

    def _get_engine(self):
        """Lazy-init the shared sync engine (thread-safe)."""
        if self._engine is None:
            with self._lock:
                if self._engine is None:  # Double-checked locking
                    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
                    self._engine = create_engine(
                        sync_url,
                        pool_size=5,
                        max_overflow=2,
                        pool_pre_ping=True,
                        pool_recycle=300,
                        connect_args={
                            "options": (
                                f"-c statement_timeout={settings.db_statement_timeout_ms} "
                                f"-c lock_timeout={settings.db_lock_timeout_ms} "
                                f"-c idle_in_transaction_session_timeout={settings.db_idle_transaction_timeout_s * 1000}"
                            ),
                        },
                    )
                    logger.info(
                        "Sync session engine created (pool_size=%d, max_overflow=%d)",
                        5, 2,
                    )
        return self._engine

    def create_session(
        self,
        tenant_id: str,
        user_id: str = "",
        user_role: str = "viewer",
    ) -> Session:
        """Create a new sync session with tenant context and timeout protections.

        Sets PostgreSQL session variables for RLS enforcement, same as
        the async TenantAwareSessionFactory.
        """
        engine = self._get_engine()
        session = Session(engine)

        try:
            # Reset ALL session variables to prevent context leaks
            session.execute(text("RESET app.tenant_id"))
            session.execute(text("RESET app.user_id"))
            session.execute(text("RESET app.user_role"))

            # Set tenant context for RLS
            session.execute(
                text(f"SET app.tenant_id = '{tenant_id}'"),
            )
            if user_id:
                session.execute(
                    text(f"SET app.user_id = '{user_id}'"),
                )
            if user_role:
                session.execute(
                    text(f"SET app.user_role = '{user_role}'"),
                )
        except Exception:
            session.close()
            raise

        return session

    def close(self):
        """Dispose the engine (call on worker shutdown)."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Sync session engine disposed")


# Module-level singleton
_sync_factory = None
_factory_lock = Lock()


def get_sync_factory() -> SyncSessionFactory:
    """Get or create the shared SyncSessionFactory singleton."""
    global _sync_factory
    if _sync_factory is None:
        with _factory_lock:
            if _sync_factory is None:
                _sync_factory = SyncSessionFactory()
    return _sync_factory
