"""Chunking, embedding, and vector storage SQLAlchemy models.

Tracks the complete chunking and embedding pipeline from extracted text
through semantic chunking, embedding generation, and pgvector storage.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Text,
    BigInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector

from app.kernel.database.base import Base


class ChunkingStrategy(str, Enum):
    SEMANTIC = "semantic"            # Paragraph/section boundaries
    FIXED_SIZE = "fixed_size"        # Fixed token count with overlap
    CLAUSE_AWARE = "clause_aware"    # Respect clause boundaries
    HEADING_AWARE = "heading_aware"  # Split at headings


class EmbeddingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"                  # Model upgraded, needs re-embed


class Chunk(Base):
    """A single semantic chunk of extracted text with its vector embedding.

    This is the HIGHEST VOLUME table. Expected: 100M+ rows at scale.
    Partitioned by HASH(tenant_id) — see production schema.
    """
    __tablename__ = "chunks"

    chunk_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    # Position within source document
    chunk_index = Column(Integer, nullable=False)  # Order within document
    page_numbers = Column(ARRAY(Integer), nullable=False, default=list)

    # Content
    text = Column(Text, nullable=False)
    text_length = Column(Integer, nullable=False, default=0)
    token_count = Column(Integer, nullable=False)

    # Chunking metadata
    chunking_strategy = Column(
        Enum("semantic", "fixed_size", "clause_aware", "heading_aware", name="chunking_strategy", create_type=True),
        nullable=False,
        default=ChunkingStrategy.SEMANTIC,
    )
    section_heading = Column(Text, nullable=True)  # Heading text if heading-aware
    clause_type = Column(Text, nullable=True)       # Clause type if clause-aware

    # Embedding (pgvector)
    embedding = Column(Vector(1536), nullable=True)
    embedding_model = Column(Text, nullable=True, default="text-embedding-3-large")
    embedding_dimension = Column(Integer, nullable=True, default=1536)
    embedding_status = Column(
        Enum("pending", "processing", "completed", "failed", "stale", name="embedding_status", create_type=True),
        nullable=False,
        default=EmbeddingStatus.PENDING,
    )

    # Deduplication
    checksum = Column(Text, nullable=True, index=True)  # SHA-256 of text

    # Lifecycle
    is_active = Column(Boolean, nullable=False, default=True)  # FALSE = re-indexed
    is_duplicate = Column(Boolean, nullable=False, default=False)

    # Metadata
    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("upload_id", "chunk_index", name="uq_chunk_per_upload"),
        CheckConstraint("token_count >= 1", name="ck_chunks_token_count_positive"),
    )


class EmbeddingRun(Base):
    """Tracks a complete embedding generation run for an upload session."""
    __tablename__ = "embedding_runs"

    run_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    model = Column(Text, nullable=False)
    dimension = Column(Integer, nullable=False, default=1536)
    status = Column(
        Enum("pending", "processing", "completed", "failed", "stale", name="embedding_run_status", create_type=True),
        nullable=False,
        default=EmbeddingStatus.PENDING,
    )

    total_chunks = Column(Integer, nullable=False, default=0)
    chunks_embedded = Column(Integer, nullable=False, default=0)
    chunks_failed = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    avg_latency_ms = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)
    retry_number = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmbeddingFailure(Base):
    """Records individual embedding failures for monitoring."""
    __tablename__ = "embedding_failures"

    failure_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(UUID, ForeignKey("chunks.chunk_id", ondelete="SET NULL"), nullable=True)

    failure_type = Column(Text, nullable=False)  # 'timeout', 'rate_limit', 'model_error', 'invalid_response'
    error_message = Column(Text, nullable=False)
    model_attempted = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
