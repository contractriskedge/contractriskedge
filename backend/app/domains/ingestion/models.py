"""Ingestion domain — SQLAlchemy ORM models for upload sessions and ingestion tracking.

Tracks the complete lifecycle of a contract document from upload through
validation, storage confirmation, OCR processing, chunking, embedding, and AI analysis.
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


class IngestionState(str, PyEnum):
    """Canonical ingestion state machine.

    Transitions:
    UPLOADED -> VALIDATING -> VALIDATED -> STORAGE_CONFIRMED -> OCR_PENDING
    -> OCR_PROCESSING -> OCR_COMPLETE -> CHUNKING_PENDING -> EMBEDDING_PENDING
    -> ANALYSIS_PENDING -> REVIEW_READY

    Any state can transition to FAILED.
    UPLOADED can transition to CANCELLED.
    Any state can transition to QUARANTINED (malware detected).
    """
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    STORAGE_CONFIRMED = "storage_confirmed"
    OCR_PENDING = "ocr_pending"
    OCR_PROCESSING = "ocr_processing"
    OCR_COMPLETE = "ocr_complete"
    CHUNKING_PENDING = "chunking_pending"
    EMBEDDING_PENDING = "embedding_pending"
    ANALYSIS_PENDING = "analysis_pending"
    REVIEW_READY = "review_ready"
    FAILED = "failed"
    CANCELLED = "cancelled"
    QUARANTINED = "quarantined"

    @classmethod
    def valid_transitions(cls) -> dict[IngestionState, set[IngestionState]]:
        return {
            cls.UPLOADED: {cls.VALIDATING, cls.CANCELLED, cls.FAILED},
            cls.VALIDATING: {cls.VALIDATED, cls.FAILED, cls.QUARANTINED},
            cls.VALIDATED: {cls.STORAGE_CONFIRMED, cls.FAILED},
            cls.STORAGE_CONFIRMED: {cls.OCR_PENDING, cls.FAILED},
            cls.OCR_PENDING: {cls.OCR_PROCESSING, cls.FAILED},
            cls.OCR_PROCESSING: {cls.OCR_COMPLETE, cls.FAILED, cls.QUARANTINED},
            cls.OCR_COMPLETE: {cls.CHUNKING_PENDING, cls.FAILED},
            cls.CHUNKING_PENDING: {cls.EMBEDDING_PENDING, cls.FAILED},
            cls.EMBEDDING_PENDING: {cls.ANALYSIS_PENDING, cls.FAILED},
            cls.ANALYSIS_PENDING: {cls.REVIEW_READY, cls.FAILED},
            cls.REVIEW_READY: set(),
            cls.FAILED: {cls.UPLOADED},  # Allow retry from failed
            cls.CANCELLED: set(),
            cls.QUARANTINED: set(),
        }

    def can_transition_to(self, target: IngestionState) -> bool:
        current = coerce_ingestion_state(self)
        target_state = coerce_ingestion_state(target)
        return target_state in current.valid_transitions().get(current, set())


def coerce_ingestion_state(value: object) -> IngestionState:
    """Normalize DB/API values to the canonical IngestionState enum."""
    if isinstance(value, IngestionState):
        return value
    # Any enum (including schema enum or duplicate class loads in Celery workers)
    if isinstance(value, PyEnum):
        return IngestionState(value.value)
    if isinstance(value, str):
        raw = value.strip()
        if raw.startswith("IngestionState."):
            return IngestionState[raw.rsplit(".", 1)[-1]]
        return IngestionState(raw)
    raise ValueError(f"Invalid ingestion state: {value!r}")


class UploadSession(Base):
    """Tracks an upload session from initiation through completion and ingestion.

    One UploadSession per file upload. Links to the Contract record once created.
    """
    __tablename__ = "upload_sessions"

    upload_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Text, nullable=False)
    filename = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    file_size = Column(BigInteger, nullable=False, default=0)

    # Checksums
    client_checksum_sha256 = Column(Text, nullable=True)  # Provided by client
    server_checksum_sha256 = Column(Text, nullable=True)  # Computed server-side

    # Storage
    storage_key = Column(Text, nullable=True)  # S3/MinIO object key
    storage_bucket = Column(Text, nullable=True)

    # Batch upload association
    batch_id = Column(UUID, ForeignKey("batch_uploads.batch_id", ondelete="SET NULL"), nullable=True, index=True)

      # Ingestion state machine (PostgreSQL enum type already exists from migrations)
    ingestion_state = Column(
        SAEnum(
            IngestionState,
            name="ingestion_state",
            create_type=False,
            values_callable=lambda states: [state.value for state in states],
        ),
        nullable=False,
        default=IngestionState.UPLOADED,
        index=True,
    )
    ingestion_error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Validation results
    mime_validated = Column(DateTime(timezone=True), nullable=True)
    magic_bytes_validated = Column(DateTime(timezone=True), nullable=True)
    checksum_validated = Column(DateTime(timezone=True), nullable=True)
    malware_scan_result = Column(Text, nullable=True)  # 'clean', 'quarantined', 'pending'

    # Metadata
    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    correlation_id = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "upload_id", name="uq_upload_tenant"),
    )


class AllowedUploadType(Base):
    """Registry of allowed MIME types and file extensions for upload validation."""
    __tablename__ = "allowed_upload_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mime_type = Column(Text, nullable=False, unique=True)
    extension = Column(Text, nullable=False)
    magic_bytes_hex = Column(Text, nullable=True)  # Hex signature for validation
    is_active = Column(Text, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
