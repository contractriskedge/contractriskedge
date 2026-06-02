"""Retrieval snapshot SQLAlchemy models for reproducible AI execution.

A retrieval snapshot freezes the exact retrieval state at execution time so
that replaying the same execution_id produces identical context chunks.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


class SnapshotStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"  # Underlying data changed, snapshot invalidated


class RetrievalSnapshot(Base):
    """Freezes the retrieval context for a single AI execution.

    This is the root entity for reproducibility. Every AI execution that
    involves retrieval MUST create a snapshot before execution.
    """
    __tablename__ = "retrieval_snapshots"

    snapshot_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID, nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    # Embedding model version — critical for reproducibility
    embedding_model = Column(Text, nullable=False)
    embedding_model_version = Column(Text, nullable=True)
    embedding_dimension = Column(Integer, nullable=False, default=1536)

    # Retrieval configuration frozen at execution time
    retrieval_strategy = Column(Text, nullable=False, default="semantic_search")
    max_documents = Column(Integer, nullable=False, default=10)
    similarity_threshold = Column(Float, nullable=False, default=0.75)
    reranker_model = Column(Text, nullable=True)
    reranker_version = Column(Text, nullable=True)

    # Vector DB state at snapshot time
    vector_collection_version = Column(Text, nullable=True)
    vector_collection_id = Column(Text, nullable=True)

    # Preprocessing version — text extraction pipeline
    preprocessing_pipeline_version = Column(Text, nullable=True)
    chunking_strategy = Column(Text, nullable=True)
    chunking_parameters = Column(JSONB, nullable=True, default=dict)

    # Snapshot metadata
    total_chunks_snapshotted = Column(Integer, nullable=False, default=0)
    total_tokens_snapshotted = Column(Integer, nullable=False, default=0)
    snapshot_hash = Column(Text, nullable=True)  # SHA-256 of all chunk IDs + versions

    status = Column(
        SAEnum("pending", "completed", "failed", "stale", name="snapshot_status", create_type=True),
        nullable=False,
        default=SnapshotStatus.PENDING,
    )

    # Provenance
    query_text = Column(Text, nullable=True)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    invalidated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Ensures fast lookup by execution_id for replay
        # Index on execution_id already defined above
    )


class RetrievalSnapshotChunk(Base):
    """An individual chunk within a retrieval snapshot.

    Preserves the exact chunk content, rank, and relevance score at execution time.
    """
    __tablename__ = "retrieval_snapshot_chunks"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(UUID, ForeignKey("retrieval_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(UUID, ForeignKey("chunks.chunk_id", ondelete="SET NULL"), nullable=True)

    # Frozen content — even if the original chunk is later modified
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    page_numbers = Column(ARRAY(Integer), nullable=False, default=list)
    section_heading = Column(Text, nullable=True)
    clause_type = Column(Text, nullable=True)
    token_count = Column(Integer, nullable=False, default=0)

    # Retrieval ranking at snapshot time
    rank = Column(Integer, nullable=False)
    similarity_score = Column(Float, nullable=True)
    rerank_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    # Provenance
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
