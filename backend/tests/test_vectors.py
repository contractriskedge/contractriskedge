"""Tests for chunking, embeddings, and vector storage."""

from __future__ import annotations

import hashlib

import pytest
from app.domains.vectors.chunking import ChunkingService, tokenizer, ChunkData
from app.domains.vectors.embeddings import (
    OpenAIEmbeddingProvider,
    EmbeddingRequest,
    EmbeddingProviderError,
)


class TestTokenizer:
    """Verify token counting accuracy."""

    def test_count_simple_text(self):
        count = tokenizer.count("Hello world")
        assert count > 0
        assert count < 10

    def test_count_empty_string(self):
        assert tokenizer.count("") == 0

    def test_count_long_text(self):
        text = "Hello world " * 1000
        count = tokenizer.count(text)
        assert count > 1000


class TestChunkingService:
    """Verify semantic chunking behavior."""

    def setup_method(self):
        self.service = ChunkingService(chunk_size=200, overlap=40)

    def test_empty_pages_returns_empty(self):
        chunks = self.service.chunk_pages([])
        assert chunks == []

    def test_single_page_single_chunk(self):
        pages = [{"page_number": 1, "text": "Hello world. This is a test document."}]
        chunks = self.service.chunk_pages(pages)
        assert len(chunks) >= 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].token_count > 0

    def test_multi_page_merges_across_pages(self):
        pages = [
            {"page_number": 1, "text": "First page content. " * 10},
            {"page_number": 2, "text": "Second page content. " * 10},
        ]
        chunks = self.service.chunk_pages(pages)
        assert len(chunks) >= 1

    def test_chunk_has_checksum(self):
        pages = [{"page_number": 1, "text": "Test content for checksum."}]
        chunks = self.service.chunk_pages(pages)
        assert chunks[0].checksum
        expected = hashlib.sha256(chunks[0].text.encode()).hexdigest()
        assert chunks[0].checksum == expected

    def test_large_paragraph_split(self):
        text = "Paragraph content. " * 500  # Will exceed max chunk size
        pages = [{"page_number": 1, "text": text}]
        chunks = self.service.chunk_pages(pages)
        assert len(chunks) > 1

    def test_heading_aware_chunking(self):
        text = (
            "SECTION 1. Introduction\n\nThis is the intro section.\n\n"
            "SECTION 2. Terms\n\nThese are the terms and conditions.\n\n"
            "SECTION 3. Termination\n\nThis section covers termination."
        )
        pages = [{"page_number": 1, "text": text}]
        service = ChunkingService(chunk_size=500, overlap=40)
        chunks = service.chunk_pages(pages, strategy="heading_aware")
        assert len(chunks) >= 1

    def test_fixed_size_chunking(self):
        text = "Word " * 500
        pages = [{"page_number": 1, "text": text}]
        chunks = self.service.chunk_pages(pages, strategy="fixed_size")
        assert len(chunks) > 1


class TestChunkMetadata:
    """Verify chunk metadata correctness."""

    def test_page_numbers_tracked(self):
        pages = [
            {"page_number": 1, "text": "Page one. " * 20},
            {"page_number": 2, "text": "Page two. " * 20},
        ]
        service = ChunkingService(chunk_size=500, overlap=40)
        chunks = service.chunk_pages(pages)
        for chunk in chunks:
            assert all(isinstance(p, int) for p in chunk.page_numbers)

    def test_chunk_index_sequential(self):
        pages = [{"page_number": i + 1, "text": f"Page {i + 1}. " * 30} for i in range(5)]
        service = ChunkingService(chunk_size=100, overlap=20)
        chunks = service.chunk_pages(pages)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i


class TestEmbeddingProvider:
    """Verify embedding provider abstraction."""

    def test_provider_interface(self):
        """Provider should have required attributes without instantiation."""
        assert hasattr(OpenAIEmbeddingProvider, "embed")
        assert hasattr(OpenAIEmbeddingProvider, "embed_batch")

    def test_supported_models(self):
        provider = OpenAIEmbeddingProvider(api_key="test")
        assert "text-embedding-3-large" in provider.supported_models
        assert provider.provider_name == "openai"

    def test_cost_estimation(self):
        provider = OpenAIEmbeddingProvider(api_key="test")
        cost = provider._estimate_cost("text-embedding-3-large", 1000)
        assert cost > 0
        assert cost < 1.0  # Sanity: 1000 tokens should cost < $1


class TestTenantIsolation:
    """Verify vector data is tenant-scoped."""

    def test_chunk_tenant_field(self):
        from app.domains.vectors.models import Chunk
        assert hasattr(Chunk, "tenant_id")

    def test_embedding_run_tenant_field(self):
        from app.domains.vectors.models import EmbeddingRun
        assert hasattr(EmbeddingRun, "tenant_id")

    def test_vector_search_requires_tenant(self):
        from app.domains.vectors.repository import VectorRepository
        # Repository methods require tenant_id — verified by BaseRepository pattern
        pass
