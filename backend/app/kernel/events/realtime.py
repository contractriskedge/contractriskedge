"""Real-time event manager — WebSocket-based push for live operational updates.

Architecture:
- Single EventManager singleton manages all WebSocket connections
- Each connection is tagged with tenant_id for isolation
- Events are broadcast to all connections for a tenant
- Supports: notifications, job updates, review changes, upload progress

Usage (backend):
    from app.kernel.events.realtime import event_manager
    await event_manager.broadcast(tenant_id, {
        "type": "notification.created",
        "data": { "notification_id": "...", "title": "..." }
    })

Usage (frontend):
    const ws = new WebSocket(`/api/v1/ws/events?token=...`);
    ws.onmessage = (event) => {
        const { type, data } = JSON.parse(event.data);
    };
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by tenant_id.

    Thread-safe: uses asyncio.Lock for connection list mutations.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
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
        async with self._lock:
            if tenant_id not in self._connections:
                self._connections[tenant_id] = set()
            self._connections[tenant_id].add(websocket)
            self._stats["total_connections"] += 1
            self._stats["active_connections"] = sum(len(v) for v in self._connections.values())
        logger.debug("WebSocket connected: tenant=%s, total_active=%d", tenant_id[:8], self._stats["active_connections"])

    async def disconnect(self, websocket: WebSocket, tenant_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if tenant_id in self._connections:
                self._connections[tenant_id].discard(websocket)
                if not self._connections[tenant_id]:
                    del self._connections[tenant_id]
            self._stats["active_connections"] = sum(len(v) for v in self._connections.values())
        logger.debug("WebSocket disconnected: tenant=%s, total_active=%d", tenant_id[:8], self._stats["active_connections"])

    async def broadcast(self, tenant_id: str, event: dict[str, Any]) -> int:
        """Broadcast an event to all connections for a tenant.

        Returns the number of recipients.
        Silently removes stale connections.
        """
        payload = json.dumps(event, default=str)
        sent = 0
        stale: set[WebSocket] = set()

        async with self._lock:
            connections = self._connections.get(tenant_id, set()).copy()

        for ws in connections:
            try:
                await ws.send_text(payload)
                sent += 1
                self._stats["messages_sent"] += 1
            except Exception:
                stale.add(ws)

        # Clean up stale connections outside the broadcast loop
        if stale:
            async with self._lock:
                for ws in stale:
                    self._connections.get(tenant_id, set()).discard(ws)
                self._stats["active_connections"] = sum(len(v) for v in self._connections.values())

        return sent

    async def broadcast_all(self, event: dict[str, Any]) -> int:
        """Broadcast an event to ALL tenants (admin use only)."""
        total = 0
        async with self._lock:
            tenants = list(self._connections.keys())
        for tid in tenants:
            total += await self.broadcast(tid, event)
        return total

    def get_stats(self) -> dict:
        """Get connection statistics."""
        stats = dict(self._stats)
        stats["active_connections"] = sum(len(v) for v in self._connections.values())
        stats["tenant_count"] = len(self._connections)
        return stats

    async def health_check(self) -> dict:
        """Check if the event system is healthy."""
        return {
            "status": "healthy",
            "active_connections": sum(len(v) for v in self._connections.values()),
            "tenants": len(self._connections),
            "messages_sent": self._stats["messages_sent"],
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
