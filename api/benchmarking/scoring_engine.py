"""Nightly pre-computation of distribution stats + real-time percentile scoring.

Computes distribution statistics (P25, P50, P75) per clause type × segment
on a nightly basis, and provides real-time percentile scoring for individual
clauses against the pre-computed benchmarks.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .models import (
    BenchmarkClause,
    BenchmarkScore,
    BenchmarkSegment,
    DistributionStats,
    SegmentationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class PercentileScore:
    """Result of a percentile scoring operation."""

    percentile: float
    distribution_stats: DistributionStats
    segment: SegmentationResult
    classification: str
    classification_confidence: float


class ScoringEngine:
    """Benchmark scoring engine with pre-computed distributions.

    Pre-computes distribution statistics nightly for all clause type ×
    segment combinations, and provides real-time percentile scoring.

    Usage:
        engine = ScoringEngine()
        engine.precompute(corpus_clauses)
        score = engine.score_clause(clause_text, clause_type, segment)
    """

    def __init__(self) -> None:
        """Initialize the scoring engine."""
        self._distributions: Dict[str, DistributionStats] = {}
        self._last_precomputed: Optional[datetime] = None
        self._clause_scores: Dict[str, List[float]] = {}

    def precompute(
        self,
        clauses: List[BenchmarkClause],
    ) -> Dict[str, DistributionStats]:
        """Pre-compute distribution statistics for all clause types.

        Computes P05, P25, P50 (median), P75, P95, mean, std_dev,
        min, and max for each clause type's scores.

        Args:
            clauses: List of all benchmark clauses.

        Returns:
            Dict mapping clause type to its DistributionStats.
        """
        # Group clauses by type
        by_type: Dict[str, List[float]] = {}
        for clause in clauses:
            by_type.setdefault(clause.clause_type, []).append(
                clause.quality_score
            )

        distributions: Dict[str, DistributionStats] = {}
        for clause_type, scores in by_type.items():
            if len(scores) < 2:
                logger.warning(
                    "Too few samples for %s: %d (need >= 2)",
                    clause_type, len(scores),
                )
                continue

            arr = np.array(scores)
            distributions[clause_type] = DistributionStats(
                count=len(scores),
                mean=round(float(np.mean(arr)), 4),
                median=round(float(np.median(arr)), 4),
                p25=round(float(np.percentile(arr, 25)), 4),
                p75=round(float(np.percentile(arr, 75)), 4),
                p05=round(float(np.percentile(arr, 5)), 4),
                p95=round(float(np.percentile(arr, 95)), 4),
                std_dev=round(float(np.std(arr)), 4),
                min_value=round(float(np.min(arr)), 4),
                max_value=round(float(np.max(arr)), 4),
            )

        self._distributions = distributions
        self._last_precomputed = datetime.utcnow()
        self._clause_scores = by_type

        logger.info(
            "Pre-computed distributions for %d clause types",
            len(distributions),
        )

        return distributions

    def score_clause(
        self,
        clause_text: str,
        clause_type: str,
        segment: BenchmarkSegment,
        segment_result: SegmentationResult,
        clause_quality_score: Optional[float] = None,
    ) -> Optional[BenchmarkScore]:
        """Score a single clause against the pre-computed benchmarks.

        Args:
            clause_text: The clause text to score.
            clause_type: The type of clause.
            segment: The segment definition.
            segment_result: The segmentation result.
            clause_quality_score: Optional pre-computed quality score.
                                 If not provided, a simple score is computed.

        Returns:
            BenchmarkScore with percentile and classification, or None
            if no benchmark data is available.
        """
        # Compute or use quality score
        if clause_quality_score is None:
            clause_quality_score = self._compute_simple_score(clause_text)

        # Get distribution for this clause type
        dist = self._distributions.get(clause_type)
        if dist is None or dist.count < 2:
            logger.warning(
                "No distribution data for clause type: %s", clause_type
            )
            return None

        # Compute percentile
        scores = self._clause_scores.get(clause_type, [])
        percentile = self._compute_percentile(clause_quality_score, scores)

        # Classify
        classification, confidence = self._classify_score(
            clause_quality_score, dist
        )

        return BenchmarkScore(
            clause_id="",
            clause_type=clause_type,
            percentile=round(percentile, 2),
            distribution_stats=dist,
            segment=segment_result,
            classification=classification,
            classification_confidence=round(confidence, 4),
            similar_clause_count=dist.count,
        )

    @staticmethod
    def _compute_simple_score(text: str) -> float:
        """Compute a simple quality score for a clause.

        Used when no pre-computed quality score is available.

        Args:
            text: The clause text.

        Returns:
            Score between 0 and 1.
        """
        if not text.strip():
            return 0.0

        score = 0.5

        # Length bonus
        if len(text) > 200:
            score += 0.1
        if len(text) > 500:
            score += 0.1

        # Legal language bonus
        legal_terms = [
            "shall", "indemnify", "notwithstanding", "pursuant",
            "hereunder", "thereof", "warrant", "represent",
        ]
        found = sum(1 for t in legal_terms if t in text.lower())
        score += min(0.2, found * 0.03)

        # Structure bonus
        if '(' in text and ')' in text:
            score += 0.05
        if '\n\n' in text:
            score += 0.05

        return min(1.0, max(0.0, score))

    @staticmethod
    def _compute_percentile(
        score: float,
        scores: List[float],
    ) -> float:
        """Compute the percentile rank of a score within a distribution.

        Args:
            score: The score to rank.
            scores: List of scores in the distribution.

        Returns:
            Percentile between 0 and 100.
        """
        if not scores:
            return 50.0

        count_below = sum(1 for s in scores if s < score)
        count_equal = sum(1 for s in scores if s == score)

        percentile = (count_below + 0.5 * count_equal) / len(scores) * 100.0
        return min(100.0, max(0.0, percentile))

    @staticmethod
    def _classify_score(
        score: float,
        dist: DistributionStats,
    ) -> Tuple[str, float]:
        """Classify a score as favorable, at_market, or unfavorable.

        Uses percentile-based classification:
        - Favorable: score > P75 (top quartile)
        - At market: score between P25 and P75 (interquartile range)
        - Unfavorable: score < P25 (bottom quartile)

        Args:
            score: The score to classify.
            dist: Distribution statistics.

        Returns:
            Tuple of (classification, confidence).
        """
        if score > dist.p75:
            confidence = min(1.0, (score - dist.p75) / (dist.max_value - dist.p75 + 0.001))
            return "favorable", round(confidence, 4)
        elif score < dist.p25:
            confidence = min(1.0, (dist.p25 - score) / (dist.p25 - dist.min_value + 0.001))
            return "unfavorable", round(confidence, 4)
        else:
            # At market — confidence based on proximity to median
            distance_from_median = abs(score - dist.median)
            iqr = dist.p75 - dist.p25
            if iqr > 0:
                confidence = max(0.5, 1.0 - (distance_from_median / iqr))
            else:
                confidence = 0.7
            return "at_market", round(confidence, 4)

    def get_distribution(
        self, clause_type: str
    ) -> Optional[DistributionStats]:
        """Get pre-computed distribution for a clause type.

        Args:
            clause_type: The clause type.

        Returns:
            DistributionStats or None if not computed.
        """
        return self._distributions.get(clause_type)

    def get_all_distributions(self) -> Dict[str, DistributionStats]:
        """Get all pre-computed distributions.

        Returns:
            Dict of clause type → DistributionStats.
        """
        return dict(self._distributions)

    @property
    def last_precomputed(self) -> Optional[datetime]:
        """Get the timestamp of the last pre-computation.

        Returns:
            Datetime of last pre-computation, or None.
        """
        return self._last_precomputed
