"""Clause Intelligence schemas — clause graph, alternatives, negotiation lineage, semantic relationships."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────


class RelationshipType(str, Enum):
    SIMILAR_TO = "similar_to"
    ALTERNATIVE_TO = "alternative_to"
    SUPERSEDES = "supersedes"
    DEPENDS_ON = "depends_on"
    CONFLICTS_WITH = "conflicts_with"
    DERIVED_FROM = "derived_from"
    FALLBACK_FOR = "fallback_for"
    NEGOTIATED_FROM = "negotiated_from"


class NegotiationOutcome(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    WITHDRAWN = "withdrawn"
    COUNTERED = "countered"


class ClauseRiskInheritance(str, Enum):
    DIRECT = "direct"           # risk directly from this clause
    DERIVED = "derived"         # risk inherited from dependency
    AGGREGATED = "aggregated"   # risk aggregated from multiple related clauses
    MITIGATED = "mitigated"     # risk reduced by other clause


# ── Clause Graph ───────────────────────────────────────────────────


class ClauseNode(BaseModel):
    """A node in the clause knowledge graph."""
    clause_id: str
    clause_type: str
    canonical_category: str
    title: str = ""
    text_snippet: str = ""
    source: str = ""  # 'contract', 'playbook', 'precedent', 'negotiation'
    upload_id: Optional[str] = None
    review_id: Optional[str] = None
    tenant_id: Optional[str] = None
    risk_score: Optional[float] = None
    severity: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClauseRelationship(BaseModel):
    """A relationship between two clauses in the knowledge graph."""
    relationship_id: str = ""
    source_clause_id: str
    target_clause_id: str
    relationship_type: RelationshipType
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    label: str = ""
    evidence: str = ""
    created_at: datetime


class ClauseGraph(BaseModel):
    """Complete clause knowledge graph."""
    nodes: list[ClauseNode] = Field(default_factory=list)
    edges: list[ClauseRelationship] = Field(default_factory=list)
    total_clauses: int = 0
    total_relationships: int = 0
    clause_types: list[str] = Field(default_factory=list)


class ClauseGraphQuery(BaseModel):
    """Query parameters for clause graph traversal."""
    clause_type: Optional[str] = None
    upload_id: Optional[str] = None
    relationship_types: Optional[list[RelationshipType]] = None
    max_depth: int = 2
    min_strength: float = 0.3
    include_metadata: bool = False


# ── Approved Alternatives ──────────────────────────────────────────


class ApprovedAlternative(BaseModel):
    """An approved alternative for a risky or non-standard clause."""
    alternative_id: str = ""
    clause_type: str
    original_text_snippet: str = ""
    alternative_text: str = ""
    title: str = ""
    rationale: str = ""
    source: str = ""  # 'playbook', 'negotiation', 'legal_review', 'ai_generated'
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    effectiveness_score: Optional[float] = None  # how well this alternative reduced risk
    risk_reduction: Optional[str] = None  # 'critical', 'high', 'medium', 'low'
    usage_count: int = 0  # how many times this alternative has been used
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlternativeSearchResult(BaseModel):
    """Search result for approved alternatives."""
    clause_type: str
    alternatives: list[ApprovedAlternative] = Field(default_factory=list)
    total_found: int = 0
    has_playbook_alternatives: bool = False
    has_negotiation_alternatives: bool = False


# ── Negotiation Lineage ────────────────────────────────────────────


class NegotiationRound(BaseModel):
    """A single round of negotiation on a clause."""
    round_number: int
    proposed_text: str = ""
    response_text: str = ""
    proposed_by: str = ""  # 'us', 'counterparty'
    outcome: NegotiationOutcome
    notes: str = ""
    created_at: datetime


class NegotiationHistory(BaseModel):
    """Full negotiation history for a clause across a contract review."""
    negotiation_id: str = ""
    upload_id: str
    review_id: Optional[str] = None
    clause_type: str
    original_text: str = ""
    final_text: str = ""
    rounds: list[NegotiationRound] = Field(default_factory=list)
    total_rounds: int = 0
    final_outcome: Optional[NegotiationOutcome] = None
    days_to_resolve: Optional[int] = None
    risk_score_initial: Optional[float] = None
    risk_score_final: Optional[float] = None
    risk_reduction_pct: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NegotiationPattern(BaseModel):
    """A recurring pattern in clause negotiations."""
    pattern_id: str = ""
    clause_type: str
    pattern_name: str = ""
    description: str = ""
    common_requests: list[str] = Field(default_factory=list)
    typical_outcomes: list[str] = Field(default_factory=list)
    success_rate: float = 0.0
    average_rounds: float = 0.0
    sample_count: int = 0


# ── Vendor Clause Patterns ─────────────────────────────────────────


class VendorClauseProfile(BaseModel):
    """A vendor's typical clause patterns across contracts."""
    vendor_name: str
    counterparty: str = ""
    clause_type: str
    typical_language: str = ""
    common_deviations: list[str] = Field(default_factory=list)
    negotiation_tendency: str = ""  # 'flexible', 'rigid', 'moderate'
    risk_tendency: str = ""  # 'favorable', 'neutral', 'aggressive'
    contract_count: int = 0
    average_risk_score: Optional[float] = None
    last_encountered: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorPatternSummary(BaseModel):
    """Summary of vendor clause patterns across all contracts."""
    vendor_name: str
    total_contracts: int = 0
    clause_profiles: list[VendorClauseProfile] = Field(default_factory=list)
    overall_risk_tendency: str = "neutral"
    common_clause_types: list[str] = Field(default_factory=list)
    last_activity: Optional[datetime] = None


