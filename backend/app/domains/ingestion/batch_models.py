"""Batch upload model — tracks a group of files uploaded together.

A BatchUpload represents a single batch operation where a user uploads
multiple contract documents at once. Each file in the batch gets its own
UploadSession record linked via batch_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Text,
    BigInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.kernel.database.base import Base


class BatchStatus(str, PyEnum):
    """Lifecycle of a batch upload operation."""
    PENDING = "pending"           # Batch created, files being collected
    UPLOADING = "uploading"       # Files actively being uploaded
    PROCESSING = "processing"     # All files uploaded, ingestion pipeline running
    COMPLETED = "completed"       # All files reached REVIEW_READY or terminal
    PARTIAL = "partial"           # Some files succeeded, some failed
    FAILED = "failed"             # All files failed
    CANCELLED = "cancelled"       # User cancelled the batch


class BatchUpload(Base):
    """Tracks a batch upload operation containing multiple files.

    One BatchUpload per batch operation. Links to UploadSession records
    via the batch_id column on UploadSession.
    """
    __tablename__ = "batch_uploads"

    batch_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Text, nullable=False)
    name = Column(Text, nullable=True)  # Optional user-friendly batch name

    # Summary counts (denormalized for fast reads)
    total_files = Column(Integer, nullable=False, default=0)
    completed_files = Column(Integer, nullable=False, default=0)
    failed_files = Column(Integer, nullable=False, default=0)
    total_bytes = Column(BigInteger, nullable=False, default=0)

    # Status
    status = Column(
        SAEnum(
            BatchStatus,
            name="batch_status",
            create_type=False,
            values_callable=lambda states: [state.value for state in states],
        ),
        nullable=False,
        default=BatchStatus.PENDING,
        index=True,
    )
    error_message = Column(Text, nullable=True)

    # Metadata
    batch_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    correlation_id = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "batch_id", name="uq_batch_tenant"),
    )
