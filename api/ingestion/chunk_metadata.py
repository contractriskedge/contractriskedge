"""Metadata attachment and enrichment for document chunks.

Provides utilities for attaching rich metadata to document chunks
including source tracking, clause references, page numbers,
extraction confidence, and computed features for downstream
analysis and search.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from ingestion.models import DocumentChunk

logger = logging.getLogger(__name__)


class ChunkMetadataError(Exception):
    """Raised when metadata enrichment fails."""


class ChunkMetadataEnricher:
    """Enriches document chunks with computed and derived metadata.

    Attaches metadata including:
    - Source document provenance
    - Clause type classification
    - Entity mentions (dates, parties, monetary amounts)
    - Text statistics (readability, complexity)
    - Embedding-ready flags
    """

    # Patterns for common contract entities
    DATE_PATTERN = re.compile(
        r"\b(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
        r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b"
        r"|\b\d{4}-\d{2}-\d{2}\b"
    )

    MONETARY_PATTERN = re.compile(
        r"\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?"
        r"|\b(?:USD|EUR|GBP)\s*\d+"
    )

    PARTY_PATTERN = re.compile(
        r"\b(?:hereinafter|hereinafter referred to as|"
        r"hereby referred to as|collectively referred to as)\s+[“\"]([^”\"]+)[”\"]",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        """Initialize the metadata enricher."""
        pass

    def enrich(
        self,
        chunks: List[DocumentChunk],
        document_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """Enrich a list of chunks with computed metadata.

        Args:
            chunks: List of DocumentChunk objects to enrich.
            document_metadata: Optional document-level metadata to
                propagate to all chunks.

        Returns:
            The same chunk list with metadata enriched in place.
        """
        document_metadata = document_metadata or {}

        for chunk in chunks:
            try:
                metadata: Dict[str, Any] = {}

                # Propagate document-level metadata
                metadata["document_id"] = chunk.document_id
                metadata["chunk_index"] = chunk.chunk_index

                # Text statistics
                metadata["char_count"] = len(chunk.text)
                metadata["word_count"] = len(chunk.text.split())
                metadata["sentence_count"] = self._count_sentences(chunk.text)
                metadata["avg_word_length"] = self._average_word_length(chunk.text)

                # Entity extraction
                metadata["dates"] = self._extract_dates(chunk.text)
                metadata["monetary_amounts"] = self._extract_monetary_amounts(chunk.text)
                metadata["party_references"] = self._extract_parties(chunk.text)

                # Readability metrics
                metadata["readability_score"] = self._compute_readability(chunk.text)

                # Clause information
                metadata["num_clauses"] = len(chunk.clause_ids)
                metadata["clause_ids"] = chunk.clause_ids

                # Page information
                metadata["page_numbers"] = chunk.page_numbers
                metadata["num_pages"] = len(chunk.page_numbers)

                # Embedding metadata
                metadata["embedding_ready"] = True
                metadata["token_count"] = chunk.token_count
                metadata["fits_in_context"] = chunk.token_count <= 512

                # Document-level propagation
                for key, value in document_metadata.items():
                    if key not in metadata:
                        metadata[key] = value

                # Merge with existing metadata
                chunk.metadata.update(metadata)

            except Exception as exc:
                logger.warning(
                    "Failed to enrich chunk %s: %s",
                    chunk.chunk_id,
                    exc,
                )
                # Ensure basic metadata is present
                chunk.metadata.setdefault("char_count", len(chunk.text))
                chunk.metadata.setdefault("word_count", len(chunk.text.split()))
                chunk.metadata.setdefault("embedding_ready", True)

        logger.info(
            "Enriched %d chunks with metadata",
            len(chunks),
        )
        return chunks

    def _count_sentences(self, text: str) -> int:
        """Count the number of sentences in text.

        Args:
            text: Input text.

        Returns:
            Sentence count.
        """
        sentences = re.split(r"[.!?]+", text)
        return len([s for s in sentences if s.strip()])

    def _average_word_length(self, text: str) -> float:
        """Compute the average word length.

        Args:
            text: Input text.

        Returns:
            Average word length in characters.
        """
        words = text.split()
        if not words:
            return 0.0
        return sum(len(w) for w in words) / len(words)

    def _extract_dates(self, text: str) -> List[str]:
        """Extract date mentions from text.

        Args:
            text: Input text.

        Returns:
            List of matched date strings.
        """
        matches = self.DATE_PATTERN.findall(text)
        return [m.strip() for m in matches if m.strip()]

    def _extract_monetary_amounts(self, text: str) -> List[str]:
        """Extract monetary amounts from text.

        Args:
            text: Input text.

        Returns:
            List of matched monetary strings.
        """
        matches = self.MONETARY_PATTERN.findall(text)
        return [m.strip() for m in matches if m.strip()]

    def _extract_parties(self, text: str) -> List[str]:
        """Extract party/entity references from text.

        Args:
            text: Input text.

        Returns:
            List of matched party names.
        """
        matches = self.PARTY_PATTERN.findall(text)
        return [m.strip() for m in matches if m.strip()]

    def _compute_readability(self, text: str) -> float:
        """Compute a simplified readability score.

        Uses a variant of the Flesch Reading Ease formula adapted
        for contract text. Higher scores indicate easier readability.

        Args:
            text: Input text.

        Returns:
            Readability score (0-100).
        """
        words = text.split()
        if len(words) < 3:
            return 50.0  # Neutral default

        sentences = self._count_sentences(text)
        if sentences == 0:
            sentences = 1

        syllables = self._estimate_syllables(text)
        total_words = len(words)

        if total_words == 0:
            return 50.0

        # Simplified Flesch Reading Ease
        score = 206.835 - 1.015 * (total_words / sentences) - 84.6 * (syllables / total_words)
        return max(0.0, min(100.0, score))

    def _estimate_syllables(self, text: str) -> int:
        """Estimate syllable count in text.

        Uses a simplified vowel-group counting approach.

        Args:
            text: Input text.

        Returns:
            Estimated syllable count.
        """
        words = text.lower().split()
        total = 0

        for word in words:
            word = word.strip(".,!?;:\"'()[]{}")
            if not word:
                continue

            # Count vowel groups
            vowel_groups = re.findall(r"[aeiouy]+", word)
            count = len(vowel_groups)

            # Adjust for silent e
            if word.endswith("e") and count > 1:
                count -= 1

            # Ensure at least 1 syllable per word
            total += max(1, count)

        return total

    def batch_enrich(
        self,
        chunk_batches: List[List[DocumentChunk]],
        document_metadata_batch: Optional[List[Dict[str, Any]]] = None,
    ) -> List[List[DocumentChunk]]:
        """Enrich multiple batches of chunks.

        Args:
            chunk_batches: List of chunk lists to enrich.
            document_metadata_batch: Optional list of document-level
                metadata dicts, one per batch.

        Returns:
            List of enriched chunk lists.
        """
        if document_metadata_batch is None:
            document_metadata_batch = [{}] * len(chunk_batches)

        enriched: List[List[DocumentChunk]] = []
        for i, chunks in enumerate(chunk_batches):
            meta = document_metadata_batch[i] if i < len(document_metadata_batch) else {}
            enriched.append(self.enrich(chunks, meta))

        return enriched

    def prepare_for_embedding(
        self,
        chunk: DocumentChunk,
    ) -> str:
        """Prepare chunk text for embedding by cleaning and formatting.

        Strips metadata markers, normalizes whitespace, and truncates
        if necessary.

        Args:
            chunk: The chunk to prepare.

        Returns:
            Cleaned text string ready for embedding.
        """
        text = chunk.text

        # Remove clause boundary markers if any leaked
        text = re.sub(r"\[\[CLAUSE:[^\]]+\]\]", "", text)
        text = re.sub(r"\[\[ENDCLAUSE:[^\]]+\]\]", "", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Truncate to max tokens if needed
        max_chars = 512 * self._estimate_syllables(text)  # rough
        if len(text) > max_chars:
            text = text[:max_chars]
            # Break at last sentence
            last_period = text.rfind(".")
            if last_period > max_chars * 0.8:
                text = text[: last_period + 1]

        return text
