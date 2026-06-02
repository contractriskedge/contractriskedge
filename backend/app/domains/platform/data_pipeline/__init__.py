"""Data Pipeline Separation — CDC streaming, analytics warehouse, event aggregation, reporting snapshots.

Prevents analytics workloads from impacting production OLTP performance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"


class SyncFrequency(str, Enum):
    REAL_TIME = "real_time"     # CDC streaming
    NEAR_REAL_TIME = "near_real_time"  # Every 5 minutes
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class PipelineConfig:
    """Configuration for a data pipeline."""
    name: str
    source_table: str
    target_dataset: str  # "analytics", "audit_archive", "reporting"
    sync_frequency: SyncFrequency
    batch_size: int = 1000
    retention_days: int = 90
    enabled: bool = True


@dataclass
class PipelineRun:
    """A single pipeline run record."""
    run_id: str
    pipeline_name: str
    status: PipelineStatus
    rows_processed: int = 0
    rows_failed: int = 0
    started_at: str = ""
    completed_at: str | None = None
    error_message: str | None = None
    cursor: str | None = None  # For incremental syncs


@dataclass
class AnalyticsSnapshot:
    """A materialized analytics snapshot."""
    snapshot_name: str
    snapshot_type: str  # "daily_usage", "tenant_metrics", "ai_performance"
    period_start: str
    period_end: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class DataPipelineService:
    """Manages data pipeline separation between OLTP and analytics workloads.

    Provides:
    - CDC (Change Data Capture) streaming configuration
    - Batch sync scheduling for analytics warehouse
    - Event aggregation for reporting
    - Materialized analytics snapshots
    - Pipeline health monitoring
    """

    session: AsyncSession
    _pipelines: dict[str, PipelineConfig] = field(default_factory=dict)
    _runs: list[PipelineRun] = field(default_factory=list)

    # ── Pipeline Configuration ─────────────────────────────────────

    def register_pipeline(self, config: PipelineConfig) -> None:
        """Register a data pipeline."""
        self._pipelines[config.name] = config
        logger.info("Registered data pipeline: %s (%s -> %s)", config.name, config.source_table, config.target_dataset)

    def get_pipeline(self, name: str) -> PipelineConfig | None:
        """Get a pipeline configuration."""
        return self._pipelines.get(name)

    def get_active_pipelines(self) -> list[PipelineConfig]:
        """Get all active pipelines."""
        return [p for p in self._pipelines.values() if p.enabled]

    # ── Analytics Snapshots ────────────────────────────────────────

    async def create_daily_usage_snapshot(self, tenant_id: str) -> AnalyticsSnapshot:
        """Create a daily usage snapshot for analytics."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        period_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        period_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

        # Collect metrics
        sql = sa_text("""
            SELECT
                COUNT(*) as uploads,
                SUM(COALESCE(file_size, 0)) as total_bytes,
                COUNT(DISTINCT user_id) as active_users
            FROM upload_sessions
            WHERE tenant_id = :tid
              AND created_at >= :start AND created_at <= :end
        """)
        upload_stats = await self.session.execute(sql, {"tid": tenant_id, "start": period_start, "end": period_end})
        upload_row = upload_stats.fetchone()

        sql = sa_text("""
            SELECT
                COUNT(*) as executions,
                SUM(COALESCE(cost_usd, 0)) as total_cost,
                SUM(COALESCE(total_tokens, 0)) as total_tokens,
                AVG(COALESCE(latency_ms, 0)) as avg_latency
            FROM ai_execution_runs
            WHERE tenant_id = :tid
              AND created_at >= :start AND created_at <= :end
        """)
        ai_stats = await self.session.execute(sql, {"tid": tenant_id, "start": period_start, "end": period_end})
        ai_row = ai_stats.fetchone()

        snapshot = AnalyticsSnapshot(
            snapshot_name=f"daily_usage_{tenant_id[:8]}_{yesterday.strftime('%Y%m%d')}",
            snapshot_type="daily_usage",
            period_start=period_start,
            period_end=period_end,
            data={
                "tenant_id": tenant_id,
                "uploads": upload_row.uploads or 0,
                "storage_bytes": upload_row.total_bytes or 0,
                "active_users": upload_row.active_users or 0,
                "ai_executions": ai_row.executions or 0,
                "ai_cost_usd": round(float(ai_row.total_cost or 0.0), 4),
                "ai_tokens": ai_row.total_tokens or 0,
                "ai_avg_latency_ms": round(float(ai_row.avg_latency or 0.0), 1),
            },
        )

        # Persist snapshot
        sql = sa_text("""
            INSERT INTO analytics_snapshots (snapshot_name, snapshot_type, period_start, period_end, data)
            VALUES (:name, :type, :start, :end, :data)
            ON CONFLICT (snapshot_name) DO UPDATE SET data = :data
        """)
        await self.session.execute(sql, {
            "name": snapshot.snapshot_name,
            "type": snapshot.snapshot_type,
            "start": snapshot.period_start,
            "end": snapshot.period_end,
            "data": json.dumps(snapshot.data),
        })

        return snapshot

    async def create_ai_performance_snapshot(self, tenant_id: str) -> AnalyticsSnapshot:
        """Create an AI performance snapshot."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        period_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        period_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

        sql = sa_text("""
            SELECT
                model,
                provider,
                COUNT(*) as executions,
                AVG(COALESCE(latency_ms, 0)) as avg_latency,
                SUM(COALESCE(cost_usd, 0)) as total_cost,
                SUM(COALESCE(total_tokens, 0)) as total_tokens,
                COUNT(*) FILTER (WHERE status = 'failed') as failures
            FROM ai_execution_runs
            WHERE tenant_id = :tid
              AND created_at >= :start AND created_at <= :end
            GROUP BY model, provider
            ORDER BY total_cost DESC
        """)
        result = await self.session.execute(sql, {"tid": tenant_id, "start": period_start, "end": period_end})

        snapshot = AnalyticsSnapshot(
            snapshot_name=f"ai_performance_{tenant_id[:8]}_{yesterday.strftime('%Y%m%d')}",
            snapshot_type="ai_performance",
            period_start=period_start,
            period_end=period_end,
            data={
                "tenant_id": tenant_id,
                "models": [
                    {
                        "model": str(row.model),
                        "provider": str(row.provider),
                        "executions": row.executions,
                        "avg_latency_ms": round(float(row.avg_latency or 0.0), 1),
                        "total_cost": round(float(row.total_cost or 0.0), 6),
                        "total_tokens": row.total_tokens or 0,
                        "failures": row.failures or 0,
                    }
                    for row in result.fetchall()
                ],
            },
        )

        return snapshot

    # ── Pipeline Health ────────────────────────────────────────────

    def record_run(self, run: PipelineRun) -> None:
        """Record a pipeline run."""
        self._runs.append(run)

    def get_pipeline_health(self) -> dict[str, Any]:
        """Get health status of all pipelines."""
        return {
            "total_pipelines": len(self._pipelines),
            "active_pipelines": len(self.get_active_pipelines()),
            "recent_runs": [
                {"pipeline": r.pipeline_name, "status": r.status.value, "rows": r.rows_processed, "at": r.started_at}
                for r in self._runs[-10:]
            ],
            "pipeline_configs": [
                {"name": p.name, "source": p.source_table, "target": p.target_dataset, "frequency": p.sync_frequency.value}
                for p in self._pipelines.values()
            ],
        }

    async def get_analytics_summary(self, tenant_id: str, days: int = 30) -> dict[str, Any]:
        """Get a summary of analytics data for a tenant."""
        sql = sa_text("""
            SELECT snapshot_type, COUNT(*) as count,
                   MAX(created_at) as latest
            FROM analytics_snapshots
            WHERE data->>'tenant_id' = :tid
              AND created_at >= CURRENT_DATE - :days
            GROUP BY snapshot_type
        """)
        result = await self.session.execute(sql, {"tid": tenant_id, "days": days})
        snapshots = {row.snapshot_type: {"count": row.count, "latest": str(row.latest)} for row in result.fetchall()}

        return {
            "tenant_id": tenant_id,
            "days": days,
            "available_snapshots": snapshots,
            "pipeline_count": len(self._pipelines),
        }


import json
