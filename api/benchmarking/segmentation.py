"""Segmentation hierarchy: exact match → partial match → general commercial fallback.

Implements a hierarchical segmentation strategy for benchmark comparison
that progressively broadens the matching criteria to ensure statistically
meaningful comparisons even for niche segments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    BenchmarkClause,
    BenchmarkSegment,
    SegmentationResult,
    ContractType,
    IndustryCategory,
    CounterpartyType,
)

logger = logging.getLogger(__name__)

# Minimum number of clauses required for a statistically valid segment
MIN_SEGMENT_SIZE = 10


@dataclass
class SegmentHierarchy:
    """Defines the hierarchy of segment fallback levels."""

    levels: List[str] = field(default_factory=lambda: [
        "exact",
        "partial",
        "general_commercial",
    ])


class SegmentationEngine:
    """Hierarchical segmentation for benchmark matching.

    Implements a 3-level fallback hierarchy:
    1. Exact match: clause_type + contract_type + industry + counterparty + deal_size
    2. Partial match: clause_type + contract_type + industry (drop counterparty + deal_size)
    3. General commercial fallback: clause_type only

    Usage:
        engine = SegmentationEngine()
        result = engine.find_segment(clause, corpus_clauses)
        matching = engine.get_matching_clauses(result, corpus_clauses)
    """

    def __init__(self, min_segment_size: int = MIN_SEGMENT_SIZE) -> None:
        """Initialize the segmentation engine.

        Args:
            min_segment_size: Minimum clauses needed for a valid segment.
        """
        self._min_segment_size = min_segment_size

    def find_segment(
        self,
        clause_type: str,
        contract_type: Optional[ContractType] = None,
        industry: Optional[IndustryCategory] = None,
        counterparty_type: Optional[CounterpartyType] = None,
        deal_size_range: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        corpus_clauses: Optional[List[BenchmarkClause]] = None,
    ) -> SegmentationResult:
        """Find the best matching segment using hierarchical fallback.

        Tries exact match first, then partial, then general commercial.

        Args:
            clause_type: The clause type.
            contract_type: Optional contract type.
            industry: Optional industry.
            counterparty_type: Optional counterparty type.
            deal_size_range: Optional deal size range.
            jurisdiction: Optional jurisdiction.
            corpus_clauses: Optional list to check counts against.

        Returns:
            SegmentationResult with the best matching segment.
        """
        fallback_path: List[str] = []

        # Level 1: Exact match
        segment = BenchmarkSegment(
            clause_type=clause_type,
            contract_type=contract_type,
            industry=industry,
            counterparty_type=counterparty_type,
            deal_size_range=deal_size_range,
            jurisdiction=jurisdiction,
        )
        count = self._count_matching(segment, corpus_clauses)
        if count >= self._min_segment_size:
            return SegmentationResult(
                segment=segment,
                matching_clause_count=count,
                match_type="exact",
                fallback_path=fallback_path,
            )

        fallback_path.append(f"exact({count} matches)")

        # Level 2: Partial match (drop counterparty and deal_size)
        segment = BenchmarkSegment(
            clause_type=clause_type,
            contract_type=contract_type,
            industry=industry,
            jurisdiction=jurisdiction,
        )
        count = self._count_matching(segment, corpus_clauses)
        if count >= self._min_segment_size:
            return SegmentationResult(
                segment=segment,
                matching_clause_count=count,
                match_type="partial",
                fallback_path=fallback_path,
            )

        fallback_path.append(f"partial({count} matches)")

        # Level 3: General commercial fallback (clause type only)
        segment = BenchmarkSegment(
            clause_type=clause_type,
        )
        count = self._count_matching(segment, corpus_clauses)
        fallback_path.append(f"general_commercial({count} matches)")

        return SegmentationResult(
            segment=segment,
            matching_clause_count=count,
            match_type="general_fallback",
            fallback_path=fallback_path,
        )

    @staticmethod
    def _count_matching(
        segment: BenchmarkSegment,
        corpus_clauses: Optional[List[BenchmarkClause]],
    ) -> int:
        """Count clauses matching a segment definition.

        Args:
            segment: The segment to match.
            corpus_clauses: List of corpus clauses.

        Returns:
            Number of matching clauses.
        """
        if corpus_clauses is None:
            return 0

        count = 0
        for clause in corpus_clauses:
            if clause.clause_type != segment.clause_type:
                continue
            if segment.contract_type and clause.contract_type != segment.contract_type:
                continue
            if segment.industry and clause.industry != segment.industry:
                continue
            if segment.counterparty_type and clause.counterparty_type != segment.counterparty_type:
                continue
            if segment.deal_size_range and clause.deal_size_range != segment.deal_size_range:
                continue
            if segment.jurisdiction and clause.jurisdiction != segment.jurisdiction:
                continue
            count += 1

        return count

    def get_matching_clauses(
        self,
        segment_result: SegmentationResult,
        corpus_clauses: List[BenchmarkClause],
    ) -> List[BenchmarkClause]:
        """Get all corpus clauses matching a segment result.

        Args:
            segment_result: The segmentation result.
            corpus_clauses: Full list of corpus clauses.

        Returns:
            List of matching BenchmarkClause objects.
        """
        segment = segment_result.segment
        matching: List[BenchmarkClause] = []

        for clause in corpus_clauses:
            if clause.clause_type != segment.clause_type:
                continue
            if segment.contract_type and clause.contract_type != segment.contract_type:
                continue
            if segment.industry and clause.industry != segment.industry:
                continue
            if segment.counterparty_type and clause.counterparty_type != segment.counterparty_type:
                continue
            if segment.deal_size_range and clause.deal_size_range != segment.deal_size_range:
                continue
            if segment.jurisdiction and clause.jurisdiction != segment.jurisdiction:
                continue
            matching.append(clause)

        return matching

    def segment_corpus(
        self,
        corpus_clauses: List[BenchmarkClause],
    ) -> Dict[str, List[BenchmarkClause]]:
        """Segment the entire corpus by clause type.

        Args:
            corpus_clauses: Full list of corpus clauses.

        Returns:
            Dict mapping clause type to list of clauses.
        """
        segments: Dict[str, List[BenchmarkClause]] = {}
        for clause in corpus_clauses:
            segments.setdefault(clause.clause_type, []).append(clause)
        return segments
