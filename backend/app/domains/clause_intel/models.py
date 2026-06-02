"""Clause Intelligence — SQLAlchemy ORM models for clause management, benchmarking, and AI analysis.

Tables:
- clauses: Core clause records with metadata, risk scoring, and AI analysis
- clause_versions: Version history for clause evolution tracking
- clause_embeddings: Vector embeddings for semantic search and similarity
- clause_benchmarks: Market benchmark data per clause category
- negotiation_history: Tracked negotiation outcomes per clause
- clause_usage: Usage analytics per clause
- fallback_clauses: Preferred fallback language mappings
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, Text, Boolean, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


class ClauseCategory(str, PyEnum):
    INDEMNIFICATION = "indemnification"
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    CONFIDENTIALITY = "confidentiality"
    DATA_PRIVACY = "data_privacy"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    TERMINATION = "termination"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    PAYMENT_TERMS = "payment_terms"
    WARRANTY = "warranty"
    INSURANCE = "insurance"
    COMPLIANCE = "compliance"
    AUDIT_RIGHTS = "audit_rights"
    ASSIGNMENT = "assignment"
    NON_COMPETE = "non_compete"
    NON_SOLICIT = "non_solicit"
    SLA = "sla"
    ESCROW = "escrow"
    GENERAL = "general"


class ClauseType(str, PyEnum):
    CUSTOMER_FAVORABLE = "customer_favorable"
    VENDOR_FAVORABLE = "vendor_favorable"
    NEUTRAL = "neutral"
    MARKET_STANDARD = "market_standard"
    REGULATORY = "regulatory"


class ApprovalStatus(str, PyEnum):
    APPROVED = "approved"
    PENDING_REVIEW = "pending_review"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    FORBIDDEN = "forbidden"


# ── Clauses ─────────────────────────────────────────────────────────


class Clause(Base):
    """Core clause record with AI analysis, risk scoring, and metadata."""
    __tablename__ = "clauses"

    clause_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False, index=True)
    clause_type = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    contract_types = Column(ARRAY(Text), nullable=False, default=list)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_explanation = Column(Text, nullable=True)
    negotiation_strength = Column(Float, nullable=True)
    negotiation_guidance = Column(Text, nullable=True)
    benchmark_percentile = Column(Float, nullable=True)
    usage_frequency = Column(Integer, nullable=False, default=0)
    approval_status = Column(Text, nullable=False, default="draft")
    owner = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_favorite = Column(Boolean, nullable=False, default=False)
    tags = Column(ARRAY(Text), nullable=False, default=list)
    governance_notes = Column(Text, nullable=True)
    deviation_frequency = Column(Integer, nullable=False, default=0)
    market_percentile = Column(Float, nullable=True)
    playbook_linkage = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
class ClauseVersion(Base):
    """Version history for clause evolution tracking."""
    __tablename__ = "clause_versions"

    version_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    clause_id = Column(UUID, ForeignKey("clauses.clause_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    risk_score = Column(Float, nullable=True)
    change_description = Column(Text, nullable=True)
    created_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClauseEmbedding(Base):
    """Vector embeddings for semantic search and similarity matching."""
    __tablename__ = "clause_embeddings"

    embedding_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    clause_id = Column(UUID, ForeignKey("clauses.clause_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_model = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClauseBenchmark(Base):
    """Market benchmark data per clause category."""
    __tablename__ = "clause_benchmarks"

    benchmark_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Text, nullable=False, index=True)
    jurisdiction = Column(Text, nullable=True)
    market_median = Column(Float, nullable=False)
    market_p25 = Column(Float, nullable=True)
    market_p75 = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=False, default=0)
    avg_risk_score = Column(Float, nullable=True)
    acceptance_rate = Column(Float, nullable=True)
    deviation_rate = Column(Float, nullable=True)
    extra_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class NegotiationHistory(Base):
    """Tracked negotiation outcomes per clause."""
    __tablename__ = "negotiation_history"

    history_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(UUID, ForeignKey("clauses.clause_id", ondelete="CASCADE"), nullable=False, index=True)
    counterparty = Column(Text, nullable=True)
    original_text = Column(Text, nullable=False)
    negotiated_text = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)  # accepted, rejected, modified
    risk_delta = Column(Float, nullable=True)
    strategy_used = Column(Text, nullable=True)
    success = Column(Boolean, nullable=True)
    created_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClauseUsage(Base):
    """Usage analytics per clause."""
    __tablename__ = "clause_usage"

    usage_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(UUID, ForeignKey("clauses.clause_id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id = Column(Text, nullable=True)
    used_as = Column(Text, nullable=True)  # original, fallback, negotiated
    was_accepted = Column(Boolean, nullable=True)
    was_deviated = Column(Boolean, nullable=False, default=False)
    deviation_reason = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FallbackClause(Base):
    """Preferred fallback language mappings for clause categories."""
    __tablename__ = "fallback_clauses"

    fallback_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Text, nullable=False, index=True)
    label = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    risk_score = Column(Float, nullable=True)
    negotiation_strength = Column(Float, nullable=True)
    usage_rate = Column(Float, nullable=True)
    is_preferred = Column(Boolean, nullable=False, default=False)
    jurisdiction = Column(Text, nullable=True)
    created_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
