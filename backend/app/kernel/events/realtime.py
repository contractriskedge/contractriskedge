"""Real-time event manager — WebSocket-based push for live operational updates.

Architecture:
- Single EventManager singleton manages all WebSocket connections
- Each connection is tagged with tenant_id for isolation
- Connections can subscribe to specific event topics (filters)
- Events are broadcast only to connections subscribed to matching topics
- Supports: notifications, job updates, review changes, upload progress

Subscription scoping:
    By default, connections receive ALL events for their tenant.
    Clients can send ``{ type: "subscribe", topics: [...] }`` to filter.
    Topics support wildcard patterns: "review.*", "recovery.*", "notification.*"

Observability:
    All WebSocket operations are recorded via Prometheus metrics:
    - Connection/disconnection counters per tenant
    - Active connection gauge per tenant
    - Messages sent/delivered counters per tenant and event type
    - Delivery failure counter per tenant and reason
    - Reconnect event counter per tenant
    - Replay event counter per tenant
    - Delivery latency histogram per tenant
    - Reconnect storm detection via DiagnosticsService

Usage (backend):
    from app.kernel.events.realtime import event_manager
    await event_manager.broadcast(tenant_id, {
        "type": "notification.created",
        "data": { "notification_id": "...", "title": "..." }
    })

Usage (frontend):
    const ws = new WebSocket(`/api/v1/ws/events?token=...`);

    // Subscribe to specific topics on connect
    ws.onopen = () => ws.send(JSON.stringify({
        type: "subscribe",
        topics: ["review.*", "notification.*"]
    }));

    ws.onmessage = (event) => {
        const { type, data } = JSON.parse(event.data);
    };
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import time
from typing import Any, Optional

from fastapi import WebSocket

from app.kernel.telemetry.metrics import metrics
from app.kernel.telemetry.diagnostics import diagnostics_service

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Manages topic subscriptions per WebSocket connection.

    Each connection can subscribe to specific event topics.
    Topic patterns support fnmatch-style wildcards:
    - ``review.*`` matches ``review.created``, ``review.updated``, etc.
    - ``recovery.*`` matches ``recovery.action_taken``, ``recovery.review_flagged``, etc.
    - ``*`` matches all events (default)
    """

    def __init__(self) -> None:
        self._subscriptions: dict[int, set[str]] = {}  # id(websocket) -> {topics}

    def set_subscriptions(self, websocket: WebSocket, topics: list[str]) -> None:
        """Set the subscription topics for a connection.

        If topics is empty, subscribes to all events (default behavior).
        """
        ws_id = id(websocket)
        if topics:
            # Normalize: strip whitespace, lowercase
            normalized = {t.strip().lower() for t in topics if t.strip()}
            self._subscriptions[ws_id] = normalized
        else:
            # Empty topics = subscribe to all
            self._subscriptions.pop(ws_id, None)

    def is_subscribed(self, websocket: WebSocket, event_type: str) -> bool:
        """Check if a connection is subscribed to an event type.

        A connection with no explicit subscriptions receives all events.
        Otherwise, the event type is matched against all subscribed patterns.
        """
        ws_id = id(websocket)
        topics = self._subscriptions.get(ws_id)
        if topics is None:
            return True  # No explicit subscriptions = receive all
        return any(fnmatch.fnmatch(event_type, pattern) for pattern in topics)

    def remove_connection(self, websocket: WebSocket) -> None:
        """Clean up subscriptions when a connection disconnects."""
        self._subscriptions.pop(id(websocket), None)

    def get_subscription_summary(self) -> dict[str, int]:
        """Get a summary of active subscriptions for observability."""
        counts: dict[str, int] = {}
        for topics in self._subscriptions.values():
            for topic in topics:
                counts[topic] = counts.get(topic, 0) + 1
        return counts


