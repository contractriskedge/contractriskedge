"""Export models — immutable audit export jobs and artifact metadata."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.kernel.database.base import Base


class AuditExportJob(Base):
    """Defines an immutable export job for audit event exports."""
    __tablename__ = "audit_export_jobs"

    job_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    actor_id = Column(Text, nullable=False)
    actor_role = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    output_format = Column(Text, nullable=False)
    filter_params = Column(JSONB, nullable=False, default=dict)
    export_reason = Column(Text, nullable=True)
    request_id = Column(Text, nullable=True)
    artifact_count = Column(Integer, nullable=False, default=0)
    checksum = Column(Text, nullable=True)
    manifest_hash = Column(Text, nullable=True)
    manifest_signature = Column(Text, nullable=True)
    chain_of_custody = Column(JSONB, nullable=False, default=dict)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AuditExportArtifact(Base):
    """Records export artifact metadata and integrity details."""
    __tablename__ = "audit_export_artifacts"

    artifact_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID, nullable=False, index=True)
    tenant_id = Column(UUID, nullable=False, index=True)
    filename = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    content_length = Column(Integer, nullable=False)
    sha256_hash = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=True)
    artifact_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
