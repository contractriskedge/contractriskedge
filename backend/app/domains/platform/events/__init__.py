"""Unified Event Bus — event registry, schema versioning, replay, dead-letter streams, exactly-once processing.

Extends the existing kernel/events/ infrastructure with platform-level governance.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EventSchemaStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    MIGRATED = "migrated"


class DeliveryGuarantee(str, Enum):
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


@dataclass
class EventSchema:
    """A registered event schema with versioning."""
    event_type: str
    version: str
    schema_def: dict[str, Any]
    status: EventSchemaStatus
    description: str = ""
    migration_from: str | None = None
    migration_to: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class EventSubscription:
    """A registered subscription to an event type."""
    subscriber_id: str
    event_type: str
    handler_name: str
    delivery_guarantee: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE
    is_active: bool = True
    max_retries: int = 3
    dead_letter_queue: str = "dlq_default"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class DeadLetterEvent:
    """An event that failed delivery and was moved to DLQ."""
    event_id: str
    event_type: str
    payload: dict[str, Any]
    subscriber_id: str
    failure_reason: str
    retry_count: int
    failed_at: str
    requeued: bool = False


EventHandler = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass
class UnifiedEventBus:
    """Platform-wide event bus with governance and reliability.

    Extends the kernel EventBus with:
    - Event schema registry and versioning
    - Schema compatibility validation
    - Event replay from persistent store
    - Dead-letter stream management
    - Subscriber management with delivery guarantees
    - Exactly-once processing via idempotency
    """

    session: AsyncSession
    _schemas: dict[str, list[EventSchema]] = field(default_factory=dict)
    _subscriptions: dict[str, list[EventSubscription]] = field(default_factory=dict)
    _handlers: dict[str, EventHandler] = field(default_factory=dict)
    _dead_letter: list[DeadLetterEvent] = field(default_factory=list)
    _processed_ids: set[str] = field(default_factory=set)

    # ── Schema Registry ────────────────────────────────────────────

    def register_schema(self, schema: EventSchema) -> None:
        """Register an event schema."""
        if schema.event_type not in self._schemas:
            self._schemas[schema.event_type] = []
        self._schemas[schema.event_type].append(schema)
        self._schemas[schema.event_type].sort(key=lambda s: s.version, reverse=True)
        logger.info("Registered event schema: %s v%s", schema.event_type, schema.version)

    def get_schema(self, event_type: str, version: str | None = None) -> EventSchema | None:
        """Get an event schema."""
        versions = self._schemas.get(event_type, [])
        if not versions:
            return None
        if version:
            for s in versions:
                if s.version == version:
                    return s
            return None
        return versions[0]

    def validate_event(self, event_type: str, payload: dict[str, Any], version: str | None = None) -> list[str]:
        """Validate an event payload against its schema."""
        schema = self.get_schema(event_type, version)
        if not schema:
            return [f"No schema registered for event type '{event_type}'"]

        issues = []
        schema_props = schema.schema_def.get("properties", {})
        schema_required = schema.schema_def.get("required", [])

        for req in schema_required:
            if req not in payload:
                issues.append(f"Missing required field: {req}")

        for key, value in payload.items():
            prop_schema = schema_props.get(key)
            if prop_schema and "type" in prop_schema:
                expected_type = prop_schema["type"]
                if expected_type == "string" and not isinstance(value, str):
                    issues.append(f"Field '{key}' should be string, got {type(value).__name__}")
                elif expected_type == "integer" and not isinstance(value, int):
                    issues.append(f"Field '{key}' should be integer, got {type(value).__name__}")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    issues.append(f"Field '{key}' should be number, got {type(value).__name__}")
                elif expected_type == "array" and not isinstance(value, list):
                    issues.append(f"Field '{key}' should be array, got {type(value).__name__}")

        return issues

    # ── Event Publishing ───────────────────────────────────────────

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant_id: str = "",
        correlation_id: str = "",
        idempotency_key: str = "",
        version: str | None = None,
    ) -> str:
        """Publish an event to the bus.

        Args:
            event_type: The type of event.
            payload: The event payload.
            tenant_id: Tenant context.
            correlation_id: Correlation ID for tracing.
            idempotency_key: For exactly-once deduplication.
            version: Schema version to validate against.

        Returns:
            The event ID.
        """
        import uuid
        event_id = str(uuid.uuid4())

        # Idempotency check
        if idempotency_key and idempotency_key in self._processed_ids:
            logger.info("Duplicate event detected (key=%s), skipping", idempotency_key[:16])
            return event_id

        # Schema validation
        issues = self.validate_event(event_type, payload, version)
        if issues:
            logger.warning("Event %s schema validation issues: %s", event_type, issues)

        # Persist to outbox
        await self._persist_event(event_id, event_type, payload, tenant_id, correlation_id)

        # Mark as processed for idempotency
        if idempotency_key:
            self._processed_ids.add(idempotency_key)

        # Deliver to subscribers
        await self._deliver(event_id, event_type, payload)

        return event_id

    async def _persist_event(
        self, event_id: str, event_type: str, payload: dict[str, Any],
        tenant_id: str, correlation_id: str,
    ) -> None:
        """Persist event to the outbox table."""
        try:
            sql = sa_text("""
                INSERT INTO event_outbox (event_id, event_type, tenant_id, correlation_id, payload)
                VALUES (:eid, :etype, :tid, :corr, :payload)
                ON CONFLICT (event_id) DO NOTHING
            """)
            await self.session.execute(sql, {
                "eid": event_id,
                "etype": event_type,
                "tid": tenant_id,
                "corr": correlation_id,
                "payload": json.dumps(payload),
            })
        except Exception as e:
            logger.error("Failed to persist event %s: %s", event_id[:8], e)

    async def _deliver(self, event_id: str, event_type: str, payload: dict[str, Any]) -> None:
        """Deliver event to all subscribed handlers."""
        subscriptions = self._subscriptions.get(event_type, [])
        handler = self._handlers.get(event_type)

        if handler:
            try:
                await handler(payload)
            except Exception as e:
                logger.error("Handler failed for event %s: %s", event_id[:8], e)
                self._dead_letter.append(DeadLetterEvent(
                    event_id=event_id,
                    event_type=event_type,
                    payload=payload,
                    subscriber_id="default",
                    failure_reason=str(e),
                    retry_count=1,
                    failed_at=datetime.utcnow().isoformat(),
                ))

    # ── Subscriptions ──────────────────────────────────────────────

    def subscribe(self, event_type: str, handler: EventHandler, subscription: EventSubscription | None = None) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type] = handler
        if subscription:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            self._subscriptions[event_type].append(subscription)
        logger.info("Subscribed handler to event type: %s", event_type)

    def unsubscribe(self, event_type: str) -> None:
        """Unsubscribe from an event type."""
        self._handlers.pop(event_type, None)
        self._subscriptions.pop(event_type, None)

    # ── Event Replay ───────────────────────────────────────────────

    async def replay_events(
        self,
        event_type: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Replay events from the outbox."""
        conditions = []
        params: dict[str, Any] = {"limit": limit}

        if event_type:
            conditions.append("event_type = :etype")
            params["etype"] = event_type
        if from_time:
            conditions.append("created_at >= :from")
            params["from"] = from_time
        if to_time:
            conditions.append("created_at <= :to")
            params["to"] = to_time

        where = " AND ".join(conditions) if conditions else "TRUE"
        sql = sa_text(f"""
            SELECT event_id, event_type, tenant_id, correlation_id, payload, created_at
            FROM event_outbox
            WHERE {where}
            ORDER BY created_at ASC
            LIMIT :limit
        """)
        result = await self.session.execute(sql, params)
        return [
            {
                "event_id": str(row.event_id),
                "event_type": row.event_type,
                "tenant_id": str(row.tenant_id) if row.tenant_id else "",
                "correlation_id": str(row.correlation_id) if row.correlation_id else "",
                "payload": row.payload,
                "created_at": str(row.created_at),
            }
            for row in result.fetchall()
        ]

    # ── Dead-Letter Queue Management ───────────────────────────────

    def get_dead_letter_queue(self) -> list[DeadLetterEvent]:
        """Get all dead-letter events."""
        return list(self._dead_letter)

    async def requeue_dead_letter(self, event_id: str) -> bool:
        """Re-queue a dead-letter event for reprocessing."""
        for entry in self._dead_letter:
            if entry.event_id == event_id and not entry.requeued:
                entry.requeued = True
                await self.publish(entry.event_type, entry.payload)
                logger.info("Re-queued dead-letter event %s", event_id[:8])
                return True
        return False

    # ── Observability ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        return {
            "registered_schemas": sum(len(v) for v in self._schemas.values()),
            "event_types": list(self._schemas.keys()),
            "active_subscriptions": len(self._handlers),
            "dead_letter_count": len(self._dead_letter),
            "idempotency_cache_size": len(self._processed_ids),
        }