class ConnectionManager:
    """Manages WebSocket connections grouped by tenant_id with subscription scoping.

    Thread-safe: uses asyncio.Lock for connection list mutations.
    Each connection can subscribe to specific event topics to reduce noise.
    """

    def __init__(self) -> None:
        self._connections: dict[str, dict[int, WebSocket]] = {}  # tenant_id -> {id(ws): ws}
        self._subscriptions = SubscriptionManager()
        self._lock = asyncio.Lock()
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "started_at": time.time(),
        }

    async def connect(self, websocket: WebSocket, tenant_id: str) -> None:
        """Accept a WebSocket connection and register it for the tenant."""
        await websocket.accept()
        tid_label = tenant_id[:8]
        async with self._lock:
            if tenant_id not in self._connections:
                self._connections[tenant_id] = {}
            self._connections[tenant_id][id(websocket)] = websocket
            self._stats["total_connections"] += 1
            active = sum(len(v) for v in self._connections.values())
            self._stats["active_connections"] = active
            # Prometheus metrics
            metrics.ws_connections_total.labels(tenant_id=tid_label).inc()
            metrics.ws_active_connections.labels(tenant_id=tid_label).set(
                len(self._connections.get(tenant_id, {}))
            )
        logger.debug(
            "WebSocket connected: tenant=%s, total_active=%d",
            tid_label, self._stats["active_connections"],
        )

    async def disconnect(self, websocket: WebSocket, tenant_id: str) -> None:
        """Remove a WebSocket connection and its subscriptions."""
        tid_label = tenant_id[:8]
        self._subscriptions.remove_connection(websocket)
        async with self._lock:
            if tenant_id in self._connections:
                self._connections[tenant_id].pop(id(websocket), None)
                if not self._connections[tenant_id]:
                    del self._connections[tenant_id]
            active = sum(len(v) for v in self._connections.values())
            self._stats["active_connections"] = active
            # Prometheus metrics
            metrics.ws_disconnections_total.labels(tenant_id=tid_label).inc()
            metrics.ws_active_connections.labels(tenant_id=tid_label).set(
                len(self._connections.get(tenant_id, {}))
            )
        logger.debug(
            "WebSocket disconnected: tenant=%s, total_active=%d",
            tid_label, self._stats["active_connections"],
        )

    def set_subscriptions(self, websocket: WebSocket, topics: list[str]) -> None:
        """Set topic subscriptions for a connection.

        Call this when a client sends ``{ type: "subscribe", topics: [...] }``.
        """
        self._subscriptions.set_subscriptions(websocket, topics)
        logger.debug(
            "Subscriptions updated for connection %d: %s",
            id(websocket), topics or ["* (all)"],
        )

    async def broadcast(self, tenant_id: str, event: dict[str, Any]) -> int:
        """Broadcast an event to subscribed connections for a tenant.

        Only connections subscribed to the event's type will receive it.
        Returns the number of recipients.
        Silently removes stale connections.
        Records delivery metrics to Prometheus.
        """
        event_type = event.get("type", "")
        payload = json.dumps(event, default=str)
        sent = 0
        stale: set[int] = set()
        tid_label = tenant_id[:8]

        async with self._lock:
            connections = dict(self._connections.get(tenant_id, {}))

        for ws_id, ws in connections.items():
            if not self._subscriptions.is_subscribed(ws, event_type):
                continue  # Skip connections not subscribed to this event type
            try:
                await ws.send_text(payload)
                sent += 1
                self._stats["messages_sent"] += 1
            except Exception:
                stale.add(ws_id)

        # Prometheus metrics
        if sent > 0:
            metrics.ws_messages_sent_total.labels(
                tenant_id=tid_label, event_type=event_type,
            ).inc(sent)
        if stale:
            metrics.ws_delivery_failures_total.labels(
                tenant_id=tid_label, reason="stale_connection",
            ).inc(len(stale))

        # Clean up stale connections outside the broadcast loop
        if stale:
            async with self._lock:
                for ws_id in stale:
                    ws = self._connections.get(tenant_id, {}).pop(ws_id, None)
                    if ws:
                        self._subscriptions.remove_connection(ws)
                active = sum(len(v) for v in self._connections.values())
                self._stats["active_connections"] = active
                metrics.ws_active_connections.labels(tenant_id=tid_label).set(
                    len(self._connections.get(tenant_id, {}))
                )

        return sent

    async def broadcast_to_topic(self, tenant_id: str, event_type: str, data: dict[str, Any]) -> int:
        """Broadcast an event to connections subscribed to a specific topic.

        Convenience wrapper around broadcast that structures the event payload.
        """
        return await self.broadcast(tenant_id, {
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        })

    async def broadcast_all(self, event: dict[str, Any]) -> int:
        """Broadcast an event to ALL tenants (admin use only)."""
        total = 0
        async with self._lock:
            tenants = list(self._connections.keys())
        for tid in tenants:
            total += await self.broadcast(tid, event)
        return total

    def record_reconnect(self, tenant_id: str) -> None:
        """Record a WebSocket reconnection event for a tenant.

        Increments reconnect counter and checks for reconnect storms.
        """
        tid_label = tenant_id[:8]
        metrics.ws_reconnect_events_total.labels(tenant_id=tid_label).inc()
        is_storm = diagnostics_service.record_reconnect(tenant_id)
        if is_storm:
            logger.warning(
                "[Realtime] Reconnect storm detected for tenant %s",
                tid_label,
            )

    def record_replay(self, tenant_id: str, event_count: int = 1) -> None:
        """Record that replay events were sent to a tenant.

        Args:
            tenant_id: The tenant that received replay events.
            event_count: Number of events replayed.
        """
        tid_label = tenant_id[:8]
        metrics.ws_replay_events_total.labels(tenant_id=tid_label).inc(event_count)

    def record_delivery_latency(self, tenant_id: str, latency_seconds: float) -> None:
        """Record WebSocket event delivery latency.

        Args:
            tenant_id: The target tenant.
            latency_seconds: Time from event creation to client receipt.
        """
        tid_label = tenant_id[:8]
        metrics.ws_delivery_latency_seconds.labels(
            tenant_id=tid_label,
        ).observe(latency_seconds)

    def get_stats(self) -> dict:
        """Get connection statistics including subscription summary."""
        stats = dict(self._stats)
        stats["active_connections"] = sum(len(v) for v in self._connections.values())
        stats["tenant_count"] = len(self._connections)
        stats["subscriptions"] = self._subscriptions.get_subscription_summary()
        return stats

    async def health_check(self) -> dict:
        """Check if the event system is healthy."""
        return {
            "status": "healthy",
            "active_connections": sum(len(v) for v in self._connections.values()),
            "tenants": len(self._connections),
            "messages_sent": self._stats["messages_sent"],
            "subscriptions": self._subscriptions.get_subscription_summary(),
            "uptime_seconds": int(time.time() - self._stats["started_at"]),
        }


