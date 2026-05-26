"""IntegrationSyncJob and SyncConflict models — sync lineage and conflict tracking."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SyncJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class SyncJobTrigger(str, enum.Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    RETRY = "retry"
    SYSTEM = "system"


class IntegrationSyncJob(Base):
    __tablename__ = "integration_sync_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    status: Mapped[SyncJobStatus] = mapped_column(
        Enum(SyncJobStatus, name="sync_job_status_enum", create_constraint=True),
        default=SyncJobStatus.PENDING,
        nullable=False,
    )
    trigger: Mapped[SyncJobTrigger] = mapped_column(
        Enum(SyncJobTrigger, name="sync_job_trigger_enum", create_constraint=True),
        default=SyncJobTrigger.MANUAL,
        nullable=False,
    )
    sync_type: Mapped[str] = mapped_column(String(50), default="full", nullable=False)

    # Sync metrics
    total_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    synced_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failed_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skipped_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bytes_transferred: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Delta sync support
    cursor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delta_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Result metadata
    result_summary: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    integration = relationship("Integration", back_populates="sync_jobs")
    conflicts = relationship("SyncConflict", back_populates="sync_job", lazy="selectin")

    __table_args__ = (
        Index("ix_sync_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_sync_jobs_integration_status", "integration_id", "status"),
        Index("ix_sync_jobs_correlation", "correlation_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<IntegrationSyncJob id={self.id} integration={self.integration_id} "
            f"status={self.status} trigger={self.trigger}>"
        )


class SyncConflict(Base):
    """Tracks conflicts detected during sync operations for resolution."""

    __tablename__ = "sync_conflicts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sync_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_sync_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    local_entity_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    conflict_type: Mapped[str] = mapped_column(String(100), nullable=False)
    field: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    local_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    external_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sync_job = relationship("IntegrationSyncJob", back_populates="conflicts")

    __table_args__ = (
        Index("ix_sync_conflicts_job", "sync_job_id"),
        Index("ix_sync_conflicts_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<SyncConflict id={self.id} job={self.sync_job_id} "
            f"type={self.conflict_type} external_id={self.external_id}>"
        )
