"""Pydantic models for document extraction results.

Defines the structured output schema for extracted document content,
including per-page data, metadata, and extraction quality metrics.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ExtractionStatus(str, Enum):
    """Status of an extraction operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    FALLBACK_USED = "fallback_used"


class ExtractionMethod(str, Enum):
    """Method used for text extraction."""

    PYMUPDF = "pymupdf"
    TIKA = "tika"
    DOCX = "docx"
    OCR_TEXTRACT = "ocr_textract"
    OCR_FALLBACK = "ocr_fallback"
    MANUAL = "manual"


class PageMetadata(BaseModel):
    """Metadata associated with a single page."""

    width: Optional[float] = Field(None, description="Page width in points")
    height: Optional[float] = Field(None, description="Page height in points")
    rotation: int = Field(default=0, description="Page rotation in degrees")
    has_images: bool = Field(default=False, description="Whether page contains images")
    has_tables: bool = Field(default=False, description="Whether page contains tables")
    language: Optional[str] = Field(None, description="Detected language")
    word_count: int = Field(default=0, description="Number of words on page")
    is_rotated: bool = Field(default=False, description="Whether page is rotated")
    is_password_protected: bool = Field(default=False, description="Password protection flag")


class ExtractedPage(BaseModel):
    """Content extracted from a single page of a document."""

    page_number: int = Field(..., ge=1, description="1-based page number")
    text: str = Field(..., description="Extracted text content")
    method: ExtractionMethod = Field(..., description="Extraction method used")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence score"
    )
    status: ExtractionStatus = Field(
        default=ExtractionStatus.SUCCESS, description="Extraction status"
    )
    metadata: PageMetadata = Field(
        default_factory=PageMetadata, description="Page-level metadata"
    )
    tables: List[List[List[str]]] = Field(
        default_factory=list,
        description="Extracted tables as list of rows of cells",
    )
    images: List[Dict[str, Any]] = Field(
        default_factory=list, description="Image metadata on page"
    )

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Extracted text must not be empty")
        return stripped

    @field_validator("page_number")
    @classmethod
    def page_number_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page number must be >= 1")
        return v


class ExtractionResult(BaseModel):
    """Complete extraction result for a document."""

    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Path to the source file")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    pages: List[ExtractedPage] = Field(..., description="Extracted pages")
    primary_method: ExtractionMethod = Field(
        ..., description="Primary extraction method used"
    )
    fallback_used: bool = Field(
        default=False, description="Whether a fallback method was used"
    )
    processing_time: float = Field(
        default=0.0, ge=0.0, description="Processing time in seconds"
    )
    total_characters: int = Field(default=0, ge=0, description="Total characters extracted")
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
