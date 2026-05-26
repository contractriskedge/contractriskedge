"""Semantic chunking service — token-aware text splitting with overlap and boundary preservation."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ChunkData:
    """A single chunk produced by the chunking service."""
    text: str
    chunk_index: int
    token_count: int
    page_numbers: list[int] = field(default_factory=list)
    section_heading: Optional[str] = None
    clause_type: Optional[str] = None
    checksum: str = ""
    char_count: int = 0


class ChunkingError(Exception):
    """Raised when chunking fails."""


class Tokenizer:
    """Token counter using tiktoken for OpenAI model compatibility."""

    MODEL_ENCODING = "cl100k_base"  # Compatible with text-embedding-3-large

    def __init__(self):
        import tiktoken
        self._encoding = tiktoken.get_encoding(self.MODEL_ENCODING)

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text))

    def encode(self, text: str) -> list[int]:
        return self._encoding.encode(text)

    def decode(self, tokens: list[int]) -> str:
        return self._encoding.decode(tokens)


tokenizer = Tokenizer()


class ChunkingService:
    """Semantic document chunking with configurable strategy.

    Supports:
    - Token-aware splitting with configurable chunk size and overlap
    - Page boundary awareness (prefer splits at page breaks)
    - Heading-aware splitting (preserve section headings)
    - Paragraph boundary preservation
    - OCR artifact cleanup
    - Content deduplication via checksums
    """

    DEFAULT_CHUNK_SIZE = 800     # tokens
    DEFAULT_OVERLAP = 120        # tokens
    MIN_CHUNK_SIZE = 100         # tokens — discard smaller
    MAX_CHUNK_SIZE = 2000        # tokens — hard upper bound

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
    ):
        if overlap >= chunk_size:
            raise ChunkingError(f"Overlap ({overlap}) must be less than chunk size ({chunk_size})")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_pages(
        self,
        pages: list[dict],  # [{"page_number": 1, "text": "..."}, ...]
        strategy: str = "semantic",
    ) -> list[ChunkData]:
        """Chunk text from extracted pages into semantic chunks.

        Args:
            pages: List of dicts with page_number and text keys.
            strategy: Chunking strategy — 'semantic', 'fixed_size', 'heading_aware'.

        Returns:
            List of ChunkData objects.
        """
        if not pages:
            return []

        if strategy == "heading_aware":
            return self._chunk_heading_aware(pages)
        elif strategy == "fixed_size":
            return self._chunk_fixed_size(pages)
        else:
            return self._chunk_semantic(pages)

    def _chunk_semantic(self, pages: list[dict]) -> list[ChunkData]:
        """Semantic chunking: split at paragraph boundaries, respect page breaks."""
        chunks: list[ChunkData] = []
        current_parts: list[str] = []
        current_tokens = 0
        current_pages: set[int] = set()
        chunk_index = 0

        for page in pages:
            page_num = page["page_number"]
            text = self._clean_text(page["text"])
            paragraphs = self._split_paragraphs(text)

            for para in paragraphs:
                para_tokens = tokenizer.count(para)

                # If this single paragraph exceeds the target chunk size, split it
                max_para_tokens = min(self.chunk_size, self.MAX_CHUNK_SIZE)
                if para_tokens > max_para_tokens:
                    # Flush current buffer first
                    if current_parts:
                        chunks.append(self._make_chunk(current_parts, current_pages, chunk_index))
                        chunk_index += 1
                        current_parts, current_tokens, current_pages = self._get_overlap_buffer(
                            current_parts, current_tokens
                        )

                    # Split long paragraph
                    sub_chunks = self._split_long_paragraph(para, page_num, chunk_index)
                    for sc in sub_chunks:
                        chunks.append(sc)
                        chunk_index += 1
                    continue

                # If adding this paragraph would exceed chunk size, flush
                if current_tokens + para_tokens > self.chunk_size and current_parts:
                    chunks.append(self._make_chunk(current_parts, current_pages, chunk_index))
                    chunk_index += 1
                    current_parts, current_tokens, current_pages = self._get_overlap_buffer(
                        current_parts, current_tokens
                    )

                current_parts.append(para)
                current_tokens += para_tokens
                current_pages.add(page_num)

        # Final chunk
        if current_parts:
            chunks.append(self._make_chunk(current_parts, current_pages, chunk_index))

        return chunks

    def _chunk_fixed_size(self, pages: list[dict]) -> list[ChunkData]:
        """Fixed-size chunking with token-level splitting and overlap."""
        all_text = "\n\n".join(p["text"] for p in pages)
        all_text = self._clean_text(all_text)
        tokens = tokenizer.encode(all_text)
        chunks: list[ChunkData] = []
        chunk_index = 0
        pos = 0

        while pos < len(tokens):
            end = min(pos + self.chunk_size, len(tokens))
            chunk_tokens = tokens[pos:end]
            chunk_text = tokenizer.decode(chunk_tokens)
            chunks.append(ChunkData(
                text=chunk_text,
                chunk_index=chunk_index,
                token_count=len(chunk_tokens),
                char_count=len(chunk_text),
                checksum=hashlib.sha256(chunk_text.encode()).hexdigest(),
            ))
            chunk_index += 1
            pos += self.chunk_size - self.overlap

        return chunks

    def _chunk_heading_aware(self, pages: list[dict]) -> list[ChunkData]:
        """Heading-aware chunking: preserve section headings as natural boundaries."""
        all_text = "\n\n".join(p["text"] for p in pages)
        all_text = self._clean_text(all_text)

        # Split by common heading patterns
        heading_pattern = re.compile(
            r'(^|\n)((?:SECTION|Section|section|Article|ARTICLE|article|'
            r'Clause|CLAUSE|clause|Exhibit|EXHIBIT)\s+[\d\.]+[\.\:\)]?\s*.*?(?:\n|$))',
            re.MULTILINE,
        )

        sections = heading_pattern.split(all_text)
        sections = [s.strip() for s in sections if s and s.strip()]

        if len(sections) < 2:
            return self._chunk_semantic(pages)

        chunks: list[ChunkData] = []
        current_heading = ""
        current_parts: list[str] = []
        current_tokens = 0
        chunk_index = 0

        for section in sections:
            if re.match(r'^(SECTION|Section|section|Article|ARTICLE|article|Clause|CLAUSE|clause)\s', section):
                current_heading = section
                continue

            section_tokens = tokenizer.count(section)
            if current_tokens + section_tokens > self.chunk_size and current_parts:
                chunks.append(ChunkData(
                    text="\n\n".join(current_parts),
                    chunk_index=chunk_index,
                    token_count=current_tokens,
                    section_heading=current_heading,
                    char_count=sum(len(p) for p in current_parts),
                    checksum=hashlib.sha256("\n\n".join(current_parts).encode()).hexdigest(),
                ))
                chunk_index += 1
                current_parts = current_parts[-1:] if current_parts else []
                current_tokens = tokenizer.count(current_parts[0]) if current_parts else 0

            current_parts.append(section)
            current_tokens += section_tokens

        if current_parts:
            chunks.append(ChunkData(
                text="\n\n".join(current_parts),
                chunk_index=chunk_index,
                token_count=current_tokens,
                section_heading=current_heading,
                char_count=sum(len(p) for p in current_parts),
                checksum=hashlib.sha256("\n\n".join(current_parts).encode()).hexdigest(),
            ))

        return chunks

    def _make_chunk(self, parts: list[str], pages: set[int], index: int) -> ChunkData:
        text = "\n\n".join(parts)
        tokens = tokenizer.count(text)
        return ChunkData(
            text=text,
            chunk_index=index,
            token_count=tokens,
            page_numbers=sorted(pages),
            char_count=len(text),
            checksum=hashlib.sha256(text.encode()).hexdigest(),
        )

    def _get_overlap_buffer(self, parts: list[str], current_tokens: int) -> tuple[list[str], int, set[int]]:
        """Keep trailing content for overlap with next chunk."""
        overlap_parts: list[str] = []
        overlap_tokens = 0
        for part in reversed(parts):
            part_tokens = tokenizer.count(part)
            if overlap_tokens + part_tokens > self.overlap:
                break
            overlap_parts.insert(0, part)
            overlap_tokens += part_tokens
        return overlap_parts, overlap_tokens, set()

    def _split_long_paragraph(self, text: str, page_num: int, start_index: int = 0) -> list[ChunkData]:
        """Split a single long paragraph into multiple chunks."""
        tokens = tokenizer.encode(text)
        chunks = []
        pos = 0
        idx = start_index
        while pos < len(tokens):
            end = min(pos + self.chunk_size, len(tokens))
            chunk_text = tokenizer.decode(tokens[pos:end])
            chunks.append(ChunkData(
                text=chunk_text,
                chunk_index=idx,
                token_count=end - pos,
                page_numbers=[page_num],
                char_count=len(chunk_text),
                checksum=hashlib.sha256(chunk_text.encode()).hexdigest(),
            ))
            idx += 1
            pos += self.chunk_size - self.overlap
        return chunks

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text before chunking."""
        from app.domains.extraction.normalizer import normalize_text
        return normalize_text(text)

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """Split text into paragraphs, preserving structure."""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]


chunking_service = ChunkingService()
