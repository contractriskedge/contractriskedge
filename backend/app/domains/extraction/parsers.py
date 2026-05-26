"""Document parser abstraction and implementations for PDF, DOCX, and TXT extraction."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    """Result of extracting text from a single page."""
    page_number: int
    text: str
    char_count: int = 0
    word_count: int = 0
    symbol_count: int = 0
    confidence: float = 1.0
    has_text_layer: Optional[bool] = None
    width_pts: Optional[float] = None
    height_pts: Optional[float] = None
    rotation_degrees: int = 0
    processing_time_ms: int = 0


@dataclass
class ExtractionResult:
    """Complete result of extracting text from a document."""
    pages: list[ExtractedPage] = field(default_factory=list)
    total_pages: int = 0
    total_chars: int = 0
    method: str = ""
    ocr_required: bool = False
    ocr_engine_used: Optional[str] = None
    avg_confidence: float = 1.0
    total_processing_time_ms: int = 0
    error: Optional[str] = None


class ExtractionError(Exception):
    """Base error for extraction failures."""


class EncryptedPDFError(ExtractionError):
    """Document is encrypted/password-protected."""


class CorruptedDocumentError(ExtractionError):
    """Document file is corrupted and cannot be processed."""


class UnsupportedFormatError(ExtractionError):
    """Document format is not supported for extraction."""


class DocumentParser(ABC):
    """Abstract base for all document format parsers."""

    @abstractmethod
    def supports(self, content_type: str, file_data: bytes) -> bool:
        """Check if this parser supports the given document."""
        ...

    @abstractmethod
    def extract(self, file_data: bytes, filename: str) -> ExtractionResult:
        """Extract text and metadata from a document."""
        ...

    @abstractmethod
    def detect_type(self, file_data: bytes) -> str:
        """Detect document type from file data."""
        ...


class PDFParser(DocumentParser):
    """PDF text extraction using PyMuPDF with OCR fallback detection."""

    def supports(self, content_type: str, file_data: bytes) -> bool:
        return content_type == "application/pdf" or file_data[:5] == b"%PDF-"

    def detect_type(self, file_data: bytes) -> str:
        return "pdf"

    def extract(self, file_data: bytes, filename: str) -> ExtractionResult:
        import fitz  # PyMuPDF
        import time

        result = ExtractionResult(method="pymupdf_direct")
        start = time.monotonic()

        try:
            doc = fitz.open(stream=file_data, filetype="pdf")
        except Exception as exc:
            error_str = str(exc).lower()
            if "encrypted" in error_str or "password" in error_str:
                raise EncryptedPDFError(f"PDF is encrypted: {exc}")
            raise CorruptedDocumentError(f"Cannot open PDF: {exc}")

        result.total_pages = len(doc)
        text_layer_found = False
        total_confidence = 0.0

        for page_num in range(len(doc)):
            page_start = time.monotonic()
            page = doc[page_num]

            # Get page text
            page_text = page.get_text("text")
            page_has_text = bool(page_text.strip())

            if page_has_text:
                text_layer_found = True

            # Page dimensions
            rect = page.rect
            width = rect.width
            height = rect.height

            # Rotation
            rotation = page.rotation or 0

            # Counts
            char_count = len(page_text)
            words = page_text.split()
            word_count = len(words)
            symbol_count = len(re.findall(r'[^\w\s]', page_text))

            page_time = int((time.monotonic() - page_start) * 1000)

            extracted = ExtractedPage(
                page_number=page_num + 1,
                text=page_text,
                char_count=char_count,
                word_count=word_count,
                symbol_count=symbol_count,
                confidence=0.95 if page_has_text else 0.1,
                has_text_layer=page_has_text,
                width_pts=width,
                height_pts=height,
                rotation_degrees=rotation,
                processing_time_ms=page_time,
            )
            result.pages.append(extracted)
            result.total_chars += char_count
            total_confidence += extracted.confidence

        doc.close()

        result.ocr_required = not text_layer_found
        result.avg_confidence = total_confidence / max(len(result.pages), 1)
        result.total_processing_time_ms = int((time.monotonic() - start) * 1000)

        if text_layer_found:
            result.method = "pymupdf_direct"
            result.ocr_engine_used = None
        else:
            result.method = "pymupdf_direct"
            result.ocr_required = True
            result.ocr_engine_used = None  # OCR will be applied later

        return result


class DOCXParser(DocumentParser):
    """DOCX text extraction using python-docx."""

    def supports(self, content_type: str, file_data: bytes) -> bool:
        return content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def detect_type(self, file_data: bytes) -> str:
        return "docx"

    def extract(self, file_data: bytes, filename: str) -> ExtractionResult:
        import io
        import time
        from docx import Document as DocxDocument

        result = ExtractionResult(method="docx_parse")
        start = time.monotonic()

        try:
            doc = DocxDocument(io.BytesIO(file_data))
        except Exception as exc:
            raise CorruptedDocumentError(f"Cannot open DOCX: {exc}")

        # Collect all paragraphs
        all_text = []
        current_page = []
        page_num = 1
        char_count = 0

        for para in doc.paragraphs:
            text = para.text
            if not text.strip():
                continue
            current_page.append(text)
            char_count += len(text)

            # Page break heuristic: split every ~3000 chars (avoid per-run XML scans — very slow on large DOCX)
            if char_count > 3000:
                page_text = "\n".join(current_page)
                words = page_text.split()
                result.pages.append(ExtractedPage(
                    page_number=page_num,
                    text=page_text,
                    char_count=len(page_text),
                    word_count=len(words),
                    symbol_count=len(re.findall(r'[^\w\s]', page_text)),
                    confidence=0.98,
                    has_text_layer=True,
                ))
                result.total_chars += len(page_text)
                current_page = []
                page_num += 1
                char_count = 0

        # Last page
        if current_page:
            page_text = "\n".join(current_page)
            words = page_text.split()
            result.pages.append(ExtractedPage(
                page_number=page_num,
                text=page_text,
                char_count=len(page_text),
                word_count=len(words),
                symbol_count=len(re.findall(r'[^\w\s]', page_text)),
                confidence=0.98,
                has_text_layer=True,
            ))
            result.total_chars += len(page_text)

        result.total_pages = len(result.pages)
        result.avg_confidence = 0.98
        result.ocr_required = False
        result.total_processing_time_ms = int((time.monotonic() - start) * 1000)

        return result


class TXTParser(DocumentParser):
    """Plain text extraction."""

    def supports(self, content_type: str, file_data: bytes) -> bool:
        return content_type == "text/plain"

    def detect_type(self, file_data: bytes) -> str:
        return "txt"

    def extract(self, file_data: bytes, filename: str) -> ExtractionResult:
        import time

        result = ExtractionResult(method="txt_parse")
        start = time.monotonic()

        try:
            text = file_data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_data.decode("latin-1")
            except Exception as exc:
                raise CorruptedDocumentError(f"Cannot decode text file: {exc}")

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Split into pages by form feeds or every ~4000 chars
        pages_text = []
        if "\f" in text:
            pages_text = [p.strip() for p in text.split("\f") if p.strip()]
        else:
            lines = text.split("\n")
            chunk = []
            chunk_len = 0
            for line in lines:
                chunk.append(line)
                chunk_len += len(line) + 1
                if chunk_len > 4000:
                    pages_text.append("\n".join(chunk))
                    chunk = []
                    chunk_len = 0
            if chunk:
                pages_text.append("\n".join(chunk))

        for i, page_text in enumerate(pages_text):
            words = page_text.split()
            result.pages.append(ExtractedPage(
                page_number=i + 1,
                text=page_text,
                char_count=len(page_text),
                word_count=len(words),
                symbol_count=len(re.findall(r'[^\w\s]', page_text)),
                confidence=0.99,
                has_text_layer=True,
            ))
            result.total_chars += len(page_text)

        result.total_pages = len(result.pages)
        result.avg_confidence = 0.99
        result.ocr_required = False
        result.total_processing_time_ms = int((time.monotonic() - start) * 1000)

        return result


class ParserRegistry:
    """Registry of available document parsers with auto-detection."""

    def __init__(self):
        self._parsers: list[DocumentParser] = [
            PDFParser(),
            DOCXParser(),
            TXTParser(),
        ]

    def get_parser(self, content_type: str, file_data: bytes) -> Optional[DocumentParser]:
        for parser in self._parsers:
            if parser.supports(content_type, file_data):
                return parser
        return None

    def detect_type(self, file_data: bytes) -> str:
        for parser in self._parsers:
            try:
                detected = parser.detect_type(file_data)
                if detected:
                    return detected
            except Exception:
                continue
        return "unknown"


parser_registry = ParserRegistry()
