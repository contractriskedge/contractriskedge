"""Event outbox — persistent event store with delivery tracking and replay capability.

Provides a reliable event persistence layer on top of the in-memory EventBus.
Events are persisted before delivery, enabling:
- At-least-once delivery semantics
- Delivery acknowledgement and retry
- Dead-letter queue for failed events
- Replay capability for missed events
- Sequence ordering for consistency
- Event idempotency (deduplication by event_id)

Observability:
    All outbox operations are recorded via Prometheus metrics:
    - Event creation counter per tenant and event type
    - Dead-letter counter per tenant
    - Replay counter per tenant
    - Pending queue depth gauge per tenant
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, Boolean, func, select, and_
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.database.base import Base
from app.kernel.telemetry.metrics import metrics

logger = logging.getLogger(__name__)


# ── Delivery States ───────────────────────────────────────────────

class DeliveryState:
    """Lifecycle states for outbox event delivery."""
    PENDING = "pending"           # Created, not yet delivered
    DELIVERED = "delivered"       # Successfully delivered to at least one client
    ACKNOWLEDGED = "acknowledged" # Client sent ack
    FAILED = "failed"             # All delivery attempts failed
    DEAD_LETTER = "dead_letter"   # Moved to dead-letter queue after max retries
    EXPIRED = "expired"           # TTL exceeded, no longer relevant


# ── ORM Model ─────────────────────────────────────────────────────

class OutboxEvent(Base):
    """Persistent event record for reliable at-least-once delivery.

    Each event is written to the outbox before being delivered to
    WebSocket clients. Delivery state is tracked for observability
    and replay capability.

    Dead-letter events (max retries exceeded) are preserved for
    operational analysis and manual replay.

    Event versioning:
    - ``event_version`` tracks the schema version of the payload
    - Clients should check ``event_version`` before processing
    - Backward-compatible changes increment the minor version
    - Breaking changes increment the major version
    - Current version: 1.0
    """
    __tablename__ = "event_outbox"

    event_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    # Event metadata
    event_type = Column(Text, nullable=False, index=True)
    event_version = Column(Text, nullable=False, default="1.0")  # Schema version for backward compat
    correlation_id = Column(Text, nullable=True, index=True)
    actor_id = Column(Text, nullable=True)

    # Payload (JSON-serialized event data)
    payload = Column(JSONB, nullable=False)

    # Delivery tracking
    delivery_state = Column(Text, nullable=False, default=DeliveryState.PENDING, index=True)
    delivery_attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Dead-letter metadata
    dead_letter_reason = Column(Text, nullable=True)
    dead_letter_at = Column(DateTime(timezone=True), nullable=True)

    # Sequence ordering
    sequence_id = Column(Integer, nullable=False, autoincrement=True)

    # Immutable audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    ttl_expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-cleanup after TTL

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "tenant_id": str(self.tenant_id),
            "event_type": self.event_type,
            "event_version": self.event_version,
            "correlation_id": self.correlation_id,
            "actor_id": self.actor_id,
            "payload": self.payload,
            "delivery_state": self.delivery_state,
            "delivery_attempts": self.delivery_attempts,
            "last_error": self.last_error,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "sequence_id": self.sequence_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── Outbox Repository ─────────────────────────────────────────────

class OutboxRepository:
    """Persistent event outbox with delivery tracking and replay.

    Usage:
        repo = OutboxRepository(db_session)
        event = await repo.create(tenant_id, event_type, payload)
        await repo.mark_delivered(event.event_id)
        pending = await repo.get_pending(limit=50)
        dead = await repo.get_dead_letters()
    """

    MAX_DELIVERY_ATTEMPTS = 5
    DEFAULT_TTL_HOURS = 168  # 7 days

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        tenant_id: str,
        event_type: str,
        payload: dict,
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        event_version: str = "1.0",
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> OutboxEvent:
        """Persist an event to the outbox for reliable delivery.

        Args:
            tenant_id: Tenant UUID string
            event_type: Dot-notation event type (e.g. "review.status_changed")
            payload: JSON-serializable event data
            correlation_id: Optional workflow correlation ID for tracing
            actor_id: Optional user/system that triggered the event
            event_version: Schema version string (e.g. "1.0"). Increment
                on breaking payload changes to maintain replay compatibility.
            ttl_hours: Hours until auto-cleanup (default 168 = 7 days)
        """
        now = datetime.now(timezone.utc)
        event = OutboxEvent(
            event_id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            event_type=event_type,
            event_version=event_version,
            correlation_id=correlation_id,
            actor_id=actor_id,
            payload=payload,
            delivery_state=DeliveryState.PENDING,
            delivery_attempts=0,
            ttl_expires_at=now.replace(hour=0, minute=0, second=0, microsecond=0) + __import__('datetime').timedelta(hours=ttl_hours),
        )
        self._session.add(event)
        await self._session.flush()

        # Prometheus metrics
        tid_label = str(tenant_id)[:8] if isinstance(tenant_id, str) else str(tenant_id)[:8]
        metrics.outbox_events_created_total.labels(
            tenant_id=tid_label, event_type=event_type,
        ).inc()

        return event

    async def mark_delivered(self, event_id: uuid.UUID) -> bool:
        """Mark an event as successfully delivered."""
        result = await self._session.execute(
            select(OutboxEvent).where(OutboxEvent.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return False
        event.delivery_state = DeliveryState.DELIVERED
        event.delivered_at = datetime.now(timezone.utc)
        event.delivery_attempts += 1
        return True

    async def acknowledge(self, event_id: uuid.UUID) -> bool:
        """Record client acknowledgement of an event."""
        result = await self._session.execute(
            select(OutboxEvent).where(OutboxEvent.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return False
        event.delivery_state = DeliveryState.ACKNOWLEDGED
        event.acknowledged_at = datetime.now(timezone.utc)
        return True

    async def mark_failed(self, event_id: uuid.UUID, error: str) -> bool:
        """Mark an event as failed. Moves to dead-letter if max attempts exceeded."""
        result = await self._session.execute(
            select(OutboxEvent).where(OutboxEvent.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return False
        event.delivery_attempts += 1
        event.last_error = error

        if event.delivery_attempts >= self.MAX_DELIVERY_ATTEMPTS:
            event.delivery_state = DeliveryState.DEAD_LETTER
            event.dead_letter_reason = error
            event.dead_letter_at = datetime.now(timezone.utc)
            # Prometheus dead-letter counter
            tid_label = str(event.tenant_id)[:8]
            metrics.outbox_events_dead_letter_total.labels(
                tenant_id=tid_label,
            ).inc()
            logger.warning(
                "[Outbox] Event %s moved to dead-letter after %d failed attempts: %s",
                event_id, event.delivery_attempts, error,
            )
        else:
            event.delivery_state = DeliveryState.FAILED

        return True

    async def get_pending(self, limit: int = 100) -> list[OutboxEvent]:
        """Get all pending (undelivered) events, oldest first."""
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.delivery_state == DeliveryState.PENDING)
            .order_by(OutboxEvent.sequence_id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_failed(self, limit: int = 50) -> list[OutboxEvent]:
        """Get failed events eligible for retry."""
        result = await self._session.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.delivery_state == DeliveryState.FAILED,
                OutboxEvent.delivery_attempts < self.MAX_DELIVERY_ATTEMPTS,
            )
            .order_by(OutboxEvent.sequence_id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_dead_letters(self, limit: int = 50) -> list[OutboxEvent]:
        """Get dead-letter events for operational review."""
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.delivery_state == DeliveryState.DEAD_LETTER)
            .order_by(OutboxEvent.dead_letter_at.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def replay_dead_letter(self, event_id: uuid.UUID) -> Optional[OutboxEvent]:
        """Replay a dead-letter event by resetting its state to pending."""
        result = await self._session.execute(
            select(OutboxEvent).where(OutboxEvent.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event or event.delivery_state != DeliveryState.DEAD_LETTER:
            return None
        event.delivery_state = DeliveryState.PENDING
        event.delivery_attempts = 0
        event.last_error = None
        event.dead_letter_reason = None
        event.dead_letter_at = None
        # Prometheus replay counter
        tid_label = str(event.tenant_id)[:8]
        metrics.outbox_events_replayed_total.labels(tenant_id=tid_label).inc()
        return event

    async def get_by_correlation_id(self, correlation_id: str) -> list[OutboxEvent]:
        """Get all events for a correlation ID (workflow tracing)."""
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.correlation_id == correlation_id)
            .order_by(OutboxEvent.sequence_id.asc())
        )
        return list(result.scalars().all())

    async def get_by_tenant(
        self,
        tenant_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[OutboxEvent]:
        """Get events for a tenant, optionally filtered by type."""
        query = select(OutboxEvent).where(
            OutboxEvent.tenant_id == uuid.UUID(tenant_id)
        )
        if event_type:
            query = query.where(OutboxEvent.event_type == event_type)
        result = await self._session.execute(
            query.order_by(OutboxEvent.sequence_id.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_expired(self) -> int:
        """Delete expired events (TTL exceeded). Returns count deleted."""
        result = await self._session.execute(
            select(OutboxEvent).where(
                OutboxEvent.ttl_expires_at.isnot(None),
                OutboxEvent.ttl_expires_at < func.now(),
                OutboxEvent.delivery_state.in_([
                    DeliveryState.DELIVERED,
                    DeliveryState.ACKNOWLEDGED,
                    DeliveryState.EXPIRED,
                ])
            )
        )
        events = list(result.scalars().all())
        count = len(events)
        for event in events:
            await self._session.delete(event)
        if count:
            logger.info("[Outbox] Cleaned up %d expired events", count)
        return count

    async def count_pending(self, tenant_id: Optional[str] = None) -> int:
        """Count pending events, optionally for a specific tenant.

        Updates the outbox_queue_depth Prometheus gauge for the tenant.
        """
        query = select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.delivery_state == DeliveryState.PENDING
        )
        if tenant_id:
            query = query.where(OutboxEvent.tenant_id == uuid.UUID(tenant_id))
        result = await self._session.execute(query)
        count = result.scalar() or 0
        # Update Prometheus gauge
        tid_label = tenant_id[:8] if tenant_id else "all"
        metrics.outbox_queue_depth.labels(tenant_id=tid_label).set(count)
        return count

