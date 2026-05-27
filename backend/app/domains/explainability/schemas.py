"""AI Explainability schemas — evidence chains, rationale, confidence, benchmarks, regulations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────


class EvidenceType(str, Enum):
    SOURCE_CLAUSE = "source_clause"
    BENCHMARK_REFERENCE = "benchmark_reference"
    POLICY_VIOLATION = "policy_violation"
    PRECEDENT_SIMILARITY = "precedent_similarity"
    REGULATION_LINKAGE = "regulation_linkage"
    MITIGATION_REASONING = "mitigation_reasoning"
    INDUSTRY_STANDARD = "industry_standard"
    HISTORICAL_PATTERN = "historical_pattern"


class ConfidenceComponent(str, Enum):
    CLAUSE_CLASSIFICATION = "clause_classification"
    SEVERITY_ASSESSMENT = "severity_assessment"
    RISK_SCORING = "risk_scoring"
    REDLINE_ACCURACY = "redline_accuracy"
    OBLIGATION_EXTRACTION = "obligation_extraction"
    POLICY_MATCH = "policy_match"
    BENCHMARK_ALIGNMENT = "benchmark_alignment"


class BenchmarkCategory(str, Enum):
    INDUSTRY_AVERAGE = "industry_average"
    PEER_GROUP = "peer_group"
    MARKET_STANDARD = "market_standard"
    REGULATORY_THRESHOLD = "regulatory_threshold"
    INTERNAL_POLICY = "internal_policy"
    HISTORICAL_AVERAGE = "historical_average"


class RegulationSource(str, Enum):
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    FCRA = "fcra"
    UCC = "ucc"
    CISG = "cisg"
    UK_DATA_PROTECTION = "uk_data_protection"
    LGPD = "lgpd"
    OTHER = "other"


# ── Evidence Chain ──────────────────────────────────────────────────


class EvidenceSource(BaseModel):
    """Source reference for an evidence item."""
    type: EvidenceType
    label: str = ""
    description: str = ""


class SourceClauseEvidence(BaseModel):
    """Evidence from the source contract clause."""
    clause_type: str
    clause_text: str = ""
    clause_text_snippet: str = ""
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None


class BenchmarkEvidence(BaseModel):
    """Evidence comparing a clause against a benchmark."""
    category: BenchmarkCategory
    benchmark_name: str = ""
    benchmark_value: str = ""
    contract_value: str = ""
    deviation: str = ""
    percentile: Optional[float] = None  # e.g., 0.85 = worse than 85% of peers
    source: str = ""


class PolicyViolationEvidence(BaseModel):
    """Evidence of a policy rule violation."""
    rule_id: str
    rule_name: str
    rule_type: str
    effect: str
    policy_name: str = ""
    policy_version: Optional[str] = None
    condition_matched: str = ""
    severity: str = "medium"


class PrecedentEvidence(BaseModel):
    """Evidence from similar clauses in past contracts."""
    precedent_contract_id: str = ""
    precedent_contract_name: str = ""
    clause_type: str
    similarity_score: float = 0.0
    outcome: str = ""  # e.g., 'accepted', 'rejected', 'modified'
    negotiated_text: Optional[str] = None
    risk_score_delta: Optional[float] = None  # how much risk changed after negotiation


class RegulationEvidence(BaseModel):
    """Evidence linking a clause to a specific regulation."""
    regulation: RegulationSource
    regulation_name: str = ""
    provision: str = ""  # e.g., 'Art. 5(1)(a)', '§1798.100'
    requirement: str = ""
    compliance_status: str = ""  # 'compliant', 'at_risk', 'non_compliant', 'unknown'
    risk_if_non_compliant: str = ""


class MitigationEvidence(BaseModel):
    """Evidence explaining why a mitigation is recommended."""
    mitigation_type: str
    mitigation_label: str = ""
    estimated_reduction_pct: float = 0.0
    rationale: str = ""
    alternatives: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class EvidenceItem(BaseModel):
    """A single piece of evidence in the explainability chain."""
    evidence_id: str = ""
    type: EvidenceType
    label: str = ""
    description: str = ""
    relevance_score: float = 1.0  # how relevant this evidence is (0-1)
    source_clause: Optional[SourceClauseEvidence] = None
    benchmark: Optional[BenchmarkEvidence] = None
    policy_violation: Optional[PolicyViolationEvidence] = None
    precedent: Optional[PrecedentEvidence] = None
    regulation: Optional[RegulationEvidence] = None
    mitigation: Optional[MitigationEvidence] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Confidence Breakdown ───────────────────────────────────────────


class ConfidenceComponentScore(BaseModel):
    """Score for a single component of confidence."""
    component: ConfidenceComponent
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    explanation: str = ""


class ConfidenceBreakdown(BaseModel):
    """Multi-component confidence breakdown for an AI analysis result."""
    overall_confidence: float = Field(ge=0.0, le=1.0)
    components: list[ConfidenceComponentScore] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)  # signals that affected confidence
    data_quality: Optional[float] = None  # quality of input data (0-1)
    model_reliability: Optional[float] = None  # reliability of the AI model used
    human_validation_status: str = "unreviewed"  # 'unreviewed', 'verified', 'disputed', 'corrected'


# ── Rationale ───────────────────────────────────────────────────────


class RationaleSegment(BaseModel):
    """A segment of the rationale for a finding or recommendation."""
    segment_type: str  # 'observation', 'analysis', 'comparison', 'conclusion', 'recommendation'
    text: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class Rationale(BaseModel):
    """Complete rationale for an AI finding or recommendation."""
    summary: str = ""
    segments: list[RationaleSegment] = Field(default_factory=list)
    evidence_chain: list[str] = Field(default_factory=list)  # ordered list of evidence IDs
    confidence_breakdown: Optional[ConfidenceBreakdown] = None


# ── Explainability Result ──────────────────────────────────────────


class FindingExplanation(BaseModel):
    """Full explainability for a single risk finding."""
    finding_id: str
    finding_title: str
    finding_severity: str
    clause_type: str
    rationale: Rationale
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: ConfidenceBreakdown
    alternatives: list[AlternativeSuggestion] = Field(default_factory=list)


class AlternativeSuggestion(BaseModel):
    """An alternative approach or language for a risky clause."""
    title: str = ""
    description: str = ""
    proposed_text: Optional[str] = None
    risk_reduction: Optional[str] = None  # 'critical', 'high', 'medium', 'low'
    confidence: float = 0.0
    source: str = ""  # 'playbook', 'precedent', 'ai_generated', 'industry_standard'


class ExplainabilityResponse(BaseModel):
    """Complete explainability response for a review's AI analysis."""
    review_id: str
    upload_id: str
    overall_confidence: ConfidenceBreakdown
    finding_explanations: list[FindingExplanation] = Field(default_factory=list)
    redline_explanations: list[RedlineExplanation] = Field(default_factory=list)
    summary: str = ""


