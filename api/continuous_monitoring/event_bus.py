"""Obligation Event Bus — post-signature monitoring engine (V2-016).

Provides an event-driven architecture for tracking contract obligations,
deadlines, and milestones. Events flow through the bus and trigger
alerts, escalations, and downstream actions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of obligation events in the contract lifecycle."""

    RENEWAL_APPROACHING = "renewal_approaching"
    RENEWAL_OVERDUE = "renewal_overdue"
    SLA_DEADLINE_APPROACHING = "sla_deadline_approaching"
    SLA_BREACHED = "sla_breached"
    INSURANCE_EXPIRING = "insurance_expiring"
    INSURANCE_EXPIRED = "insurance_expired"
    COMPLIANCE_DRIFT_DETECTED = "compliance_drift_detected"
    REGULATORY_CHANGE = "regulatory_change"
    COUNTERPARTY_LITIGATION = "counterparty_litigation"
    PAYMENT_DEADLINE_APPROACHING = "payment_deadline_approaching"
    PAYMENT_OVERDUE = "payment_overdue"
    OBLIGATION_DUE = "obligation_due"
    OBLIGATION_OVERDUE = "obligation_overdue"
    CONTRACT_TERMINATION_APPROACHING = "contract_termination_approaching"
    FORCE_MAJEURE_TRIGGERED = "force_majeure_triggered"


