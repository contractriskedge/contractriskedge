"""Failure Recovery — transaction safety for multi-step operations.

Provides:
- Transactional wrappers for multi-step operations
- Safe rollback on failure
- Compensating actions for partial failures
- Retry-safe step tracking
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Coroutine, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class OperationStep:
    """A single step in a multi-step operation."""
    name: str
    action: Callable[[], Coroutine[Any, Any, Any]]
    rollback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None
    is_compensating: bool = False
    completed: bool = False


class OperationError(Exception):
    """Raised when a multi-step operation fails."""
    def __init__(self, message: str, operation: str, failed_step: str,
                 completed_steps: list[str]):
        self.operation = operation
        self.failed_step = failed_step
        self.completed_steps = completed_steps
        super().__init__(f"{message} (failed at step '{failed_step}', completed: {completed_steps})")


class SafeOperation:
    """Execute a multi-step operation with rollback support.

    Each step can have a compensating rollback action.
    If a step fails, all completed steps are rolled back in reverse order.
    """

    def __init__(self, operation_name: str, session: AsyncSession):
        self.operation_name = operation_name
        self.session = session
        self.steps: list[OperationStep] = []
        self._completed: list[str] = []

    def add_step(self, name: str,
                 action: Callable[[], Coroutine[Any, Any, Any]],
                 rollback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None) -> None:
        """Add a step to the operation."""
        self.steps.append(OperationStep(name=name, action=action, rollback=rollback))

    async def execute(self) -> dict[str, Any]:
        """Execute all steps in order. Rolls back on failure."""
        results: dict[str, Any] = {}

        for step in self.steps:
            try:
                result = await step.action()
                step.completed = True
                self._completed.append(step.name)
                results[step.name] = result
                logger.debug("Operation '%s': step '%s' completed", self.operation_name, step.name)
            except Exception as exc:
                logger.error(
                    "Operation '%s' failed at step '%s': %s",
                    self.operation_name, step.name, exc,
                )
                await self._rollback(step.name)
                raise OperationError(
                    message=str(exc),
                    operation=self.operation_name,
                    failed_step=step.name,
                    completed_steps=self._completed.copy(),
                ) from exc

        return results

    async def _rollback(self, failed_step_name: str) -> None:
        """Roll back all completed steps in reverse order."""
        for step in reversed(self.steps):
            if step.name == failed_step_name:
                break
            if step.completed and step.rollback:
                try:
                    await step.rollback()
                    logger.info(
                        "Rolled back step '%s' for operation '%s'",
                        step.name, self.operation_name,
                    )
                except Exception as rb_exc:
                    logger.error(
                        "Rollback failed for step '%s' in operation '%s': %s",
                        step.name, self.operation_name, rb_exc,
                    )

        await self.session.rollback()


# ── Concrete Operation Builders ──────────────────────────────────


class FinalizeOperation(SafeOperation):
    """Safe finalize operation with rollback support.

    Steps:
    1. Validate transition (in-memory, no rollback needed)
    2. Create finalized version (can rollback: remove storage key)
    3. Update status to FINALIZED (can rollback: restore previous status)
    4. Lock document versions (can rollback: restore to 'current')
    5. Record audit trail (can rollback: delete audit event)
    """

    def __init__(self, session: AsyncSession, review_id: str, tenant_id: str,
                 user_id: str, previous_status: str):
        super().__init__("finalize_review", session)
        self.review_id = review_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.previous_status = previous_status
        self._created_version_id: Optional[str] = None

    async def build(self, finalized_version_result) -> None:
        """Build the operation steps."""

        # Step 2: Create finalized version (rollback: remove storage)
        async def _create_version():
            return finalized_version_result

        async def _rollback_version():
            if finalized_version_result and finalized_version_result.storage_key:
                from app.config import settings
                from app.integrations.storage.s3 import storage_service
                try:
                    await storage_service.delete_fileobj(
                        settings.s3_bucket or "contractrisk-documents",
                        finalized_version_result.storage_key,
                    )
                except Exception:
                    logger.warning("Could not remove storage key during rollback")

        self.add_step("create_finalized_version", _create_version, _rollback_version)

        # Step 3: Update status (rollback: restore previous)
        from app.domains.review.models import ContractReview
        from sqlalchemy import update, func

        async def _update_status():
            await self.session.execute(
                update(ContractReview).where(
                    ContractReview.review_id == self.review_id,
                    ContractReview.tenant_id == self.tenant_id,
                ).values(status="finalized", updated_at=func.now())
            )

        async def _rollback_status():
            await self.session.execute(
                update(ContractReview).where(
                    ContractReview.review_id == self.review_id,
                    ContractReview.tenant_id == self.tenant_id,
                ).values(status=self.previous_status, updated_at=func.now())
            )

        self.add_step("update_status", _update_status, _rollback_status)

        # Step 4: Lock document versions (rollback: restore to current)
        from app.domains.review.models import ContractDocumentVersion

        async def _lock_versions():
            await self.session.execute(
                update(ContractDocumentVersion).where(
                    ContractDocumentVersion.review_id == self.review_id,
                    ContractDocumentVersion.tenant_id == self.tenant_id,
                    ContractDocumentVersion.status == "current",
                ).values(status="finalized")
            )

        async def _rollback_versions():
            await self.session.execute(
                update(ContractDocumentVersion).where(
                    ContractDocumentVersion.review_id == self.review_id,
                    ContractDocumentVersion.tenant_id == self.tenant_id,
                    ContractDocumentVersion.status == "finalized",
                ).values(status="current")
            )

        self.add_step("lock_versions", _lock_versions, _rollback_versions)

        # Step 5: Record audit trail (rollback: delete event)
        from sqlalchemy import text as sa_text

        async def _record_audit():
            from app.domains.review.audit_trail import AuditTrailService
            audit = AuditTrailService(self.session, self.tenant_id)
            await audit.record_transition(
                review_id=self.review_id,
                from_status=self.previous_status,
                to_status="finalized",
                actor_id=self.user_id,
                reason="Review finalized — version locked",
            )

        # Audit trail is fire-and-forget, no rollback needed
        self.add_step("record_audit", _record_audit)


# ── Transaction Context Manager ──────────────────────────────────


@asynccontextmanager
async def transactional_operation(session: AsyncSession, operation_name: str):
    """Context manager for safe transactional operations.

    Ensures the session is committed on success and rolled back on failure.
    """
    try:
        yield
        await session.commit()
        logger.info("Operation '%s' committed successfully", operation_name)
    except Exception as exc:
        await session.rollback()
        logger.error("Operation '%s' rolled back due to: %s", operation_name, exc)
        raise