class RedlineExplanation(BaseModel):
    """Explainability for a single redline suggestion."""
    redline_id: str
    operation: str
    rationale: Rationale
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: ConfidenceBreakdown
    risk_impact: Optional[str] = None  # how this redline changes risk


# ── Benchmark Registry ─────────────────────────────────────────────


class BenchmarkEntry(BaseModel):
    """A benchmark entry for comparing contract clauses."""
    benchmark_id: str = ""
    category: BenchmarkCategory
    clause_type: str
    metric_name: str  # e.g., 'liability_cap_pct', 'indemnity_duration_months'
    metric_value: float
    label: str = ""
    source: str = ""
    percentile_rank: Optional[float] = None
    sample_size: Optional[int] = None
    effective_date: Optional[datetime] = None


class BenchmarkComparison(BaseModel):
    """Comparison of a contract clause against benchmarks."""
    clause_type: str
    metric_name: str
    contract_value: float
    benchmarks: list[BenchmarkEntry] = Field(default_factory=list)
    percentile_vs_peers: Optional[float] = None
    percentile_vs_industry: Optional[float] = None
    risk_signal: Optional[str] = None  # 'favorable', 'neutral', 'concerning', 'critical'


# ── Regulation Mapping ─────────────────────────────────────────────


class RegulationMapping(BaseModel):
    """Mapping of a clause type to applicable regulations."""
    clause_type: str
    regulations: list[RegulationEvidence] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    risk_if_non_compliant: str = ""


class RegulationCheckResult(BaseModel):
    """Result of checking a contract against applicable regulations."""
    upload_id: str
    mappings: list[RegulationMapping] = Field(default_factory=list)
    total_checks: int = 0
    compliant: int = 0
    at_risk: int = 0
    non_compliant: int = 0
    unknown: int = 0
    overall_status: str = "unknown"  # 'compliant', 'attention_needed', 'action_required', 'unknown'
