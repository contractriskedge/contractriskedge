"""SyncFailure model — dead-letter tracking for failed sync operations."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SyncFailure(Base):
    """Immutable record of sync failures for dead-letter analysis and retry."""

    __tablename__ = "sync_failures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sync_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_sync_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    # Failure details
    failure_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Context
    external_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    external_endpoint: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )
    request_payload: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_dead_letter: Mapped[bool] = mapped_column(default=False, nullable=False)
    dead_lettered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Resolution
    is_resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_sync_failures_tenant", "tenant_id"),
        Index("ix_sync_failures_job", "sync_job_id"),
        Index("ix_sync_failures_integration", "integration_id"),
        Index("ix_sync_failures_dead_letter", "is_dead_letter", "is_resolved"),
        Index("ix_sync_failures_retry", "next_retry_at", "is_dead_letter"),
    )

    def __repr__(self) -> str:
        return (
            f"<SyncFailure id={self.id} job={self.sync_job_id} "
            f"type={self.failure_type} dead_letter={self.is_dead_letter}>"
        )
