"""Batch upload Pydantic schemas for API request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BatchUploadCreate(BaseModel):
    """Request to create a new batch upload container."""
    name: Optional[str] = Field(None, max_length=255, description="Optional friendly name for the batch")


class BatchUploadFileItem(BaseModel):
    """Summary of a single file within a batch."""
    upload_id: uuid.UUID
    filename: str
    file_size: int
    status: str  # IngestionState value
    error_message: Optional[str] = None
    created_at: datetime


class BatchUploadResponse(BaseModel):
    """Response representing a batch upload operation."""
    batch_id: uuid.UUID
    name: Optional[str] = None
    status: str
    total_files: int
    completed_files: int
    failed_files: int
    total_bytes: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class BatchUploadDetailResponse(BatchUploadResponse):
    """Detailed batch response including per-file status."""
    files: list[BatchUploadFileItem] = []


class BatchUploadListResponse(BaseModel):
    """Paginated list of batch uploads."""
    items: list[BatchUploadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
