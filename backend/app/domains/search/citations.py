"""Citation generator — produces structured citations for retrieved chunks with source references."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Citation:
    """A structured citation linking a search result to its source document."""
    chunk_id: str
    upload_id: Optional[str] = None
    contract_id: Optional[str] = None
    contract_name: Optional[str] = None
    page_numbers: list[int] = field(default_factory=list)
    section_heading: Optional[str] = None
    clause_type: Optional[str] = None
    snippet: str = ""
    relevance_score: float = 0.0
    text_excerpt: str = ""
    source_url: Optional[str] = None


class CitationGenerator:
    """Generates structured citations from retrieved chunks with source attribution.

    Every citation includes:
    - Source contract identifier
    - Page numbers for direct reference
    - Section heading for context
    - Clause type classification
    - Relevance score for transparency
    - Text excerpt for verification
    """

    @staticmethod
    def from_chunk(
        chunk_id: str,
        text: str,
        score: float,
        page_numbers: Optional[list[int]] = None,
        section_heading: Optional[str] = None,
        clause_type: Optional[str] = None,
        upload_id: Optional[str] = None,
        contract_id: Optional[str] = None,
        contract_name: Optional[str] = None,
        max_excerpt_length: int = 500,
    ) -> Citation:
        """Build a citation from a retrieved chunk."""
        excerpt = text[:max_excerpt_length]
        if len(text) > max_excerpt_length:
            excerpt += "..."

        return Citation(
            chunk_id=chunk_id,
            upload_id=upload_id,
            contract_id=contract_id,
            contract_name=contract_name,
            page_numbers=page_numbers or [],
            section_heading=section_heading,
            clause_type=clause_type,
            snippet=CitationGenerator._make_snippet(text, max_length=300),
            relevance_score=round(score, 4),
            text_excerpt=excerpt,
        )

    @staticmethod
    def from_chunks(chunks: list, max_citations: int = 10) -> list[Citation]:
        """Build citations from a list of retrieved chunks, deduplicated by source."""
        seen_sources: set[str] = set()
        citations: list[Citation] = []

        for chunk in chunks:
            source_key = f"{chunk.upload_id or ''}:{chunk.chunk_id}"
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)

            citation = CitationGenerator.from_chunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                score=chunk.score,
                page_numbers=chunk.page_numbers,
                section_heading=chunk.section_heading,
                clause_type=chunk.clause_type,
                upload_id=chunk.upload_id,
            )
            citations.append(citation)

            if len(citations) >= max_citations:
                break

        return citations

    @staticmethod
    def _make_snippet(text: str, max_length: int = 300) -> str:
        """Generate a readable snippet from text."""
        if len(text) <= max_length:
            return text
        # Try to break at a sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind(".")
        if last_period > max_length // 2:
            return text[:last_period + 1]
        return truncated + "..."
