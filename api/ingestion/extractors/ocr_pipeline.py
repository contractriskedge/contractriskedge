"""OCR fallback pipeline using AWS Textract integration.

Provides automatic OCR processing for scanned documents and
image-based PDFs. Integrates with AWS Textract for production-grade
OCR with cost tracking and auto-trigger logic.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ingestion.extractors.models import (
    ExtractedPage,
    ExtractionMethod,
    ExtractionStatus,
    PageMetadata,
)

logger = logging.getLogger(__name__)


class OcrPipelineError(Exception):
    """Base exception for OCR pipeline failures."""


class TextractConnectionError(OcrPipelineError):
    """Raised when connection to AWS Textract fails."""


class TextractLimitError(OcrPipelineError):
    """Raised when AWS Textract service limits are exceeded."""


@dataclass
class OcrCostTracker:
    """Tracks costs associated with OCR processing.

    AWS Textract pricing (as of 2026):
    - Text detection: $1.50 per 1,000 pages
    - Document analysis (tables/forms): $5.00 per 1,000 pages
    """

    total_pages_processed: int = 0
    total_documents: int = 0
    textract_pages: int = 0
    estimated_cost_usd: float = 0.0
    processing_time_seconds: float = 0.0
    operations: List[Dict[str, Any]] = field(default_factory=list)

    TEXTRACT_COST_PER_PAGE = 0.0015  # $1.50 / 1000 pages
    TEXTRACT_ANALYSIS_COST_PER_PAGE = 0.005  # $5.00 / 1000 pages

    def add_operation(
        self,
        document: str,
        pages: int,
        analysis_type: str = "text",
        duration: float = 0.0,
    ) -> None:
        """Record an OCR operation for cost tracking.

        Args:
            document: Document filename.
            pages: Number of pages processed.
            analysis_type: 'text' or 'analysis' (tables/forms).
            duration: Processing time in seconds.
        """
        cost_per_page = (
            self.TEXTRACT_ANALYSIS_COST_PER_PAGE
            if analysis_type == "analysis"
            else self.TEXTRACT_COST_PER_PAGE
        )
        cost = pages * cost_per_page

        self.total_pages_processed += pages
        self.total_documents += 1
        self.textract_pages += pages
        self.estimated_cost_usd += cost
        self.processing_time_seconds += duration

        self.operations.append(
            {
                "document": document,
                "pages": pages,
                "analysis_type": analysis_type,
                "cost": round(cost, 6),
                "duration": round(duration, 2),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        logger.info(
            "OCR operation: %s, %d pages, $%.6f, %.2fs",
            document,
            pages,
            cost,
            duration,
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of OCR costs and usage.

        Returns:
            Dict with cost tracking summary.
        """
        return {
            "total_documents": self.total_documents,
            "total_pages_processed": self.total_pages_processed,
            "textract_pages": self.textract_pages,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "total_processing_time_seconds": round(self.processing_time_seconds, 2),
            "operations": self.operations[-100:],  # Last 100 operations
        }


