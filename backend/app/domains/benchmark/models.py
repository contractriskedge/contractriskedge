"""Benchmark domain — ORM models for corpus management, clause benchmarking, percentile scoring, orchestration, and governance.

Provides the data foundation for:
- BenchmarkCorpus: A collection of reference contracts for a market segment
- BenchmarkClause: Normalized clauses extracted from corpus with embeddings
- BenchmarkScore: Computed percentile scores for a contract's clauses vs corpus
- BenchmarkJob: Trackable async jobs for recompute, refresh, and export operations
- BenchmarkCorpusVersion: Snapshot/version history for corpus integrity
- BenchmarkCorpusApproval: Approval workflow states for corpus governance
- BenchmarkDedupeReport: Clause deduplication analysis results
- BenchmarkLineage: Recompute provenance and score ancestry tracking
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Text,
    BigInteger,
    Float,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from pgvector.sqlalchemy import Vector

from app.kernel.database.base import Base


class CorpusSource(str, PyEnum):
    """Origin of a benchmark corpus entry."""
    UPLOADED = "uploaded"           # User-uploaded benchmark contract
    INDUSTRY_STANDARD = "industry_standard"  # Pre-loaded industry standard
    AGGREGATED = "aggregated"       # Aggregated from customer contracts (anonymized)
    MANUAL = "manual"               # Manually entered reference data


class CorpusIndustry(str, PyEnum):
    """Industry segments for benchmark cohorting."""
    TECHNOLOGY = "technology"
    FINANCIAL_SERVICES = "financial_services"
    HEALTHCARE = "healthcare"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    ENERGY = "energy"
    TELECOM = "telecom"
    PHARMACEUTICAL = "pharmaceutical"
    GENERAL = "general"


class Geography(str, PyEnum):
    """Geographic regions for benchmark segmentation."""
    NORTH_AMERICA = "north_america"
    EMEA = "emea"
    APAC = "apac"
    LATAM = "latam"
    GLOBAL = "global"


class ContractType(str, PyEnum):
    """Types of contracts in the benchmark corpus."""
    MSA = "msa"
    SOW = "sow"
    NDA = "nda"
    LICENSE = "license"
    SERVICE_AGREEMENT = "service_agreement"
    PARTNERSHIP = "partnership"
    SAAS = "saas"
    OTHER = "other"


class ClauseCategory(str, PyEnum):
    """Normalized clause taxonomy for benchmark comparison."""
    INDEMNIFICATION = "indemnification"
    LIABILITY_CAP = "liability_cap"
    TERMINATION = "termination"
    CONFIDENTIALITY = "confidentiality"
    DATA_PRIVACY = "data_privacy"
    COMPLIANCE = "compliance"
    PAYMENT_TERMS = "payment_terms"
    FORCE_MAJEURE = "force_majeure"
    ASSIGNMENT = "assignment"
    GOVERNING_LAW = "governing_law"
    NON_COMPETE = "non_compete"
    IP_OWNERSHIP = "ip_ownership"
    AUTO_RENEWAL = "auto_renewal"
    SLA = "sla"
    INSURANCE = "insurance"
    AUDIT_RIGHTS = "audit_rights"
    GENERAL = "general"


# ── Benchmark Corpus ───────────────────────────────────────────────


class BenchmarkCorpus(Base):
    """A collection of reference contracts for a specific market segment.

    Each corpus represents a cohort (e.g., "Tech MSA North America 2024").
    Contains multiple BenchmarkClause entries.
    """
    __tablename__ = "benchmark_corpora"

    corpus_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    source = Column(
        SAEnum(CorpusSource, name="corpus_source", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=False, default=CorpusSource.UPLOADED,
    )
    industry = Column(
        SAEnum(CorpusIndustry, name="corpus_industry", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=True,
    )
    geography = Column(
        SAEnum(Geography, name="corpus_geography", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=True,
    )
    contract_type = Column(
        SAEnum(ContractType, name="corpus_contract_type", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=True,
    )
    document_count = Column(Integer, nullable=False, default=0)
    clause_count = Column(Integer, nullable=False, default=0)
    corpus_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    is_active = Column(Text, nullable=False, default="true")
    created_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_corpus_tenant_name"),
    )


# ── Benchmark Clause ────────────────────────────────────────────────


class BenchmarkClause(Base):
    """A normalized clause entry in a benchmark corpus with embedding.

    Stores the canonical clause text, its normalized category, and a
    vector embedding for similarity-based retrieval and comparison.
    """
    __tablename__ = "benchmark_clauses"

    clause_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    corpus_id = Column(UUID, ForeignKey("benchmark_corpora.corpus_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(
        SAEnum(ClauseCategory, name="clause_category", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=False, index=True,
    )
    clause_text = Column(Text, nullable=False)
    clause_text_snippet = Column(Text, nullable=True)  # First 200 chars for preview
    source_document = Column(Text, nullable=True)       # Original document name
    embedding = Column(Vector(1536), nullable=True)     # OpenAI text-embedding-3-small
    risk_score = Column(Float, nullable=True)           # Normalized risk score 0-100
    is_favorable = Column(Text, nullable=True)          # 'favorable', 'neutral', 'unfavorable'
    clause_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_benchmark_clauses_corpus_category", "corpus_id", "category"),
        Index("ix_benchmark_clauses_embedding", "embedding", postgresql_using="ivfflat"),
    )


# ── Benchmark Score ────────────────────────────────────────────────


class BenchmarkScore(Base):
    """Computed percentile scores for a contract's clauses vs a benchmark corpus.

    One record per (upload_id, corpus_id, clause_category) combination.
    Stores the percentile, deviation, and statistical confidence.
    """
    __tablename__ = "benchmark_scores"

    score_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    corpus_id = Column(UUID, ForeignKey("benchmark_corpora.corpus_id", ondelete="CASCADE"), nullable=False)
    category = Column(
        SAEnum(ClauseCategory, name="benchmark_score_category", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=False,
    )

    # Your contract's score
    your_score = Column(Float, nullable=False)

    # Market distribution
    market_median = Column(Float, nullable=False)
    market_p25 = Column(Float, nullable=True)
    market_p75 = Column(Float, nullable=True)
    market_mean = Column(Float, nullable=True)
    market_stddev = Column(Float, nullable=True)

    # Percentile
    percentile = Column(Float, nullable=False)  # 0-100
    deviation = Column(Float, nullable=True)    # Signed difference from median
    deviation_percent = Column(Float, nullable=True)  # Percentage deviation
    direction = Column(Text, nullable=True)      # 'above_market', 'below_market', 'at_market'

    # Statistical quality
    sample_size = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=True)   # 0-1 confidence score

    # Metadata
    score_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("upload_id", "corpus_id", "category", name="uq_benchmark_score_triple"),
        Index("ix_benchmark_scores_upload", "upload_id", "tenant_id"),
    )


# ── Benchmark Job (Orchestration) ──────────────────────────────────


class BenchmarkJobType(str, PyEnum):
    """Types of async benchmark orchestration jobs."""
    RECOMPUTE_SCORES = "recompute_scores"
    REFRESH_EMBEDDINGS = "refresh_embeddings"
    STALE_DETECTION = "stale_detection"
    EXPORT_CSV = "export_csv"
    CORPUS_REFRESH = "corpus_refresh"


class BenchmarkJobStatus(str, PyEnum):
    """Lifecycle states for an async benchmark job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkJob(Base):
    """Trackable async job for benchmark orchestration operations.

    Each row represents a single async operation (recompute, refresh,
    export, etc.) with status tracking, progress, error details, and
    timing.  Used by the Celery task layer and the job status API.
    """
    __tablename__ = "benchmark_jobs"

    job_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(
        SAEnum(BenchmarkJobType, name="benchmark_job_type", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=False,
    )
    status = Column(
        SAEnum(BenchmarkJobStatus, name="benchmark_job_status", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=False, default=BenchmarkJobStatus.PENDING,
    )
    progress_pct = Column(Integer, nullable=False, default=0)       # 0-100
    progress_message = Column(Text, nullable=True)                   # Current step description
    error_message = Column(Text, nullable=True)                      # Failure detail
    error_details = Column(JSONB, nullable=True)                     # Structured error context

    # Scope: which corpus/upload does this job operate on?
    corpus_id = Column(UUID, ForeignKey("benchmark_corpora.corpus_id", ondelete="SET NULL"), nullable=True)
    upload_id = Column(UUID, nullable=True)                          # Optional target upload

    # Results summary
    items_processed = Column(Integer, nullable=False, default=0)
    items_failed = Column(Integer, nullable=False, default=0)
    items_total = Column(Integer, nullable=False, default=0)
    result_summary = Column(JSONB, nullable=True)                   # Job-specific result payload

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_benchmark_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_benchmark_jobs_created", "created_at"),
    )


# ── Corpus Versioning (Governance) ────────────────────────────────


class BenchmarkCorpusVersion(Base):
    """Immutable snapshot of a benchmark corpus at a point in time.

    Created before each significant mutation (clause addition, removal,
    bulk update) to provide auditability and rollback capability.

    The ``snapshot`` column stores a JSON representation of all clauses
    in the corpus at version creation time, enabling deterministic
    recomputation and historical comparison.
    """
    __tablename__ = "benchmark_corpus_versions"

    version_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    corpus_id = Column(UUID, ForeignKey("benchmark_corpora.corpus_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)  # Monotonically increasing per corpus
    version_label = Column(Text, nullable=True)        # Human-readable: "v1", "pre-approval-2024-06", etc.
    snapshot = Column(JSONB, nullable=False)           # Full clause data at this version
    clause_count = Column(Integer, nullable=False, default=0)
    change_description = Column(Text, nullable=True)   # What changed in this version
    created_by = Column(Text, nullable=True)            # User or job that created this version
    job_id = Column(UUID, ForeignKey("benchmark_jobs.job_id", ondelete="SET NULL"), nullable=True)  # Link to orchestration job
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("corpus_id", "version_number", name="uq_corpus_version"),
        Index("ix_corpus_versions_corpus", "corpus_id", "version_number"),
    )


# ── Corpus Approval Workflow (Governance) ─────────────────────────


class ApprovalState(str, PyEnum):
    """Lifecycle states for corpus approval workflow."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class BenchmarkCorpusApproval(Base):
    """Approval workflow tracking for benchmark corpus governance.

    Each corpus has a lifecycle: DRAFT → PENDING_REVIEW → APPROVED/REJECTED.
    Only APPROVED corpora are used for production benchmarking.
    DRAFT corpora are visible only to corpus editors.
    """
    __tablename__ = "benchmark_corpus_approvals"

    approval_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    corpus_id = Column(UUID, ForeignKey("benchmark_corpora.corpus_id", ondelete="CASCADE"), nullable=False, unique=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    state = Column(
        SAEnum(ApprovalState, name="approval_state", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=False, default=ApprovalState.DRAFT,
    )
    submitted_by = Column(Text, nullable=True)         # User who submitted for review
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Text, nullable=True)           # User who approved/rejected
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)          # Approver's notes or rejection reason
    approval_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ── Deduplication Reports (Governance) ────────────────────────────


class DedupeSeverity(str, PyEnum):
    """Severity of a detected clause duplication."""
    EXACT = "exact"          # Identical text
    NEAR = "near"            # >0.95 cosine similarity
    SIMILAR = "similar"      # >0.85 cosine similarity


class BenchmarkDedupeReport(Base):
    """Record of a deduplication analysis run on a corpus.

    Stores detected duplicate or near-duplicate clauses to help
    corpus maintainers clean skewed statistics.
    """
    __tablename__ = "benchmark_dedupe_reports"

    report_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    corpus_id = Column(UUID, ForeignKey("benchmark_corpora.corpus_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    severity = Column(
        SAEnum(DedupeSeverity, name="dedupe_severity", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=False,
    )
    clause_id_a = Column(UUID, ForeignKey("benchmark_clauses.clause_id", ondelete="CASCADE"), nullable=False)
    clause_id_b = Column(UUID, ForeignKey("benchmark_clauses.clause_id", ondelete="CASCADE"), nullable=False)
    similarity_score = Column(Float, nullable=False)   # Cosine similarity 0-1
    clause_category = Column(
        SAEnum(ClauseCategory, name="dedupe_clause_category", create_type=False,
               values_callable=lambda s: [e.value for e in s]),
        nullable=True,
    )
    detected_by = Column(Text, nullable=True)            # 'auto' or user ID
    resolved = Column(Text, nullable=False, default="false")  # 'true', 'false', 'dismissed'
    resolution_action = Column(Text, nullable=True)      # 'merged', 'removed', 'kept'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_dedupe_corpus_severity", "corpus_id", "severity"),
    )


# ── Benchmark Lineage (Governance) ────────────────────────────────


class BenchmarkLineage(Base):
    """Provenance tracking for benchmark recompute operations.

    Records each recompute event: which scores were affected, which
    corpus version was used, which job triggered it, and the statistical
    delta from the previous recompute.

    Enables auditability: "What version of the corpus produced this score?"
    """
    __tablename__ = "benchmark_lineage"

    lineage_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    corpus_id = Column(UUID, ForeignKey("benchmark_corpora.corpus_id", ondelete="CASCADE"), nullable=False, index=True)
    corpus_version_id = Column(UUID, ForeignKey("benchmark_corpus_versions.version_id", ondelete="SET NULL"), nullable=True)
    job_id = Column(UUID, ForeignKey("benchmark_jobs.job_id", ondelete="SET NULL"), nullable=True)
    operation = Column(Text, nullable=False)              # 'recompute', 'refresh_embeddings', 'corpus_update', 'seed'
    score_count_affected = Column(Integer, nullable=False, default=0)
    corpus_clause_count = Column(Integer, nullable=False, default=0)
    previous_lineage_id = Column(UUID, nullable=True)     # Link to previous recompute for delta tracking
    delta_summary = Column(JSONB, nullable=True)          # Statistical changes from previous recompute
    lineage_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_benchmark_lineage_corpus", "corpus_id", "created_at"),
    )
