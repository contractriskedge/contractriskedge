"""Executive summary page generator for PDF redline export.

Generates a formatted executive summary page that serves as Page 1
of the PDF export, providing an overview of all redline suggestions,
risk distribution, and key statistics.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..redline.models import RedlineSuggestion
from .annotation_layer import AnnotationLayer, RiskLevel

logger = logging.getLogger(__name__)


class SummaryPageGenerator:
    """Generates an executive summary page for PDF redline exports.

    Creates a formatted summary page with risk distribution charts,
    key statistics, and a table of contents for the redline suggestions.

    Usage:
        generator = SummaryPageGenerator()
        elements = generator.generate(suggestions, annotation_layer)
    """

    def __init__(self) -> None:
        """Initialize the summary page generator."""
        pass

    def generate(
        self,
        suggestions: List[RedlineSuggestion],
        annotation_layer: Optional[AnnotationLayer] = None,
        document_title: str = "Contract Redline Analysis",
    ) -> Dict[str, Any]:
        """Generate the summary page data structure.

        Args:
            suggestions: List of redline suggestions.
            annotation_layer: Optional annotation layer for risk summary.
            document_title: Title for the summary page.

        Returns:
            Dict with structured summary data for PDF rendering.
        """
        risk_summary = self._compute_risk_summary(suggestions)
        status_summary = self._compute_status_summary(suggestions)
        clause_type_distribution = self._compute_clause_type_distribution(suggestions)

        if annotation_layer:
            annotation_summary = annotation_layer.get_risk_summary()
        else:
            annotation_summary = None

        return {
            "type": "summary_page",
            "title": document_title,
            "generated_at": datetime.utcnow().isoformat(),
            "generator": "AI Contract Risk Analyzer",
            "statistics": {
                "total_suggestions": len(suggestions),
                "risk_summary": risk_summary,
                "status_summary": status_summary,
                "clause_type_distribution": clause_type_distribution,
                "annotation_summary": annotation_summary,
            },
            "risk_distribution": self._format_risk_distribution(risk_summary),
            "suggestion_overview": self._generate_overview(suggestions),
            "recommendations": self._generate_recommendations(
                suggestions, risk_summary
            ),
        }

    @staticmethod
    def _compute_risk_summary(
        suggestions: List[RedlineSuggestion],
    ) -> Dict[str, int]:
        """Compute risk impact distribution.

        Args:
            suggestions: List of suggestions.

        Returns:
            Dict with counts per risk impact level.
        """
        summary: Dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for s in suggestions:
            impact = s.risk_impact if s.risk_impact in summary else "medium"
            summary[impact] += 1
        return summary

    @staticmethod
    def _compute_status_summary(
        suggestions: List[RedlineSuggestion],
    ) -> Dict[str, int]:
        """Compute status distribution.

        Args:
            suggestions: List of suggestions.

        Returns:
            Dict with counts per status.
        """
        summary: Dict[str, int] = {
            "pending": 0,
            "accepted": 0,
            "rejected": 0,
            "modified": 0,
            "superseded": 0,
        }
        for s in suggestions:
            status = s.status if s.status in summary else "pending"
            summary[status] += 1
        return summary

    @staticmethod
    def _compute_clause_type_distribution(
        suggestions: List[RedlineSuggestion],
    ) -> Dict[str, int]:
        """Compute clause type distribution.

        Args:
            suggestions: List of suggestions.

        Returns:
            Dict mapping clause type names to counts.
        """
        distribution: Dict[str, int] = {}
        for s in suggestions:
            ct = s.clause_type.value.replace("_", " ").title()
            distribution[ct] = distribution.get(ct, 0) + 1
        return dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))

    @staticmethod
    def _format_risk_distribution(
        risk_summary: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """Format risk distribution for PDF rendering.

        Args:
            risk_summary: Risk distribution dict.

        Returns:
            List of formatted risk items.
        """
        total = sum(risk_summary.values()) or 1
        return [
            {
                "level": level,
                "count": count,
                "percentage": round(count / total * 100, 1),
                "color": _get_risk_color(level),
            }
            for level, count in risk_summary.items()
        ]

    @staticmethod
    def _generate_overview(
        suggestions: List[RedlineSuggestion],
    ) -> List[Dict[str, Any]]:
        """Generate a table-of-contents overview of suggestions.

        Args:
            suggestions: List of suggestions.

        Returns:
            List of suggestion overview entries.
        """
        overview = []
        for idx, s in enumerate(suggestions, 1):
            overview.append({
                "number": idx,
                "suggestion_id": s.suggestion_id,
                "clause_type": s.clause_type.value.replace("_", " ").title(),
                "risk_impact": s.risk_impact,
                "change_type": s.change_type.title(),
                "confidence": round(s.confidence * 100, 0),
                "status": s.status,
                "attorney_review": s.attorney_review_required,
                "preview": s.original_text[:100] + "..." if len(s.original_text) > 100 else s.original_text,
            })
        return overview

    @staticmethod
    def _generate_recommendations(
        suggestions: List[RedlineSuggestion],
        risk_summary: Dict[str, int],
    ) -> List[str]:
        """Generate high-level recommendations based on analysis.

        Args:
            suggestions: List of suggestions.
            risk_summary: Risk distribution.

        Returns:
            List of recommendation strings.
        """
        recommendations: List[str] = []

        total = len(suggestions)
        critical_high = risk_summary.get("critical", 0) + risk_summary.get("high", 0)

        if critical_high > 0:
            recommendations.append(
                f"Immediate attention required: {critical_high} of {total} suggestions "
                f"are classified as critical or high risk. These should be reviewed by "
                f"legal counsel before proceeding."
            )

        attorney_review = sum(1 for s in suggestions if s.attorney_review_required)
        if attorney_review > 0:
            recommendations.append(
                f"{attorney_review} of {total} suggestions require attorney review due "
                f"to legal complexity or jurisdiction-specific considerations."
            )

        pending = sum(1 for s in suggestions if s.status == "pending")
        if pending > 0:
            recommendations.append(
                f"{pending} suggestions are pending review. It is recommended to "
                f"review all suggestions before finalizing the contract."
            )

        if total == 0:
            recommendations.append(
                "No redline suggestions were generated for this contract."
            )

        if not recommendations:
            recommendations.append(
                "All suggestions have been reviewed. No further action required."
            )

        return recommendations


def _get_risk_color(level: str) -> str:
    """Get a hex color string for a risk level.

    Args:
        level: The risk level string.

    Returns:
        Hex color string (e.g., "#FF0000").
    """
    colors = {
        "critical": "#FF0000",
        "high": "#FF6600",
        "medium": "#FFD700",
        "low": "#00AA00",
    }
    return colors.get(level, "#808080")