# ── Singleton ────────────────────────────────────────────────────

event_manager = ConnectionManager()


# ── Event Type Constants ─────────────────────────────────────────

class EventTypes:
    """Standardized event type constants for the real-time system."""
    NOTIFICATION_CREATED = "notification.created"
    NOTIFICATION_READ = "notification.read"
    JOB_CREATED = "job.created"
    JOB_UPDATED = "job.updated"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    REVIEW_CREATED = "review.created"
    REVIEW_UPDATED = "review.updated"
    REVIEW_STATUS_CHANGED = "review.status_changed"
    UPLOAD_COMPLETED = "upload.completed"
    UPLOAD_FAILED = "upload.failed"
    AI_COMPLETED = "ai.completed"
    AI_FAILED = "ai.failed"
    RECOMMENDATION_CREATED = "recommendation.created"
    RECOMMENDATION_ACTIONED = "recommendation.actioned"
    FINDING_RESOLVED = "finding.resolved"
    EXPORT_COMPLETED = "export.completed"
    DASHBOARD_CHANGED = "dashboard.changed"

    # ── Recovery Events ──────────────────────────────────────────
    RECOVERY_ACTION_TAKEN = "recovery.action_taken"
    RECOVERY_REVIEW_FLAGGED = "recovery.review_flagged"
    RECOVERY_REVIEW_ASSIGNED = "recovery.review_assigned"
    RECOVERY_MAX_ESCALATION = "recovery.max_escalation_reached"
    RECOVERY_COOLDOWN_ACTIVE = "recovery.cooldown_active"


# ── Helper Function ──────────────────────────────────────────────

async def emit_event(tenant_id: str, event_type: str, data: dict[str, Any]) -> int:
    """Convenience function to emit a real-time event.

    Args:
        tenant_id: The tenant to broadcast to.
        event_type: One of EventTypes constants.
        data: The event payload.

    Returns:
        Number of recipients that received the event.
    """
    return await event_manager.broadcast(tenant_id, {
        "type": event_type,
        "data": data,
        "timestamp": time.time(),
    })
