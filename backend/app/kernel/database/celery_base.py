"""Base Celery task classes with automatic session lifecycle management.

Provides:
- TenantSafeTask: Base task with auto-created/closed tenant-safe sync sessions
- Ensures sessions are always closed, even on failure
- Prevents connection leaks across worker task invocations
"""

from __future__ import annotations

import logging

from celery import Task
from sqlalchemy.orm import Session

from app.kernel.database.sync_session import get_sync_factory

logger = logging.getLogger(__name__)


class TenantSafeTask(Task):
    """Celery task base class with automatic tenant-safe session management.

    Features:
    - Lazy session creation via self.get_session(tenant_id, user_id, role)
    - Automatic session close in after_return() and on_failure()
    - Shared engine across all tasks (no per-task engine creation)
    - Tenant RLS context isolation

    Usage:
        @celery_app.task(base=TenantSafeTask, ...)
        def my_task(self, ...):
            session = self.get_session(tenant_id="...", user_id="...", user_role="admin")
            try:
                # ... work with session ...
                session.commit()
            except Exception:
                session.rollback()
                raise
    """

    abstract = True
    _session: Session | None = None

    def get_session(
        self,
        tenant_id: str = "system",
        user_id: str = "system",
        user_role: str = "admin",
    ) -> Session:
        """Get or create a tenant-safe database session.

        The session is cached on the task instance and automatically
        closed when the task completes (success or failure).
        """
        if self._session is None:
            factory = get_sync_factory()
            self._session = factory.create_session(
                tenant_id=tenant_id,
                user_id=user_id,
                user_role=user_role,
            )
        return self._session

    def cleanup_session(self) -> None:
        """Close the session if it exists and is open."""
        if self._session is not None:
            try:
                self._session.close()
            except Exception as exc:
                logger.warning("Error closing task session: %s", exc)
            finally:
                self._session = None

    def after_return(self, status: str, retval: object, task_id: str,
                     args: tuple, kwargs: dict, einfo: object | None) -> None:
        """Ensure session is cleaned up after task completes."""
        self.cleanup_session()

    def on_failure(self, exc: Exception, task_id: str, args: tuple,
                   kwargs: dict, einfo: object) -> None:
        """Ensure session is cleaned up on task failure."""
        self.cleanup_session()
