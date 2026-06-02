"""Retrieval snapshot service — freezes retrieval context for reproducible AI execution.

Every AI execution involving retrieval MUST create a snapshot to ensure that
replaying the same execution_id produces identical context chunks.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.snapshots.models import (
    RetrievalSnapshot,
    RetrievalSnapshotChunk,
    SnapshotStatus,
)
from app.domains.vectors.models import Chunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievalSnapshotService:
    """Creates and manages retrieval snapshots for AI execution reproducibility."""

    session: AsyncSession
    tenant_id: str

    async def create_snapshot(
        self,
        execution_id: str,
        upload_id: str,
        query_text: str,
        chunks: Sequence[Chunk],
        embedding_model: str = "text-embedding-3-large",
        embedding_model_version: str | None = None,
        embedding_dimension: int = 1536,
        retrieval_strategy: str = "semantic_search",
        max_documents: int = 10,
        similarity_threshold: float = 0.75,
        reranker_model: str | None = None,
        reranker_version: str | None = None,
        vector_collection_version: str | None = None,
        vector_collection_id: str | None = None,
        preprocessing_pipeline_version: str | None = None,
        chunking_strategy: str | None = None,
        chunking_parameters: dict[str, Any] | None = None,
        scores: list[float] | None = None,
        rerank_scores: list[float] | None = None,
    ) -> RetrievalSnapshot:
        """Create a frozen retrieval snapshot for an AI execution.

        Args:
            execution_id: The AI execution this snapshot belongs to.
            upload_id: The source upload/document.
            query_text: The retrieval query used.
            chunks: The retrieved chunks (in ranked order).
            scores: Similarity scores corresponding to chunks (same order).
            rerank_scores: Reranker scores corresponding to chunks (same order).

        Returns:
            The created RetrievalSnapshot.
        """
        total_tokens = sum(getattr(c, "token_count", 0) or 0 for c in chunks)

        # Build a content hash for integrity verification
        hash_input = "|".join(
            f"{getattr(c, 'chunk_id', '')}:{c.chunk_index}:{getattr(c, 'checksum', '')}"
            for c in chunks
        )
        snapshot_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        snapshot = RetrievalSnapshot(
            execution_id=execution_id,
            tenant_id=self.tenant_id,
            embedding_model=embedding_model,
            embedding_model_version=embedding_model_version,
            embedding_dimension=embedding_dimension,
            retrieval_strategy=retrieval_strategy,
            max_documents=max_documents,
            similarity_threshold=similarity_threshold,
            reranker_model=reranker_model,
            reranker_version=reranker_version,
            vector_collection_version=vector_collection_version,
            vector_collection_id=vector_collection_id,
            preprocessing_pipeline_version=preprocessing_pipeline_version,
            chunking_strategy=chunking_strategy,
            chunking_parameters=chunking_parameters or {},
            total_chunks_snapshotted=len(chunks),
            total_tokens_snapshotted=total_tokens,
            snapshot_hash=snapshot_hash,
            status=SnapshotStatus.COMPLETED,
            query_text=query_text,
            upload_id=upload_id,
        )
        self.session.add(snapshot)
        await self.session.flush()

        # Persist individual chunk records
        snapshot_chunks = []
        for rank, chunk in enumerate(chunks):
            score = scores[rank] if scores and rank < len(scores) else None
            r_score = rerank_scores[rank] if rerank_scores and rank < len(rerank_scores) else None
            final = r_score if r_score is not None else score

            snapshot_chunks.append(
                RetrievalSnapshotChunk(
                    snapshot_id=snapshot.snapshot_id,
                    chunk_id=getattr(chunk, "chunk_id", None),
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    page_numbers=getattr(chunk, "page_numbers", []) or [],
                    section_heading=getattr(chunk, "section_heading", None),
                    clause_type=getattr(chunk, "clause_type", None),
                    token_count=getattr(chunk, "token_count", 0) or 0,
                    rank=rank,
                    similarity_score=score,
                    rerank_score=r_score,
                    final_score=final,
                    upload_id=upload_id,
                )
            )

        self.session.add_all(snapshot_chunks)
        await self.session.flush()

        logger.info(
            "Created retrieval snapshot %s for execution %s with %d chunks (hash=%s)",
            snapshot.snapshot_id,
            execution_id,
            len(chunks),
            snapshot_hash[:12],
        )

        return snapshot

    async def get_snapshot_by_execution(
        self, execution_id: str
    ) -> RetrievalSnapshot | None:
        """Get the retrieval snapshot for a given execution ID."""
        stmt = (
            select(RetrievalSnapshot)
            .where(
                RetrievalSnapshot.execution_id == execution_id,
                RetrievalSnapshot.tenant_id == self.tenant_id,
            )
            .order_by(RetrievalSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_snapshot_chunks(
        self, snapshot_id: str
    ) -> list[RetrievalSnapshotChunk]:
        """Get all chunks in a snapshot, ordered by rank."""
        stmt = (
            select(RetrievalSnapshotChunk)
            .where(RetrievalSnapshotChunk.snapshot_id == snapshot_id)
            .order_by(RetrievalSnapshotChunk.rank)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def invalidate_snapshot(self, snapshot_id: str) -> None:
        """Mark a snapshot as stale (e.g., when underlying data changes)."""
        stmt = (
            update(RetrievalSnapshot)
            .where(RetrievalSnapshot.snapshot_id == snapshot_id)
            .values(
                status=SnapshotStatus.STALE,
                invalidated_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
        logger.info("Invalidated retrieval snapshot %s", snapshot_id)

    async def verify_snapshot_integrity(
        self, snapshot_id: str
    ) -> tuple[bool, str | None]:
        """Verify that a snapshot's content hash matches its stored hash.

        Returns:
            (is_valid, error_message)
        """
        stmt = select(RetrievalSnapshot).where(
            RetrievalSnapshot.snapshot_id == snapshot_id,
            RetrievalSnapshot.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            return False, "Snapshot not found"

        chunks = await self.get_snapshot_chunks(snapshot_id)
        hash_input = "|".join(
            f"{c.chunk_id}:{c.chunk_index}:{getattr(c, 'text', '')[:64]}"
            for c in chunks
        )
        computed = hashlib.sha256(hash_input.encode()).hexdigest()

        if computed != snapshot.snapshot_hash:
            return False, f"Hash mismatch: stored={snapshot.snapshot_hash[:12]} computed={computed[:12]}"

        return True, None