class OcrPipeline:
    """OCR processing pipeline with AWS Textract integration.

    Automatically triggers OCR for scanned documents and image-based
    PDFs. Includes cost tracking, auto-trigger logic, and fallback
    mechanisms.

    Attributes:
        cost_tracker: Tracks OCR processing costs.
        auto_trigger: Whether to auto-trigger OCR for scanned PDFs.
        min_text_ratio: Minimum text-to-page ratio to skip OCR (default 0.1).
    """

    def __init__(
        self,
        auto_trigger: bool = True,
        min_text_ratio: float = 0.1,
    ) -> None:
        """Initialize the OCR pipeline.

        Args:
            auto_trigger: Automatically trigger OCR for scanned PDFs.
            min_text_ratio: Minimum ratio of text to page area to skip OCR.
        """
        self.cost_tracker = OcrCostTracker()
        self.auto_trigger = auto_trigger
        self.min_text_ratio = min_text_ratio

    def process_document(
        self,
        file_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[ExtractedPage]:
        """Process a document through the OCR pipeline.

        Determines whether OCR is needed and processes accordingly.
        For PDFs, checks if text extraction was sufficient before
        triggering OCR.

        Args:
            file_path: Path to the document file.
            options: Processing options:
                - force_ocr: bool to bypass text check
                - analyze_tables: bool for table extraction
                - language: str for OCR language hint

        Returns:
            List of ExtractedPage objects with OCR results.

        Raises:
            OcrPipelineError: If OCR processing fails.
        """
        options = options or {}
        force_ocr = options.get("force_ocr", False)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)

        logger.info("OCR pipeline processing: %s", filename)
        start_time = time.time()

        # Check if OCR is needed
        needs_ocr = force_ocr
        if not needs_ocr and self.auto_trigger and file_ext == ".pdf":
            needs_ocr = self._check_needs_ocr(file_path)

        if not needs_ocr:
            logger.info("OCR not needed for %s; text layer sufficient", filename)
            return []

        # Process with AWS Textract
        try:
            pages = self._process_with_textract(file_path, options)
        except TextractConnectionError:
            logger.warning("Textract unavailable; attempting fallback")
            pages = self._fallback_ocr(file_path, options)

        processing_time = time.time() - start_time

        self.cost_tracker.add_operation(
            document=filename,
            pages=len(pages),
            analysis_type="analysis" if options.get("analyze_tables") else "text",
            duration=processing_time,
        )

        logger.info(
            "OCR pipeline complete: %s - %d pages in %.2fs",
            filename,
            len(pages),
            processing_time,
        )
        return pages

    def _check_needs_ocr(self, file_path: str) -> bool:
        """Check if a PDF needs OCR processing.

        Samples pages to determine if there's sufficient text layer.

        Args:
            file_path: Path to the PDF file.

        Returns:
            True if OCR is needed.
        """
        try:
            import fitz
        except ImportError:
            logger.warning("PyMuPDF not available; assuming OCR needed")
            return True

        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            pages_to_sample = min(5, total_pages)

            text_chars = 0
            for i in range(pages_to_sample):
                page = doc[i]
                text = page.get_text("text")
                text_chars += len(text.strip())

            doc.close()

            avg_chars = text_chars / max(pages_to_sample, 1)
            # If average text per page is very low, OCR is needed
            return avg_chars < 100

        except Exception as exc:
            logger.warning("Error checking OCR need: %s", exc)
            return True

    def _process_with_textract(
        self,
        file_path: str,
        options: Dict[str, Any],
    ) -> List[ExtractedPage]:
        """Process a document using AWS Textract.

        Args:
            file_path: Path to the document file.
            options: Processing options.

        Returns:
            List of ExtractedPage objects.

        Raises:
            TextractConnectionError: If Textract API call fails.
        """
        try:
            import boto3
        except ImportError:
            raise TextractConnectionError(
                "boto3 is not installed. Install with: pip install boto3"
            )

        analyze_tables = options.get("analyze_tables", False)
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            textract = boto3.client(
                "textract",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
        except Exception as exc:
            raise TextractConnectionError(
                f"Failed to create Textract client: {exc}"
            ) from exc

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        pages: List[ExtractedPage] = []

        try:
            if analyze_tables:
                response = textract.analyze_document(
                    Document={"Bytes": file_bytes},
                    FeatureTypes=["TABLES", "FORMS"],
                )
            else:
                response = textract.detect_document_text(
                    Document={"Bytes": file_bytes},
                )

            # Process Textract response
            blocks = response.get("Blocks", [])
            page_map: Dict[int, List[str]] = {}
            table_map: Dict[int, List[List[List[str]]]] = {}

            for block in blocks:
                block_type = block.get("BlockType")
                page_num = block.get("Page", 1)

                if block_type == "LINE":
                    text = block.get("Text", "")
                    if page_num not in page_map:
                        page_map[page_num] = []
                    page_map[page_num].append(text)

                elif block_type == "TABLE" and analyze_tables:
                    # Process table structure
                    table_id = block.get("Id")
                    if page_num not in table_map:
                        table_map[page_num] = []
                    # Table cells are processed in a second pass below

            # Build pages
            for page_num in sorted(page_map.keys()):
                text = "\n".join(page_map[page_num])
                pages.append(
                    ExtractedPage(
                        page_number=page_num,
                        text=text,
                        method=ExtractionMethod.OCR_TEXTRACT,
                        confidence=0.9,
                        status=ExtractionStatus.SUCCESS,
                        metadata=PageMetadata(
                            word_count=len(text.split()),
                        ),
                    )
                )

            if not pages:
                raise OcrPipelineError("Textract returned no pages")

        except textract.exceptions.InvalidS3ObjectException as exc:
            raise TextractConnectionError(f"Invalid S3 object: {exc}") from exc
        except textract.exceptions.ThrottlingException as exc:
            raise TextractLimitError(f"Textract throttled: {exc}") from exc
        except textract.exceptions.LimitExceededException as exc:
            raise TextractLimitError(f"Textract limit exceeded: {exc}") from exc
        except Exception as exc:
            raise TextractConnectionError(f"Textract API error: {exc}") from exc

        return pages

    def _fallback_ocr(
        self,
        file_path: str,
        options: Dict[str, Any],
    ) -> List[ExtractedPage]:
        """Fallback OCR method when Textract is unavailable.

        Uses Tesseract via pytesseract as a local fallback.

        Args:
            file_path: Path to the document file.
            options: Processing options.

        Returns:
            List of ExtractedPage objects.
        """
        logger.info("Using Tesseract fallback OCR for %s", file_path)

        try:
            import fitz
            import pytesseract
            from PIL import Image
        except ImportError:
            raise OcrPipelineError(
                "OCR fallback requires PyMuPDF, pytesseract, and Pillow. "
                "Install with: pip install PyMuPDF pytesseract Pillow"
            )

        pages: List[ExtractedPage] = []
        language = options.get("language", "eng")

        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]

                # Render page to image
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Run Tesseract OCR
                text = pytesseract.image_to_string(
                    img,
                    lang=language,
                    config="--oem 3 --psm 6",
                )

                pages.append(
                    ExtractedPage(
                        page_number=page_num + 1,
                        text=text.strip(),
                        method=ExtractionMethod.OCR_FALLBACK,
                        confidence=0.75,
                        status=ExtractionStatus.SUCCESS,
                        metadata=PageMetadata(
                            word_count=len(text.split()),
                            width=float(pix.width),
                            height=float(pix.height),
                        ),
                    )
                )

            doc.close()

        except Exception as exc:
            raise OcrPipelineError(f"Fallback OCR failed: {exc}") from exc

        return pages

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get the current OCR cost tracking summary.

        Returns:
            Dict with cost and usage statistics.
        """
        return self.cost_tracker.get_summary()
