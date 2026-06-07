"""Hybrid retrieval engine — pgvector ANN, BM25 full-text, and RRF fusion with tenant-safe authorization."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.search.repository import SearchRepository
from app.domains.search.telemetry import SearchTelemetry, search_metrics
from app.domains.search.citations import CitationGenerator, Citation
from app.domains.search.reranking import RerankCandidate, reranking_pipeline
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A single retrieved chunk with ranking metadata."""
    chunk_id: str
    upload_id: Optional[str] = None
    contract_id: Optional[str] = None
    contract_name: Optional[str] = None
    text: str = ""
    page_numbers: list[int] = field(default_factory=list)
    section_heading: Optional[str] = None
    clause_type: Optional[str] = None
    token_count: int = 0
    score: float = 0.0
    vector_score: float = 0.0
    bm25_score: float = 0.0
    strategy: str = "hybrid"


@dataclass
class RetrievalResult:
    """Complete retrieval result with metadata."""
    results: list[RetrievedChunk]
    total: int
    query: str
    strategy: str
    latency_ms: int
    citations: list[Citation] = field(default_factory=list)


class RetrievalAuthorizationError(Exception):
    """Raised when a search violates tenant or permission boundaries."""


class HybridRetrievalEngine:
    """Enterprise hybrid retrieval engine with tenant-safe authorization.

    Combines pgvector ANN search with PostgreSQL BM25 full-text search
    via Reciprocal Rank Fusion. All queries enforce tenant isolation.
    """

    RRF_K = 60          # RRF constant
    VECTOR_WEIGHT = 0.7  # Weight for vector similarity scores
    BM25_WEIGHT = 0.3    # Weight for BM25 scores
    TOP_K = 50           # Candidates from each strategy before fusion
    MAX_RESULTS = 100    # Hard limit on returned results

    def __init__(self, session: AsyncSession, tenant_id: str, user: Optional[UserContext] = None):
        if not tenant_id or not str(tenant_id).strip():
            raise ValueError("tenant_id is required for tenant-safe retrieval")
        self.session = session
        self.tenant_id = tenant_id
        self.user = user
        self.repo = SearchRepository(session, tenant_id=tenant_id)

    async def search(
        self,
        query: str,
        strategy: str = "hybrid",
        filters: Optional[dict] = None,
        clause_type: Optional[str] = None,
        contract_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> RetrievalResult:
        """Execute a tenant-safe hybrid search with tracing and citation generation.

        All queries include tenant_id filter. Never returns cross-tenant data.
        """
        span = SearchTelemetry.trace_search(query, strategy, self.tenant_id)
        start = time.monotonic()

        try:
            # Validate tenant context
            if not self.tenant_id:
                raise RetrievalAuthorizationError("Tenant context required for search")

            if strategy == "vector":
                results = await self._vector_search(query, filters, clause_type, contract_id)
            elif strategy == "keyword":
                results = await self._bm25_search(query, filters, clause_type, contract_id)
            else:
                results = await self._hybrid_search(query, filters, clause_type, contract_id)

            # Reranking preparation (V1 identity, V2+ cross-encoder)
            rerank_candidates = [
                RerankCandidate(
                    chunk_id=r.chunk_id, text=r.text, initial_score=r.score,
                    page_numbers=r.page_numbers, section_heading=r.section_heading,
                    clause_type=r.clause_type, token_count=r.token_count,
                )
                for r in results
            ]
            rerank_results = await reranking_pipeline.rerank(query, rerank_candidates)
            rerank_scores = {r.chunk_id: r.reranked_score for r in rerank_results}

            # Apply reranked scores
            for r in results:
                if r.chunk_id in rerank_scores:
                    r.score = rerank_scores[r.chunk_id]

            # Sort by updated score
            results.sort(key=lambda x: x.score, reverse=True)

            # Generate citations
            citations = CitationGenerator.from_chunks(results, max_citations=10)

            # Paginate
            total = len(results)
            start_idx = (page - 1) * page_size
            paginated = results[start_idx:start_idx + page_size]

            latency_ms = int((time.monotonic() - start) * 1000)

            # Record metrics
            search_metrics.record_search(latency_ms, total)

            # Log query
            await self.repo.log_query(
                tenant_id=self.tenant_id,
                user_id=self.user.id if self.user else None,
                query_text=query,
                result_count=total,
                latency_ms=latency_ms,
                strategy=strategy,
                filters=filters,
            )

            SearchTelemetry.set_span_attributes(span, {
                "search.total_results": total,
                "search.latency_ms": latency_ms,
                "search.citations_generated": len(citations),
            })
            SearchTelemetry.end_span(span)

            return RetrievalResult(
                results=paginated,
                total=total,
                query=query,
                strategy=strategy,
                latency_ms=latency_ms,
                citations=citations,
            )

        except Exception as exc:
            SearchTelemetry.end_span(span, error=str(exc))
            raise

    async def _vector_search(
        self, query: str, filters: Optional[dict] = None,
        clause_type: Optional[str] = None, contract_id: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """pgvector ANN cosine similarity search with tenant isolation."""
        # Generate query embedding via OpenAI
        embedding = await self._embed_query(query)
        embedding_str = f"[{','.join(str(x) for x in embedding)}]"

        where = [
            "c.tenant_id = :tenant_id",
            "c.embedding IS NOT NULL",
            "c.is_active = TRUE",
            "c.is_duplicate = FALSE",
        ]
        params = {"tenant_id": self.tenant_id, "limit": self.TOP_K, "query_embedding": embedding_str}

        sql = f"""
            SELECT c.chunk_id, c.upload_id, c.text, c.page_numbers,
                   c.section_heading, c.clause_type, c.token_count,
                   u.filename AS contract_name,
                   1 - (c.embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM chunks c
            LEFT JOIN upload_sessions u ON u.upload_id = c.upload_id AND u.tenant_id = c.tenant_id
            WHERE {' AND '.join(where)}
            ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """
        result = await self.session.execute(text(sql), params)
        rows = result.fetchall()

        return [
            RetrievedChunk(
                chunk_id=str(r.chunk_id), upload_id=str(r.upload_id) if r.upload_id else None,
                contract_name=r.contract_name,
                text=r.text, page_numbers=r.page_numbers or [],
                section_heading=r.section_heading, clause_type=r.clause_type,
                token_count=r.token_count, score=float(r.similarity),
                vector_score=float(r.similarity), bm25_score=0.0, strategy="vector",
            )
            for r in rows
        ]

    async def _bm25_search(
        self, query: str, filters: Optional[dict] = None,
        clause_type: Optional[str] = None, contract_id: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """PostgreSQL BM25 full-text search with tenant isolation."""
        where = [
            "c.tenant_id = :tenant_id",
            "c.is_active = TRUE",
            "c.is_duplicate = FALSE",
        ]
        params = {"tenant_id": self.tenant_id, "query": query, "limit": self.TOP_K}

        sql = f"""
            SELECT c.chunk_id, c.upload_id, c.text, c.page_numbers,
                   c.section_heading, c.clause_type, c.token_count,
                   u.filename AS contract_name,
                   ts_rank(to_tsvector('english', c.text),
                           plainto_tsquery('english', :query)) AS rank
            FROM chunks c
            LEFT JOIN upload_sessions u ON u.upload_id = c.upload_id AND u.tenant_id = c.tenant_id
            WHERE {' AND '.join(where)}
              AND to_tsvector('english', c.text) @@ plainto_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """
        result = await self.session.execute(text(sql), params)
        rows = result.fetchall()

        return [
            RetrievedChunk(
                chunk_id=str(r.chunk_id), upload_id=str(r.upload_id) if r.upload_id else None,
                contract_name=r.contract_name,
                text=r.text, page_numbers=r.page_numbers or [],
                section_heading=r.section_heading, clause_type=r.clause_type,
                token_count=r.token_count, score=float(r.rank),
                vector_score=0.0, bm25_score=float(r.rank), strategy="bm25",
            )
            for r in rows
        ]

    async def _hybrid_search(
        self, query: str, filters: Optional[dict] = None,
        clause_type: Optional[str] = None, contract_id: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """Hybrid search: vector + BM25 fused via Reciprocal Rank Fusion."""
        vector_results = await self._vector_search(query, filters, clause_type, contract_id)
        bm25_results = await self._bm25_search(query, filters, clause_type, contract_id)

        # RRF fusion
        scores: dict[str, dict] = {}

        for rank, r in enumerate(vector_results):
            scores[r.chunk_id] = {
                "chunk": r,
                "fusion_score": self.VECTOR_WEIGHT / (self.RRF_K + rank),
                "vector_rank": rank,
                "bm25_rank": None,
            }

        for rank, r in enumerate(bm25_results):
            if r.chunk_id in scores:
                scores[r.chunk_id]["fusion_score"] += self.BM25_WEIGHT / (self.RRF_K + rank)
                scores[r.chunk_id]["bm25_rank"] = rank
            else:
                scores[r.chunk_id] = {
                    "chunk": r,
                    "fusion_score": self.BM25_WEIGHT / (self.RRF_K + rank),
                    "vector_rank": None,
                    "bm25_rank": rank,
                }

        # Sort by fusion score
        sorted_chunks = sorted(scores.values(), key=lambda x: x["fusion_score"], reverse=True)

        # Build results
        results = []
        for item in sorted_chunks[:self.MAX_RESULTS]:
            chunk = item["chunk"]
            chunk.score = item["fusion_score"]
            chunk.strategy = "hybrid"
            results.append(chunk)

        return results

    async def _embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query using the configured provider.

        Self-initializes the OpenAIEmbeddingProvider if the registry is empty
        (e.g., on fresh application startup before any document ingestion).
        """
        from app.domains.vectors.embeddings import OpenAIEmbeddingProvider, EmbeddingRequest, embedding_registry

        try:
            provider = embedding_registry.get_default()
        except ValueError:
            provider = None

        if not isinstance(provider, OpenAIEmbeddingProvider):
            provider = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
            embedding_registry.register(provider)

        response = await provider.embed(EmbeddingRequest(text=query))
        return response.embedding

    @staticmethod
    def generate_snippet(text: str, query: str, max_length: int = 300) -> str:
        """Generate a highlighted snippet from chunk text centered on query terms."""
        import re
        query_lower = query.lower()
        text_lower = text.lower()

        # Find the first occurrence of any query term
        terms = query_lower.split()
        best_pos = -1
        for term in terms:
            pos = text_lower.find(term)
            if pos != -1 and (best_pos == -1 or pos < best_pos):
                best_pos = pos

        if best_pos == -1:
            # No match — return prefix
            return text[:max_length] + ("..." if len(text) > max_length else "")

        # Center snippet around the match
        start = max(0, best_pos - max_length // 3)
        end = min(len(text), start + max_length)

        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    @staticmethod
    def query_hash(query: str) -> str:
        """Generate a deterministic hash for cache key."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()
