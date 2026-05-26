"""PDF text extraction using PyMuPDF with Apache Tika fallback.

Provides robust PDF text extraction with automatic fallback from
PyMuPDF (primary) to Apache Tika (secondary). Handles common PDF
edge cases including rotated pages, password-protected documents,
and mixed-content layouts.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional

from ingestion.extractors.edge_cases import EdgeCaseHandler
from ingestion.extractors.models import (
    ExtractedPage,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
    PageMetadata,
)

logger = logging.getLogger(__name__)


class PdfExtractionError(Exception):
    """Base exception for PDF extraction failures."""


class PyMuPDFExtractionError(PdfExtractionError):
    """Raised when PyMuPDF extraction fails."""


class TikaExtractionError(PdfExtractionError):
    """Raised when Apache Tika extraction fails."""


class PdfExtractor:
    """Extracts text from PDF documents using PyMuPDF with Tika fallback.

    Uses PyMuPDF (fitz) as the primary extraction engine for speed and
    accuracy. Falls back to Apache Tika for PDFs that PyMuPDF cannot
    handle (e.g., certain encoded or malformed PDFs).

    Attributes:
        use_fallback: Whether to attempt Tika fallback on PyMuPDF failure.
        tika_endpoint: Apache Tika server endpoint URL.
        edge_handler: Handler for PDF edge cases.
    """

    SUPPORTED_EXTENSIONS = {".pdf"}

    def __init__(
        self,
        use_fallback: bool = True,
        tika_endpoint: str = "http://localhost:9998",
    ) -> None:
        """Initialize the PDF extractor.

        Args:
            use_fallback: Whether to enable Apache Tika fallback.
            tika_endpoint: URL of the Apache Tika server.
        """
        self.use_fallback = use_fallback
        self.tika_endpoint = tika_endpoint
        self.edge_handler = EdgeCaseHandler()

    def extract(
        self,
        file_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[ExtractedPage]:
        """Extract text from a PDF file.

        Attempts PyMuPDF first, then falls back to Tika if enabled
        and the primary extraction fails.

        Args:
            file_path: Absolute path to the PDF file.
            options: Extraction options dict with optional keys:
                - password: str for password-protected PDFs
                - page_range: tuple[int, int] for specific page range
                - enable_ocr: bool to force OCR fallback

        Returns:
            List of ExtractedPage objects.

        Raises:
            PdfExtractionError: If all extraction methods fail.
            FileNotFoundError: If the PDF file does not exist.
        """
        options = options or {}

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if not file_path.lower().endswith(".pdf"):
            raise PdfExtractionError(f"File is not a PDF: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise PdfExtractionError(f"PDF file is empty: {file_path}")

        logger.info(
            "Starting PDF extraction: %s (size: %d bytes)",
            os.path.basename(file_path),
            file_size,
        )

        start_time = time.time()

        # Check for edge cases first
        edge_result = self.edge_handler.check_pdf(file_path)
        if edge_result.get("is_password_protected", False):
            password = options.get("password")
            if not password:
                raise PdfExtractionError(
                    f"PDF is password-protected: {file_path}. "
                    f"Provide a password in extraction options."
                )

        # Primary extraction: PyMuPDF
        try:
            pages = self._extract_with_pymupdf(file_path, options)
            method = ExtractionMethod.PYMUPDF
            fallback_used = False
            logger.info(
                "PyMuPDF extraction successful: %d pages from %s",
                len(pages),
                os.path.basename(file_path),
            )
        except PyMuPDFExtractionError as exc:
            logger.warning(
                "PyMuPDF extraction failed for %s: %s",
                file_path,
                exc,
            )
            if not self.use_fallback:
                raise PdfExtractionError(
                    f"PyMuPDF extraction failed and fallback disabled: {exc}"
                ) from exc

            # Fallback: Apache Tika
            try:
                pages = self._extract_with_tika(file_path, options)
                method = ExtractionMethod.TIKA
                fallback_used = True
                logger.info(
                    "Tika fallback extraction successful: %d pages from %s",
                    len(pages),
                    os.path.basename(file_path),
                )
            except TikaExtractionError as tika_exc:
                raise PdfExtractionError(
                    f"Both PyMuPDF and Tika extraction failed. "
                    f"PyMuPDF: {exc}. Tika: {tika_exc}"
                ) from tika_exc

        processing_time = time.time() - start_time

        # Apply edge case post-processing
        pages = self.edge_handler.post_process_pages(pages)

        total_chars = sum(len(p.text) for p in pages)

        logger.info(
            "PDF extraction complete: %s - %d pages, %d chars in %.2fs (method: %s%s)",
            os.path.basename(file_path),
            len(pages),
            total_chars,
            processing_time,
            method.value,
            " + fallback" if fallback_used else "",
        )

        return pages

    def _extract_with_pymupdf(
        self,
        file_path: str,
        options: Dict[str, Any],
    ) -> List[ExtractedPage]:
        """Extract text using PyMuPDF (fitz).

        Args:
            file_path: Path to the PDF file.
            options: Extraction options.

        Returns:
            List of ExtractedPage objects.

        Raises:
            PyMuPDFExtractionError: If extraction fails.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise PyMuPDFExtractionError(
                "PyMuPDF (fitz) is not installed. Install with: pip install PyMuPDF"
            )

        password = options.get("password")
        page_range = options.get("page_range")

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            raise PyMuPDFExtractionError(
                f"Failed to open PDF with PyMuPDF: {exc}"
            ) from exc

        if password and doc.needs_pass:
            if not doc.authenticate(password):
                doc.close()
                raise PyMuPDFExtractionError("Incorrect password for PDF")

        try:
            pages: List[ExtractedPage] = []
            total_pages = len(doc)

            start_page, end_page = 0, total_pages
            if page_range and len(page_range) == 2:
                start_page = max(0, page_range[0] - 1)  # Convert to 0-based
                end_page = min(total_pages, page_range[1])

            for page_num in range(start_page, end_page):
                try:
                    page = doc[page_num]
                    page_rect = page.rect

                    # Handle rotated pages
                    rotation = page.rotation or 0
                    is_rotated = rotation in (90, 180, 270)

                    # Extract text with layout preservation
                    text = page.get_text("text")

                    # Fallback to "blocks" mode if text extraction is empty
                    if not text.strip():
                        blocks = page.get_text("blocks")
                        text = "\n\n".join(
                            b[4] for b in blocks if b[4].strip()
                        )

                    # Detect tables
                    tables: List[List[List[str]]] = []
                    try:
                        tab = page.find_tables()
                        if tab:
                            for t in tab.tables:
                                table_data: List[List[str]] = []
                                for row in t.extract():
                                    table_data.append(
                                        [str(cell) if cell else "" for cell in row]
                                    )
                                tables.append(table_data)
                    except Exception:
                        pass

                    page_metadata = PageMetadata(
                        width=page_rect.width,
                        height=page_rect.height,
                        rotation=rotation,
                        is_rotated=is_rotated,
                        has_images=len(page.get_images()) > 0,
                        has_tables=len(tables) > 0,
                        word_count=len(text.split()),
                    )

                    extracted_page = ExtractedPage(
                        page_number=page_num + 1,
                        text=text.strip(),
                        method=ExtractionMethod.PYMUPDF,
                        confidence=0.95,
                        status=ExtractionStatus.SUCCESS,
                        metadata=page_metadata,
                        tables=tables,
                    )
                    pages.append(extracted_page)

                except Exception as exc:
                    logger.warning(
                        "Failed to extract page %d from %s: %s",
                        page_num + 1,
                        file_path,
                        exc,
                    )
                    # Add a failed page entry
                    pages.append(
                        ExtractedPage(
                            page_number=page_num + 1,
                            text="",
                            method=ExtractionMethod.PYMUPDF,
                            confidence=0.0,
                            status=ExtractionStatus.FAILED,
                            metadata=PageMetadata(),
                        )
                    )

        finally:
            doc.close()

        if not pages:
            raise PyMuPDFExtractionError(
                f"No pages extracted from {file_path}"
            )

        return pages

    def _extract_with_tika(
        self,
        file_path: str,
        options: Dict[str, Any],
    ) -> List[ExtractedPage]:
        """Extract text using Apache Tika as fallback.

        Args:
            file_path: Path to the PDF file.
            options: Extraction options.

        Returns:
            List of ExtractedPage objects.

        Raises:
            TikaExtractionError: If Tika extraction fails.
        """
        password = options.get("password")

        try:
            from tika import parser as tika_parser
        except ImportError:
            raise TikaExtractionError(
                "Apache Tika Python client is not installed. "
                "Install with: pip install tika"
            )

        try:
            headers = {"X-Tika-PDFOcrStrategy": "no_ocr"}
            if password:
                headers["X-Tika-PDFPassword"] = password

            parsed = tika_parser.from_file(
                file_path,
                serverEndpoint=self.tika_endpoint,
                headers=headers,
                requestOptions={"timeout": 300},
            )

            if parsed is None:
                raise TikaExtractionError("Tika returned None")

            content = parsed.get("content", "")
            metadata = parsed.get("metadata", {})

            if not content or not content.strip():
                raise TikaExtractionError("Tika returned empty content")

            # Tika returns flat text; we split by form feed or page breaks
            page_texts = content.split("\f")
            pages: List[ExtractedPage] = []

            for i, page_text in enumerate(page_texts):
                if not page_text.strip():
                    continue

                pages.append(
                    ExtractedPage(
                        page_number=i + 1,
                        text=page_text.strip(),
                        method=ExtractionMethod.TIKA,
                        confidence=0.85,
                        status=ExtractionStatus.SUCCESS,
                        metadata=PageMetadata(
                            word_count=len(page_text.split()),
                        ),
                    )
                )

            if not pages:
                # If no page breaks, treat as single page
                pages.append(
                    ExtractedPage(
                        page_number=1,
                        text=content.strip(),
                        method=ExtractionMethod.TIKA,
                        confidence=0.85,
                        status=ExtractionStatus.SUCCESS,
                        metadata=PageMetadata(
                            word_count=len(content.split()),
                        ),
                    )
                )

            return pages

        except Exception as exc:
            raise TikaExtractionError(f"Tika extraction failed: {exc}") from exc

    def extract_full(
        self,
        file_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResult:
        """Extract text and return a full ExtractionResult with metadata.

        Args:
            file_path: Path to the PDF file.
            options: Extraction options.

        Returns:
            An ExtractionResult with complete extraction metadata.
        """
        options = options or {}
        start_time = time.time()

        pages = self.extract(file_path, options)
        processing_time = time.time() - start_time

        total_chars = sum(len(p.text) for p in pages)
        methods_used = set(p.method for p in pages)

        return ExtractionResult(
            filename=os.path.basename(file_path),
            file_path=file_path,
            total_pages=len(pages),
            pages=pages,
            primary_method=ExtractionMethod.PYMUPDF
            if ExtractionMethod.PYMUPDF in methods_used
            else ExtractionMethod.TIKA,
            fallback_used=ExtractionMethod.TIKA in methods_used,
            processing_time=processing_time,
            total_characters=total_chars,
        )
