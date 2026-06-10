"""Pydantic schemas for upload and ingestion APIs.

Includes schemas for multipart upload, status tracking, chunk retrieval,
retry flows, and paginated listing.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class IngestionState(str, Enum):
    """Mirrors the ORM model's IngestionState for Pydantic compatibility."""
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


def ingestion_state_for_api(value: object) -> IngestionState:
    """Map ORM/DB ingestion state to the API schema enum."""
    from app.domains.ingestion.models import coerce_ingestion_state

    return IngestionState(coerce_ingestion_state(value).value)


# ── Upload ─────────────────────────────────────────────────────────

class UploadRequest(BaseModel):
    """Request body for multipart file upload metadata."""
    filename: str = Field(..., description="Original filename", max_length=500)
    content_type: str = Field(..., description="MIME type", max_length=200)
    file_size: int = Field(..., gt=0, le=100_000_000, description="File size in bytes")
    client_checksum_sha256: Optional[str] = Field(None, description="Client-computed SHA-256", max_length=64)
    metadata: dict = Field(default_factory=dict, description="Optional document metadata")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("Invalid filename")
        return v.strip()

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        allowed = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        }
        if v not in allowed:
            raise ValueError(f"Content type '{v}' is not supported. Allowed: {', '.join(sorted(allowed))}")
        return v


class UploadResponse(BaseModel):
    """Response after a successful multipart upload."""
    upload_id: str
    filename: str
    file_size: int
    content_type: str
    ingestion_state: IngestionState
    message: str = "Upload received. Ingestion pipeline started."
    correlation_id: Optional[str] = None


class UploadStatusResponse(BaseModel):
    """Detailed status of an upload session."""
    upload_id: str
    filename: str
    file_size: int
    content_type: str
    ingestion_state: IngestionState
    ingestion_error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    can_retry: bool = False
    progress: Optional[dict[str, Any]] = None
    storage_key: Optional[str] = None
    checksum_sha256: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class UploadRetryResponse(BaseModel):
    """Response after requesting an ingestion retry."""
    upload_id: str
    ingestion_state: IngestionState
    retry_count: int
    message: str = "Ingestion retry initiated."


class UploadChunkResponse(BaseModel):
    """A single chunk with its embedding status."""
    chunk_id: str
    chunk_index: int
    text: str
    token_count: int
    page_numbers: list[int]
    section_heading: Optional[str] = None
    clause_type: Optional[str] = None
    checksum: str
    embedding_status: str
    similarity_score: Optional[float] = None


class UploadChunkListResponse(BaseModel):
    """Paginated list of chunks for an upload."""
    upload_id: str
    total_chunks: int
    chunks: list[UploadChunkResponse]


# ── Upload Initiation (presigned URL flow) ─────────────────────────

class UploadInitiateRequest(BaseModel):
    """Request to initiate a new upload session."""
    filename: str = Field(..., description="Original filename", max_length=500)
    content_type: str = Field(..., description="MIME type", max_length=200)
    file_size: int = Field(..., gt=0, le=100_000_000, description="File size in bytes")
    client_checksum_sha256: Optional[str] = Field(None, description="Client-computed SHA-256", max_length=64)
    metadata: dict = Field(default_factory=dict, description="Optional metadata")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("Invalid filename")
        return v.strip()

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        allowed = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        }
        if v not in allowed:
            raise ValueError(f"Content type '{v}' is not supported. Allowed: {', '.join(sorted(allowed))}")
        return v


class UploadInitiateResponse(BaseModel):
    """Response after initiating an upload session."""
    upload_id: str
    storage_url: str  # Presigned URL for direct upload
    expires_in: int  # Seconds until presigned URL expires
    allowed_methods: list[str] = ["PUT"]
    required_headers: dict = {
        "Content-Type": "The file's MIME type",
        "X-Checksum-SHA256": "Optional SHA-256 checksum of the file",
    }


# ── Upload Completion (presigned URL flow) ─────────────────────────

class UploadCompleteRequest(BaseModel):
    """Request to confirm upload completion."""
    upload_id: str
    client_checksum_sha256: Optional[str] = Field(None, max_length=64)


class UploadCompleteResponse(BaseModel):
    upload_id: str
    ingestion_state: IngestionState
    message: str = "Upload confirmed. Ingestion pipeline started."


# ── Upload List ────────────────────────────────────────────────────

class UploadSummary(BaseModel):
    upload_id: str
    filename: str
    file_size: int
    content_type: str
    ingestion_state: IngestionState
    created_at: datetime
    contract_number: Optional[str] = None


# ── Error ──────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    request_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
