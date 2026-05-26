"""Idempotency Protection — prevents duplicate operations and race conditions.

Provides:
- Idempotency keys for critical operations (approve, finalize, escalate)
- Operation locking to prevent concurrent duplicate actions
- Duplicate detection for audit events
- Safe retry support for multi-step operations
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── Idempotency Key Management ───────────────────────────────────


@dataclass
class IdempotencyRecord:
    """Record of an already-processed idempotent operation."""
    idempotency_key: str
    operation_type: str  # 'approve', 'finalize', 'escalate', 'bulk_action'
    entity_id: str
    result: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))


class IdempotencyService:
    """Prevents duplicate operations via idempotency keys.

    Uses the governance_audit_events table as the source of truth for
    detecting already-completed operations, plus an in-memory cache
    for fast checking during a single request.
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self._memory_cache: dict[str, IdempotencyRecord] = {}

    def generate_key(self, operation_type: str, entity_id: str, actor_id: str) -> str:
        """Generate a deterministic idempotency key for an operation."""
        raw = f"{operation_type}:{entity_id}:{actor_id}:{self.tenant_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    async def is_duplicate(self, operation_type: str, entity_id: str, actor_id: str) -> bool:
        """Check if an operation has already been performed.

        Checks both the in-memory cache and the audit trail.
        """
        key = self.generate_key(operation_type, entity_id, actor_id)

        # Check memory cache first
        if key in self._memory_cache:
            return True

        # Check audit trail for existing event
        event_type = self._operation_to_event_type(operation_type)
        if event_type:
            try:
                tenant_uuid = uuid.UUID(str(self.tenant_id))
                entity_uuid = uuid.UUID(str(entity_id))
            except (ValueError, TypeError):
                return False

            result = await self.session.execute(
                sa_text("""
                    SELECT 1 FROM governance_audit_events
                    WHERE tenant_id = :tenant_id
                      AND event_type = :event_type
                      AND entity_id = :entity_id
                      AND actor_id = :actor_id
                    LIMIT 1
                """),
                {
                    "tenant_id": tenant_uuid,
                    "event_type": event_type,
                    "entity_id": entity_uuid,
                    "actor_id": actor_id,
                },
            )
            if result.fetchone():
                self._memory_cache[key] = IdempotencyRecord(
                    idempotency_key=key,
                    operation_type=operation_type,
                    entity_id=entity_id,
                )
                return True

        return False

    async def mark_completed(self, operation_type: str, entity_id: str,
                              actor_id: str, result: dict[str, Any]) -> None:
        """Mark an operation as completed in the memory cache."""
        key = self.generate_key(operation_type, entity_id, actor_id)
        self._memory_cache[key] = IdempotencyRecord(
            idempotency_key=key,
            operation_type=operation_type,
            entity_id=entity_id,
            result=result,
        )

    def _operation_to_event_type(self, operation_type: str) -> Optional[str]:
        mapping = {
            "approve": "review.approved",
            "reject": "review.rejected",
            "finalize": None,  # Uses review.status_transition
            "escalate": "review.escalated",
            "bulk_accept": "redline.bulk_accepted",
            "bulk_reject": "redline.bulk_rejected",
        }
        return mapping.get(operation_type)


# ── Operation Locking ────────────────────────────────────────────


class OperationLock:
    """Prevents concurrent execution of the same operation on the same entity.

    Uses a simple in-memory lock. For distributed environments, this should
    be backed by Redis or PostgreSQL advisory locks.
    """

    _locks: dict[str, datetime] = {}

    @classmethod
    def acquire(cls, lock_key: str, timeout_seconds: int = 30) -> bool:
        """Try to acquire a lock. Returns True if acquired."""
        now = datetime.utcnow()
        existing = cls._locks.get(lock_key)

        if existing and (now - existing).total_seconds() < timeout_seconds:
            return False  # Lock is still held

        cls._locks[lock_key] = now
        return True

    @classmethod
    def release(cls, lock_key: str) -> None:
        """Release a lock."""
        cls._locks.pop(lock_key, None)


# ── Duplicate Audit Event Prevention ─────────────────────────────


class DeduplicatedAuditTrail:
    """Audit trail wrapper that prevents duplicate events.

    Wraps AuditTrailService to check for existing events before writing.
    """

    def __init__(self, audit_trail, idempotency: IdempotencyService):
        self._audit_trail = audit_trail
        self._idempotency = idempotency

    async def record_once(self, operation_type: str, entity_id: str,
                           actor_id: str, record_func, **kwargs) -> bool:
        """Record an audit event only if it hasn't been recorded before.

        Args:
            operation_type: Type of operation (e.g., 'approve', 'finalize')
            entity_id: The entity being operated on
            actor_id: Who performed the operation
            record_func: Async callable that takes **kwargs and records the event
            **kwargs: Passed to record_func

        Returns:
            True if the event was recorded, False if it was a duplicate
        """
        if await self._idempotency.is_duplicate(operation_type, entity_id, actor_id):
            logger.info(
                "Skipping duplicate audit event: %s/%s by %s",
                operation_type, entity_id, actor_id,
            )
            return False

        await record_func(**kwargs)
        await self._idempotency.mark_completed(operation_type, entity_id, actor_id, {})
        return True


# ── Safe Retry Context Manager ───────────────────────────────────


class SafeRetry:
    """Context manager for safe retry of multi-step operations.

    Tracks which steps have been completed so partial failures can be
    safely retried without repeating completed steps.
    """

    def __init__(self, operation_id: str):
        self.operation_id = operation_id
        self.completed_steps: list[str] = []
        self.failed_step: Optional[str] = None

    def mark_step(self, step_name: str) -> None:
        """Mark a step as completed."""
        self.completed_steps.append(step_name)

    def is_step_completed(self, step_name: str) -> bool:
        """Check if a step was already completed (for retry safety)."""
        return step_name in self.completed_steps

    @property
    def can_retry(self) -> bool:
        """Check if the operation can be retried (no unrecoverable failure)."""
        return self.failed_step is None

    def get_summary(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "completed_steps": self.completed_steps,
            "failed_step": self.failed_step,
            "can_retry": self.can_retry,
        }
