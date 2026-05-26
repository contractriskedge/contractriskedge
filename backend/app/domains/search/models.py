"""Search and retrieval SQLAlchemy models — query logging, click tracking, semantic cache, and metrics."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    BigInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


class SearchQuery(Base):
    """Logs every search query for analytics, quality monitoring, and future ranking training."""
    __tablename__ = "search_queries"

    query_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Text, nullable=True, index=True)

    query_text = Column(Text, nullable=False)
    normalized_query = Column(Text, nullable=True)  # Lowercased, stemmed version
    query_type = Column(Text, nullable=True)  # 'semantic', 'keyword', 'hybrid', 'clause', 'contract'

    result_count = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False)
    retrieval_strategy = Column(Text, nullable=True)  # 'vector_only', 'bm25_only', 'hybrid'

    filters = Column(JSONB, nullable=False, default=dict)
    search_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class SearchClick(Base):
    """Tracks which search results users clicked — for ranking model training."""
    __tablename__ = "search_clicks"

    click_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID, ForeignKey("search_queries.query_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    result_position = Column(Integer, nullable=False)  # 0-based position in results
    result_entity_type = Column(Text, nullable=False)  # 'chunk', 'contract', 'clause'
    result_entity_id = Column(UUID, nullable=False)
    chunk_id = Column(UUID, ForeignKey("chunks.chunk_id", ondelete="SET NULL"), nullable=True)

    score = Column(Float, nullable=True)  # The score at time of display
    dwell_time_ms = Column(Integer, nullable=True)
    was_conversion = Column(Boolean, nullable=True)  # User took action on result

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SemanticCacheEntry(Base):
    """Caches search results for semantically similar queries — tenant-isolated."""
    __tablename__ = "semantic_cache"

    cache_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    query_hash = Column(Text, nullable=False, index=True)  # SHA-256 of normalized query
    query_embedding = Column(Float, nullable=True)  # vector(1536) — for similarity matching
    query_text = Column(Text, nullable=False)

    results = Column(JSONB, nullable=False)  # Cached search results
    result_count = Column(Integer, nullable=False, default=0)

    hit_count = Column(Integer, nullable=False, default=1)
    last_hit_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ttl_seconds = Column(Integer, nullable=False, default=300)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "query_hash", name="uq_semantic_cache_tenant_query"),
    )


class RetrievalMetric(Base):
    """Aggregated retrieval performance metrics for monitoring."""
    __tablename__ = "retrieval_metrics"

    metric_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    total_queries = Column(Integer, nullable=False, default=0)
    avg_latency_ms = Column(Float, nullable=True)
    p50_latency_ms = Column(Float, nullable=True)
    p95_latency_ms = Column(Float, nullable=True)
    p99_latency_ms = Column(Float, nullable=True)

    zero_result_rate = Column(Float, nullable=True)  # % of queries with 0 results
    avg_result_count = Column(Float, nullable=True)
    cache_hit_rate = Column(Float, nullable=True)

    strategy_breakdown = Column(JSONB, nullable=True)  # {"hybrid": 0.7, "vector": 0.2, "bm25": 0.1}

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
