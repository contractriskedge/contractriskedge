"""Benchmark confidence scoring + segment reliability indicators (V2-033).

Computes confidence scores and reliability indicators for benchmark
data segments, enabling the UI to show data quality and trustworthiness.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfidence:
    """Confidence score for a benchmark segment."""

    segment_id: str
    segment_type: str  # industry, deal_size, jurisdiction, contract_type
    segment_name: str
    sample_size: int
    confidence_score: float  # 0.0 - 1.0
    reliability_label: str  # very_high, high, medium, low, very_low
    margin_of_error: float
    data_freshness_days: int
    freshness_label: str  # fresh, acceptable, stale, outdated
    variance: float
    outlier_count: int
    recommended_for_reporting: bool
    caveats: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "segment_type": self.segment_type,
            "segment_name": self.segment_name,
            "sample_size": self.sample_size,
            "confidence_score": round(self.confidence_score, 3),
            "reliability_label": self.reliability_label,
            "margin_of_error": round(self.margin_of_error, 3),
            "data_freshness_days": self.data_freshness_days,
            "freshness_label": self.freshness_label,
            "variance": round(self.variance, 3),
            "outlier_count": self.outlier_count,
            "recommended_for_reporting": self.recommended_for_reporting,
            "caveats": self.caveats,
        }


class BenchmarkConfidenceScorer:
    """Computes confidence scores and reliability for benchmark segments.

    Evaluates benchmark data quality based on sample size, variance,
    data freshness, and outlier detection.

    Usage:
        scorer = BenchmarkConfidenceScorer()
        confidence = scorer.compute_confidence(segment_data)
        indicators = scorer.get_reliability_indicators(segment_id)
    """

    def __init__(self) -> None:
        """Initialize the confidence scorer."""
        self._confidence_cache: Dict[str, BenchmarkConfidence] = {}

        # Confidence thresholds
        self._sample_size_thresholds = {
            "very_high": 1000,
            "high": 500,
            "medium": 100,
            "low": 30,
            "very_low": 0,
        }

        # Freshness thresholds (days)
        self._freshness_thresholds = {
            "fresh": 30,
            "acceptable": 90,
            "stale": 180,
            "outdated": 365,
        }

        # Reliability thresholds
        self._reliability_thresholds = {
            "very_high": 0.9,
            "high": 0.75,
            "medium": 0.5,
            "low": 0.25,
            "very_low": 0.0,
        }

    def compute_confidence(
        self,
        segment_id: str,
        segment_type: str,
        segment_name: str,
        sample_size: int,
        values: List[float],
        data_timestamp: Optional[str] = None,
        variance: Optional[float] = None,
    ) -> BenchmarkConfidence:
        """Compute confidence score for a benchmark segment.

        Args:
            segment_id: Unique segment identifier.
            segment_type: Type of segment.
            segment_name: Human-readable name.
            sample_size: Number of data points.
            values: List of benchmark values.
            data_timestamp: ISO timestamp of last data update.
            variance: Pre-computed variance (computed if not provided).

        Returns:
            BenchmarkConfidence with score and indicators.
        """
        # Compute variance if not provided
        if variance is None and values:
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
        elif variance is None:
            variance = 0.0

        # Sample size score (0-1)
        sample_score = self._score_sample_size(sample_size)

        # Variance score (0-1) - lower variance = higher confidence
        variance_score = max(0.0, 1.0 - (variance / 10.0)) if variance > 0 else 1.0

        # Freshness score (0-1)
        freshness_days = self._compute_freshness_days(data_timestamp)
        freshness_score = self._score_freshness(freshness_days)

        # Outlier detection
        outlier_count, cleaned_values = self._detect_outliers(values)

        # Overall confidence score (weighted average)
        confidence_score = (
            sample_score * 0.4 +
            variance_score * 0.25 +
            freshness_score * 0.25 +
            (1.0 - (outlier_count / max(len(values), 1))) * 0.1
        )
        confidence_score = max(0.0, min(1.0, confidence_score))

        # Determine labels
        reliability_label = self._get_reliability_label(confidence_score)
        freshness_label = self._get_freshness_label(freshness_days)

        # Margin of error (approximate)
        margin_of_error = self._compute_margin_of_error(variance, sample_size)

        # Generate caveats
        caveats = self._generate_caveats(
            sample_size, variance, freshness_days, outlier_count
        )

        confidence = BenchmarkConfidence(
            segment_id=segment_id,
            segment_type=segment_type,
            segment_name=segment_name,
            sample_size=sample_size,
            confidence_score=confidence_score,
            reliability_label=reliability_label,
            margin_of_error=margin_of_error,
            data_freshness_days=freshness_days,
            freshness_label=freshness_label,
            variance=variance,
            outlier_count=outlier_count,
            recommended_for_reporting=confidence_score >= 0.5,
            caveats=caveats,
        )

        self._confidence_cache[segment_id] = confidence
        return confidence

    def _score_sample_size(self, sample_size: int) -> float:
        """Score based on sample size.

        Args:
            sample_size: Number of data points.

        Returns:
            Score 0-1.
        """
        if sample_size >= self._sample_size_thresholds["very_high"]:
            return 1.0
        elif sample_size >= self._sample_size_thresholds["high"]:
            return 0.9
        elif sample_size >= self._sample_size_thresholds["medium"]:
            return 0.6
        elif sample_size >= self._sample_size_thresholds["low"]:
            return 0.3
        else:
            return 0.1

    def _compute_freshness_days(self, timestamp: Optional[str]) -> int:
        """Compute days since last data update.

        Args:
            timestamp: ISO timestamp.

        Returns:
            Days since update.
        """
        if not timestamp:
            return 999
        try:
            updated = datetime.fromisoformat(timestamp)
            return (datetime.utcnow() - updated).days
        except (ValueError, TypeError):
            return 999

    def _score_freshness(self, days: int) -> float:
        """Score based on data freshness.

        Args:
            days: Days since last update.

        Returns:
            Score 0-1.
        """
        if days <= self._freshness_thresholds["fresh"]:
            return 1.0
        elif days <= self._freshness_thresholds["acceptable"]:
            return 0.8
        elif days <= self._freshness_thresholds["stale"]:
            return 0.5
        elif days <= self._freshness_thresholds["outdated"]:
            return 0.2
        else:
            return 0.0

    def _get_reliability_label(self, score: float) -> str:
        """Get reliability label from score.

        Args:
            score: Confidence score.

        Returns:
            Reliability label.
        """
        for label, threshold in sorted(
            self._reliability_thresholds.items(), key=lambda x: -x[1]
        ):
            if score >= threshold:
                return label
        return "very_low"

    def _get_freshness_label(self, days: int) -> str:
        """Get freshness label.

        Args:
            days: Days since update.

        Returns:
            Freshness label.
        """
        if days <= self._freshness_thresholds["fresh"]:
            return "fresh"
        elif days <= self._freshness_thresholds["acceptable"]:
            return "acceptable"
        elif days <= self._freshness_thresholds["stale"]:
            return "stale"
        else:
            return "outdated"

    def _detect_outliers(
        self,
        values: List[float],
    ) -> tuple:
        """Detect outliers using IQR method.

        Args:
            values: List of values.

        Returns:
            Tuple of (outlier_count, cleaned_values).
        """
        if len(values) < 4:
            return 0, values

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = [v for v in values if v < lower_bound or v > upper_bound]
        cleaned = [v for v in values if lower_bound <= v <= upper_bound]

        return len(outliers), cleaned

    def _compute_margin_of_error(
        self,
        variance: float,
        sample_size: int,
    ) -> float:
        """Compute approximate margin of error.

        Args:
            variance: Data variance.
            sample_size: Sample size.

        Returns:
            Margin of error.
        """
        if sample_size < 2:
            return 1.0
        std_dev = variance ** 0.5
        # 95% confidence interval approximation
        return 1.96 * (std_dev / (sample_size ** 0.5))

    def _generate_caveats(
        self,
        sample_size: int,
        variance: float,
        freshness_days: int,
        outlier_count: int,
    ) -> List[str]:
        """Generate caveats about data quality.

        Args:
            sample_size: Sample size.
            variance: Data variance.
            freshness_days: Days since update.
            outlier_count: Number of outliers.

        Returns:
            List of caveat strings.
        """
        caveats = []

        if sample_size < self._sample_size_thresholds["medium"]:
            caveats.append(f"Small sample size ({sample_size} data points) - interpret with caution")
        if variance > 5.0:
            caveats.append("High variance in segment data - results may not be representative")
        if freshness_days > self._freshness_thresholds["acceptable"]:
            caveats.append(f"Data is {freshness_days} days old - consider refreshing")
        if outlier_count > 0:
            caveats.append(f"{outlier_count} outlier(s) detected and excluded from scoring")
        if sample_size < 10:
            caveats.append("Very limited data - not recommended for reporting")

        return caveats

    def get_confidence(self, segment_id: str) -> Optional[BenchmarkConfidence]:
        """Get cached confidence for a segment.

        Args:
            segment_id: Segment identifier.

        Returns:
            BenchmarkConfidence or None.
        """
        return self._confidence_cache.get(segment_id)

    def get_reliability_indicators(
        self,
        segment_id: str,
    ) -> Dict[str, Any]:
        """Get reliability indicators for UI display.

        Args:
            segment_id: Segment identifier.

        Returns:
            Dict with reliability indicators.
        """
        confidence = self._confidence_cache.get(segment_id)
        if not confidence:
            return {
                "available": False,
                "message": "No confidence data for this segment",
            }

        return {
            "available": True,
            "confidence_score": confidence.confidence_score,
            "reliability_label": confidence.reliability_label,
            "freshness_label": confidence.freshness_label,
            "data_freshness_days": confidence.data_freshness_days,
            "sample_size": confidence.sample_size,
            "margin_of_error": confidence.margin_of_error,
            "recommended_for_reporting": confidence.recommended_for_reporting,
            "caveats": confidence.caveats,
            "color": self._get_reliability_color(confidence.reliability_label),
            "icon": self._get_reliability_icon(confidence.reliability_label),
        }

    def _get_reliability_color(self, label: str) -> str:
        """Get display color for reliability label.

        Args:
            label: Reliability label.

        Returns:
            CSS color string.
        """
        colors = {
            "very_high": "#16A34A",  # green
            "high": "#22C55E",       # light green
            "medium": "#EAB308",     # yellow
            "low": "#F97316",        # orange
            "very_low": "#DC2626",   # red
        }
        return colors.get(label, "#6B7280")

    def _get_reliability_icon(self, label: str) -> str:
        """Get icon name for reliability label.

        Args:
            label: Reliability label.

        Returns:
            Icon name string.
        """
        icons = {
            "very_high": "shield-check",
            "high": "shield",
            "medium": "alert-triangle",
            "low": "alert-circle",
            "very_low": "x-circle",
        }
        return icons.get(label, "help-circle")
