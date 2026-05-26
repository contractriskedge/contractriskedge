"""OCR and document extraction SQLAlchemy models.

Tracks page-level extraction, OCR quality metrics, extraction failures,
and extraction run history for the complete document processing pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Text,
    BigInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.kernel.database.base import Base


class ExtractionMethod(str, Enum):
    """Method used to extract text from a document."""
    PYMUPDF_DIRECT = "pymupdf_direct"       # Digital PDF with text layer
    PYMUPDF_OCR = "pymupdf_ocr"             # PDF processed with OCRmyPDF then PyMuPDF
    TESSERACT_OCR = "tesseract_ocr"         # Direct Tesseract OCR on images
    DOCX_PARSE = "docx_parse"               # python-docx extraction
    TXT_PARSE = "txt_parse"                 # Direct text read
    OCR_FALLBACK = "ocr_fallback"           # Multi-engine OCR fallback


class ExtractionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentPage(Base):
    """Extracted text and metadata for a single page of a document.

    One row per page. Linked to the upload session via upload_id.
    """
    __tablename__ = "document_pages"

    page_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False, default="")
    text_length = Column(Integer, nullable=False, default=0)

    extraction_method = Column(
        Enum("pymupdf_direct", "pymupdf_ocr", "tesseract_ocr", "docx_parse", "txt_parse", "ocr_fallback", name="extraction_method", create_type=True),
        nullable=False,
    )
    extraction_status = Column(
        Enum("pending", "processing", "completed", "failed", "skipped", name="extraction_status", create_type=True),
        nullable=False,
        default=ExtractionStatus.PENDING,
    )

    # OCR quality
    ocr_confidence = Column(Float, nullable=True)
    char_count = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=False, default=0)
    symbol_count = Column(Integer, nullable=False, default=0)  # non-alphanumeric chars
    blank_ratio = Column(Float, nullable=True)  # ratio of whitespace to total

    # Page metadata
    page_width_pts = Column(Float, nullable=True)
    page_height_pts = Column(Float, nullable=True)
    rotation_degrees = Column(Integer, nullable=True, default=0)
    has_text_layer = Column(Boolean, nullable=True)  # For PDF: TRUE if digital text found

    # Processing
    processing_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Metadata
    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("upload_id", "page_number", name="uq_page_per_upload"),
        CheckConstraint("page_number >= 1", name="ck_document_pages_page_number_positive"),
        CheckConstraint(
            "ocr_confidence >= 0 AND ocr_confidence <= 1",
            name="ck_document_pages_ocr_confidence_range",
        ),
    )


class ExtractionRun(Base):
    """Tracks a complete extraction run for an upload session.

    One row per extraction pipeline execution. Enables retry tracking
    and performance monitoring across multiple extraction attempts.
    """
    __tablename__ = "extraction_runs"

    run_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    method = Column(
        Enum("pymupdf_direct", "pymupdf_ocr", "tesseract_ocr", "docx_parse", "txt_parse", "ocr_fallback", name="extraction_method_run", create_type=True),
        nullable=False,
    )
    status = Column(
        Enum("pending", "processing", "completed", "failed", "skipped", name="extraction_run_status", create_type=True),
        nullable=False,
        default=ExtractionStatus.PENDING,
    )

    total_pages = Column(Integer, nullable=False, default=0)
    pages_extracted = Column(Integer, nullable=False, default=0)
    pages_failed = Column(Integer, nullable=False, default=0)
    total_chars = Column(BigInteger, nullable=False, default=0)

    ocr_required = Column(Boolean, nullable=True)  # TRUE if scanned PDF detected
    ocr_engine_used = Column(Text, nullable=True)  # 'tesseract', 'ocrmypdf', 'none'

    avg_confidence = Column(Float, nullable=True)
    total_processing_time_ms = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)
    retry_number = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExtractionFailure(Base):
    """Records individual extraction failures for monitoring and debugging."""
    __tablename__ = "extraction_failures"

    failure_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    page_number = Column(Integer, nullable=True)
    failure_type = Column(Text, nullable=False)  # 'encrypted_pdf', 'corrupted_file', 'ocr_failed', 'timeout'
    error_message = Column(Text, nullable=False)
    error_detail = Column(Text, nullable=True)
    method_attempted = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
