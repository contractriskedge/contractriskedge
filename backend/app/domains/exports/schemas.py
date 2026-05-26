"""Export schemas — report generation and file export models."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExportFormat(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"


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
