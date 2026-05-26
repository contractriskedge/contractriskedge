"""Production-grade semantic vector search service using pgvector.

Provides tenant-safe cosine similarity search over chunk embeddings with
optional metadata filtering, hybrid retrieval (vector + keyword RRF fusion),
and comprehensive observability.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.vectors.services.embedding_service import (
    EMBEDDING_DIMENSION,
    EmbeddingService,
    EmptyTextError,
    _clean_text,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_LIMIT: int = 10
"""Default number of results to return."""

DEFAULT_SIMILARITY_THRESHOLD: float = 0.75
"""Default cosine similarity threshold (0.0 to 1.0)."""

TOP_K_CANDIDATES: int = 50
"""Number of candidates to fetch from each retrieval strategy before fusion."""

MAX_RESULTS_HARD_LIMIT: int = 100
"""Hard upper bound on returned results."""

RRF_K: int = 60
"""Reciprocal Rank Fusion constant."""

VECTOR_WEIGHT: float = 0.7
"""Weight for vector similarity in hybrid fusion."""

KEYWORD_WEIGHT: float = 0.3
"""Weight for keyword score in hybrid fusion."""


# ── Exceptions ────────────────────────────────────────────────────────────────


class VectorSearchError(Exception):
    """Base exception for vector search failures."""


class EmptyQueryError(VectorSearchError):
    """Raised when the search query is empty after cleaning."""


class TenantIsolationError(VectorSearchError):
    """Raised when a cross-tenant access attempt is detected."""


class InvalidDimensionError(VectorSearchError):
    """Raised when embedding dimension does not match expected value."""


# ── Result Schema ─────────────────────────────────────────────────────────────


@dataclass
class SearchResult:
    """A single ranked search result from semantic vector search.

    All fields are populated from the ``chunks`` table after a pgvector
    cosine similarity (``<=>``) query.
    """

    chunk_id: UUID
    """Unique identifier of the matching chunk."""

    upload_id: UUID
    """Upload session the chunk belongs to."""

    text: str
    """The chunk text content."""

    similarity_score: float
    """Cosine similarity score in range ``[0.0, 1.0]`` (1.0 = identical)."""

    page_numbers: list[int]
    """Page numbers within the source document."""

    clause_type: Optional[str] = None
    """Type of clause if clause-aware chunking was used."""

    metadata: dict = field(default_factory=dict)
    """Additional document metadata from the chunk."""


@dataclass
class SearchMetrics:
    """Observability metrics for a single search operation."""

    query_latency_ms: int = 0
    """Total end-to-end query latency."""

    embedding_latency_ms: int = 0
    """Time spent generating the query embedding."""

    vector_search_latency_ms: int = 0
    """Time spent in pgvector similarity search."""

    total_results: int = 0
    """Number of results returned."""

    strategy: str = "vector"
    """Retrieval strategy used."""


# ── Vector Search Service ─────────────────────────────────────────────────────


class VectorSearchService:
    """Production-grade semantic vector search service using pgvector.

    Performs tenant-safe cosine similarity search over chunk embeddings with
    optional metadata filtering and hybrid retrieval support.

    Workflow:
        1. Generate query embedding via ``EmbeddingService``
        2. Execute pgvector ``<=>`` ANN search with tenant isolation
        3. Apply optional filters (document_ids, clause_types)
        4. Optionally blend with keyword (BM25) scores via RRF
        5. Return ranked ``SearchResult`` list

    Usage::

        service = VectorSearchService(session, embedding_service)
        results = await service.semantic_search(
            tenant_id=UUID("..."),
            query="indemnification clause",
            limit=10,
        )
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
    ) -> None:
        """Initialize the vector search service.

        Args:
            session: Async SQLAlchemy session (tenant-scoped).
            embedding_service: Embedding service for query vectorization.
        """
        self._session = session
        self._embedding_service = embedding_service

    # ── Public API ────────────────────────────────────────────────────────

    async def semantic_search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = DEFAULT_LIMIT,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        document_ids: Optional[list[UUID]] = None,
        clause_types: Optional[list[str]] = None,
    ) -> tuple[list[SearchResult], SearchMetrics]:
        """Execute a tenant-safe semantic vector search.

        Generates a query embedding, performs pgvector cosine similarity search
        with tenant isolation, applies optional filters, and returns ranked chunks.

        Args:
            tenant_id: Tenant UUID — **REQUIRED**. All queries enforce tenant isolation.
            query: Natural language search query.
            limit: Maximum number of results to return (default: 10, max: 100).
            similarity_threshold: Minimum cosine similarity score ``[0.0, 1.0]``.
            document_ids: Optional list of document upload UUIDs to restrict search to.
            clause_types: Optional list of clause types to filter by.

        Returns:
            A tuple of ``(list[SearchResult], SearchMetrics)``.

        Raises:
            EmptyQueryError: If the query is empty after cleaning.
            TenantIsolationError: If tenant_id is missing or invalid.
            VectorSearchError: For unexpected failures.
        """
        # ── Validate ─────────────────────────────────────────────────
        cleaned_query = _clean_text(query)
        if not cleaned_query:
            raise EmptyQueryError("Search query is empty after cleaning")

        if not tenant_id or tenant_id.int == 0:
            raise TenantIsolationError("tenant_id is required for vector search")

        cap_limit = min(max(limit, 1), MAX_RESULTS_HARD_LIMIT)
        metrics = SearchMetrics(strategy="vector")
        overall_start = time.monotonic()

        # ── Step 1: Generate query embedding ────────────────────────
        embed_start = time.monotonic()
        try:
            query_embedding = await self._embedding_service.generate_embedding(
                cleaned_query
            )
        except EmptyTextError as exc:
            raise EmptyQueryError(str(exc)) from exc
        except Exception as exc:
            raise VectorSearchError(f"Failed to generate query embedding: {exc}") from exc

        metrics.embedding_latency_ms = int((time.monotonic() - embed_start) * 1000)

        # Validate embedding dimension
        if len(query_embedding) != EMBEDDING_DIMENSION:
            raise InvalidDimensionError(
                f"Query embedding has dimension {len(query_embedding)}, "
                f"expected {EMBEDDING_DIMENSION}"
            )

        # ── Step 2: Execute pgvector search ─────────────────────────
        search_start = time.monotonic()
        try:
            rows = await self._execute_vector_search(
                tenant_id=tenant_id,
                query_embedding=query_embedding,
                limit=cap_limit,
                similarity_threshold=similarity_threshold,
                document_ids=document_ids,
                clause_types=clause_types,
            )
        except Exception as exc:
            raise VectorSearchError(f"Vector search failed: {exc}") from exc

        metrics.vector_search_latency_ms = int(
            (time.monotonic() - search_start) * 1000
        )

        # ── Step 3: Map to result schema ────────────────────────────
        results = self._rows_to_results(rows)
        metrics.total_results = len(results)
        metrics.query_latency_ms = int((time.monotonic() - overall_start) * 1000)

        # ── Logging ─────────────────────────────────────────────────
        logger.info(
            "Semantic search completed",
            extra={
                "query_length": len(cleaned_query),
                "tenant_id": str(tenant_id),
                "limit": cap_limit,
                "similarity_threshold": similarity_threshold,
                "total_results": metrics.total_results,
                "query_latency_ms": metrics.query_latency_ms,
                "embedding_latency_ms": metrics.embedding_latency_ms,
                "vector_search_latency_ms": metrics.vector_search_latency_ms,
                "document_ids": [str(d) for d in document_ids] if document_ids else None,
                "clause_types": clause_types,
                "strategy": metrics.strategy,
            },
        )

        return results, metrics

    async def hybrid_search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = DEFAULT_LIMIT,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        document_ids: Optional[list[UUID]] = None,
        clause_types: Optional[list[str]] = None,
    ) -> tuple[list[SearchResult], SearchMetrics]:
        """Execute a hybrid search blending vector similarity with keyword (BM25) scores.

        Uses Reciprocal Rank Fusion (RRF) to combine:
            - Vector cosine similarity (weight: 0.7)
            - PostgreSQL full-text BM25 ranking (weight: 0.3)

        Args:
            Same as :meth:`semantic_search`.

        Returns:
            A tuple of ``(list[SearchResult], SearchMetrics)`` with blended ranking.
        """
        cleaned_query = _clean_text(query)
        if not cleaned_query:
            raise EmptyQueryError("Search query is empty after cleaning")

        if not tenant_id or tenant_id.int == 0:
            raise TenantIsolationError("tenant_id is required for hybrid search")

        cap_limit = min(max(limit, 1), MAX_RESULTS_HARD_LIMIT)
        metrics = SearchMetrics(strategy="hybrid")
        overall_start = time.monotonic()

        # ── Step 1: Generate query embedding ────────────────────────
        embed_start = time.monotonic()
        try:
            query_embedding = await self._embedding_service.generate_embedding(
                cleaned_query
            )
        except EmptyTextError as exc:
            raise EmptyQueryError(str(exc)) from exc
        except Exception as exc:
            raise VectorSearchError(
                f"Failed to generate query embedding: {exc}"
            ) from exc

        metrics.embedding_latency_ms = int((time.monotonic() - embed_start) * 1000)

        if len(query_embedding) != EMBEDDING_DIMENSION:
            raise InvalidDimensionError(
                f"Query embedding has dimension {len(query_embedding)}, "
                f"expected {EMBEDDING_DIMENSION}"
            )

        # ── Step 2: Execute vector and keyword searches ─────────────
        search_start = time.monotonic()

        try:
            vector_rows = await self._execute_vector_search(
                tenant_id=tenant_id,
                query_embedding=query_embedding,
                limit=TOP_K_CANDIDATES,
                similarity_threshold=0.0,  # No threshold for candidates
                document_ids=document_ids,
                clause_types=clause_types,
            )

            keyword_rows = await self._execute_keyword_search(
                tenant_id=tenant_id,
                query_text=cleaned_query,
                limit=TOP_K_CANDIDATES,
                document_ids=document_ids,
                clause_types=clause_types,
            )
        except Exception as exc:
            raise VectorSearchError(f"Hybrid search failed: {exc}") from exc

        # ── Step 3: RRF Fusion ──────────────────────────────────────
        fused = self._rrf_fuse(vector_rows, keyword_rows)

        # Apply similarity threshold and limit
        fused = [
            r for r in fused
            if r.similarity_score >= similarity_threshold
        ][:cap_limit]

        metrics.vector_search_latency_ms = int(
            (time.monotonic() - search_start) * 1000
        )
        metrics.total_results = len(fused)
        metrics.query_latency_ms = int((time.monotonic() - overall_start) * 1000)

        logger.info(
            "Hybrid search completed",
            extra={
                "query_length": len(cleaned_query),
                "tenant_id": str(tenant_id),
                "limit": cap_limit,
                "similarity_threshold": similarity_threshold,
                "total_results": metrics.total_results,
                "query_latency_ms": metrics.query_latency_ms,
                "embedding_latency_ms": metrics.embedding_latency_ms,
                "vector_search_latency_ms": metrics.vector_search_latency_ms,
                "vector_candidates": len(vector_rows),
                "keyword_candidates": len(keyword_rows),
                "document_ids": [str(d) for d in document_ids] if document_ids else None,
                "clause_types": clause_types,
                "strategy": "hybrid",
            },
        )

        return fused, metrics

    # ── Internal: pgvector Search ────────────────────────────────────────

    async def _execute_vector_search(
        self,
        tenant_id: UUID,
        query_embedding: list[float],
        limit: int,
        similarity_threshold: float,
        document_ids: Optional[list[UUID]] = None,
        clause_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Execute pgvector cosine similarity (``<=>``) search with filters.

        Uses raw SQL for pgvector ``<=>`` operator access. All queries include
        ``tenant_id`` filter — never returns cross-tenant data.
        """
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        where_clauses = [
            "c.tenant_id = :tenant_id",
            "c.embedding IS NOT NULL",
            "c.is_active = TRUE",
            "c.is_duplicate = FALSE",
        ]
        params: dict = {
            "tenant_id": str(tenant_id),
            "query_embedding": embedding_str,
            "limit": limit,
        }

        if similarity_threshold > 0.0:
            where_clauses.append(
                "1 - (c.embedding <=> :query_embedding::vector) >= :threshold"
            )
            params["threshold"] = similarity_threshold

        if document_ids:
            placeholders = [f":doc_id_{i}" for i in range(len(document_ids))]
            where_clauses.append(
                f"c.upload_id IN ({', '.join(placeholders)})"
            )
            for i, doc_id in enumerate(document_ids):
                params[f"doc_id_{i}"] = str(doc_id)

        if clause_types:
            placeholders = [f":clause_{i}" for i in range(len(clause_types))]
            where_clauses.append(
                f"c.clause_type IN ({', '.join(placeholders)})"
            )
            for i, ct in enumerate(clause_types):
                params[f"clause_{i}"] = ct

        sql = f"""
            SELECT c.chunk_id,
                   c.upload_id,
                   c.text,
                   c.page_numbers,
                   c.clause_type,
                   c.document_metadata AS metadata,
                   1 - (c.embedding <=> :query_embedding::vector) AS similarity
            FROM chunks c
            WHERE {' AND '.join(where_clauses)}
            ORDER BY c.embedding <=> :query_embedding::vector
            LIMIT :limit
        """

        result = await self._session.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "chunk_id": UUID(str(r.chunk_id)),
                "upload_id": UUID(str(r.upload_id)),
                "text": r.text,
                "page_numbers": list(r.page_numbers) if r.page_numbers else [],
                "clause_type": r.clause_type,
                "metadata": dict(r.metadata) if r.metadata else {},
                "similarity": float(r.similarity),
            }
            for r in rows
        ]

    # ── Internal: Keyword Search ─────────────────────────────────────────

    async def _execute_keyword_search(
        self,
        tenant_id: UUID,
        query_text: str,
        limit: int,
        document_ids: Optional[list[UUID]] = None,
        clause_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Execute PostgreSQL full-text search with BM25-style ranking.

        Uses ``ts_rank`` over ``to_tsvector`` for exact term scoring.
        """
        where_clauses = [
            "c.tenant_id = :tenant_id",
            "c.is_active = TRUE",
            "c.is_duplicate = FALSE",
            "to_tsvector('english', c.text) @@ plainto_tsquery('english', :query_text)",
        ]
        params: dict = {
            "tenant_id": str(tenant_id),
            "query_text": query_text,
            "limit": limit,
        }

        if document_ids:
            placeholders = [f":doc_id_{i}" for i in range(len(document_ids))]
            where_clauses.append(
                f"c.upload_id IN ({', '.join(placeholders)})"
            )
            for i, doc_id in enumerate(document_ids):
                params[f"doc_id_{i}"] = str(doc_id)

        if clause_types:
            placeholders = [f":clause_{i}" for i in range(len(clause_types))]
            where_clauses.append(
                f"c.clause_type IN ({', '.join(placeholders)})"
            )
            for i, ct in enumerate(clause_types):
                params[f"clause_{i}"] = ct

        sql = f"""
            SELECT c.chunk_id,
                   c.upload_id,
                   c.text,
                   c.page_numbers,
                   c.clause_type,
                   c.document_metadata AS metadata,
                   ts_rank(to_tsvector('english', c.text),
                           plainto_tsquery('english', :query_text)) AS score
            FROM chunks c
            WHERE {' AND '.join(where_clauses)}
            ORDER BY score DESC
            LIMIT :limit
        """

        result = await self._session.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "chunk_id": UUID(str(r.chunk_id)),
                "upload_id": UUID(str(r.upload_id)),
                "text": r.text,
                "page_numbers": list(r.page_numbers) if r.page_numbers else [],
                "clause_type": r.clause_type,
                "metadata": dict(r.metadata) if r.metadata else {},
                "similarity": float(r.score),
            }
            for r in rows
        ]

    # ── Internal: RRF Fusion ─────────────────────────────────────────────

    def _rrf_fuse(
        self,
        vector_results: list[dict],
        keyword_results: list[dict],
    ) -> list[SearchResult]:
        """Blend vector and keyword results using Reciprocal Rank Fusion.

        Each result's final score is::

            score = VECTOR_WEIGHT / (RRF_K + vector_rank)
                  + KEYWORD_WEIGHT / (RRF_K + keyword_rank)

        Results appearing in both lists get boosted scores.
        """
        scores: dict[UUID, dict] = {}

        for rank, row in enumerate(vector_results):
            cid = row["chunk_id"]
            scores[cid] = {
                "data": row,
                "fusion_score": VECTOR_WEIGHT / (RRF_K + rank),
                "vector_rank": rank,
                "keyword_rank": None,
            }

        for rank, row in enumerate(keyword_results):
            cid = row["chunk_id"]
            if cid in scores:
                scores[cid]["fusion_score"] += KEYWORD_WEIGHT / (RRF_K + rank)
                scores[cid]["keyword_rank"] = rank
            else:
                scores[cid] = {
                    "data": row,
                    "fusion_score": KEYWORD_WEIGHT / (RRF_K + rank),
                    "vector_rank": None,
                    "keyword_rank": rank,
                }

        sorted_items = sorted(
            scores.values(), key=lambda x: x["fusion_score"], reverse=True
        )

        return [
            SearchResult(
                chunk_id=item["data"]["chunk_id"],
                upload_id=item["data"]["upload_id"],
                text=item["data"]["text"],
                similarity_score=item["fusion_score"],
                page_numbers=item["data"]["page_numbers"],
                clause_type=item["data"]["clause_type"],
                metadata=item["data"]["metadata"],
            )
            for item in sorted_items
        ]

    # ── Internal: Row Mapping ────────────────────────────────────────────

    @staticmethod
    def _rows_to_results(rows: list[dict]) -> list[SearchResult]:
        """Map raw query result rows to ``SearchResult`` dataclasses."""
        return [
            SearchResult(
                chunk_id=r["chunk_id"],
                upload_id=r["upload_id"],
                text=r["text"],
                similarity_score=r["similarity"],
                page_numbers=r["page_numbers"],
                clause_type=r["clause_type"],
                metadata=r["metadata"],
            )
            for r in rows
        ]

    # ── Index Management ─────────────────────────────────────────────────

    @staticmethod
    async def ensure_indexes(session: AsyncSession) -> dict[str, str]:
        """Create pgvector indexes if they do not already exist.

        Creates:
            - ``idx_chunks_embedding_hnsw``: HNSW index on ``chunks.embedding``
              for approximate nearest neighbor search.

        HNSW is preferred over IVFFlat for production due to better recall
        and faster query times, at the cost of slower index build and
        higher memory usage.

        Returns:
            Dict mapping index name to status (``"created"`` or ``"already_exists"``).
        """
        results: dict[str, str] = {}

        # HNSW index on embedding column
        # Uses vector_cosine_ops for cosine distance (<=> operator)
        hnsw_sql = """
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
            ON chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 200);
        """
        try:
            await session.execute(text(hnsw_sql))
            results["idx_chunks_embedding_hnsw"] = "created"
            logger.info("Created HNSW index on chunks.embedding")
        except Exception as exc:
            logger.warning("Failed to create HNSW index: %s", exc)
            results["idx_chunks_embedding_hnsw"] = f"failed: {exc}"

        # Also ensure a GIN index on the full-text search vector
        gin_sql = """
            CREATE INDEX IF NOT EXISTS idx_chunks_text_fts
            ON chunks
            USING gin (to_tsvector('english', text));
        """
        try:
            await session.execute(text(gin_sql))
            results["idx_chunks_text_fts"] = "created"
            logger.info("Created GIN index on chunks.text FTS")
        except Exception as exc:
            logger.warning("Failed to create GIN index: %s", exc)
            results["idx_chunks_text_fts"] = f"failed: {exc}"

        return results
