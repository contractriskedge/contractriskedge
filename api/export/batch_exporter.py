"""Batch export of multiple contracts as ZIP archive of DOCX files.

Supports exporting up to 20 contracts simultaneously as individual
DOCX files packaged in a ZIP archive for download.
"""

from __future__ import annotations

import io
import logging
import os
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..redline.models import RedlineSuggestion
from .docx_exporter import DocxExporter, DocxExportResult

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 20


@dataclass
class BatchExportResult:
    """Result of a batch export operation."""

    success: bool
    zip_bytes: Optional[bytes] = None
    file_count: int = 0
    results: List[DocxExportResult] = field(default_factory=list)
    error: Optional[str] = None
    export_time_ms: float = 0.0


class BatchExportError(Exception):
    """Raised when a batch export operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class BatchExporter:
    """Batch export of multiple contracts as ZIP archive.

    Takes a dictionary mapping contract names to lists of redline
    suggestions, exports each as a DOCX, and packages them into
    a single ZIP file.

    Usage:
        exporter = BatchExporter()
        contracts = {
            "Contract_A.docx": suggestions_a,
            "Contract_B.docx": suggestions_b,
        }
        result = exporter.export_batch(contracts)
        with open("redlines.zip", "wb") as f:
            f.write(result.zip_bytes)
    """

    def __init__(self) -> None:
        """Initialize the batch exporter."""
        self._docx_exporter = DocxExporter()

    def export_batch(
        self,
        contracts: Dict[str, List[RedlineSuggestion]],
        zip_comment: Optional[str] = None,
    ) -> BatchExportResult:
        """Export multiple contracts as a ZIP archive.

        Args:
            contracts: Dict mapping output filenames to suggestion lists.
                      Filenames should end with .docx.
            zip_comment: Optional comment for the ZIP archive.

        Returns:
            BatchExportResult with the ZIP bytes.

        Raises:
            BatchExportError: If the batch exceeds MAX_BATCH_SIZE.
        """
        start_time = datetime.utcnow()

        if len(contracts) > MAX_BATCH_SIZE:
            raise BatchExportError(
                f"Batch size {len(contracts)} exceeds maximum of {MAX_BATCH_SIZE}"
            )

        if not contracts:
            raise BatchExportError("No contracts provided for batch export")

        buffer = io.BytesIO()
        results: List[DocxExportResult] = []

        try:
            with zipfile.ZipFile(
                buffer, "w", zipfile.ZIP_DEFLATED, allowZip64=True
            ) as zf:
                if zip_comment:
                    zf.comment = zip_comment.encode("utf-8")

                # Add a README
                readme_content = self._generate_readme(contracts)
                zf.writestr("README.txt", readme_content)

                # Export each contract
                for filename, suggestions in contracts.items():
                    safe_name = self._sanitize_filename(filename)
                    result = self._docx_exporter.export_to_bytes(
                        suggestions,
                        title=safe_name.replace(".docx", ""),
                    )
                    results.append(result)

                    if result.success and result.file_bytes:
                        zf.writestr(safe_name, result.file_bytes)
                        logger.info(
                            "Added %s to batch (%d suggestions, %.0f bytes)",
                            safe_name,
                            len(suggestions),
                            len(result.file_bytes),
                        )
                    else:
                        logger.warning(
                            "Failed to export %s: %s",
                            safe_name,
                            result.error,
                        )
                        # Add error report
                        error_content = (
                            f"Export failed for {safe_name}\n"
                            f"Error: {result.error}\n"
                            f"Suggestions: {len(suggestions)}\n"
                        )
                        zf.writestr(
                            f"ERROR_{safe_name}.txt",
                            error_content,
                        )

            buffer.seek(0)
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            successful = sum(1 for r in results if r.success)
            logger.info(
                "Batch export complete: %d/%d succeeded in %.0fms",
                successful,
                len(contracts),
                elapsed,
            )

            return BatchExportResult(
                success=successful > 0,
                zip_bytes=buffer.getvalue(),
                file_count=len(contracts),
                results=results,
                export_time_ms=elapsed,
            )

        except Exception as exc:
            logger.error("Batch export failed: %s", exc, exc_info=True)
            return BatchExportResult(
                success=False,
                error=str(exc),
                file_count=len(contracts),
                results=results,
            )

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize a filename to be safe for ZIP archives.

        Args:
            filename: The original filename.

        Returns:
            A safe filename string.
        """
        # Remove path separators
        safe = filename.replace("/", "_").replace("\\", "_")

        # Ensure .docx extension
        if not safe.lower().endswith(".docx"):
            safe += ".docx"

        # Limit length
        if len(safe) > 200:
            name, ext = os.path.splitext(safe)
            safe = name[:196] + ext

        return safe

    @staticmethod
    def _generate_readme(
        contracts: Dict[str, List[RedlineSuggestion]]
    ) -> str:
        """Generate a README file for the ZIP archive.

        Args:
            contracts: The contracts being exported.

        Returns:
            README text content.
        """
        total_suggestions = sum(len(s) for s in contracts.values())
        accepted = sum(
            1 for suggestions in contracts.values()
            for s in suggestions if s.status == "accepted"
        )
        pending = sum(
            1 for suggestions in contracts.values()
            for s in suggestions if s.status == "pending"
        )

        lines = [
            "=" * 60,
            "AI Contract Risk Analyzer - Batch Redline Export",
            "=" * 60,
            "",
            f"Export Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"Total Contracts: {len(contracts)}",
            f"Total Suggestions: {total_suggestions}",
            f"Accepted: {accepted}",
            f"Pending Review: {pending}",
            "",
            "Contents:",
            "-" * 40,
        ]

        for filename, suggestions in contracts.items():
            lines.append(
                f"  {filename}: {len(suggestions)} suggestions"
            )

        lines.extend([
            "",
            "Instructions:",
            "-" * 40,
            "1. Open each .docx file in Microsoft Word.",
            "2. Enable editing to view tracked changes.",
            "3. Use Review > Accept/Reject to process suggestions.",
            "4. Each suggestion includes the original deleted text (red, strikethrough)",
            "   and proposed inserted text (green, underline).",
            "5. Review the rationale provided for each change.",
            "",
            "Generated by AI Contract Risk Analyzer",
        ])

        return "\n".join(lines)
