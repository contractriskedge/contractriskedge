"""Clause Intelligence Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


CLAUSE_CATEGORIES = [
    "indemnification", "limitation_of_liability", "confidentiality", "data_privacy",
    "intellectual_property", "termination", "governing_law", "dispute_resolution",
    "force_majeure", "payment_terms", "warranty", "insurance", "compliance",
    "audit_rights", "assignment", "non_compete", "non_solicit", "sla", "escrow", "general",
]


class ClauseCreate(BaseModel):
    name: str
    category: str
    clause_type: Optional[str] = None
    text: str
    jurisdiction: Optional[str] = None
    contract_types: list[str] = Field(default_factory=list)
    risk_score: Optional[float] = None
    owner: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    governance_notes: Optional[str] = None


class ClauseUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    clause_type: Optional[str] = None
    text: Optional[str] = None
    jurisdiction: Optional[str] = None
    contract_types: Optional[list[str]] = None
    risk_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    ai_explanation: Optional[str] = None
    negotiation_strength: Optional[float] = None
    negotiation_guidance: Optional[str] = None
    approval_status: Optional[str] = None
    owner: Optional[str] = None
    is_favorite: Optional[bool] = None
    tags: Optional[list[str]] = None
    governance_notes: Optional[str] = None


class ClauseResponse(BaseModel):
    id: str
    name: str
    category: str
    clause_type: Optional[str] = None
    text: str
    jurisdiction: Optional[str] = None
    contract_types: list[str] = []
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_explanation: Optional[str] = None
    negotiation_strength: Optional[float] = None
    negotiation_guidance: Optional[str] = None
    benchmark_percentile: Optional[float] = None
    usage_frequency: int = 0
    approval_status: str = "draft"
    owner: Optional[str] = None
    version: int = 1
    is_favorite: bool = False
    tags: list[str] = []
    deviation_frequency: int = 0
    market_percentile: Optional[float] = None
    playbook_linkage: Optional[str] = None
    governance_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ClauseListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    category: Optional[str] = None
    search: Optional[str] = None
    approval_status: Optional[str] = None
    risk_level: Optional[str] = None
    sort_by: str = "updated_at"
    sort_order: str = "desc"


class FallbackVariantResponse(BaseModel):
    id: str
    label: str
    text: str
    risk_score: Optional[float] = None
    negotiation_strength: Optional[float] = None
    usage_rate: Optional[float] = None
    is_preferred: bool = False
    jurisdiction: Optional[str] = None


class BenchmarkResponse(BaseModel):
    category: str
    market_median: float
    market_p25: Optional[float] = None
    market_p75: Optional[float] = None
    sample_size: int = 0
    avg_risk_score: Optional[float] = None
    acceptance_rate: Optional[float] = None
    deviation_rate: Optional[float] = None


class NegotiationHistoryResponse(BaseModel):
    id: str
    clause_id: str
    counterparty: Optional[str] = None
    original_text: str
    negotiated_text: Optional[str] = None
    outcome: Optional[str] = None
    risk_delta: Optional[float] = None
    strategy_used: Optional[str] = None
    success: Optional[bool] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class AiReviewRequest(BaseModel):
    clause_text: str
    category: str
    jurisdiction: Optional[str] = None
    contract_type: Optional[str] = None


class AiReviewResponse(BaseModel):
    risk_score: float
    risk_level: str
    confidence: float
    explanation: str
    negotiation_strength: float
    negotiation_guidance: str
    compliance_warnings: list[str] = []
    suggested_fallback: Optional[str] = None
    escalation_triggers: list[str] = []


class SimilarityRequest(BaseModel):
    clause_text: str
    category: Optional[str] = None
    limit: int = 10


class SimilarityResult(BaseModel):
    clause_id: str
    name: str
    similarity: float
    text: str
    category: str
    risk_score: Optional[float] = None


class DeviationResponse(BaseModel):
    clause_id: str
    name: str
    category: str
    deviation_score: float
    market_median: float
    your_score: float
    risk_impact: str
    recommendation: str


class UsageTrendResponse(BaseModel):
    date: str
    count: int
    category: Optional[str] = None


class MarketComparisonResponse(BaseModel):
    category: str
    your_percentile: float
    market_median: float
    market_p25: float
    market_p75: float
    sample_size: int


class RejectionPatternResponse(BaseModel):
    category: str
    rejection_rate: float
    common_reasons: list[str]
    recommendation: str


class ClauseKpiResponse(BaseModel):
    total_clauses: int
    approved_count: int
    pending_review: int
    deprecated_count: int
    avg_risk_score: float
    avg_ai_confidence: float
    total_fallbacks: int
    total_playbooks: int
