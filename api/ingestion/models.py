"""Pydantic models for the document ingestion pipeline.

Defines the data structures used for tracking job status,
ingestion requests, and extraction results throughout the
async document processing workflow.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    """Enumeration of possible job statuses in the ingestion pipeline."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return self.value


class ExtractionMethod(str, Enum):
    """Extraction method used for document processing."""

    PYMUPDF = "pymupdf"
    TIKA = "tika"
    DOCX = "docx"
    OCR_TEXTRACT = "ocr_textract"
    OCR_FALLBACK = "ocr_fallback"


class PageExtraction(BaseModel):
    """Extracted content from a single page of a document."""

    page_number: int = Field(..., ge=1, description="1-based page number")
    text: str = Field(..., description="Extracted text content")
    method: ExtractionMethod = Field(..., description="Method used for extraction")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence score"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Page-level metadata"
    )

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Extracted text must not be empty")
        return stripped


class ClauseSegment(BaseModel):
    """A single clause segment identified within a document."""

    clause_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique clause identifier"
    )
    text: str = Field(..., description="Clause text content")
    section_number: Optional[str] = Field(None, description="Section number if available")
    heading: Optional[str] = Field(None, description="Clause heading/title")
    page_number: int = Field(..., ge=1, description="Source page number")
    start_char: int = Field(..., ge=0, description="Start character offset in source text")
    end_char: int = Field(..., ge=0, description="End character offset in source text")
    parent_clause_id: Optional[str] = Field(
        None, description="Parent clause ID for hierarchical structure"
    )
    child_clause_ids: List[str] = Field(
        default_factory=list, description="Child clause IDs"
    )
    level: int = Field(default=1, ge=1, description="Hierarchy depth level")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DocumentChunk(BaseModel):
    """A semantic chunk of document text for embedding and analysis."""

    chunk_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique chunk identifier"
    )
    document_id: str = Field(..., description="Source document identifier")
    text: str = Field(..., description="Chunk text content")
    chunk_index: int = Field(..., ge=0, description="Zero-based chunk sequence number")
    token_count: int = Field(..., ge=1, description="Approximate token count")
    start_char: int = Field(..., ge=0, description="Start character offset in source")
    end_char: int = Field(..., ge=0, description="End character offset in source")
    clause_ids: List[str] = Field(
        default_factory=list, description="Clause IDs contained in this chunk"
    )
    page_numbers: List[int] = Field(
        default_factory=list, description="Page numbers covered by this chunk"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class IngestionRequest(BaseModel):
    """Request payload for submitting a document for ingestion."""

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the document")
    tenant_id: str = Field(..., description="Tenant/organization identifier")
    user_id: str = Field(..., description="User who submitted the document")
    webhook_url: Optional[str] = Field(
        None, description="Optional webhook URL for completion notification"
    )
    webhook_secret: Optional[str] = Field(
        None, description="Secret for HMAC signing webhook payload"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extraction options (e.g., enable_ocr, language)",
    )


class JobRecord(BaseModel):
    """Complete record of an ingestion job."""

    job_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique job identifier"
    )
    document_id: str = Field(..., description="Document identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    progress: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Progress percentage"
    )
    error_message: Optional[str] = Field(None, description="Error details if failed")
    extraction_results: Optional[List[PageExtraction]] = Field(
        None, description="Per-page extraction results"
    )
    clauses: Optional[List[ClauseSegment]] = Field(
        None, description="Identified clause segments"
    )
    chunks: Optional[List[DocumentChunk]] = Field(
        None, description="Semantic document chunks"
    )
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)

    model_config = {"from_attributes": True}


class JobStatusResponse(BaseModel):
    """API response model for job status queries."""

    job_id: str
    status: JobStatus
    progress: float
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class IngestionSummary(BaseModel):
    """Summary of a completed ingestion for API responses."""

    job_id: str
    document_id: str
    filename: str
    status: JobStatus
    total_pages: int
    total_clauses: int
    total_chunks: int
    extraction_methods: List[ExtractionMethod]
    processing_time_seconds: float