# ── Semantic Clause Graph ──────────────────────────────────────────


class SemanticCluster(BaseModel):
    """A cluster of semantically similar clauses."""
    cluster_id: str = ""
    label: str = ""
    clause_type: str
    clause_count: int = 0
    representative_text: str = ""
    risk_range: tuple[float, float] = (0.0, 0.0)
    common_issues: list[str] = Field(default_factory=list)
    clauses: list[ClauseNode] = Field(default_factory=list)


class SemanticSearchResult(BaseModel):
    """Result of a semantic clause search."""
    query: str
    clause_type: Optional[str] = None
    results: list[SemanticMatch] = Field(default_factory=list)
    total: int = 0


class SemanticMatch(BaseModel):
    """A semantically similar clause match."""
    clause_id: str
    clause_type: str
    text_snippet: str = ""
    similarity_score: float = 0.0
    source: str = ""
    upload_id: Optional[str] = None
    risk_score: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Risk Inheritance ───────────────────────────────────────────────


class RiskInheritanceChain(BaseModel):
    """Chain of risk inheritance between related clauses."""
    source_clause_id: str
    source_clause_type: str
    inheritance_type: ClauseRiskInheritance
    inherited_risk_score: float = 0.0
    contributing_clauses: list[RiskContribution] = Field(default_factory=list)
    mitigation_factors: list[str] = Field(default_factory=list)
    net_risk_score: float = 0.0


class RiskContribution(BaseModel):
    """A single clause's contribution to inherited risk."""
    clause_id: str
    clause_type: str
    risk_score: float = 0.0
    contribution_weight: float = 0.0
    relationship_type: RelationshipType
    text_snippet: str = ""


# ── Clause Intelligence Summary ────────────────────────────────────


class ClauseIntelligenceDashboard(BaseModel):
    """Executive dashboard for clause intelligence."""
    total_clauses_analyzed: int = 0
    total_relationships: int = 0
    unique_clause_types: int = 0
    approved_alternatives_count: int = 0
    negotiation_histories: int = 0
    vendor_patterns_tracked: int = 0
    semantic_clusters: int = 0
    most_common_risky_clauses: list[ClauseTypeRiskSummary] = Field(default_factory=list)
    top_negotiated_clauses: list[ClauseTypeNegotiationSummary] = Field(default_factory=list)


class ClauseTypeRiskSummary(BaseModel):
    """Risk summary for a clause type."""
    clause_type: str
    count: int = 0
    average_risk_score: float = 0.0
    high_risk_count: int = 0
    trend: str = "stable"  # 'improving', 'worsening', 'stable'


class ClauseTypeNegotiationSummary(BaseModel):
    """Negotiation summary for a clause type."""
    clause_type: str
    total_negotiations: int = 0
    acceptance_rate: float = 0.0
    average_rounds: float = 0.0
    average_risk_reduction: float = 0.0
