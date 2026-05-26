"""PDF export with highlighted risk clauses and redline margin annotations.

Uses PyMuPDF to render redline suggestions as PDF documents with
color-coded highlights, margin annotations, and an executive summary
page.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..redline.models import RedlineSuggestion
from .annotation_layer import (
    AnnotationLayer,
    ColorCodedAnnotation,
    RiskLevel,
    RISK_COLORS,
    RISK_OPACITY,
)
from .summary_page import SummaryPageGenerator

logger = logging.getLogger(__name__)


@dataclass
class PdfExportResult:
    """Result of a PDF export operation."""

    success: bool
    file_path: Optional[str] = None
    file_bytes: Optional[bytes] = None
    suggestion_count: int = 0
    page_count: int = 0
    error: Optional[str] = None
    export_time_ms: float = 0.0


class PdfExporter:
    """Exports redline suggestions as PDF with highlighted markup.

    Creates a PDF with:
    - Page 1: Executive summary
    - Subsequent pages: Original contract text with highlighted clauses
      and margin annotations showing the redline suggestions

    Usage:
        exporter = PdfExporter()
        result = exporter.export(suggestions, "output.pdf")
        bytes_result = exporter.export_to_bytes(suggestions)
    """

    # Page layout constants (points)
    PAGE_WIDTH = 612   # US Letter
    PAGE_HEIGHT = 792
    MARGIN_LEFT = 72
    MARGIN_RIGHT = 72
    MARGIN_TOP = 72
    MARGIN_BOTTOM = 72
    TEXT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    ANNOTATION_WIDTH = 180
    CONTENT_WIDTH = TEXT_WIDTH - ANNOTATION_WIDTH - 20

    def __init__(self) -> None:
        """Initialize the PDF exporter."""
        self._summary_generator = SummaryPageGenerator()

    def export(
        self,
        suggestions: List[RedlineSuggestion],
        output_path: str,
        original_pdf_path: Optional[str] = None,
        title: str = "Contract Redline Analysis",
    ) -> PdfExportResult:
        """Export redline suggestions as a PDF file.

        Args:
            suggestions: List of redline suggestions to export.
            output_path: Path to write the PDF file.
            original_pdf_path: Optional path to original PDF for overlay.
            title: Document title.

        Returns:
            PdfExportResult with the result.
        """
        start_time = datetime.utcnow()

        try:
            pdf_bytes = self._build_pdf(suggestions, original_pdf_path, title)

            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                "Exported %d suggestions to %s in %.0fms",
                len(suggestions), output_path, elapsed,
            )

            return PdfExportResult(
                success=True,
                file_path=output_path,
                file_bytes=pdf_bytes,
                suggestion_count=len(suggestions),
                export_time_ms=elapsed,
            )

        except Exception as exc:
            logger.error("PDF export failed: %s", exc, exc_info=True)
            return PdfExportResult(
                success=False,
                error=str(exc),
                suggestion_count=len(suggestions),
            )

    def export_to_bytes(
        self,
        suggestions: List[RedlineSuggestion],
        original_pdf_path: Optional[str] = None,
        title: str = "Contract Redline Analysis",
    ) -> PdfExportResult:
        """Export redline suggestions as PDF bytes.

        Args:
            suggestions: List of redline suggestions to export.
            original_pdf_path: Optional path to original PDF for overlay.
            title: Document title.

        Returns:
            PdfExportResult with file_bytes populated.
        """
        start_time = datetime.utcnow()

        try:
            pdf_bytes = self._build_pdf(suggestions, original_pdf_path, title)

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Count pages
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = doc.page_count
            doc.close()

            return PdfExportResult(
                success=True,
                file_bytes=pdf_bytes,
                suggestion_count=len(suggestions),
                page_count=page_count,
                export_time_ms=elapsed,
            )

        except Exception as exc:
            logger.error("PDF bytes export failed: %s", exc, exc_info=True)
            return PdfExportResult(
                success=False,
                error=str(exc),
                suggestion_count=len(suggestions),
            )

    def _build_pdf(
        self,
        suggestions: List[RedlineSuggestion],
        original_pdf_path: Optional[str] = None,
        title: str = "Contract Redline Analysis",
    ) -> bytes:
        """Build the PDF document.

        Args:
            suggestions: List of redline suggestions.
            original_pdf_path: Optional original PDF path.
            title: Document title.

        Returns:
            PDF bytes.
        """
        import fitz  # PyMuPDF

        output_doc = fitz.open()

        # Build annotation layer
        annotation_layer = AnnotationLayer()
        for suggestion in suggestions:
            risk_level = RiskLevel.HIGH
            if suggestion.risk_impact == "low":
                risk_level = RiskLevel.LOW
            elif suggestion.risk_impact == "medium":
                risk_level = RiskLevel.MEDIUM

            annotation_layer.add_annotation(
                page_number=1,  # Will be adjusted if original PDF is used
                rect=(0, 0, 0, 0),  # Will be computed during text search
                risk_level=risk_level,
                text=suggestion.original_text[:200],
                suggestion_text=suggestion.proposed_text[:200],
                rationale=suggestion.rationale[:300],
            )

        # Add summary page
        self._add_summary_page(output_doc, suggestions, annotation_layer, title)

        # Add suggestion detail pages
        self._add_suggestion_pages(output_doc, suggestions)

        # If original PDF is provided, overlay annotations
        if original_pdf_path:
            output_doc = self._overlay_on_original(
                output_doc, original_pdf_path, suggestions
            )

        # Save to bytes
        buffer = io.BytesIO()
        output_doc.save(buffer, garbage=4, deflate=True)
        output_doc.close()
        buffer.seek(0)

        return buffer.getvalue()

    def _add_summary_page(
        self,
        doc: Any,
        suggestions: List[RedlineSuggestion],
        annotation_layer: AnnotationLayer,
        title: str,
    ) -> None:
        """Add the executive summary page.

        Args:
            doc: PyMuPDF document.
            suggestions: List of suggestions.
            annotation_layer: Annotation layer.
            title: Document title.
        """
        import fitz

        page = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)

        # Get summary data
        summary_data = self._summary_generator.generate(
            suggestions, annotation_layer, title
        )

        # Title
        title_rect = fitz.Rect(
            self.MARGIN_LEFT, 40,
            self.PAGE_WIDTH - self.MARGIN_RIGHT, 80,
        )
        page.insert_textbox(
            title_rect,
            summary_data["title"],
            fontsize=20,
            bold=True,
            color=(0, 0, 0.4),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        # Metadata
        meta_y = 95
        meta_text = (
            f"Generated: {summary_data['generated_at'][:10]} | "
            f"Total Suggestions: {summary_data['statistics']['total_suggestions']}"
        )
        page.insert_text(
            fitz.Point(self.MARGIN_LEFT, meta_y),
            meta_text,
            fontsize=9,
            color=(0.4, 0.4, 0.4),
        )

        # Risk distribution section
        section_y = meta_y + 30
        page.insert_text(
            fitz.Point(self.MARGIN_LEFT, section_y),
            "Risk Distribution",
            fontsize=14,
            bold=True,
            color=(0, 0, 0),
        )

        risk_items = summary_data["risk_distribution"]
        risk_y = section_y + 20
        for item in risk_items:
            color = item["color"]
            rgb = self._hex_to_rgb(color)
            bar_width = int(self.TEXT_WIDTH * item["percentage"] / 100)

            # Draw color bar
            bar_rect = fitz.Rect(
                self.MARGIN_LEFT, risk_y - 8,
                self.MARGIN_LEFT + max(bar_width, 20), risk_y + 2,
            )
            page.draw_rect(bar_rect, color=rgb, fill=rgb, fill_opacity=0.3)

            # Label
            page.insert_text(
                fitz.Point(self.MARGIN_LEFT + 5, risk_y),
                f"{item['level'].title()}: {item['count']} ({item['percentage']}%)",
                fontsize=10,
                color=(0, 0, 0),
            )
            risk_y += 16

        # Status summary
        status_y = risk_y + 15
        page.insert_text(
            fitz.Point(self.MARGIN_LEFT, status_y),
            "Review Status",
            fontsize=14,
            bold=True,
            color=(0, 0, 0),
        )

        status = summary_data["statistics"]["status_summary"]
        status_text = (
            f"Pending: {status.get('pending', 0)} | "
            f"Accepted: {status.get('accepted', 0)} | "
            f"Rejected: {status.get('rejected', 0)} | "
            f"Modified: {status.get('modified', 0)}"
        )
        page.insert_text(
            fitz.Point(self.MARGIN_LEFT, status_y + 20),
            status_text,
            fontsize=10,
            color=(0.2, 0.2, 0.2),
        )

        # Recommendations
        rec_y = status_y + 45
        page.insert_text(
            fitz.Point(self.MARGIN_LEFT, rec_y),
            "Recommendations",
            fontsize=14,
            bold=True,
            color=(0, 0, 0),
        )

        rec_text_y = rec_y + 20
        for rec in summary_data.get("recommendations", []):
            rec_box = fitz.Rect(
                self.MARGIN_LEFT, rec_text_y - 10,
                self.PAGE_WIDTH - self.MARGIN_RIGHT, rec_text_y + 15,
            )
            page.insert_textbox(
                rec_box,
                f"• {rec}",
                fontsize=9,
                color=(0.2, 0.2, 0.2),
            )
            rec_text_y += 25

    def _add_suggestion_pages(
        self,
        doc: Any,
        suggestions: List[RedlineSuggestion],
    ) -> None:
        """Add detail pages for each suggestion.

        Args:
            doc: PyMuPDF document.
            suggestions: List of suggestions.
        """
        import fitz

        for idx, suggestion in enumerate(suggestions, 1):
            page = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)

            y = self.MARGIN_TOP

            # Suggestion header
            header = (
                f"Suggestion {idx}: "
                f"{suggestion.clause_type.value.replace('_', ' ').title()}"
            )
            page.insert_text(
                fitz.Point(self.MARGIN_LEFT, y),
                header,
                fontsize=14,
                bold=True,
                color=(0, 0, 0.4),
            )
            y += 20

            # Metadata line
            meta = (
                f"Confidence: {suggestion.confidence:.0%} | "
                f"Risk: {suggestion.risk_impact.upper()} | "
                f"Change: {suggestion.change_type.title()} | "
                f"Status: {suggestion.status.title()}"
            )
            page.insert_text(
                fitz.Point(self.MARGIN_LEFT, y),
                meta,
                fontsize=8,
                color=(0.4, 0.4, 0.4),
            )
            y += 15

            if suggestion.attorney_review_required:
                page.insert_text(
                    fitz.Point(self.MARGIN_LEFT, y),
                    "⚠ ATTORNEY REVIEW REQUIRED",
                    fontsize=9,
                    bold=True,
                    color=(0.8, 0, 0),
                )
                y += 15

            y += 10

            # Original text
            page.insert_text(
                fitz.Point(self.MARGIN_LEFT, y),
                "Original Text:",
                fontsize=11,
                bold=True,
                color=(0.6, 0, 0),
            )
            y += 15

            orig_box = fitz.Rect(
                self.MARGIN_LEFT, y,
                self.PAGE_WIDTH - self.MARGIN_RIGHT, y + 100,
            )
            page.insert_textbox(
                orig_box,
                suggestion.original_text,
                fontsize=9,
                color=(0.6, 0, 0),
            )
            # Estimate text height
            text_height = self._estimate_text_height(suggestion.original_text, 9)
            y += max(text_height, 30) + 10

            # Proposed text
            page.insert_text(
                fitz.Point(self.MARGIN_LEFT, y),
                "Proposed Text:",
                fontsize=11,
                bold=True,
                color=(0, 0.4, 0),
            )
            y += 15

            prop_box = fitz.Rect(
                self.MARGIN_LEFT, y,
                self.PAGE_WIDTH - self.MARGIN_RIGHT, y + 100,
            )
            page.insert_textbox(
                prop_box,
                suggestion.proposed_text,
                fontsize=9,
                color=(0, 0.4, 0),
            )
            text_height = self._estimate_text_height(suggestion.proposed_text, 9)
            y += max(text_height, 30) + 10

            # Rationale
            page.insert_text(
                fitz.Point(self.MARGIN_LEFT, y),
                "Rationale:",
                fontsize=11,
                bold=True,
                color=(0, 0, 0),
            )
            y += 15

            rationale_box = fitz.Rect(
                self.MARGIN_LEFT, y,
                self.PAGE_WIDTH - self.MARGIN_RIGHT, y + 80,
            )
            page.insert_textbox(
                rationale_box,
                suggestion.rationale,
                fontsize=9,
                color=(0.2, 0.2, 0.2),
            )

    def _overlay_on_original(
        self,
        output_doc: Any,
        original_pdf_path: str,
        suggestions: List[RedlineSuggestion],
    ) -> Any:
        """Overlay annotations on the original PDF document.

        Args:
            output_doc: The generated output document.
            original_pdf_path: Path to the original PDF.
            suggestions: List of suggestions to overlay.

        Returns:
            The modified output document with original content + annotations.
        """
        import fitz

        try:
            original_doc = fitz.open(original_pdf_path)

            # Create a new document with original pages + annotations
            combined_doc = fitz.open()

            # Add the summary page first
            summary_page = output_doc[0]
            combined_doc.insert_pdf(output_doc, from_page=0, to_page=0)

            # Add original pages with annotations
            for page_num in range(original_doc.page_count):
                combined_doc.insert_pdf(
                    original_doc, from_page=page_num, to_page=page_num
                )

                # Add annotations to this page
                page = combined_doc[-1]
                self._apply_annotations_to_page(
                    page, suggestions, page_num + 1
                )

            original_doc.close()
            return combined_doc

        except Exception as exc:
            logger.warning(
                "Could not overlay on original PDF: %s. Using generated output.",
                exc,
            )
            return output_doc

    def _apply_annotations_to_page(
        self,
        page: Any,
        suggestions: List[RedlineSuggestion],
        page_number: int,
    ) -> None:
        """Apply highlight and margin annotations to a PDF page.

        Args:
            page: PyMuPDF page object.
            suggestions: List of suggestions to annotate.
            page_number: The 1-based page number.
        """
        import fitz

        for suggestion in suggestions:
            # Search for original text on the page
            text_instances = page.search_for(suggestion.original_text[:100])

            if not text_instances:
                continue

            risk_level = RiskLevel.HIGH
            if suggestion.risk_impact == "low":
                risk_level = RiskLevel.LOW
            elif suggestion.risk_impact == "medium":
                risk_level = RiskLevel.MEDIUM

            color = RISK_COLORS.get(risk_level, (1.0, 0.0, 0.0))
            opacity = RISK_OPACITY.get(risk_level, 0.3)

            for inst in text_instances:
                # Add highlight
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(stroke=color)
                highlight.set_opacity(opacity)
                highlight.update()

            # Add margin annotation (on the first instance)
            if text_instances:
                first_inst = text_instances[0]
                margin_rect = fitz.Rect(
                    self.PAGE_WIDTH - self.MARGIN_RIGHT + 5,
                    first_inst.y0,
                    self.PAGE_WIDTH - 10,
                    first_inst.y0 + 60,
                )

                annotation_text = (
                    f"[{risk_level.value.upper()}] "
                    f"→ {suggestion.proposed_text[:80]}..."
                )
                annot = page.add_text_annot(
                    (margin_rect.x0, margin_rect.y0),
                    annotation_text,
                )
                annot.set_colors(stroke=color)
                annot.update()

    @staticmethod
    def _estimate_text_height(text: str, font_size: int) -> int:
        """Estimate the height of text at a given font size.

        Args:
            text: The text content.
            font_size: The font size in points.

        Returns:
            Estimated height in points.
        """
        lines = max(1, len(text) // 80 + 1)
        return lines * (font_size + 4)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
        """Convert a hex color string to an RGB tuple.

        Args:
            hex_color: Hex color string (e.g., "#FF0000").

        Returns:
            RGB tuple with values in 0-1 range.
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b)
