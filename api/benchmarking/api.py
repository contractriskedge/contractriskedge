"""Benchmark scoring API endpoint.

Provides the GET /benchmarks/score endpoint for scoring individual
clauses against the benchmark corpus.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import (
    BenchmarkClause,
    BenchmarkScore,
    BenchmarkSegment,
    ContractType,
    IndustryCategory,
    CounterpartyType,
)
from .scoring_engine import ScoringEngine
from .segmentation import SegmentationEngine
from .classification import ClauseClassifier

logger = logging.getLogger(__name__)


class BenchmarkAPI:
    """Benchmark scoring API for clause evaluation.

    Provides the scoring logic behind the GET /benchmarks/score endpoint,
    combining segmentation, distribution scoring, and classification.

    Usage:
        api = BenchmarkAPI(scoring_engine, segmentation_engine)
        result = api.score_clause(
            clause_text="...",
            clause_type="liability_caps",
            contract_type=ContractType.SaaS_AGREEMENT,
            industry=IndustryCategory.TECHNOLOGY,
        )
    """

    def __init__(
        self,
        scoring_engine: ScoringEngine,
        segmentation_engine: SegmentationEngine,
        classifier: Optional[ClauseClassifier] = None,
        corpus_clauses: Optional[List[BenchmarkClause]] = None,
    ) -> None:
        """Initialize the benchmark API.

        Args:
            scoring_engine: The scoring engine with pre-computed distributions.
            segmentation_engine: The segmentation engine for segment matching.
            classifier: Optional clause classifier.
            corpus_clauses: Optional list of corpus clauses for segment counting.
        """
        self._scoring_engine = scoring_engine
        self._segmentation_engine = segmentation_engine
        self._classifier = classifier or ClauseClassifier()
        self._corpus_clauses = corpus_clauses or []

    def score_clause(
        self,
        clause_text: str,
        clause_type: str,
        contract_type: Optional[ContractType] = None,
        industry: Optional[IndustryCategory] = None,
        counterparty_type: Optional[CounterpartyType] = None,
        deal_size_range: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        quality_score: Optional[float] = None,
    ) -> Optional[BenchmarkScore]:
        """Score a clause against the benchmark corpus.

        Args:
            clause_text: The clause text to score.
            clause_type: The type of clause.
            contract_type: Optional contract type for segmentation.
            industry: Optional industry for segmentation.
            counterparty_type: Optional counterparty type for segmentation.
            deal_size_range: Optional deal size range for segmentation.
            jurisdiction: Optional jurisdiction for segmentation.
            quality_score: Optional pre-computed quality score.

        Returns:
            BenchmarkScore with percentile, distribution, and classification,
            or None if no benchmark data is available.
        """
        # Find the best matching segment
        segment_result = self._segmentation_engine.find_segment(
            clause_type=clause_type,
            contract_type=contract_type,
            industry=industry,
            counterparty_type=counterparty_type,
            deal_size_range=deal_size_range,
            jurisdiction=jurisdiction,
            corpus_clauses=self._corpus_clauses,
        )

        segment = segment_result.segment

        # Score the clause
        score = self._scoring_engine.score_clause(
            clause_text=clause_text,
            clause_type=clause_type,
            segment=segment,
            segment_result=segment_result,
            clause_quality_score=quality_score,
        )

        if score is None:
            return None

        # Classify the score
        classification = self._classifier.classify(score)
        score.classification = classification.classification
        score.classification_confidence = classification.confidence

        return score

    def score_batch(
        self,
        clauses: List[Dict[str, Any]],
    ) -> List[Optional[BenchmarkScore]]:
        """Score multiple clauses in batch.

        Args:
            clauses: List of dicts with clause data. Each dict should
                    contain 'clause_text' and 'clause_type' at minimum.

        Returns:
            List of BenchmarkScore or None for each clause.
        """
        results: List[Optional[BenchmarkScore]] = []
        for clause_data in clauses:
            result = self.score_clause(
                clause_text=clause_data.get("clause_text", ""),
                clause_type=clause_data.get("clause_type", ""),
                contract_type=clause_data.get("contract_type"),
                industry=clause_data.get("industry"),
                counterparty_type=clause_data.get("counterparty_type"),
                deal_size_range=clause_data.get("deal_size_range"),
                jurisdiction=clause_data.get("jurisdiction"),
                quality_score=clause_data.get("quality_score"),
            )
            results.append(result)
        return results

    def get_available_segments(self) -> Dict[str, Any]:
        """Get information about available benchmark segments.

        Returns:
            Dict with segment information.
        """
        distributions = self._scoring_engine.get_all_distributions()

        return {
            "clause_types": list(distributions.keys()),
            "segment_count": len(distributions),
            "last_updated": (
                self._scoring_engine.last_precomputed.isoformat()
                if self._scoring_engine.last_precomputed
                else None
            ),
            "distributions": {
                ct: {
                    "count": d.count,
                    "mean": d.mean,
                    "median": d.median,
                    "p25": d.p25,
                    "p75": d.p75,
                }
                for ct, d in distributions.items()
            },
        }

    def get_clause_type_stats(
        self, clause_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific clause type.

        Args:
            clause_type: The clause type.

        Returns:
            Dict with statistics or None.
        """
        dist = self._scoring_engine.get_distribution(clause_type)
        if dist is None:
            return None

        return {
            "clause_type": clause_type,
            "sample_count": dist.count,
            "distribution": {
                "mean": dist.mean,
                "median": dist.median,
                "p25": dist.p25,
                "p75": dist.p75,
                "p05": dist.p05,
                "p95": dist.p95,
                "std_dev": dist.std_dev,
                "min": dist.min_value,
                "max": dist.max_value,
            },
            "classification_thresholds": {
                "favorable_above_p75": dist.p75,
                "unfavorable_below_p25": dist.p25,
            },
        }
