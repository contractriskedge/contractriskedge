"""Pipeline for benchmark corpus ingestion: receive → anonymize → classify → extract → store.

Implements the full ingestion pipeline for adding contract clauses to
the benchmark corpus with PII anonymization, quality filtering, and
semantic deduplication.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .models import (
    BenchmarkClause,
    BenchmarkCorpusMetadata,
    ContractType,
    IndustryCategory,
    CounterpartyType,
)
from .anonymizer import PIIAnonymizer, AnonymizationResult
from .quality_filter import QualityFilter, QualityScore
from .deduplicator import SemanticDeduplicator, DeduplicationResult

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of a corpus ingestion operation."""

    total_received: int = 0
    passed_quality_filter: int = 0
    duplicates_removed: int = 0
    stored: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    ingestion_id: str = ""
    duration_ms: float = 0.0


class CorpusIngestionPipeline:
    """Pipeline for ingesting clauses into the benchmark corpus.

    Implements the full pipeline:
    1. Receive raw clause data
    2. PII anonymize using spaCy NER + regex
    3. Classify contract type
    4. Extract benchmark clause fields
    5. Quality filter (score > 0.85)
    6. Semantic deduplication
    7. Store in corpus

    Usage:
        pipeline = CorpusIngestionPipeline()
        result = pipeline.ingest(clauses_data)
    """

    def __init__(
        self,
        quality_threshold: float = 0.85,
        dedup_threshold: float = 0.92,
    ) -> None:
        """Initialize the ingestion pipeline.

        Args:
            quality_threshold: Minimum quality score for admission.
            dedup_threshold: Similarity threshold for deduplication.
        """
        self._anonymizer = PIIAnonymizer()
        self._quality_filter = QualityFilter(threshold=quality_threshold)
        self._deduplicator = SemanticDeduplicator(
            similarity_threshold=dedup_threshold
        )
        self._corpus: Dict[str, BenchmarkClause] = {}
        self._metadata = BenchmarkCorpusMetadata()

    def ingest(
        self,
        raw_clauses: List[Dict[str, Any]],
    ) -> IngestionResult:
        """Ingest raw clause data into the benchmark corpus.

        Args:
            raw_clauses: List of raw clause data dicts. Each dict should
                         contain at minimum a 'clause_text' field.

        Returns:
            IngestionResult with counts and errors.
        """
        import uuid
        start_time = datetime.utcnow()

        result = IngestionResult(
            total_received=len(raw_clauses),
            ingestion_id=str(uuid.uuid4()),
        )

        processed_clauses: List[BenchmarkClause] = []

        for idx, raw in enumerate(raw_clauses):
            try:
                clause = self._process_single_clause(raw, idx)
                if clause is not None:
                    processed_clauses.append(clause)
                    result.passed_quality_filter += 1
            except Exception as exc:
                result.failed += 1
                error_msg = f"Item {idx}: {exc}"
                result.errors.append(error_msg)
                logger.warning("Ingestion failed for item %d: %s", idx, exc)

        # Deduplicate
        if processed_clauses:
            dedup_result = self._deduplicator.deduplicate(processed_clauses)
            result.duplicates_removed = dedup_result.duplicates_removed

            # Store unique clauses
            for clause in processed_clauses:
                if clause.clause_id in {
                    c.clause_id for c in processed_clauses[:dedup_result.unique_kept]
                }:
                    # In a real implementation, this would store to a database
                    self._corpus[clause.clause_id] = clause
                    result.stored += 1

        # Update metadata
        self._update_metadata()

        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
        result.duration_ms = elapsed

        logger.info(
            "Ingestion complete: %d received, %d quality passed, "
            "%d duplicates removed, %d stored in %.0fms",
            result.total_received,
            result.passed_quality_filter,
            result.duplicates_removed,
            result.stored,
            elapsed,
        )

        return result

    def _process_single_clause(
        self,
        raw: Dict[str, Any],
        index: int,
    ) -> Optional[BenchmarkClause]:
        """Process a single raw clause through the pipeline.

        Args:
            raw: Raw clause data.
            index: Index for error reporting.

        Returns:
            BenchmarkClause if it passes all filters, None otherwise.
        """
        clause_text = raw.get("clause_text", "")
        if not clause_text.strip():
            logger.warning("Item %d: empty clause_text, skipping", index)
            return None

        # Step 1: Anonymize PII
        anonymized = self._anonymizer.anonymize(clause_text)
        if anonymized.pii_found:
            logger.info(
                "Item %d: anonymized %d PII entities",
                index, anonymized.replacements_made,
            )

        # Step 2: Build clause object
        clause = BenchmarkClause(
            clause_text=anonymized.anonymized_text,
            source_document_id=raw.get("source_document_id", f"source_{index}"),
            clause_type=raw.get("clause_type", "unknown"),
            contract_type=ContractType(raw.get("contract_type", "other")),
            industry=IndustryCategory(raw.get("industry", "technology")),
            counterparty_type=CounterpartyType(raw.get("counterparty_type", "enterprise")),
            deal_size_range=raw.get("deal_size_range"),
            jurisdiction=raw.get("jurisdiction"),
            quality_score=raw.get("quality_score", 0.0),
            is_attorney_reviewed=raw.get("is_attorney_reviewed", False),
            favorability=raw.get("favorability"),
            metadata=raw.get("metadata", {}),
        )

        # Step 3: Quality filter
        quality_score = self._quality_filter.evaluate(clause)
        clause.quality_score = quality_score.overall

        if not self._quality_filter.should_admit(quality_score):
            logger.info(
                "Item %d: quality score %.3f below threshold %.2f",
                index, quality_score.overall, self._quality_filter.threshold,
            )
            return None

        # Step 4: Check deduplication against existing corpus
        existing = list(self._corpus.values())
        is_dup, sim = self._deduplicator.is_duplicate(clause, existing)
        if is_dup:
            logger.info(
                "Item %d: duplicate detected (similarity=%.3f), skipping",
                index, sim,
            )
            return None

        return clause

    def get_corpus_size(self) -> int:
        """Get the total number of clauses in the corpus.

        Returns:
            Corpus size.
        """
        return len(self._corpus)

    def get_clauses_by_type(
        self, clause_type: str
    ) -> List[BenchmarkClause]:
        """Get all clauses of a specific type.

        Args:
            clause_type: The clause type to filter by.

        Returns:
            List of matching clauses.
        """
        return [
            c for c in self._corpus.values()
            if c.clause_type == clause_type
        ]

    def get_metadata(self) -> BenchmarkCorpusMetadata:
        """Get current corpus metadata.

        Returns:
            BenchmarkCorpusMetadata with current stats.
        """
        return self._metadata

    def _update_metadata(self) -> None:
        """Update corpus metadata from current state."""
        clauses = list(self._corpus.values())

        clause_type_counts: Dict[str, int] = {}
        contract_type_counts: Dict[str, int] = {}
        industry_counts: Dict[str, int] = {}
        counterparty_counts: Dict[str, int] = {}
        total_quality = 0.0

        for c in clauses:
            clause_type_counts[c.clause_type] = (
                clause_type_counts.get(c.clause_type, 0) + 1
            )
            contract_type_counts[c.contract_type.value] = (
                contract_type_counts.get(c.contract_type.value, 0) + 1
            )
            industry_counts[c.industry.value] = (
                industry_counts.get(c.industry.value, 0) + 1
            )
            counterparty_counts[c.counterparty_type.value] = (
                counterparty_counts.get(c.counterparty_type.value, 0) + 1
            )
            total_quality += c.quality_score

        source_docs = len(set(c.source_document_id for c in clauses))

        self._metadata = BenchmarkCorpusMetadata(
            total_clauses=len(clauses),
            total_documents=source_docs,
            clause_type_counts=clause_type_counts,
            contract_type_counts=contract_type_counts,
            industry_counts=industry_counts,
            counterparty_counts=counterparty_counts,
            avg_quality_score=round(
                total_quality / len(clauses), 4
            ) if clauses else 0.0,
            last_updated=datetime.utcnow(),
        )
