"""Color-coded annotation layer for PDF redline export.

Provides color-coded annotations (red=high risk, yellow=medium risk,
green=low risk) for highlighting risk clauses in PDF documents with
margin annotations explaining the redline suggestion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level for color-coded annotations."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def __str__(self) -> str:
        return self.value


# Color mappings for annotations (RGB tuples)
RISK_COLORS: Dict[RiskLevel, Tuple[float, float, float]] = {
    RiskLevel.HIGH: (1.0, 0.0, 0.0),      # Red
    RiskLevel.MEDIUM: (1.0, 1.0, 0.0),     # Yellow
    RiskLevel.LOW: (0.0, 0.8, 0.0),        # Green
}

# Highlight opacity values
RISK_OPACITY: Dict[RiskLevel, float] = {
    RiskLevel.HIGH: 0.3,
    RiskLevel.MEDIUM: 0.25,
    RiskLevel.LOW: 0.2,
}


@dataclass
class ColorCodedAnnotation:
    """A single annotation for PDF markup.

    Defines a highlighted region in the PDF with associated metadata
    for rendering the annotation layer.
    """

    page_number: int
    rect: Tuple[float, float, float, float]  # (x0, y0, x1, y1) in PDF coordinates
    risk_level: RiskLevel
    text: str
    suggestion_text: str
    rationale: str
    annotation_id: str = ""

    @property
    def color(self) -> Tuple[float, float, float]:
        """Get the RGB color for this annotation's risk level.

        Returns:
            RGB tuple with values in 0-1 range.
        """
        return RISK_COLORS.get(self.risk_level, (0.5, 0.5, 0.5))

    @property
    def opacity(self) -> float:
        """Get the highlight opacity for this annotation's risk level.

        Returns:
            Opacity value between 0 and 1.
        """
        return RISK_OPACITY.get(self.risk_level, 0.2)


class AnnotationLayer:
    """Manages color-coded annotations for PDF redline export.

    Organizes annotations by page and risk level, and provides
    methods for adding, querying, and rendering annotations.

    Usage:
        layer = AnnotationLayer()
        layer.add_annotation(
            page_number=1,
            rect=(100, 500, 400, 550),
            risk_level=RiskLevel.HIGH,
            text="Original clause text",
            suggestion_text="Proposed replacement",
            rationale="This clause is one-sided...",
        )
        page_annos = layer.get_annotations_for_page(1)
        summary = layer.get_risk_summary()
    """

    def __init__(self) -> None:
        """Initialize the annotation layer."""
        self._annotations: List[ColorCodedAnnotation] = []
        self._annotation_counter: int = 0

    def add_annotation(
        self,
        page_number: int,
        rect: Tuple[float, float, float, float],
        risk_level: RiskLevel,
        text: str,
        suggestion_text: str,
        rationale: str,
    ) -> ColorCodedAnnotation:
        """Add an annotation to the layer.

        Args:
            page_number: 1-based page number.
            rect: Bounding rectangle (x0, y0, x1, y1) in PDF coordinates.
            risk_level: Risk level for color coding.
            text: The original text being annotated.
            suggestion_text: The proposed replacement text.
            rationale: Explanation for the annotation.

        Returns:
            The created ColorCodedAnnotation.
        """
        self._annotation_counter += 1
        annotation = ColorCodedAnnotation(
            page_number=page_number,
            rect=rect,
            risk_level=risk_level,
            text=text,
            suggestion_text=suggestion_text,
            rationale=rationale,
            annotation_id=f"anno_{self._annotation_counter:04d}",
        )
        self._annotations.append(annotation)
        return annotation

    def add_annotations_from_suggestions(
        self,
        suggestions: List[Any],
        page_mapping: Dict[str, int],
    ) -> int:
        """Add annotations from a list of redline suggestions.

        Args:
            suggestions: List of RedlineSuggestion objects.
            page_mapping: Dict mapping suggestion_id to page number.

        Returns:
            Number of annotations added.
        """
        count = 0
        for suggestion in suggestions:
            page = page_mapping.get(suggestion.suggestion_id, 1)

            risk_level = RiskLevel.HIGH
            if suggestion.risk_impact == "low":
                risk_level = RiskLevel.LOW
            elif suggestion.risk_impact == "medium":
                risk_level = RiskLevel.MEDIUM

            # Use a default rect — actual positioning requires text search in PDF
            rect = (72, 500, 500, 550)  # Will be refined during PDF rendering

            self.add_annotation(
                page_number=page,
                rect=rect,
                risk_level=risk_level,
                text=suggestion.original_text[:200],
                suggestion_text=suggestion.proposed_text[:200],
                rationale=suggestion.rationale[:300],
            )
            count += 1

        return count

    def get_annotations_for_page(
        self, page_number: int
    ) -> List[ColorCodedAnnotation]:
        """Get all annotations for a specific page.

        Args:
            page_number: The page number to filter by.

        Returns:
            List of annotations on that page.
        """
        return [
            a for a in self._annotations
            if a.page_number == page_number
        ]

    def get_annotations_by_risk(
        self, risk_level: RiskLevel
    ) -> List[ColorCodedAnnotation]:
        """Get all annotations with a specific risk level.

        Args:
            risk_level: The risk level to filter by.

        Returns:
            List of matching annotations.
        """
        return [
            a for a in self._annotations
            if a.risk_level == risk_level
        ]

    def get_risk_summary(self) -> Dict[str, int]:
        """Get a summary of annotations by risk level.

        Returns:
            Dict with counts per risk level.
        """
        return {
            "high": len(self.get_annotations_by_risk(RiskLevel.HIGH)),
            "medium": len(self.get_annotations_by_risk(RiskLevel.MEDIUM)),
            "low": len(self.get_annotations_by_risk(RiskLevel.LOW)),
            "total": len(self._annotations),
        }

    def clear(self) -> None:
        """Clear all annotations."""
        self._annotations.clear()
        self._annotation_counter = 0

    @property
    def total_annotations(self) -> int:
        """Get the total number of annotations.

        Returns:
            Total annotation count.
        """
        return len(self._annotations)
