"""Vector repository — pgvector CRUD operations, ANN queries, and chunk persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.repository.base import BaseRepository
from app.domains.vectors.models import Chunk, EmbeddingRun, EmbeddingFailure, EmbeddingStatus
from app.domains.vectors.chunking import ChunkData


@dataclass
class VectorRepository(BaseRepository):
    """Repository for chunk and embedding operations with pgvector support."""

    async def store_chunk(self, upload_id: str, tenant_id: str, chunk: ChunkData) -> Chunk:
        """Store a single chunk without embedding (set after generation)."""
        db_chunk = Chunk(
            upload_id=upload_id,
            tenant_id=tenant_id,
            chunk_index=chunk.chunk_index,
            page_numbers=chunk.page_numbers,
            text=chunk.text,
            text_length=chunk.char_count,
            token_count=chunk.token_count,
            chunking_strategy="semantic",
            section_heading=chunk.section_heading,
            clause_type=chunk.clause_type,
            checksum=chunk.checksum,
            embedding_status=EmbeddingStatus.PENDING,
        )
        self.session.add(db_chunk)
        await self.session.flush()
        return db_chunk

    async def store_chunks_bulk(self, upload_id: str, tenant_id: str, chunks: list[ChunkData]) -> list[Chunk]:
        """Store multiple chunks in bulk."""
        db_chunks = []
        for chunk in chunks:
            db_chunks.append(Chunk(
                upload_id=upload_id,
                tenant_id=tenant_id,
                chunk_index=chunk.chunk_index,
                page_numbers=chunk.page_numbers,
                text=chunk.text,
                text_length=chunk.char_count,
                token_count=chunk.token_count,
                chunking_strategy="semantic",
                section_heading=chunk.section_heading,
                clause_type=chunk.clause_type,
                checksum=chunk.checksum,
                embedding_status=EmbeddingStatus.PENDING,
            ))
        self.session.add_all(db_chunks)
        await self.session.flush()
        return db_chunks

    async def get_chunks_by_upload(self, upload_id: str, tenant_id: str):
        stmt = (
            select(Chunk)
            .where(Chunk.upload_id == upload_id, Chunk.tenant_id == tenant_id)
            .order_by(Chunk.chunk_index)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pending_chunks(self, upload_id: str, tenant_id: str, limit: int = 100):
        stmt = (
            select(Chunk)
            .where(
                Chunk.upload_id == upload_id,
                Chunk.tenant_id == tenant_id,
                Chunk.embedding_status == EmbeddingStatus.PENDING,
                Chunk.is_active == True,
                Chunk.is_duplicate == False,
            )
            .order_by(Chunk.chunk_index)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_embedding(
        self, chunk_id: str, tenant_id: str,
        embedding: list[float], model: str, dimension: int, token_count: int,
    ) -> None:
        """Update chunk with generated embedding."""
        stmt = (
            update(Chunk)
            .where(Chunk.chunk_id == chunk_id, Chunk.tenant_id == tenant_id)
            .values(
                embedding=embedding,
                embedding_model=model,
                embedding_dimension=dimension,
                embedding_status=EmbeddingStatus.COMPLETED,
                token_count=token_count,
            )
        )
        await self.session.execute(stmt)

    async def mark_duplicate(self, chunk_id: str, tenant_id: str) -> None:
        stmt = (
            update(Chunk)
            .where(Chunk.chunk_id == chunk_id, Chunk.tenant_id == tenant_id)
            .values(is_duplicate=True, embedding_status=EmbeddingStatus.COMPLETED)
        )
        await self.session.execute(stmt)

    async def mark_failed(self, chunk_id: str, tenant_id: str, error: str) -> None:
        stmt = (
            update(Chunk)
            .where(Chunk.chunk_id == chunk_id, Chunk.tenant_id == tenant_id)
            .values(embedding_status=EmbeddingStatus.FAILED)
        )
        await self.session.execute(stmt)

    async def count_by_upload(self, upload_id: str, tenant_id: str) -> int:
        stmt = select(func.count()).select_from(Chunk).where(
            Chunk.upload_id == upload_id, Chunk.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def create_run(self, upload_id: str, tenant_id: str, model: str, dimension: int) -> EmbeddingRun:
        run = EmbeddingRun(
            upload_id=upload_id,
            tenant_id=tenant_id,
            model=model,
            dimension=dimension,
            status=EmbeddingStatus.PROCESSING,
            started_at=datetime.utcnow(),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def complete_run(
        self, run_id: str, total_chunks: int, chunks_embedded: int,
        total_tokens: int, total_cost_usd: float, avg_latency_ms: int,
    ) -> None:
        stmt = (
            update(EmbeddingRun)
            .where(EmbeddingRun.run_id == run_id)
            .values(
                status=EmbeddingStatus.COMPLETED,
                total_chunks=total_chunks,
                chunks_embedded=chunks_embedded,
                total_tokens=total_tokens,
                total_cost_usd=total_cost_usd,
                avg_latency_ms=avg_latency_ms,
                completed_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)

    async def record_failure(
        self, upload_id: str, tenant_id: str, failure_type: str,
        error_message: str, chunk_id: Optional[str] = None, model: Optional[str] = None,
    ) -> EmbeddingFailure:
        failure = EmbeddingFailure(
            upload_id=upload_id,
            tenant_id=tenant_id,
            chunk_id=chunk_id,
            failure_type=failure_type,
            error_message=error_message,
            model_attempted=model,
        )
        self.session.add(failure)
        await self.session.flush()
        return failure

    # ── Vector Search Queries ──────────────────────────────────────

    async def vector_search(
        self, tenant_id: str, query_embedding: list[float],
        limit: int = 20, filters: Optional[dict] = None,
    ):
        """Cosine similarity search with tenant isolation."""
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        where_clauses = [
            "c.tenant_id = :tenant_id",
            "c.embedding IS NOT NULL",
            "c.is_active = TRUE",
            "c.is_duplicate = FALSE",
        ]
        params = {"tenant_id": tenant_id, "limit": limit}

        sql = f"""
            SELECT c.chunk_id, c.text, c.page_numbers, c.section_heading,
                   c.token_count, c.upload_id,
                   1 - (c.embedding <=> :query_embedding::vector) AS similarity
            FROM chunks c
            WHERE {' AND '.join(where_clauses)}
            ORDER BY c.embedding <=> :query_embedding::vector
            LIMIT :limit
        """
        params["query_embedding"] = embedding_str

        result = await self.session.execute(text(sql), params)
        return result.fetchall()

    async def hybrid_search(
        self, tenant_id: str, query_text: str, query_embedding: list[float],
        limit: int = 20,
    ):
        """BM25 + vector hybrid search via RRF."""
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        sql = """
            WITH vector_results AS (
                SELECT chunk_id, text, 1 - (embedding <=> :query_embedding::vector) AS score
                FROM chunks
                WHERE tenant_id = :tenant_id
                  AND embedding IS NOT NULL
                  AND is_active = TRUE
                  AND is_duplicate = FALSE
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT 50
            ),
            bm25_results AS (
                SELECT chunk_id, text,
                       ts_rank(to_tsvector('english', text), plainto_tsquery('english', :query_text)) AS score
                FROM chunks
                WHERE tenant_id = :tenant_id
                  AND to_tsvector('english', text) @@ plainto_tsquery('english', :query_text)
                  AND is_active = TRUE
                  AND is_duplicate = FALSE
                ORDER BY score DESC
                LIMIT 50
            ),
            fused AS (
                SELECT chunk_id, text,
                       COALESCE(0.7 / (60 + ROW_NUMBER() OVER (ORDER BY v.score DESC)), 0) +
                       COALESCE(0.3 / (60 + ROW_NUMBER() OVER (ORDER BY b.score DESC)), 0) AS fusion_score
                FROM vector_results v
                FULL OUTER JOIN bm25_results b USING (chunk_id)
            )
            SELECT chunk_id, text, fusion_score AS score
            FROM fused
            ORDER BY fusion_score DESC
            LIMIT :limit
        """
        result = await self.session.execute(text(sql), {
            "tenant_id": tenant_id,
            "query_text": query_text,
            "query_embedding": embedding_str,
            "limit": limit,
        })
        return result.fetchall()
