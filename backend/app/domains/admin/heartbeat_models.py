"""Worker heartbeat ORM model for worker observability.

Tracks:
  - Worker identity and queue assignment
  - Last heartbeat timestamp for liveness detection
  - Task throughput (completed/failed counts)
  - Worker status (active, idle, draining, stopped)

Usage:
    from app.domains.admin.heartbeat_models import WorkerHeartbeat

    # Record a heartbeat
    heartbeat = WorkerHeartbeat(
        worker_id="worker-1",
        queue="ingestion",
        status="active",
        tasks_completed=42,
        tasks_failed=1,
    )
    session.add(heartbeat)
    await session.flush()

Querying:
    # Get all active workers (heartbeat within last 5 minutes)
    active = await session.execute(
        select(WorkerHeartbeat)
        .where(WorkerHeartbeat.last_heartbeat_at > func.now() - text("INTERVAL '5 minutes'"))
        .order_by(WorkerHeartbeat.last_heartbeat_at.desc())
    )
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.kernel.database.base import Base


class WorkerHeartbeat(Base):
    """Tracks worker process heartbeats for liveness monitoring.

    One row per worker process. Updated periodically (every 30s) by
    the worker itself. The diagnostics service queries this table to
    determine worker health and detect stuck/dead workers.
    """
    __tablename__ = "worker_heartbeats"

    worker_id = Column(Text, primary_key=True)
    queue = Column(Text, nullable=False, index=True)
    status = Column(Text, nullable=False, default="active")  # active, idle, draining, stopped
    tasks_completed = Column(Integer, nullable=False, default=0)
    tasks_failed = Column(Integer, nullable=False, default=0)
    last_heartbeat_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
