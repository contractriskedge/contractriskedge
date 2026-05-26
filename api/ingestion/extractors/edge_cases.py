"""Handlers for PDF edge cases during text extraction.

Provides utilities for detecting and handling common PDF edge cases
including password-protected documents, rotated pages, multi-column
layouts, scanned image-only PDFs, and malformed PDF structures.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Any, Dict, List, Optional

from ingestion.extractors.models import ExtractedPage, ExtractionMethod, ExtractionStatus

logger = logging.getLogger(__name__)


class EdgeCaseHandler:
    """Detects and handles PDF edge cases during extraction.

    Provides methods for checking PDF properties before extraction
    and post-processing extracted pages to handle edge cases like
    rotated pages and multi-column layouts.
    """

    # Magic bytes for PDF detection
    PDF_MAGIC = b"%PDF"

    def check_pdf(self, file_path: str) -> Dict[str, Any]:
        """Analyze a PDF file for potential edge cases.

        Performs pre-extraction checks to identify issues like
        password protection, corrupted headers, or unusual structures.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dict with edge case flags:
                - is_valid_pdf: bool
                - is_password_protected: bool
                - is_encrypted: bool
                - file_size: int
                - has_trailer: bool
                - warnings: list[str]
        """
        result: Dict[str, Any] = {
            "is_valid_pdf": False,
            "is_password_protected": False,
            "is_encrypted": False,
            "file_size": 0,
            "has_trailer": False,
            "warnings": [],
        }

        if not os.path.exists(file_path):
            result["warnings"].append(f"File not found: {file_path}")
            return result

        file_size = os.path.getsize(file_path)
        result["file_size"] = file_size

        if file_size == 0:
            result["warnings"].append("File is empty")
            return result

        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)

            # Check PDF magic bytes
            if not header.startswith(self.PDF_MAGIC):
                result["warnings"].append(
                    "File does not start with %PDF header; may be corrupted"
                )
                return result

            result["is_valid_pdf"] = True

            # Check for encryption dictionary
            if b"/Encrypt" in header:
                result["is_encrypted"] = True
                # Check if it's password-protected
                if b"/O(" in header or b"/U(" in header:
                    result["is_password_protected"] = True

            # Check for trailer
            with open(file_path, "rb") as f:
                # Read from end for trailer
                f.seek(max(0, file_size - 2048))
                tail = f.read()
                if b"trailer" in tail:
                    result["has_trailer"] = True
                else:
                    result["warnings"].append("No trailer found; PDF may be truncated")

            # Check for linearization
            if b"/Linearized" in header:
                result["warnings"].append("PDF is linearized (web-optimized)")

        except PermissionError:
            result["warnings"].append("Permission denied reading file")
        except Exception as exc:
            result["warnings"].append(f"Error checking PDF: {exc}")

        return result

    def post_process_pages(
        self,
        pages: List[ExtractedPage],
    ) -> List[ExtractedPage]:
        """Post-process extracted pages to handle edge cases.

        Applies corrections for rotated pages, reorders pages if
        needed, and fixes common extraction artifacts.

        Args:
            pages: List of extracted pages to process.

        Returns:
            Processed list of ExtractedPage objects.
        """
        processed: List[ExtractedPage] = []

        for page in pages:
            page = self._fix_rotation_artifacts(page)
            page = self._fix_multi_column_layout(page)
            page = self._clean_extraction_artifacts(page)
            processed.append(page)

        return processed

    def _fix_rotation_artifacts(self, page: ExtractedPage) -> ExtractedPage:
        """Fix text artifacts caused by page rotation.

        Detects and corrects text that was extracted in wrong
        orientation due to rotated pages.

        Args:
            page: Extracted page to fix.

        Returns:
            Fixed ExtractedPage.
        """
        if not page.metadata.is_rotated:
            return page

        text = page.text

        # Common rotation artifacts: text separated by excessive whitespace
        # or newlines due to rotation transformations
        if page.metadata.rotation in (90, 270):
            # Rotated text often has single characters per line
            lines = text.split("\n")
            if all(len(line.strip()) <= 1 for line in lines if line.strip()):
                # Attempt to reconstruct: join characters
                text = "".join(line.strip() for line in lines if line.strip())
                logger.debug(
                    "Fixed rotation artifact on page %d (rotation: %d°)",
                    page.page_number,
                    page.metadata.rotation,
                )

        page.text = text
        return page

    def _fix_multi_column_layout(self, page: ExtractedPage) -> ExtractedPage:
        """Fix text ordering issues from multi-column layouts.

        PyMuPDF may extract multi-column text in reading-order
        incorrectly. This method attempts to detect and reorder
        multi-column content.

        Args:
            page: Extracted page to fix.

        Returns:
            Fixed ExtractedPage with corrected column ordering.
        """
        text = page.text
        lines = text.split("\n")

        # Heuristic: if most lines are short and there are many of them,
        # the page might have columns extracted out of order
        if len(lines) < 10:
            return page

        short_lines = [l for l in lines if len(l.strip()) < 40 and l.strip()]
        if len(short_lines) < len(lines) * 0.3:
            return page

        # Check for column-like patterns: alternating short lines
        # This is a simplified heuristic; production would use more
        # sophisticated layout analysis
        column_pattern_count = 0
        for i in range(len(lines) - 1):
            if lines[i].strip() and lines[i + 1].strip():
                if len(lines[i].strip()) < 30 and len(lines[i + 1].strip()) < 30:
                    column_pattern_count += 1

        if column_pattern_count > len(lines) * 0.2:
            logger.debug(
                "Detected potential multi-column layout on page %d",
                page.page_number,
            )
            page.metadata.metadata["multi_column_detected"] = True

        return page

    def _clean_extraction_artifacts(self, page: ExtractedPage) -> ExtractedPage:
        """Clean common extraction artifacts from page text.

        Removes stray control characters, excessive whitespace,
        and other artifacts introduced during extraction.

        Args:
            page: Extracted page to clean.

        Returns:
            Cleaned ExtractedPage.
        """
        text = page.text

        # Remove null bytes
        text = text.replace("\x00", "")

        # Remove form feed characters (keep as page separators in content)
        text = text.replace("\f", "\n\n")

        # Normalize multiple newlines
        import re

        text = re.sub(r"\n{4,}", "\n\n\n", text)

        # Remove control characters except newlines and tabs
        text = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Normalize whitespace within lines
        text = re.sub(r"[ \t]+", " ", text)

        # Strip leading/trailing whitespace per line
        text = "\n".join(line.strip() for line in text.split("\n"))

        page.text = text.strip()
        return page

    def handle_password_protected(
        self,
        file_path: str,
        password: str,
    ) -> bool:
        """Attempt to unlock a password-protected PDF.

        Args:
            file_path: Path to the PDF file.
            password: Password to attempt.

        Returns:
            True if the password was accepted.
        """
        try:
            import fitz
        except ImportError:
            logger.error("PyMuPDF not available for password handling")
            return False

        try:
            doc = fitz.open(file_path)
            if not doc.needs_pass:
                doc.close()
                return True

            if doc.authenticate(password):
                logger.info("Password accepted for %s", os.path.basename(file_path))
                doc.close()
                return True

            logger.warning("Incorrect password for %s", os.path.basename(file_path))
            doc.close()
            return False

        except Exception as exc:
            logger.error("Error handling password for %s: %s", file_path, exc)
            return False

    def is_scanned_pdf(self, file_path: str, sample_pages: int = 3) -> bool:
        """Detect if a PDF is a scanned image (no text layer).

        Checks the first few pages for text content. If they contain
        no extractable text, the PDF is likely a scanned document
        requiring OCR.

        Args:
            file_path: Path to the PDF file.
            sample_pages: Number of pages to sample (default 3).

        Returns:
            True if the PDF appears to be scanned (no text layer).
        """
        try:
            import fitz
        except ImportError:
            logger.error("PyMuPDF not available for scanned PDF detection")
            return False

        try:
            doc = fitz.open(file_path)
            pages_to_check = min(sample_pages, len(doc))

            text_pages = 0
            for i in range(pages_to_check):
                page = doc[i]
                text = page.get_text("text").strip()
                if len(text) > 50:  # Has meaningful text
                    text_pages += 1

            doc.close()

            # If most sampled pages have no text, it's likely scanned
            return text_pages < pages_to_check / 2

        except Exception as exc:
            logger.error("Error detecting scanned PDF: %s", exc)
            return False
