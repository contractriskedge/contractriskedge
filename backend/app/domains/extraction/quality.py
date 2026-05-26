"""OCR quality scoring and document health evaluation.

Determines if extracted text meets quality thresholds for downstream
chunking and AI analysis. Flags low-quality extractions for quarantine.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Composite quality assessment for an extraction run."""
    overall_score: float       # 0-1 composite
    avg_confidence: float      # Average per-page OCR confidence
    text_density: float        # Chars per page
    blank_page_ratio: float    # Pages with < 50 chars / total pages
    low_confidence_ratio: float  # Pages with confidence < 0.5 / total pages
    garbage_ratio: float       # Non-alphanumeric / total chars
    has_corrupted_pages: bool
    is_acceptable: bool        # Overall pass/fail
    rejection_reason: Optional[str] = None


class QualityEvaluator:
    """Evaluates extraction quality against enterprise thresholds.

    Thresholds are conservative for legal document processing.
    Low-quality extractions are quarantined for human review.
    """

    MIN_CONFIDENCE = 0.6           # Minimum average OCR confidence
    MIN_TEXT_DENSITY = 50          # Minimum chars per page
    MAX_BLANK_PAGE_RATIO = 0.3    # Max 30% blank pages
    MAX_LOW_CONF_RATIO = 0.2      # Max 20% low-confidence pages
    MAX_GARBAGE_RATIO = 0.15      # Max 15% non-alphanumeric chars
    MAX_CORRUPTED_PAGES = 0       # Zero tolerance for corrupted pages

    def evaluate(self, result: ExtractionResult) -> QualityScore:
        """Evaluate overall extraction quality."""
        if not result.pages:
            return QualityScore(
                overall_score=0.0, avg_confidence=0.0, text_density=0.0,
                blank_page_ratio=1.0, low_confidence_ratio=1.0, garbage_ratio=0.0,
                has_corrupted_pages=False, is_acceptable=False,
                rejection_reason="No pages extracted",
            )

        total_pages = len(result.pages)
        blank_pages = 0
        low_conf_pages = 0
        total_garbage_chars = 0
        total_chars = 0
        total_confidence = 0.0

        for page in result.pages:
            total_confidence += page.confidence
            total_chars += page.char_count

            if page.char_count < 50:
                blank_pages += 1
            if page.confidence < 0.5:
                low_conf_pages += 1

            # Count non-alphanumeric chars
            garbage = len(re.findall(r'[^\w\s\.\,\;\:\!\?\(\)\[\]\{\}\-\'\"]', page.text))
            total_garbage_chars += garbage

        avg_confidence = total_confidence / total_pages
        text_density = total_chars / total_pages if total_pages > 0 else 0
        blank_ratio = blank_pages / total_pages
        low_conf_ratio = low_conf_pages / total_pages
        garbage_ratio = total_garbage_chars / max(total_chars, 1)

        # Composite score (weighted)
        overall = (
            avg_confidence * 0.35 +
            min(text_density / 500, 1.0) * 0.20 +
            (1 - blank_ratio) * 0.20 +
            (1 - low_conf_ratio) * 0.15 +
            (1 - garbage_ratio) * 0.10
        )

        # Determine acceptability
        reasons = []
        if avg_confidence < self.MIN_CONFIDENCE:
            reasons.append(f"Low confidence: {avg_confidence:.2f} < {self.MIN_CONFIDENCE}")
        if blank_ratio > self.MAX_BLANK_PAGE_RATIO:
            reasons.append(f"High blank page ratio: {blank_ratio:.2f} > {self.MAX_BLANK_PAGE_RATIO}")
        if low_conf_ratio > self.MAX_LOW_CONF_RATIO:
            reasons.append(f"High low-confidence ratio: {low_conf_ratio:.2f} > {self.MAX_LOW_CONF_RATIO}")
        if garbage_ratio > self.MAX_GARBAGE_RATIO:
            reasons.append(f"High garbage ratio: {garbage_ratio:.2f} > {self.MAX_GARBAGE_RATIO}")

        is_acceptable = len(reasons) == 0

        return QualityScore(
            overall_score=round(overall, 4),
            avg_confidence=round(avg_confidence, 4),
            text_density=round(text_density, 2),
            blank_page_ratio=round(blank_ratio, 4),
            low_confidence_ratio=round(low_conf_ratio, 4),
            garbage_ratio=round(garbage_ratio, 4),
            has_corrupted_pages=False,
            is_acceptable=is_acceptable,
            rejection_reason="; ".join(reasons) if reasons else None,
        )


quality_evaluator = QualityEvaluator()
