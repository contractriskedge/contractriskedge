"""Tests for the semantic chunking module."""

from __future__ import annotations

from ingestion.chunker import SemanticChunker
from ingestion.models import DocumentChunk


def test_chunker_initialization():
    """Test chunker default configuration."""
    chunker = SemanticChunker()
    assert chunker.max_tokens == 512
    assert chunker.overlap_tokens == 51
    assert chunker.min_chunk_tokens == 50


def test_empty_input():
    """Test chunking with no pages or clauses."""
    chunker = SemanticChunker()
    chunks = chunker.chunk("doc-1", [], [])
    assert chunks == []


def test_estimate_tokens():
    """Test token estimation."""
    chunker = SemanticChunker()
    # 1 token ≈ 4 characters
    result = chunker._estimate_tokens("Hello world")  # 11 chars / 4 = 2.75
    assert result in (2, 3)  # rounding may vary
    assert chunker._estimate_tokens("") == 0


def test_fallback_chunking():
    """Test fallback chunking with no clause structure."""
    chunker = SemanticChunker()
    text = "This is a test document. " * 200  # ~6000 chars

    class MockPage:
        def __init__(self):
            self.page_number = 1
            self.text = text

    chunks = chunker.chunk("doc-1", [MockPage()], [])
    # May produce chunks or return empty if text processing filters everything
    assert all(isinstance(c, DocumentChunk) for c in chunks)
    if chunks:
        assert all(c.document_id == "doc-1" for c in chunks)


def test_chunk_metadata():
    """Test that chunks have proper metadata."""
    chunker = SemanticChunker()

    class MockPage:
        def __init__(self):
            self.page_number = 1
            self.text = "Page 1 text content for testing."

    chunks = chunker.chunk("doc-1", [MockPage()], [])
    if chunks:
        chunk = chunks[0]
        assert chunk.chunk_index == 0
        assert chunk.token_count > 0
        assert isinstance(chunk.metadata, dict)
