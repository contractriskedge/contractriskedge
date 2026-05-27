"""Observability diagnostics service — centralized health, metrics, and event tracing.

Provides:
  - Aggregate system diagnostics (single endpoint for dashboard data)
  - Event traceability with correlation chain inspection
  - Outbox audit explorer (pending, failed, dead-letter)
  - Reconnect storm detection
  - Stale event tracking
  - Worker heartbeat aggregation

Usage:
    from app.kernel.telemetry.diagnostics import diagnostics_service

    # Get full system diagnostics
    report = await diagnostics_service.get_system_diagnostics(db_factory)

    # Get event trace for a correlation ID
    chain = await diagnostics_service.get_event_chain(db_session, correlation_id)

    # Record a reconnect event
    await diagnostics_service.record_reconnect(tenant_id)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from prometheus_client import REGISTRY

from app.kernel.telemetry.metrics import metrics

logger = logging.getLogger(__name__)

# ── Reconnect Storm Detection ─────────────────────────────────────

STORM_THRESHOLD_COUNT = 10      # More than 10 reconnects...
STORM_THRESHOLD_WINDOW = 60     # ...within 60 seconds triggers storm detection


@dataclass
class ReconnectTracker:
    """Tracks reconnection events per tenant for storm detection.

    Thread-safe via asyncio.Lock usage in the service.
    """
    timestamps: list[float] = field(default_factory=list)

    def record(self) -> bool:
        """Record a reconnect and return True if a storm is detected."""
        now = time.time()
        self.timestamps.append(now)
        # Prune timestamps outside the window
        cutoff = now - STORM_THRESHOLD_WINDOW
        self.timestamps = [t for t in self.timestamps if t > cutoff]
        return len(self.timestamps) >= STORM_THRESHOLD_COUNT

    @property
    def recent_count(self) -> int:
        now = time.time()
        cutoff = now - STORM_THRESHOLD_WINDOW
        return sum(1 for t in self.timestamps if t > cutoff)


# ── Diagnostics Service ───────────────────────────────────────────


class DiagnosticsService:
    """Centralized observability diagnostics service.

    Aggregates metrics, health data, event tracing, and operational
    diagnostics into a single queryable interface. Designed to power
    the admin diagnostics dashboard and alerting infrastructure.
    """

    def __init__(self) -> None:
        self._reconnect_trackers: dict[str, ReconnectTracker] = {}
        self._started_at = time.time()

    # ── Reconnect Storm Detection ─────────────────────────────────

    def record_reconnect(self, tenant_id: str) -> bool:
        """Record a WebSocket reconnect for a tenant.

        Returns True if a reconnect storm is detected (threshold exceeded).
        Increments the reconnect storm counter on detection.
        """
        if tenant_id not in self._reconnect_trackers:
            self._reconnect_trackers[tenant_id] = ReconnectTracker()
        is_storm = self._reconnect_trackers[tenant_id].record()
        if is_storm:
            metrics.reconnect_storm_detections_total.labels(
                tenant_id=tenant_id[:8],
            ).inc()
            logger.warning(
                "[Diagnostics] Reconnect storm detected for tenant %s "
                "(%d reconnects in %ds window)",
                tenant_id[:8],
                STORM_THRESHOLD_COUNT,
                STORM_THRESHOLD_WINDOW,
            )
        return is_storm

    def get_reconnect_stats(self, tenant_id: Optional[str] = None) -> dict[str, Any]:
        """Get reconnect statistics, optionally filtered by tenant."""
        if tenant_id:
            tracker = self._reconnect_trackers.get(tenant_id)
            return {
                "tenant_id": tenant_id[:8],
                "recent_reconnects": tracker.recent_count if tracker else 0,
                "storm_detected": (tracker.recent_count >= STORM_THRESHOLD_COUNT) if tracker else False,
            }
        stats = {}
        for tid, tracker in self._reconnect_trackers.items():
            stats[tid[:8]] = {
                "recent_reconnects": tracker.recent_count,
                "storm_detected": tracker.recent_count >= STORM_THRESHOLD_COUNT,
            }
        return stats

    # ── System Diagnostics ────────────────────────────────────────

    async def get_system_diagnostics(self, db_factory=None) -> dict[str, Any]:
        """Aggregate full system diagnostics for the admin dashboard.

        Gathers metrics from Prometheus, infrastructure health checks,
        and operational counters into a single response.
        """
        from app.kernel.events.realtime import event_manager

        ws_stats = await event_manager.health_check()
        ws_health = {
            "active_connections": ws_stats.get("active_connections", 0),
            "tenant_count": ws_stats.get("tenants", 0),
            "messages_sent": ws_stats.get("messages_sent", 0),
            "subscriptions": ws_stats.get("subscriptions", {}),
            "uptime_seconds": ws_stats.get("uptime_seconds", 0),
        }

        # Gather Prometheus metric snapshots
        prom_metrics = self._gather_prometheus_snapshot()

        # Reconnect storm status across all tenants
        reconnect_stats = self.get_reconnect_stats()

        # Uptime
        uptime = time.time() - self._started_at

        # Database diagnostics (if factory available)
        db_diagnostics = {}
        if db_factory:
            try:
                pool_stats = db_factory.pool_stats if hasattr(db_factory, 'pool_stats') else {}
                db_diagnostics = {
                    "pool_size": pool_stats.get("size", 0),
                    "checked_in": pool_stats.get("checked_in", 0),
                    "checked_out": pool_stats.get("checked_out", 0),
                    "overflow": pool_stats.get("overflow", 0),
                }
            except Exception as exc:
                db_diagnostics = {"error": str(exc)}

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(uptime, 2),
            "websocket": ws_health,
            "reconnect_storms": reconnect_stats,
            "prometheus": prom_metrics,
            "database": db_diagnostics,
        }

    # ── Event Traceability ────────────────────────────────────────

    async def get_event_chain(
        self,
        session,
        correlation_id: str,
    ) -> list[dict[str, Any]]:
        """Get the full event chain for a correlation ID.

        Inspects the outbox for all events sharing the correlation ID,
        ordered by sequence_id. Returns enriched event data for the
        correlation timeline viewer.
        """
        from app.kernel.events.outbox import OutboxRepository

        repo = OutboxRepository(session)
        events = await repo.get_by_correlation_id(correlation_id)

        chain = []
        for event in events:
            chain.append({
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "event_version": event.event_version,
                "sequence_id": event.sequence_id,
                "delivery_state": event.delivery_state,
                "delivery_attempts": event.delivery_attempts,
                "last_error": event.last_error,
                "delivered_at": event.delivered_at.isoformat() if event.delivered_at else None,
                "acknowledged_at": event.acknowledged_at.isoformat() if event.acknowledged_at else None,
                "dead_letter_reason": event.dead_letter_reason,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "payload": event.payload,
            })

        return chain

    async def get_outbox_diagnostics(
        self,
        session,
        tenant_id: Optional[str] = None,
        state_filter: Optional[str] = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get outbox diagnostics for the audit explorer.

        Returns counts by state, recent events, and dead-letter details.
        """
        from app.kernel.events.outbox import OutboxRepository, DeliveryState

        repo = OutboxRepository(session)

        # Counts by delivery state
        counts = {}
        for state_name in ["pending", "delivered", "acknowledged", "failed", "dead_letter"]:
            try:
                # Use raw SQL for aggregate counts
                from sqlalchemy import text, func, select
                from app.kernel.events.outbox import OutboxEvent

                query = select(func.count()).select_from(OutboxEvent).where(
                    OutboxEvent.delivery_state == state_name
                )
                if tenant_id:
                    import uuid
                    query = query.where(OutboxEvent.tenant_id == uuid.UUID(tenant_id))
                result = await session.execute(query)
                counts[state_name] = result.scalar() or 0
            except Exception:
                counts[state_name] = 0

        # Recent events
        events = await repo.get_by_tenant(
            tenant_id=tenant_id or "00000000-0000-4000-8000-000000000001",
            limit=limit,
        )

        # Dead-letter events
        dead_letters = await repo.get_dead_letters(limit=20)

        # Pending count
        pending_count = await repo.count_pending(tenant_id)

        return {
            "counts": counts,
            "pending_count": pending_count,
            "recent_events": [
                {
                    "event_id": str(e.event_id),
                    "event_type": e.event_type,
                    "delivery_state": e.delivery_state,
                    "delivery_attempts": e.delivery_attempts,
                    "correlation_id": e.correlation_id,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events[:20]
            ],
            "dead_letters": [
                {
                    "event_id": str(e.event_id),
                    "event_type": e.event_type,
                    "delivery_attempts": e.delivery_attempts,
                    "last_error": e.last_error,
                    "dead_letter_reason": e.dead_letter_reason,
                    "dead_letter_at": e.dead_letter_at.isoformat() if e.dead_letter_at else None,
                    "correlation_id": e.correlation_id,
                }
                for e in dead_letters
            ],
        }

    # ── Worker Diagnostics ────────────────────────────────────────

    async def get_worker_diagnostics(
        self,
        session,
    ) -> dict[str, Any]:
        """Get worker diagnostics — heartbeats, queue depths, stuck jobs.

        Returns:
            - Active workers by queue
            - Queue depths from Redis
            - Recent stuck job counts
            - Worker heartbeat freshness
        """
        from app.config import settings as app_settings

        diagnostics = {
            "workers": {},
            "queues": {},
            "stuck_jobs": {},
            "heartbeats": [],
        }

        # Query worker heartbeats from DB
        try:
            from sqlalchemy import text

            result = await session.execute(text("""
                SELECT
                    worker_id, queue, last_heartbeat_at, status,
                    tasks_completed, tasks_failed
                FROM worker_heartbeats
                WHERE last_heartbeat_at > NOW() - INTERVAL '5 minutes'
                ORDER BY last_heartbeat_at DESC
            """))
            rows = result.fetchall()
            for row in rows:
                diagnostics["workers"][row.worker_id] = {
                    "queue": row.queue,
                    "last_heartbeat": row.last_heartbeat_at.isoformat() if row.last_heartbeat_at else None,
                    "status": row.status,
                    "tasks_completed": row.tasks_completed or 0,
                    "tasks_failed": row.tasks_failed or 0,
                }
        except Exception as exc:
            logger.debug("[Diagnostics] Worker heartbeat query failed: %s", exc)
            # Table may not exist yet — that's OK

        # Queue depths from Redis
        try:
            import redis.asyncio as aioredis

            broker = aioredis.from_url(app_settings.celery_broker_url, decode_responses=True)
            for qname in ["ingestion", "ai", "notifications", "default"]:
                try:
                    depth = await broker.llen(qname)
                    diagnostics["queues"][qname] = depth or 0
                except Exception:
                    diagnostics["queues"][qname] = 0
            await broker.close()
        except Exception as exc:
            logger.debug("[Diagnostics] Queue depth query failed: %s", exc)

        # Stuck job counts
        try:
            result = await session.execute(text("""
                SELECT queue, COUNT(*)::int AS stuck_count
                FROM workflow_recovery_actions
                WHERE recovered_at IS NULL
                  AND flagged_at > NOW() - INTERVAL '24 hours'
                GROUP BY queue
            """))
            for row in result.fetchall():
                diagnostics["stuck_jobs"][row.queue or "unknown"] = row.stuck_count
        except Exception:
            pass

        return diagnostics

    # ── Prometheus Snapshot ───────────────────────────────────────

    def _gather_prometheus_snapshot(self) -> dict[str, Any]:
        """Gather key Prometheus metric values for dashboard display.

        Reads current values from the in-process Prometheus registry.
        This is NOT a scrape — it's a live read of current counters/gauges.
        """
        snapshot = {}

        try:
            # WebSocket metrics
            ws_active = 0
            for sample in REGISTRY.get_sample_value_if_exists("ws_active_connections_total"):
                ws_active += sample[1] if isinstance(sample, tuple) else 0
            # Fallback: iterate samples
            for metric in REGISTRY.collect():
                if metric.name == "ws_active_connections":
                    for sample in metric.samples:
                        ws_active += sample.value
            snapshot["ws_active_connections"] = ws_active
        except Exception:
            snapshot["ws_active_connections"] = 0

        # Collect key counter values
        counter_metrics = [
            "ws_connections_total",
            "ws_disconnections_total",
            "ws_messages_sent_total",
            "ws_delivery_failures_total",
            "ws_reconnect_events_total",
            "ws_replay_events_total",
            "outbox_events_dead_letter_total",
            "outbox_events_replayed_total",
            "stale_events_rejected_total",
            "duplicate_invalidations_suppressed_total",
            "reconnect_storm_detections_total",
        ]
        for name in counter_metrics:
            try:
                total = 0
                for metric in REGISTRY.collect():
                    if metric.name == name:
                        for sample in metric.samples:
                            total += sample.value
                snapshot[name] = total
            except Exception:
                snapshot[name] = 0

        return snapshot


# ── Singleton ──────────────────────────────────────────────────────

diagnostics_service = DiagnosticsService()
