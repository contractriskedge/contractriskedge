"""Comprehensive unit tests for the VectorSearchService.

Tests cover:
    - Semantic search (basic, empty query, tenant isolation)
    - Hybrid search (vector + keyword RRF fusion)
    - Similarity threshold filtering
    - Metadata filtering (document_ids, clause_types)
    - Empty result handling
    - Cross-tenant prevention
    - Ranking correctness
    - Index management
    - SearchResult schema
    - SearchMetrics observability
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.domains.vectors.services.vector_search_service import (
    DEFAULT_LIMIT,
    DEFAULT_SIMILARITY_THRESHOLD,
    EMBEDDING_DIMENSION,
    RRF_K,
    VECTOR_WEIGHT,
    KEYWORD_WEIGHT,
    VectorSearchService,
    VectorSearchError,
    EmptyQueryError,
    TenantIsolationError,
    InvalidDimensionError,
    SearchResult,
    SearchMetrics,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock async SQLAlchemy session with proper sync chaining.

    Usage::

        mock_session.execute.return_value.fetchall.return_value = [row1, row2]
    """
    session = MagicMock()
    # execute is an AsyncMock — its return_value is a regular MagicMock
    # whose .fetchall() returns synchronously
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    session.execute = AsyncMock(return_value=mock_result)
    return session


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Create a mock EmbeddingService that returns a fixed 1536-dim vector."""
    service = MagicMock()
    service.generate_embedding = AsyncMock()
    service.generate_embedding.return_value = [0.1] * EMBEDDING_DIMENSION
    return service


@pytest.fixture
def vector_search_service(
    mock_session: MagicMock,
    mock_embedding_service: MagicMock,
) -> VectorSearchService:
    """Create a VectorSearchService with mocked dependencies."""
    return VectorSearchService(
        session=mock_session,
        embedding_service=mock_embedding_service,
    )


@pytest.fixture
def sample_tenant_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def sample_document_ids() -> list[UUID]:
    return [
        UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    ]


def _make_db_row(
    chunk_id: Optional[UUID] = None,
    upload_id: Optional[UUID] = None,
    text: str = "Test chunk content for search",
    similarity: float = 0.85,
    page_numbers: Optional[list[int]] = None,
    clause_type: Optional[str] = None,
) -> MagicMock:
    """Build a mock database row matching the vector search SQL result shape."""
    row = MagicMock()
    row.chunk_id = chunk_id or UUID("22222222-2222-2222-2222-222222222222")
    row.upload_id = upload_id or UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    row.text = text
    row.page_numbers = page_numbers or [1]
    row.clause_type = clause_type
    row.metadata = {"document_name": "test.pdf"}
    row.similarity = similarity
    return row


def _make_keyword_row(
    chunk_id: Optional[UUID] = None,
    upload_id: Optional[UUID] = None,
    text: str = "Test keyword match content",
    score: float = 0.5,
    page_numbers: Optional[list[int]] = None,
    clause_type: Optional[str] = None,
) -> MagicMock:
    """Build a mock database row for keyword search results."""
    row = MagicMock()
    row.chunk_id = chunk_id or UUID("33333333-3333-3333-3333-333333333333")
    row.upload_id = upload_id or UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    row.text = text
    row.page_numbers = page_numbers or [2]
    row.clause_type = clause_type
    row.metadata = {"document_name": "test.pdf"}
    row.score = score
    return row


# ── SearchResult Schema ───────────────────────────────────────────────────────


class TestSearchResultSchema:
    """Verify SearchResult dataclass structure."""

    def test_all_fields_present(self) -> None:
        result = SearchResult(
            chunk_id=UUID("22222222-2222-2222-2222-222222222222"),
            upload_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            text="test",
            similarity_score=0.85,
            page_numbers=[1, 2],
            clause_type="indemnification",
            metadata={"key": "value"},
        )
        assert result.chunk_id == UUID("22222222-2222-2222-2222-222222222222")
        assert result.upload_id == UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        assert result.text == "test"
        assert result.similarity_score == 0.85
        assert result.page_numbers == [1, 2]
        assert result.clause_type == "indemnification"
        assert result.metadata == {"key": "value"}

    def test_default_values(self) -> None:
        result = SearchResult(
            chunk_id=UUID("22222222-2222-2222-2222-222222222222"),
            upload_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            text="test",
            similarity_score=0.85,
            page_numbers=[],
        )
        assert result.clause_type is None
        assert result.metadata == {}

    def test_search_metrics_defaults(self) -> None:
        metrics = SearchMetrics()
        assert metrics.query_latency_ms == 0
        assert metrics.embedding_latency_ms == 0
        assert metrics.vector_search_latency_ms == 0
        assert metrics.total_results == 0
        assert metrics.strategy == "vector"


# ── VectorSearchService: Initialization ───────────────────────────────────────


class TestVectorSearchServiceInit:
    """Verify service initialization."""

    def test_init(self, mock_session: MagicMock, mock_embedding_service: MagicMock) -> None:
        service = VectorSearchService(
            session=mock_session,
            embedding_service=mock_embedding_service,
        )
        assert service._session is mock_session
        assert service._embedding_service is mock_embedding_service


# ── VectorSearchService: semantic_search ──────────────────────────────────────


class TestSemanticSearch:
    """Verify semantic search behavior."""

    async def test_basic_search(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Basic search returns ranked results."""
        chunk_id = UUID("22222222-2222-2222-2222-222222222222")
        upload_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(chunk_id=chunk_id, upload_id=upload_id, similarity=0.92),
            _make_db_row(
                chunk_id=UUID("33333333-3333-3333-3333-333333333333"),
                upload_id=upload_id,
                similarity=0.85,
            ),
        ]

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="indemnification clause",
        )

        assert len(results) == 2
        assert results[0].similarity_score >= results[1].similarity_score
        assert results[0].chunk_id == chunk_id
        assert results[0].upload_id == upload_id
        assert results[0].text == "Test chunk content for search"
        assert metrics.total_results == 2
        assert metrics.strategy == "vector"
        assert metrics.embedding_latency_ms >= 0
        assert metrics.vector_search_latency_ms >= 0
        assert metrics.query_latency_ms >= 0

    async def test_empty_query_raises(
        self,
        vector_search_service: VectorSearchService,
        sample_tenant_id: UUID,
    ) -> None:
        """Empty query raises EmptyQueryError."""
        with pytest.raises(EmptyQueryError, match="empty after cleaning"):
            await vector_search_service.semantic_search(
                tenant_id=sample_tenant_id,
                query="",
            )

    async def test_whitespace_query_raises(
        self,
        vector_search_service: VectorSearchService,
        sample_tenant_id: UUID,
    ) -> None:
        """Whitespace-only query raises EmptyQueryError."""
        with pytest.raises(EmptyQueryError, match="empty after cleaning"):
            await vector_search_service.semantic_search(
                tenant_id=sample_tenant_id,
                query="   \n  \t  ",
            )

    async def test_missing_tenant_raises(
        self,
        vector_search_service: VectorSearchService,
    ) -> None:
        """Missing tenant_id raises TenantIsolationError."""
        with pytest.raises(TenantIsolationError, match="tenant_id is required"):
            await vector_search_service.semantic_search(
                tenant_id=UUID(int=0),  # nil UUID
                query="test query",
            )

    async def test_tenant_isolation_enforced(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Tenant ID is included in the SQL query."""
        mock_session.execute.return_value.fetchall.return_value = []

        await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="test query",
        )

        # Verify tenant_id was passed in the SQL params
        call_args, _call_kwargs = mock_session.execute.await_args
        params = call_args[1] if len(call_args) > 1 else {}
        assert params.get("tenant_id") == str(sample_tenant_id)

    async def test_similarity_threshold_filters(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Results below threshold are excluded."""
        # The threshold filter is applied in SQL via `>= :threshold`
        # We verify the threshold param is passed in the SQL call
        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(similarity=0.95),
            _make_db_row(similarity=0.80),
        ]

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="test",
            similarity_threshold=0.75,
        )

        # Verify threshold was included in params
        call_args, _call_kwargs = mock_session.execute.await_args
        params = call_args[1] if len(call_args) > 1 else {}
        assert params.get("threshold") == 0.75
        assert len(results) == 2

    async def test_document_ids_filter(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
        sample_document_ids: list[UUID],
    ) -> None:
        """Document IDs filter is passed in SQL params."""
        mock_session.execute.return_value.fetchall.return_value = []

        await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="test",
            document_ids=sample_document_ids,
        )

        call_args, _call_kwargs = mock_session.execute.await_args
        params = call_args[1] if len(call_args) > 1 else {}
        # Verify document IDs appear in params
        assert "doc_id_0" in params
        assert params["doc_id_0"] == str(sample_document_ids[0])

    async def test_clause_types_filter(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Clause types filter is passed in SQL params."""
        mock_session.execute.return_value.fetchall.return_value = []

        await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="test",
            clause_types=["indemnification", "termination"],
        )

        call_args, _call_kwargs = mock_session.execute.await_args
        params = call_args[1] if len(call_args) > 1 else {}
        assert "clause_0" in params
        assert params["clause_0"] == "indemnification"

    async def test_empty_results(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Empty results return empty list with metrics."""
        mock_session.execute.return_value.fetchall.return_value = []

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="nonexistent content",
        )

        assert len(results) == 0
        assert metrics.total_results == 0

    async def test_limit_capped(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Limit is capped at MAX_RESULTS_HARD_LIMIT."""
        from app.domains.vectors.services.vector_search_service import (
            MAX_RESULTS_HARD_LIMIT,
        )

        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(similarity=0.9) for _ in range(MAX_RESULTS_HARD_LIMIT)
        ]

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="test",
            limit=200,  # Above max
        )

        # Verify the limit param was capped
        call_args, _call_kwargs = mock_session.execute.await_args
        params = call_args[1] if len(call_args) > 1 else {}
        assert params["limit"] == MAX_RESULTS_HARD_LIMIT
        assert len(results) == MAX_RESULTS_HARD_LIMIT

    async def test_embedding_dimension_validated(
        self,
        mock_session: MagicMock,
        mock_embedding_service: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Wrong embedding dimension raises InvalidDimensionError."""
        mock_embedding_service.generate_embedding.return_value = [0.1] * 512  # Wrong
        service = VectorSearchService(
            session=mock_session,
            embedding_service=mock_embedding_service,
        )

        with pytest.raises(InvalidDimensionError, match=str(EMBEDDING_DIMENSION)):
            await service.semantic_search(
                tenant_id=sample_tenant_id,
                query="test",
            )

    async def test_embedding_service_error_propagates(
        self,
        mock_session: MagicMock,
        mock_embedding_service: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Embedding service errors are wrapped in VectorSearchError."""
        mock_embedding_service.generate_embedding.side_effect = Exception(
            "API connection failed"
        )
        service = VectorSearchService(
            session=mock_session,
            embedding_service=mock_embedding_service,
        )

        with pytest.raises(VectorSearchError, match="Failed to generate"):
            await service.semantic_search(
                tenant_id=sample_tenant_id,
                query="test",
            )

    async def test_search_result_fields_populated(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """All SearchResult fields are correctly populated from DB rows."""
        chunk_id = UUID("44444444-4444-4444-4444-444444444444")
        upload_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(
                chunk_id=chunk_id,
                upload_id=upload_id,
                text="Specific contract clause text",
                similarity=0.95,
                page_numbers=[3, 4],
                clause_type="indemnification",
            ),
        ]

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="indemnification",
        )

        assert len(results) == 1
        result = results[0]
        assert result.chunk_id == chunk_id
        assert result.upload_id == upload_id
        assert result.text == "Specific contract clause text"
        assert result.similarity_score == 0.95
        assert result.page_numbers == [3, 4]
        assert result.clause_type == "indemnification"
        assert isinstance(result.metadata, dict)


# ── VectorSearchService: hybrid_search ────────────────────────────────────────


class TestHybridSearch:
    """Verify hybrid search (vector + keyword RRF fusion)."""

    async def test_hybrid_search_basic(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Hybrid search returns RRF-fused results."""
        chunk_id_a = UUID("aaaaaaaa-1aaa-aaaa-aaaa-aaaaaaaaaaaa")
        chunk_id_b = UUID("bbbbbbbb-2bbb-bbbb-bbbb-bbbbbbbbbbbb")
        upload_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

        # Vector search returns chunk A and B
        # Keyword search returns chunk A (boosted)
        # side_effect for AsyncMock: return values in order
        kw_result = MagicMock()
        kw_result.fetchall.return_value = [
            _make_keyword_row(chunk_id=chunk_id_a, score=0.8),
        ]

        vec_result = MagicMock()
        vec_result.fetchall.return_value = [
            _make_db_row(chunk_id=chunk_id_a, upload_id=upload_id, similarity=0.9),
            _make_db_row(chunk_id=chunk_id_b, upload_id=upload_id, similarity=0.7),
        ]

        mock_session.execute.side_effect = [vec_result, kw_result]

        results, metrics = await vector_search_service.hybrid_search(
            tenant_id=sample_tenant_id,
            query="indemnification clause",
            similarity_threshold=0.0,  # RRF scores are small fractions
        )

        # Chunk A appears in both lists so it should be ranked first
        assert len(results) >= 1
        assert results[0].chunk_id == chunk_id_a
        assert metrics.strategy == "hybrid"

    async def test_hybrid_empty_query_raises(
        self,
        vector_search_service: VectorSearchService,
        sample_tenant_id: UUID,
    ) -> None:
        """Empty query raises EmptyQueryError."""
        with pytest.raises(EmptyQueryError, match="empty after cleaning"):
            await vector_search_service.hybrid_search(
                tenant_id=sample_tenant_id,
                query="",
            )

    async def test_hybrid_missing_tenant_raises(
        self,
        vector_search_service: VectorSearchService,
    ) -> None:
        """Missing tenant_id raises TenantIsolationError."""
        with pytest.raises(TenantIsolationError, match="tenant_id is required"):
            await vector_search_service.hybrid_search(
                tenant_id=UUID(int=0),
                query="test",
            )

    async def test_hybrid_empty_results(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Empty hybrid results return empty list."""
        mock_session.execute.return_value.fetchall.return_value = []

        results, metrics = await vector_search_service.hybrid_search(
            tenant_id=sample_tenant_id,
            query="nonexistent",
        )

        assert len(results) == 0
        assert metrics.total_results == 0

    async def test_hybrid_document_filter(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
        sample_document_ids: list[UUID],
    ) -> None:
        """Document filter is applied to both vector and keyword searches."""
        mock_session.execute.return_value.fetchall.return_value = []

        await vector_search_service.hybrid_search(
            tenant_id=sample_tenant_id,
            query="test",
            document_ids=sample_document_ids,
        )

        # Should have been called twice (vector + keyword)
        assert mock_session.execute.await_count == 2

    async def test_hybrid_similarity_threshold(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Threshold filters low-scoring results after fusion."""
        mock_session.execute.return_value.fetchall.return_value = []

        results, metrics = await vector_search_service.hybrid_search(
            tenant_id=sample_tenant_id,
            query="test",
            similarity_threshold=1.5,  # Above max possible score
        )

        assert len(results) == 0


# ── VectorSearchService: Tenant Isolation ─────────────────────────────────────


class TestTenantIsolation:
    """Verify strict tenant isolation in all search operations."""

    async def test_tenant_a_cannot_see_tenant_b_data(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
    ) -> None:
        """Tenant A search should not return Tenant B data."""
        tenant_a = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        mock_session.execute.return_value.fetchall.return_value = []

        await vector_search_service.semantic_search(
            tenant_id=tenant_a,
            query="confidential",
        )

        call_args, _call_kwargs = mock_session.execute.await_args
        params = call_args[1] if len(call_args) > 1 else {}
        assert params.get("tenant_id") == str(tenant_a)

    async def test_cross_tenant_prevention(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
    ) -> None:
        """Different tenant IDs produce different SQL params."""
        tenant_a = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        tenant_b = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

        mock_session.execute.return_value.fetchall.return_value = []

        await vector_search_service.semantic_search(
            tenant_id=tenant_a, query="test"
        )
        call_args_a, _ = mock_session.execute.await_args
        params_a = call_args_a[1]["tenant_id"] if len(call_args_a) > 1 else ""

        await vector_search_service.semantic_search(
            tenant_id=tenant_b, query="test"
        )
        call_args_b, _ = mock_session.execute.await_args
        params_b = call_args_b[1]["tenant_id"] if len(call_args_b) > 1 else ""

        assert params_a != params_b


# ── VectorSearchService: Ranking Correctness ──────────────────────────────────


class TestRankingCorrectness:
    """Verify ranking order and score correctness."""

    async def test_results_ordered_by_similarity_desc(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Results are returned in descending similarity order."""
        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(similarity=0.95),
            _make_db_row(similarity=0.85),
            _make_db_row(similarity=0.75),
        ]

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="test",
        )

        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)

    async def test_rrf_boost_for_overlapping_results(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Results appearing in both vector and keyword get boosted fusion score."""
        chunk_id = UUID("aaaaaaaa-1aaa-aaaa-aaaa-aaaaaaaaaaaa")

        kw_result = MagicMock()
        kw_result.fetchall.return_value = [
            _make_keyword_row(chunk_id=chunk_id, score=0.9),
        ]

        vec_result = MagicMock()
        vec_result.fetchall.return_value = [
            _make_db_row(chunk_id=chunk_id, similarity=0.9),
        ]

        mock_session.execute.side_effect = [vec_result, kw_result]

        results, metrics = await vector_search_service.hybrid_search(
            tenant_id=sample_tenant_id,
            query="test",
            similarity_threshold=0.0,  # RRF scores are small fractions
        )

        # Fusion score for chunk in both lists = VECTOR_WEIGHT/(RRF_K+0) + KEYWORD_WEIGHT/(RRF_K+0)
        expected_fusion = VECTOR_WEIGHT / (RRF_K + 0) + KEYWORD_WEIGHT / (RRF_K + 0)
        assert len(results) == 1
        assert results[0].similarity_score == pytest.approx(expected_fusion)


# ── VectorSearchService: Index Management ─────────────────────────────────────


class TestIndexManagement:
    """Verify pgvector index creation."""

    async def test_ensure_indexes_creates_hnsw(
        self,
        mock_session: MagicMock,
    ) -> None:
        """ensure_indexes creates HNSW and GIN indexes."""
        mock_session.execute = AsyncMock()

        results = await VectorSearchService.ensure_indexes(mock_session)

        assert "idx_chunks_embedding_hnsw" in results
        assert "idx_chunks_text_fts" in results
        # Should have called execute twice
        assert mock_session.execute.await_count == 2

    async def test_ensure_indexes_handles_failure(
        self,
        mock_session: MagicMock,
    ) -> None:
        """ensure_indexes handles index creation failures gracefully."""
        mock_session.execute = AsyncMock()
        mock_session.execute.side_effect = Exception("permission denied")

        results = await VectorSearchService.ensure_indexes(mock_session)

        # Should still return results with failure info
        assert "idx_chunks_embedding_hnsw" in results
        assert "failed" in results["idx_chunks_embedding_hnsw"]


# ── VectorSearchService: Edge Cases ───────────────────────────────────────────


class TestVectorSearchEdgeCases:
    """Verify edge case handling."""

    async def test_control_chars_in_query_stripped(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Control characters are stripped from query before embedding."""
        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(similarity=0.9),
        ]

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="valid\x00query\x01text",
        )

        assert len(results) == 1
        # Embedding service should have been called with cleaned text
        call_args = vector_search_service._embedding_service.generate_embedding.await_args
        assert call_args is not None
        assert "\x00" not in call_args[0]
        assert "\x01" not in call_args[0]

    async def test_single_result(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Single result is handled correctly."""
        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(similarity=0.95),
        ]

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="specific term",
            limit=1,
        )

        assert len(results) == 1

    async def test_limit_one_returns_one(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Limit=1 returns at most 1 result."""
        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(similarity=0.95),
        ]

        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query="test",
            limit=1,
        )

        assert len(results) == 1
        call_args, _call_kwargs = mock_session.execute.await_args
        params = call_args[1] if len(call_args) > 1 else {}
        assert params["limit"] == 1

    async def test_very_long_query(
        self,
        vector_search_service: VectorSearchService,
        mock_session: MagicMock,
        sample_tenant_id: UUID,
    ) -> None:
        """Very long queries are handled without error."""
        mock_session.execute.return_value.fetchall.return_value = [
            _make_db_row(similarity=0.9),
        ]

        long_query = "test " * 5000
        results, metrics = await vector_search_service.semantic_search(
            tenant_id=sample_tenant_id,
            query=long_query,
        )

        assert len(results) == 1
