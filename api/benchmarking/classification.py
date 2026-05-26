"""Favorable/at-market/unfavorable classification per clause type.

Classifies clauses as favorable, at-market, or unfavorable based on
their percentile rank within the benchmark distribution for their
clause type and segment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import BenchmarkScore, DistributionStats

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of a clause classification."""

    classification: str  # favorable, at_market, unfavorable
    confidence: float
    percentile: float
    rationale: str
    comparable_count: int


class ClauseClassifier:
    """Classifies clauses as favorable, at-market, or unfavorable.

    Uses percentile-based thresholds with configurable boundaries
    for each classification tier.

    Usage:
        classifier = ClauseClassifier()
        result = classifier.classify(score)
    """

    # Default percentile thresholds
    FAVORABLE_THRESHOLD = 75.0  # Top quartile
    UNFAVORABLE_THRESHOLD = 25.0  # Bottom quartile

    def __init__(
        self,
        favorable_threshold: float = FAVORABLE_THRESHOLD,
        unfavorable_threshold: float = UNFAVORABLE_THRESHOLD,
    ) -> None:
        """Initialize the classifier.

        Args:
            favorable_threshold: Percentile above which is favorable.
            unfavorable_threshold: Percentile below which is unfavorable.
        """
        self._favorable_threshold = favorable_threshold
        self._unfavorable_threshold = unfavorable_threshold

    def classify(self, score: BenchmarkScore) -> ClassificationResult:
        """Classify a benchmark score.

        Args:
            score: The benchmark score to classify.

        Returns:
            ClassificationResult with classification and rationale.
        """
        percentile = score.percentile
        dist = score.distribution_stats

        if percentile >= self._favorable_threshold:
            classification = "favorable"
            confidence = self._compute_confidence(
                percentile, self._favorable_threshold, 100.0
            )
            rationale = (
                f"Clause ranks at P{percentile:.0f} which is above the "
                f"P{self._favorable_threshold:.0f} threshold for favorable "
                f"classification. This clause is in the top "
                f"{100 - percentile:.0f}% of the benchmark distribution."
            )

        elif percentile <= self._unfavorable_threshold:
            classification = "unfavorable"
            confidence = self._compute_confidence(
                percentile, 0.0, self._unfavorable_threshold
            )
            rationale = (
                f"Clause ranks at P{percentile:.0f} which is below the "
                f"P{self._unfavorable_threshold:.0f} threshold for unfavorable "
                f"classification. This clause is in the bottom "
                f"{percentile:.0f}% of the benchmark distribution."
            )

        else:
            classification = "at_market"
            # Confidence based on proximity to median
            distance_to_favorable = self._favorable_threshold - percentile
            distance_to_unfavorable = percentile - self._unfavorable_threshold
            max_distance = self._favorable_threshold - self._unfavorable_threshold
            if max_distance > 0:
                proximity_to_center = 1.0 - (
                    abs(percentile - 50.0) / 50.0
                )
                confidence = max(0.5, proximity_to_center)
            else:
                confidence = 0.7

            rationale = (
                f"Clause ranks at P{percentile:.0f} which is within the market "
                f"range (P{self._unfavorable_threshold:.0f}-"
                f"P{self._favorable_threshold:.0f}). This clause is consistent "
                f"with market standards for this segment."
            )

        return ClassificationResult(
            classification=classification,
            confidence=round(confidence, 4),
            percentile=percentile,
            rationale=rationale,
            comparable_count=dist.count,
        )

    def _compute_confidence(
        self, percentile: float, lower_bound: float, upper_bound: float
    ) -> float:
        """Compute confidence in a classification.

        Confidence increases with distance from the threshold boundary.

        Args:
            percentile: The percentile value.
            lower_bound: Lower bound of the range.
            upper_bound: Upper bound of the range.

        Returns:
            Confidence between 0 and 1.
        """
        range_size = upper_bound - lower_bound
        if range_size <= 0:
            return 0.5

        # Distance from the nearest threshold boundary
        if percentile >= 50.0:
            distance = percentile - self._favorable_threshold
        else:
            distance = self._unfavorable_threshold - percentile

        # Normalize by range
        normalized_distance = abs(distance) / range_size
        return min(1.0, max(0.5, 0.5 + normalized_distance))

    def classify_batch(
        self,
        scores: List[BenchmarkScore],
    ) -> List[ClassificationResult]:
        """Classify multiple benchmark scores.

        Args:
            scores: List of benchmark scores.

        Returns:
            List of classification results.
        """
        return [self.classify(score) for score in scores]

    def get_distribution_summary(
        self,
        dist: DistributionStats,
    ) -> Dict[str, Any]:
        """Get a human-readable summary of a distribution.

        Args:
            dist: Distribution statistics.

        Returns:
            Dict with summary information.
        """
        return {
            "sample_size": dist.count,
            "range": f"{dist.min_value:.3f} - {dist.max_value:.3f}",
            "central_tendency": {
                "mean": dist.mean,
                "median": dist.median,
            },
            "spread": {
                "p25": dist.p25,
                "p75": dist.p75,
                "std_dev": dist.std_dev,
            },
            "classification_thresholds": {
                "favorable_above": f"P{self._favorable_threshold:.0f} ({self._percentile_to_value(dist, self._favorable_threshold):.3f})",
                "unfavorable_below": f"P{self._unfavorable_threshold:.0f} ({self._percentile_to_value(dist, self._unfavorable_threshold):.3f})",
            },
        }

    @staticmethod
    def _percentile_to_value(
        dist: DistributionStats, percentile: float
    ) -> float:
        """Estimate the value at a given percentile.

        Uses linear interpolation between known percentiles.

        Args:
            dist: Distribution statistics.
            percentile: Target percentile.

        Returns:
            Estimated value at the given percentile.
        """
        if percentile <= 5:
            return dist.p05
        elif percentile <= 25:
            ratio = (percentile - 5) / (25 - 5)
            return dist.p05 + ratio * (dist.p25 - dist.p05)
        elif percentile <= 50:
            ratio = (percentile - 25) / (50 - 25)
            return dist.p25 + ratio * (dist.median - dist.p25)
        elif percentile <= 75:
            ratio = (percentile - 50) / (75 - 50)
            return dist.median + ratio * (dist.p75 - dist.median)
        elif percentile <= 95:
            ratio = (percentile - 75) / (95 - 75)
            return dist.p75 + ratio * (dist.p95 - dist.p75)
        else:
            return dist.p95
