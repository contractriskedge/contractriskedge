"""Export schemas — report generation and file export models."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExportFormat(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    CSV = "csv"
    JSONL = "jsonl"


class ExportRequest(BaseModel):
    """Request to generate an export."""
    review_id: str = Field(..., description="Review to export")
    format: ExportFormat = Field(default=ExportFormat.PDF)
    include_findings: bool = Field(default=True)
    include_redlines: bool = Field(default=True)
    include_evidence: bool = Field(default=False)
    include_activity: bool = Field(default=False)


class ExportResponse(BaseModel):
    """Response after initiating an export."""
    export_id: str
    review_id: str
    format: str
    status: str = "processing"
    message: str = "Export generation started."


class ExportDownloadResponse(BaseModel):
    """Response containing export file metadata."""
    export_id: str
    filename: str
    content_type: str
    file_size_bytes: int
    created_at: datetime


class AuditExportRequest(BaseModel):
    """Request payload for an immutable audit export."""
    event_type: Optional[str] = Field(None, description="Filter by event type")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    entity_id: Optional[str] = Field(None, description="Filter by entity ID")
    actor_id: Optional[str] = Field(None, description="Filter by actor ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for traceability")
    request_id: Optional[str] = Field(None, description="The requesting client request ID")
    export_reason: Optional[str] = Field(None, description="Reason for the export")
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    output_format: ExportFormat = Field(default=ExportFormat.CSV)


class AuditExportArtifactResponse(BaseModel):
    artifact_id: str
    filename: str
    content_type: str
    content_length: int
    sha256_hash: str
    storage_key: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AuditExportJobResponse(BaseModel):
    job_id: str
    status: str
    output_format: ExportFormat
    filter_params: dict[str, Any]
    export_reason: Optional[str] = None
    request_id: Optional[str] = None
    artifact_count: int
    checksum: Optional[str] = None
    manifest_hash: Optional[str] = None
    manifest_signature: Optional[str] = None
    chain_of_custody: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[AuditExportArtifactResponse] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
