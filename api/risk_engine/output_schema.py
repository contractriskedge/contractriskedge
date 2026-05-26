"""Canonical JSON schema for risk flagging output — 8-field enterprise explainability model.

Defines the standard output format for all risk flagging operations,
ensuring consistency across the platform for downstream consumers.
Includes the 8-field enterprise explainability model:
1. clause_text         2. risk_category         3. why_flagged
4. potential_business_impact  5. market_benchmark_comparison
6. confidence_score    7. suggested_remediation  8. linked_evidence
9. jurisdictional_considerations
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BenchmarkComparison(BaseModel):
    """Comparison of a clause against market benchmarks."""

    benchmark_percentile: float = Field(
        ..., ge=0.0, le=100.0, description="Percentile rank vs benchmark corpus"
    )
    benchmark_score: float = Field(
        ..., ge=0.0, le=1.0, description="Average benchmark score for this clause type"
    )
    deviation: float = Field(
        ..., description="Deviation from benchmark (positive = worse than benchmark)"
    )
    comparison_summary: str = Field(
        ..., description="Human-readable comparison summary"
    )
    similar_clauses_count: int = Field(
        ..., ge=0, description="Number of similar clauses in benchmark"
    )


class SuggestedAction(BaseModel):
    """Suggested action for addressing a risk flag."""

    action: str = Field(
        ..., description="Primary action: accept, review, negotiate, reject"
    )
    priority: str = Field(
        default="medium", description="Priority: critical, high, medium, low"
    )
    description: str = Field(
        ..., description="Description of the suggested action"
    )
    alternative_language: Optional[str] = Field(
        None, description="Suggested alternative clause language"
    )
    negotiation_points: List[str] = Field(
        default_factory=list, description="Key negotiation points"
    )


class LinkedEvidence(BaseModel):
    """Evidence linking a risk flag to specific source contract text."""

    clause_reference: str = Field(
        ..., description="Reference to the specific clause in the source contract"
    )
    excerpt: str = Field(
        ..., description="Exact excerpt from the contract supporting this flag"
    )
    page_number: Optional[int] = Field(None, ge=1, description="Page number")
    section: Optional[str] = Field(None, description="Section heading")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="How relevant this evidence is"
    )


class JurisdictionalConsideration(BaseModel):
    """Jurisdiction-specific risk considerations."""

    jurisdiction: str = Field(
        ..., description="Jurisdiction code (US / EU / UK / APAC)"
    )
    rule_reference: str = Field(
        ..., description="Specific rule or regulation reference"
    )
    risk_modifier: float = Field(
        ..., ge=-2.0, le=2.0,
        description="Risk score modifier based on jurisdiction rules"
    )
    explanation: str = Field(
        ..., description="Explanation of jurisdictional impact"
    )


class RiskFlagOutput(BaseModel):
    """Canonical risk flag output schema — 8-field enterprise explainability model.

    This is the standard output format for all risk flagging operations
    in the platform. Every risk flag produced by the system conforms
    to this schema with the 8-field explainability model.

    Fields:
    1. clause_text                    - The clause text that triggered the flag
    2. risk_category                  - Primary risk category from taxonomy
    3. why_flagged                    - Explanation of why this clause is flagged
    4. potential_business_impact      - Business impact assessment
    5. market_benchmark_comparison    - Comparison against market benchmarks
    6. confidence_score               - Confidence in the risk assessment (0.0-1.0)
    7. suggested_remediation          - Recommended remediation actions
    8. linked_evidence                - Evidence links to source contract clauses
    9. jurisdictional_considerations  - Jurisdiction-specific context
    """

    risk_flag_id: str = Field(
        ..., description="Unique identifier for this risk flag"
    )
    contract_id: str = Field(
        ..., description="Identifier of the analyzed contract"
    )
    clause_id: str = Field(
        ..., description="Identifier of the specific clause"
    )
    # ── Field 1: clause_text ──
    clause_text: str = Field(
        ..., description="Excerpt of the clause text that triggered the flag"
    )
    page_ref: Optional[int] = Field(
        None, ge=1, description="Page number where the clause appears"
    )
    section: Optional[str] = Field(
        None, description="Section heading or number"
    )
    # ── Field 2: risk_category ──
    risk_category: str = Field(
        ..., description="Primary risk category from taxonomy"
    )
    sub_type: Optional[str] = Field(
        None, description="Specific sub-type within the category"
    )
    severity: int = Field(
        ..., ge=1, le=10, description="Severity score (1-10)"
    )
    # ── Field 3: why_flagged ──
    why_flagged: str = Field(
        ..., min_length=10,
        description="Detailed explanation of why this clause was flagged, "
        "including specific language that triggered the alert"
    )
    # ── Field 4: potential_business_impact ──
    potential_business_impact: str = Field(
        ..., min_length=10,
        description="Assessment of the potential business impact including "
        "financial, operational, and reputational consequences"
    )
    # ── Field 5: market_benchmark_comparison ──
    market_benchmark_comparison: str = Field(
        ..., min_length=10,
        description="How this clause compares against market standards and "
        "industry benchmarks for similar contract types"
    )
    # ── Field 6: confidence_score ──
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence score (0.0-1.0) based on self-consistency "
        "and grounding verification"
    )
    confidence_label: str = Field(
        ..., pattern="^(high|medium|low)$",
        description="Human-readable confidence level"
    )
    # ── Field 7: suggested_remediation ──
    suggested_remediation: str = Field(
        ..., min_length=10,
        description="Specific, actionable remediation recommendations "
        "including alternative language and negotiation positions"
    )
    suggested_action: SuggestedAction = Field(
        ..., description="Recommended action for this risk"
    )
    # ── Field 8: linked_evidence ──
    linked_evidence: List[LinkedEvidence] = Field(
        default_factory=list,
        description="Evidence links mapping each claim to specific clauses "
        "in the source contract text for grounding verification"
    )
    # ── Field 9: jurisdictional_considerations ──
    jurisdictional_considerations: List[JurisdictionalConsideration] = Field(
        default_factory=list,
        description="Jurisdiction-specific risk considerations covering "
        "US / EU / UK / APAC regulatory frameworks"
    )
    # ── Legacy / additional fields ──
    rationale: str = Field(
        ..., min_length=10,
        description="Detailed explanation of the risk assessment"
    )
    benchmark_percentile: Optional[float] = Field(
        None, ge=0.0, le=100.0,
        description="Percentile rank vs market benchmark"
    )
    benchmark_comparison: Optional[BenchmarkComparison] = Field(
        None, description="Detailed benchmark comparison"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this risk flag was created"
    )
    model_version: str = Field(
        ..., description="Version of the model that generated this flag"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for extensibility"
    )

    @field_validator("clause_text")
    @classmethod
    def clause_text_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("clause_text must not be empty")
        return stripped

    @field_validator("rationale")
    @classmethod
    def rationale_min_length(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError("rationale must be at least 10 characters")
        return stripped


class RiskFlagSet(BaseModel):
    """A complete set of risk flags for a contract."""

    contract_id: str = Field(
        ..., description="Identifier of the analyzed contract"
    )
    tenant_id: str = Field(
        ..., description="Tenant identifier"
    )
    analysis_id: str = Field(
        ..., description="Unique identifier for this analysis run"
    )
    flags: List[RiskFlagOutput] = Field(
        ..., description="List of risk flags found"
    )
    total_flags: int = Field(
        ..., ge=0, description="Total number of risk flags"
    )
    average_severity: float = Field(
        ..., ge=0.0, le=10.0, description="Average severity across all flags"
    )
    high_risk_count: int = Field(
        ..., ge=0, description="Number of flags with severity >= 7"
    )
    medium_risk_count: int = Field(
        ..., ge=0, description="Number of flags with severity 4-6"
    )
    low_risk_count: int = Field(
        ..., ge=0, description="Number of flags with severity <= 3"
    )
    categories_covered: List[str] = Field(
        ..., description="Risk categories present in this analysis"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this flag set was created"
    )
    model_version: str = Field(
        ..., description="Model version used for analysis"
    )

    @field_validator("total_flags")
    @classmethod
    def total_matches_flags(cls, v: int, info: Any) -> int:
        data = info.data
        expected = len(data.get("flags", []))
        if v != expected:
            raise ValueError(
                f"total_flags ({v}) must match number of flags ({expected})"
            )
        return v
