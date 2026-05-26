"""Semantic deduplication to avoid benchmark skew.

Uses sentence embeddings and cosine similarity to identify and remove
near-duplicate clauses from the benchmark corpus, preventing data skew
from repeated or very similar clauses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from .models import BenchmarkClause

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationResult:
    """Result of a deduplication operation."""

    total_input: int = 0
    duplicates_removed: int = 0
    unique_kept: int = 0
    duplicate_groups: List[List[str]] = field(default_factory=list)
    duplicate_scores: List[float] = field(default_factory=list)


class SemanticDeduplicator:
    """Semantic deduplication using embedding similarity.

    Uses sentence-transformers to compute embeddings for each clause
    and removes near-duplicates based on cosine similarity threshold.

    Usage:
        dedup = SemanticDeduplicator(threshold=0.92)
        result = dedup.deduplicate(clauses)
        unique_clauses = result.unique_kept
    """

    def __init__(
        self,
        similarity_threshold: float = 0.92,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 64,
    ) -> None:
        """Initialize the semantic deduplicator.

        Args:
            similarity_threshold: Cosine similarity threshold above which
                                  clauses are considered duplicates.
            model_name: Sentence transformer model name.
            batch_size: Batch size for embedding computation.
        """
        self._similarity_threshold = similarity_threshold
        self._model_name = model_name
        self._batch_size = batch_size
        self._model = None

    def _load_model(self) -> None:
        """Lazy-load the sentence transformer model."""
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            logger.info("Loaded embedding model: %s", self._model_name)
        except ImportError:
            logger.warning(
                "sentence-transformers not available. "
                "Falling back to text-based deduplication."
            )

    def deduplicate(
        self,
        clauses: List[BenchmarkClause],
    ) -> DeduplicationResult:
        """Deduplicate a list of benchmark clauses.

        Args:
            clauses: List of clauses to deduplicate.

        Returns:
            DeduplicationResult with unique clauses and metadata.
        """
        if len(clauses) <= 1:
            return DeduplicationResult(
                total_input=len(clauses),
                duplicates_removed=0,
                unique_kept=len(clauses),
            )

        self._load_model()

        if self._model is not None:
            return self._semantic_deduplicate(clauses)
        else:
            return self._text_deduplicate(clauses)

    def _semantic_deduplicate(
        self,
        clauses: List[BenchmarkClause],
    ) -> DeduplicationResult:
        """Deduplicate using semantic embeddings.

        Args:
            clauses: List of clauses.

        Returns:
            DeduplicationResult.
        """
        texts = [c.clause_text for c in clauses]

        # Compute embeddings in batches
        all_embeddings: List[np.ndarray] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i:i + self._batch_size]
            embeddings = self._model.encode(batch, show_progress_bar=False)
            all_embeddings.append(embeddings)

        embeddings = np.vstack(all_embeddings) if all_embeddings else np.array([])

        # Find near-duplicates using greedy clustering
        kept: List[int] = []
        removed: Set[int] = set()
        duplicate_groups: List[List[str]] = []
        duplicate_scores: List[float] = []

        for i in range(len(clauses)):
            if i in removed:
                continue

            kept.append(i)
            group: List[str] = [clauses[i].clause_id]
            max_sim = 0.0

            for j in range(i + 1, len(clauses)):
                if j in removed:
                    continue

                similarity = float(np.dot(embeddings[i], embeddings[j]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                ))

                if similarity >= self._similarity_threshold:
                    removed.add(j)
                    group.append(clauses[j].clause_id)
                    max_sim = max(max_sim, similarity)

            if len(group) > 1:
                duplicate_groups.append(group)
                duplicate_scores.append(max_sim)

        unique_clauses = [clauses[i] for i in kept]

        logger.info(
            "Semantic deduplication: %d input → %d unique (%d duplicates removed)",
            len(clauses),
            len(unique_clauses),
            len(removed),
        )

        return DeduplicationResult(
            total_input=len(clauses),
            duplicates_removed=len(removed),
            unique_kept=len(unique_clauses),
            duplicate_groups=duplicate_groups,
            duplicate_scores=duplicate_scores,
        )

    def _text_deduplicate(
        self,
        clauses: List[BenchmarkClause],
    ) -> DeduplicationResult:
        """Fallback deduplication using text similarity.

        Uses Jaccard similarity on word sets as a fallback when
        sentence-transformers is not available.

        Args:
            clauses: List of clauses.

        Returns:
            DeduplicationResult.
        """
        kept: List[int] = []
        removed: Set[int] = set()
        duplicate_groups: List[List[str]] = []
        duplicate_scores: List[float] = []

        for i in range(len(clauses)):
            if i in removed:
                continue

            kept.append(i)
            group: List[str] = [clauses[i].clause_id]
            max_sim = 0.0
            words_i = set(clauses[i].clause_text.lower().split())

            for j in range(i + 1, len(clauses)):
                if j in removed:
                    continue

                words_j = set(clauses[j].clause_text.lower().split())
                intersection = words_i & words_j
                union = words_i | words_j

                if not union:
                    continue

                jaccard = len(intersection) / len(union)

                if jaccard >= self._similarity_threshold:
                    removed.add(j)
                    group.append(clauses[j].clause_id)
                    max_sim = max(max_sim, jaccard)

            if len(group) > 1:
                duplicate_groups.append(group)
                duplicate_scores.append(max_sim)

        unique_clauses = [clauses[i] for i in kept]

        logger.info(
            "Text deduplication: %d input → %d unique (%d duplicates removed)",
            len(clauses),
            len(unique_clauses),
            len(removed),
        )

        return DeduplicationResult(
            total_input=len(clauses),
            duplicates_removed=len(removed),
            unique_kept=len(unique_clauses),
            duplicate_groups=duplicate_groups,
            duplicate_scores=duplicate_scores,
        )

    def is_duplicate(
        self,
        clause: BenchmarkClause,
        existing_clauses: List[BenchmarkClause],
    ) -> Tuple[bool, float]:
        """Check if a clause is a duplicate of any existing clauses.

        Args:
            clause: The clause to check.
            existing_clauses: List of existing clauses to compare against.

        Returns:
            Tuple of (is_duplicate, max_similarity_score).
        """
        if not existing_clauses:
            return False, 0.0

        self._load_model()

        if self._model is not None:
            # Semantic comparison
            clause_emb = self._model.encode([clause.clause_text])[0]

            for existing in existing_clauses:
                existing_emb = self._model.encode([existing.clause_text])[0]
                similarity = float(np.dot(clause_emb, existing_emb) / (
                    np.linalg.norm(clause_emb) * np.linalg.norm(existing_emb)
                ))
                if similarity >= self._similarity_threshold:
                    return True, similarity
        else:
            # Text comparison fallback
            words_new = set(clause.clause_text.lower().split())
            for existing in existing_clauses:
                words_existing = set(existing.clause_text.lower().split())
                intersection = words_new & words_existing
                union = words_new | words_existing
                if union:
                    jaccard = len(intersection) / len(union)
                    if jaccard >= self._similarity_threshold:
                        return True, jaccard

        return False, 0.0
