"""Semantic clause-aware document chunking algorithm.

Splits extracted contract text into chunks optimized for embedding
and vector search. Uses clause boundaries as natural break points,
enforces a 512-token maximum with 10% overlap, and preserves
clause metadata across chunks.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from ingestion.models import DocumentChunk

logger = logging.getLogger(__name__)


class ChunkerError(Exception):
    """Raised when chunking fails."""


class SemanticChunker:
    """Semantic chunker for contract documents.

    Splits document text into chunks using clause boundaries as
    primary split points. Enforces 512-token maximum chunk size
    with configurable overlap between consecutive chunks.

    Attributes:
        max_tokens: Maximum tokens per chunk (default 512).
        overlap_tokens: Token overlap between chunks (default 51, ~10%).
        min_chunk_tokens: Minimum tokens for a valid chunk (default 50).
    """

    # Rough estimate: 1 token ≈ 4 characters for English text
    TOKEN_TO_CHAR_RATIO = 4.0

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 51,
        min_chunk_tokens: int = 50,
    ) -> None:
        """Initialize the semantic chunker.

        Args:
            max_tokens: Maximum tokens per chunk.
            overlap_tokens: Token overlap between adjacent chunks.
            min_chunk_tokens: Minimum tokens to form a chunk.
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens

        self._max_chars = max_tokens * self.TOKEN_TO_CHAR_RATIO
        self._overlap_chars = overlap_tokens * self.TOKEN_TO_CHAR_RATIO
        self._min_chars = min_chunk_tokens * self.TOKEN_TO_CHAR_RATIO

    def chunk(
        self,
        document_id: str,
        pages: List[Any],
        clauses: List[Dict[str, Any]],
    ) -> List[DocumentChunk]:
        """Chunk a document into semantic pieces.

        Uses clause boundaries as primary split points. Falls back
        to sentence-level splitting for large clauses.

        Args:
            document_id: The source document identifier.
            pages: Extracted page content (list of PageExtraction or ExtractedPage).
            clauses: Identified clause segments from ClauseSegmenter.

        Returns:
            List of DocumentChunk objects with metadata.

        Raises:
            ChunkerError: If chunking fails.
        """
        if not pages:
            logger.warning("No pages provided for chunking")
            return []

        try:
            # Build full text with clause annotations
            full_text, clause_map = self._build_annotated_text(clauses)

            if not full_text.strip():
                logger.warning("Empty text after clause annotation")
                return []

            # Build page number map
            page_map = self._build_page_map(pages)

            # Perform clause-aware chunking
            chunks = self._clause_aware_chunking(
                document_id, full_text, clause_map, page_map
            )

            logger.info(
                "Chunking complete: %d chunks from %d clauses (document %s)",
                len(chunks),
                len(clauses),
                document_id,
            )
            return chunks

        except Exception as exc:
            raise ChunkerError(f"Chunking failed: {exc}") from exc

    def _build_annotated_text(
        self,
        clauses: List[Dict[str, Any]],
    ) -> tuple[str, Dict[str, Dict[str, Any]]]:
        """Build annotated full text with clause boundary markers.

        Args:
            clauses: List of clause dicts.

        Returns:
            Tuple of (full_text, clause_map).
        """
        clause_map: Dict[str, Dict[str, Any]] = {}
        text_parts: List[str] = []
        current_pos = 0

        for clause in sorted(clauses, key=lambda c: c.get("start_char", 0)):
            clause_id = clause.get("clause_id", "")
            clause_text = clause.get("text", "")
            start_char = clause.get("start_char", current_pos)

            # Add gap text between clauses (if any)
            if start_char > current_pos:
                text_parts.append(" " * (start_char - current_pos))

            # Add clause boundary marker
            marker = f"\n[[CLAUSE:{clause_id}]]\n"
            text_parts.append(marker)
            text_parts.append(clause_text)
            text_parts.append(f"\n[[ENDCLAUSE:{clause_id}]]\n")

            clause_map[clause_id] = {
                "text": clause_text,
                "section_number": clause.get("section_number"),
                "heading": clause.get("heading"),
                "level": clause.get("level", 1),
                "clause_type": clause.get("clause_type"),
                "page_number": clause.get("page_number", 1),
                "start_char": len("".join(text_parts)) - len(clause_text) - len(marker) - len(f"\n[[ENDCLAUSE:{clause_id}]]\n") - 2,
                "end_char": len("".join(text_parts)),
            }
            current_pos = start_char + len(clause_text)

        return "".join(text_parts), clause_map

    def _build_page_map(
        self,
        pages: List[Any],
    ) -> Dict[int, int]:
        """Build a mapping from page number to character offset.

        Args:
            pages: List of page objects with page_number and text.

        Returns:
            Dict mapping page_number -> cumulative char offset.
        """
        page_map: Dict[int, int] = {}
        cumulative = 0

        for page in sorted(pages, key=lambda p: p.page_number):
            page_map[page.page_number] = cumulative
            cumulative += len(page.text) + 1

        return page_map

    def _clause_aware_chunking(
        self,
        document_id: str,
        full_text: str,
        clause_map: Dict[str, Dict[str, Any]],
        page_map: Dict[int, int],
    ) -> List[DocumentChunk]:
        """Perform clause-aware semantic chunking.

        Creates chunks that respect clause boundaries. If a clause
        is too large, it's split at sentence boundaries.

        Args:
            document_id: Source document ID.
            full_text: Annotated full document text.
            clause_map: Clause metadata map.
            page_map: Page number to offset map.

        Returns:
            List of DocumentChunk objects.
        """
        chunks: List[DocumentChunk] = []
        chunk_index = 0

        # Extract clause IDs in order
        clause_ids_in_order = list(clause_map.keys())

        if not clause_ids_in_order:
            # No clause structure; chunk by character count
            return self._fallback_chunking(document_id, full_text, page_map)

        current_chunk_text: List[str] = []
        current_chunk_chars = 0
        current_chunk_clauses: Set[str] = set()
        current_chunk_pages: Set[int] = set()

        def flush_chunk(
            text: List[str],
            clauses: Set[str],
            pages: Set[int],
            force: bool = False,
        ) -> Optional[DocumentChunk]:
            """Flush the current chunk buffer.

            Args:
                text: Current chunk text parts.
                clauses: Clause IDs in current chunk.
                pages: Page numbers in current chunk.
                force: If True, flush even if below min_chars.

            Returns:
                A DocumentChunk if the buffer has content, else None.
            """
            nonlocal chunk_index

            combined = "".join(text)
            token_count = self._estimate_tokens(combined)

            if not combined.strip():
                return None

            if not force and token_count < self.min_chunk_tokens:
                return None

            chunk = DocumentChunk(
                document_id=document_id,
                text=combined.strip(),
                chunk_index=chunk_index,
                token_count=token_count,
                start_char=0,  # Will be set during assembly
                end_char=0,
                clause_ids=sorted(clauses),
                page_numbers=sorted(pages),
                metadata={
                    "chunking_strategy": "clause_aware",
                    "num_clauses": len(clauses),
                },
            )
            chunk_index += 1
            return chunk

        # Process each clause
        for clause_id in clause_ids_in_order:
            clause_info = clause_map[clause_id]
            clause_text = clause_info["text"]
            clause_chars = len(clause_text)
            clause_tokens = self._estimate_tokens(clause_text)
            clause_page = clause_info.get("page_number", 1)

            # If adding this clause would exceed max tokens, flush first
            if current_chunk_chars + clause_chars > self._max_chars and current_chunk_text:
                chunk = flush_chunk(
                    current_chunk_text,
                    current_chunk_clauses,
                    current_chunk_pages,
                )
                if chunk:
                    chunks.append(chunk)

                # Keep overlap from previous chunk
                overlap_text = self._get_overlap_text(current_chunk_text)
                current_chunk_text = [overlap_text] if overlap_text else []
                current_chunk_chars = len(overlap_text) if overlap_text else 0
                current_chunk_clauses = set()
                current_chunk_pages = set()

            # If a single clause exceeds max tokens, split it
            if clause_tokens > self.max_tokens:
                # Flush any existing buffer first
                if current_chunk_text:
                    chunk = flush_chunk(
                        current_chunk_text,
                        current_chunk_clauses,
                        current_chunk_pages,
                        force=True,
                    )
                    if chunk:
                        chunks.append(chunk)
                    current_chunk_text = []
                    current_chunk_chars = 0
                    current_chunk_clauses = set()
                    current_chunk_pages = set()

                # Split the large clause
                sub_chunks = self._split_large_clause(
                    document_id, clause_id, clause_text, clause_page, chunk_index
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                continue

            current_chunk_text.append(clause_text)
            current_chunk_chars += clause_chars
            current_chunk_clauses.add(clause_id)
            current_chunk_pages.add(clause_page)

        # Flush remaining buffer
        final_chunk = flush_chunk(
            current_chunk_text,
            current_chunk_clauses,
            current_chunk_pages,
            force=True,
        )
        if final_chunk:
            chunks.append(final_chunk)

        return chunks

    def _split_large_clause(
        self,
        document_id: str,
        clause_id: str,
        clause_text: str,
        page_number: int,
        start_index: int,
    ) -> List[DocumentChunk]:
        """Split a single large clause into multiple chunks.

        Uses sentence boundaries (period, newline, semicolon) as
        split points.

        Args:
            document_id: Source document ID.
            clause_id: The clause being split.
            clause_text: The clause text content.
            page_number: Source page number.
            start_index: Starting chunk index.

        Returns:
            List of DocumentChunk objects.
        """
        chunks: List[DocumentChunk] = []

        # Split by sentence boundaries
        sentences = re.split(r"(?<=[.!;])\s+", clause_text)
        current_batch: List[str] = []
        current_chars = 0

        for sentence in sentences:
            sentence_chars = len(sentence)

            if current_chars + sentence_chars > self._max_chars and current_batch:
                combined = " ".join(current_batch)
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        text=combined.strip(),
                        chunk_index=start_index + len(chunks),
                        token_count=self._estimate_tokens(combined),
                        start_char=0,
                        end_char=0,
                        clause_ids=[clause_id],
                        page_numbers=[page_number],
                        metadata={
                            "chunking_strategy": "sentence_split",
                            "parent_clause": clause_id,
                        },
                    )
                )

                # Overlap
                overlap = current_batch[-1:] if current_batch else []
                current_batch = overlap
                current_chars = sum(len(s) for s in overlap)

            current_batch.append(sentence)
            current_chars += sentence_chars

        # Flush remaining
        if current_batch:
            combined = " ".join(current_batch)
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    text=combined.strip(),
                    chunk_index=start_index + len(chunks),
                    token_count=self._estimate_tokens(combined),
                    start_char=0,
                    end_char=0,
                    clause_ids=[clause_id],
                    page_numbers=[page_number],
                    metadata={
                        "chunking_strategy": "sentence_split",
                        "parent_clause": clause_id,
                    },
                )
            )

        return chunks

    def _get_overlap_text(self, text_parts: List[str]) -> str:
        """Extract the overlapping portion from the end of text parts.

        Args:
            text_parts: List of text segments forming a chunk.

        Returns:
            Overlap text string.
        """
        combined = "".join(text_parts)
        if len(combined) <= self._overlap_chars:
            return combined

        # Find a good break point near the overlap boundary
        overlap_start = len(combined) - int(self._overlap_chars)
        # Try to find a sentence boundary near the overlap start
        search_region = combined[overlap_start:]
        match = re.search(r"^[^.!?\n]*[.!?\n]", search_region)
        if match:
            return search_region[match.end():]
        return search_region

    def _fallback_chunking(
        self,
        document_id: str,
        full_text: str,
        page_map: Dict[int, int],
    ) -> List[DocumentChunk]:
        """Fallback chunking when no clause structure is available.

        Splits text by character count with overlap.

        Args:
            document_id: Source document ID.
            full_text: Full document text.
            page_map: Page number mapping.

        Returns:
            List of DocumentChunk objects.
        """
        chunks: List[DocumentChunk] = []
        start = 0
        chunk_index = 0

        while start < len(full_text):
            end = min(start + self._max_chars, len(full_text))

            # Try to break at a natural boundary
            if end < len(full_text):
                search_start = max(end - 200, start)
                search_region = full_text[search_start:end + 100]

                # Find last sentence boundary
                boundaries = list(
                    re.finditer(r"(?<=[.!?\n])\s+", search_region)
                )
                if boundaries:
                    last_boundary = boundaries[-1]
                    end = search_start + last_boundary.end()

            chunk_text = full_text[start:end].strip()
            if not chunk_text:
                break

            # Determine page numbers
            chunk_pages = self._get_page_numbers(start, end, page_map)

            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    text=chunk_text,
                    chunk_index=chunk_index,
                    token_count=self._estimate_tokens(chunk_text),
                    start_char=start,
                    end_char=end,
                    clause_ids=[],
                    page_numbers=chunk_pages,
                    metadata={
                        "chunking_strategy": "fallback_character",
                    },
                )
            )

            chunk_index += 1
            start = end - int(self._overlap_chars)

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in a text string.

        Uses character count divided by the token-to-char ratio.

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        return max(1, int(len(text) / self.TOKEN_TO_CHAR_RATIO))

    def _get_page_numbers(
        self,
        start_char: int,
        end_char: int,
        page_map: Dict[int, int],
    ) -> List[int]:
        """Determine which page numbers a character range spans.

        Args:
            start_char: Start character offset.
            end_char: End character offset.
            page_map: Page number to offset mapping.

        Returns:
            Sorted list of page numbers.
        """
        pages: List[int] = []
        sorted_pages = sorted(page_map.keys())

        for page_num in sorted_pages:
            page_offset = page_map[page_num]
            next_offset = (
                page_map.get(sorted_pages[sorted_pages.index(page_num) + 1])
                if sorted_pages.index(page_num) + 1 < len(sorted_pages)
                else float("inf")
            )

            if start_char < next_offset and end_char > page_offset:
                pages.append(page_num)

        return pages