class EventPriority(str, Enum):
    """Priority levels for obligation events."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ObligationEvent:
    """An event representing a contract obligation milestone or alert.

    Attributes:
        event_id: Unique event identifier.
        event_type: The type of obligation event.
        contract_id: The contract this event relates to.
        tenant_id: The tenant owning this event.
        priority: Event priority level.
        title: Human-readable event title.
        description: Detailed event description.
        due_date: The deadline date for this obligation (ISO format).
        days_until_due: Days until the deadline (negative if overdue).
        risk_score: Computed risk score for this event (0-10).
        metadata: Additional event-specific data.
        created_at: When the event was created.
        acknowledged: Whether the event has been acknowledged.
        acknowledged_by: Who acknowledged the event.
        acknowledged_at: When the event was acknowledged.
        resolved: Whether the event has been resolved.
        resolved_at: When the event was resolved.
    """

    event_id: str
    event_type: EventType
    contract_id: str
    tenant_id: str
    priority: EventPriority
    title: str
    description: str
    due_date: Optional[str] = None
    days_until_due: Optional[int] = None
    risk_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "contract_id": self.contract_id,
            "tenant_id": self.tenant_id,
            "priority": self.priority.value if isinstance(self.priority, EventPriority) else self.priority,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date,
            "days_until_due": self.days_until_due,
            "risk_score": round(self.risk_score, 2),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
        }


class ObligationEventBus:
    """Event bus for contract obligation monitoring.

    Manages event creation, subscription, dispatch, and persistence.
    Supports in-memory operation and database-backed persistence.

    Usage:
        bus = ObligationEventBus()
        bus.subscribe("renewal_approaching", my_handler)
        await bus.emit(ObligationEvent(...))
    """

    def __init__(self, db_pool: Optional[Any] = None) -> None:
        """Initialize the event bus.

        Args:
            db_pool: Optional database connection pool for persistence.
        """
        self._db_pool = db_pool
        self._subscribers: Dict[str, List[Callable]] = {}
        self._events: List[ObligationEvent] = []
        self._max_memory_events: int = 50_000

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[ObligationEvent], Any],
    ) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: The event type to subscribe to (EventType value).
            handler: Async callable that processes the event.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed handler to %s (total: %d)", event_type, len(self._subscribers[event_type]))

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove a handler subscription.

        Args:
            event_type: The event type to unsubscribe from.
            handler: The handler to remove.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h is not handler
            ]
            logger.debug("Unsubscribed handler from %s", event_type)

    async def emit(self, event: ObligationEvent) -> None:
        """Emit an event to all subscribers.

        Args:
            event: The event to emit.
        """
        # Store event
        self._events.append(event)
        if len(self._events) > self._max_memory_events:
            self._events = self._events[-self._max_memory_events:]

        # Persist to database if available
        if self._db_pool:
            try:
                await self._persist_event(event)
            except Exception as exc:
                logger.error("Failed to persist event %s: %s", event.event_id, exc)

        # Dispatch to subscribers
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        subscribers = self._subscribers.get(event_type, [])
        if not subscribers:
            # Also dispatch to wildcard subscribers
            subscribers = self._subscribers.get("*", [])

        for handler in subscribers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error("Handler failed for event %s: %s", event.event_id, exc)

        logger.info(
            "Emitted %s event for contract %s (priority=%s, risk=%.2f)",
            event_type,
            event.contract_id,
            event.priority.value if isinstance(event.priority, EventPriority) else event.priority,
            event.risk_score,
        )

    async def emit_many(self, events: List[ObligationEvent]) -> None:
        """Emit multiple events efficiently.

        Args:
            events: List of events to emit.
        """
        for event in events:
            await self.emit(event)

    async def get_events(
        self,
        contract_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        priority: Optional[str] = None,
        unresolved_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ObligationEvent]:
        """Query events with filters.

        Args:
            contract_id: Filter by contract.
            tenant_id: Filter by tenant.
            event_type: Filter by event type.
            priority: Filter by priority.
            unresolved_only: Only return unresolved events.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            Filtered list of events.
        """
        results = self._events

        if contract_id:
            results = [e for e in results if e.contract_id == contract_id]
        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]
        if event_type:
            results = [e for e in results if
                       (e.event_type.value if isinstance(e.event_type, EventType) else e.event_type) == event_type]
        if priority:
            results = [e for e in results if
                       (e.priority.value if isinstance(e.priority, EventPriority) else e.priority) == priority]
        if unresolved_only:
            results = [e for e in results if not e.resolved]

        # Sort by created_at descending
        results.sort(key=lambda e: e.created_at, reverse=True)

        return results[offset:offset + limit]

    async def acknowledge_event(
        self,
        event_id: str,
        user_id: str,
    ) -> Optional[ObligationEvent]:
        """Acknowledge an event.

        Args:
            event_id: The event to acknowledge.
            user_id: The user acknowledging.

        Returns:
            Updated event or None if not found.
        """
        for event in self._events:
            if event.event_id == event_id:
                event.acknowledged = True
                event.acknowledged_by = user_id
                event.acknowledged_at = datetime.utcnow().isoformat()
                return event
        return None

    async def resolve_event(
        self,
        event_id: str,
    ) -> Optional[ObligationEvent]:
        """Mark an event as resolved.

        Args:
            event_id: The event to resolve.

        Returns:
            Updated event or None if not found.
        """
        for event in self._events:
            if event.event_id == event_id:
                event.resolved = True
                event.resolved_at = datetime.utcnow().isoformat()
                return event
        return None

    async def get_event_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get aggregate event statistics.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            Dict with event statistics.
        """
        events = self._events
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]

        total = len(events)
        unresolved = sum(1 for e in events if not e.resolved)
        critical = sum(1 for e in events if
                       (e.priority.value if isinstance(e.priority, EventPriority) else e.priority) == "critical")
        high = sum(1 for e in events if
                   (e.priority.value if isinstance(e.priority, EventPriority) else e.priority) == "high")

        # Count by type
        by_type: Dict[str, int] = {}
        for e in events:
            et = e.event_type.value if isinstance(e.event_type, EventType) else e.event_type
            by_type[et] = by_type.get(et, 0) + 1

        return {
            "total_events": total,
            "unresolved_events": unresolved,
            "critical_events": critical,
            "high_priority_events": high,
            "events_by_type": by_type,
            "resolution_rate": round((total - unresolved) / total * 100, 1) if total > 0 else 0.0,
        }

    async def _persist_event(self, event: ObligationEvent) -> None:
        """Persist an event to the database.

        Args:
            event: The event to persist.
        """
        if not self._db_pool:
            return

        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO obligation_events
                       (event_id, event_type, contract_id, tenant_id, priority,
                        title, description, due_date, days_until_due, risk_score,
                        metadata, created_at, acknowledged, resolved)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                       ON CONFLICT (event_id) DO NOTHING""",
                    event.event_id,
                    event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
                    event.contract_id,
                    event.tenant_id,
                    event.priority.value if isinstance(event.priority, EventPriority) else event.priority,
                    event.title,
                    event.description,
                    event.due_date,
                    event.days_until_due,
                    event.risk_score,
                    json.dumps(event.metadata),
                    event.created_at,
                    event.acknowledged,
                    event.resolved,
                )
        except Exception as exc:
            logger.warning("Database persistence not available: %s", exc)

    @classmethod
    def create_event(
        cls,
        event_type: EventType,
        contract_id: str,
        tenant_id: str,
        title: str,
        description: str,
        priority: EventPriority = EventPriority.MEDIUM,
        due_date: Optional[str] = None,
        days_until_due: Optional[int] = None,
        risk_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ObligationEvent:
        """Factory method to create a new obligation event.

        Args:
            event_type: Type of event.
            contract_id: Related contract.
            tenant_id: Owning tenant.
            title: Event title.
            description: Event description.
            priority: Event priority.
            due_date: ISO format deadline.
            days_until_due: Days until deadline.
            risk_score: Risk score (0-10).
            metadata: Additional data.

        Returns:
            New ObligationEvent instance.
        """
        return ObligationEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            contract_id=contract_id,
            tenant_id=tenant_id,
            priority=priority,
            title=title,
            description=description,
            due_date=due_date,
            days_until_due=days_until_due,
            risk_score=risk_score,
            metadata=metadata or {},
        )
