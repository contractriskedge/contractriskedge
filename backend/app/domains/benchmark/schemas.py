"""Benchmark Pydantic schemas for API request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Corpus ─────────────────────────────────────────────────────────

class BenchmarkCorpusCreate(BaseModel):
    name: str = Field(..., max_length=255, description="Corpus name")
    description: Optional[str] = None
    industry: Optional[str] = None
    geography: Optional[str] = None
    contract_type: Optional[str] = None
    source: str = "uploaded"


class BenchmarkCorpusResponse(BaseModel):
    corpus_id: uuid.UUID
    name: str
    description: Optional[str] = None
    source: str
    industry: Optional[str] = None
    geography: Optional[str] = None
    contract_type: Optional[str] = None
    document_count: int
    clause_count: int
    is_active: str
    created_at: datetime
    updated_at: datetime


class BenchmarkCorpusListResponse(BaseModel):
    items: list[BenchmarkCorpusResponse]
    total: int


# ── Clauses ─────────────────────────────────────────────────────────

class BenchmarkClauseCreate(BaseModel):
    category: str
    clause_text: str
    source_document: Optional[str] = None
    risk_score: Optional[float] = None
    is_favorable: Optional[str] = None


class BenchmarkClauseResponse(BaseModel):
    clause_id: uuid.UUID
    corpus_id: uuid.UUID
    category: str
    clause_text: str
    clause_text_snippet: Optional[str] = None
    source_document: Optional[str] = None
    risk_score: Optional[float] = None
    is_favorable: Optional[str] = None
    created_at: datetime


# ── Scoring ─────────────────────────────────────────────────────────

class SimilarClauseInfo(BaseModel):
    """A similar clause from the corpus with similarity score for explainability."""
    clause_id: str
    category: str
    clause_text: str
    similarity: float
    risk_score: Optional[float] = None
    is_favorable: Optional[str] = None


class ClauseBenchmarkScore(BaseModel):
    """Score for a single clause category against a corpus."""
    clause_type: str
    your_score: float
    market_median: float
    market_p25: Optional[float] = None
    market_p75: Optional[float] = None
    deviation: Optional[float] = None
    deviation_percent: Optional[float] = None
    direction: Optional[str] = None
    percentile: float
    sample_size: int
    confidence: Optional[float] = None
    category: str
    similar_clauses: list[SimilarClauseInfo] = []
    explainability: Optional[str] = None  # Human-readable explanation of the score


class BenchmarkScoreRequest(BaseModel):
    """Request to score a contract's clauses against a corpus."""
    upload_id: uuid.UUID
    corpus_id: uuid.UUID
    clauses: list[ClauseScoreInput]


class ClauseScoreInput(BaseModel):
    category: str
    score: float  # Your contract's risk score for this clause (0-100)
    clause_text: Optional[str] = None  # Full clause text for similarity search


class BenchmarkScoreResponse(BaseModel):
    upload_id: uuid.UUID
    corpus_id: uuid.UUID
    scores: list[ClauseBenchmarkScore]
    overall_percentile: Optional[float] = None
    overall_risk_level: Optional[str] = None


# ── Industry Comparison ─────────────────────────────────────────────

class IndustryComparisonResponse(BaseModel):
    industry: str
    your_score: float
    industry_avg: float
    industry_p10: Optional[float] = None
    industry_p90: Optional[float] = None
    deviation: Optional[float] = None
    sample_size: int


# ── Dashboard ───────────────────────────────────────────────────────

class BenchmarkDashboardResponse(BaseModel):
    kpis: list[BenchmarkKpiResponse]
    clause_benchmarks: list[ClauseBenchmarkScore]
    industry_comparisons: list[IndustryComparisonResponse]
    total_corpora: int
    total_clauses: int


class BenchmarkKpiResponse(BaseModel):
    label: str
    value: str
    trend: float
    trend_direction: str
    severity: str
    tooltip: str


# ── Job Orchestration ───────────────────────────────────────────────

class BenchmarkJobResponse(BaseModel):
    """Status of an async benchmark orchestration job."""
    job_id: uuid.UUID
    job_type: str
    status: str
    progress_pct: int
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    items_processed: int
    items_failed: int
    items_total: int
    result_summary: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class BenchmarkJobListResponse(BaseModel):
    items: list[BenchmarkJobResponse]
    total: int


class BenchmarkJobCreateResponse(BaseModel):
    """Response after submitting an async benchmark job."""
    job_id: uuid.UUID
    job_type: str
    status: str
    message: str


# ── Corpus Versioning (Governance) ──────────────────────────────────

class BenchmarkCorpusVersionResponse(BaseModel):
    """A snapshot/version of a benchmark corpus."""
    version_id: uuid.UUID
    corpus_id: uuid.UUID
    version_number: int
    version_label: Optional[str] = None
    clause_count: int
    change_description: Optional[str] = None
    created_by: Optional[str] = None
    job_id: Optional[uuid.UUID] = None
    created_at: datetime


class BenchmarkCorpusVersionListResponse(BaseModel):
    items: list[BenchmarkCorpusVersionResponse]
    total: int


# ── Approval Workflow (Governance) ─────────────────────────────────

class ApprovalAction(BaseModel):
    """Action to take on a corpus approval request."""
    action: str = Field(..., pattern="^(submit|approve|reject|archive)$")
    notes: Optional[str] = None


class BenchmarkCorpusApprovalResponse(BaseModel):
    """Current approval state of a benchmark corpus."""
    approval_id: uuid.UUID
    corpus_id: uuid.UUID
    state: str
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Deduplication (Governance) ─────────────────────────────────────

class BenchmarkDedupeReportResponse(BaseModel):
    """A detected duplicate clause pair."""
    report_id: uuid.UUID
    corpus_id: uuid.UUID
    severity: str
    clause_id_a: uuid.UUID
    clause_id_b: uuid.UUID
    similarity_score: float
    clause_category: Optional[str] = None
    detected_by: Optional[str] = None
    resolved: str
    resolution_action: Optional[str] = None
    created_at: datetime


class BenchmarkDedupeReportListResponse(BaseModel):
    items: list[BenchmarkDedupeReportResponse]
    total: int
    exact_duplicates: int
    near_duplicates: int
    similar_duplicates: int


class DedupeResolveRequest(BaseModel):
    """Action to resolve a deduplication report."""
    action: str = Field(..., pattern="^(merge|remove|keep|dismiss)$")
    notes: Optional[str] = None


# ── Lineage (Governance) ────────────────────────────────────────────

class BenchmarkLineageResponse(BaseModel):
    """A recompute provenance record."""
    lineage_id: uuid.UUID
    corpus_id: uuid.UUID
    corpus_version_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    operation: str
    score_count_affected: int
    corpus_clause_count: int
    previous_lineage_id: Optional[uuid.UUID] = None
    delta_summary: Optional[dict] = None
    created_by: Optional[str] = None
    created_at: datetime


class BenchmarkLineageListResponse(BaseModel):
    items: list[BenchmarkLineageResponse]
    total: int
