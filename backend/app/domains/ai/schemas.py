"""AI analysis Pydantic schemas — request/response DTOs, structured outputs, and validation models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ObligationType(str, Enum):
    DELIVERABLE = "deliverable"
    PAYMENT = "payment"
    REPORTING = "reporting"
    COMPLIANCE = "compliance"
    NOTICE = "notice"


class ObligationParty(str, Enum):
    US = "us"
    COUNTERPARTY = "counterparty"
    BOTH = "both"


class AnalysisType(str, Enum):
    FULL = "full"
    RISK_ONLY = "risk_only"
    REDLINE_ONLY = "redline_only"


# ── Analysis Request/Response ──────────────────────────────────────

class AnalysisRequest(BaseModel):
    """Request to trigger AI analysis on an upload."""
    upload_id: str
    analysis_type: AnalysisType = AnalysisType.FULL


class AnalysisResponse(BaseModel):
    """Response after triggering analysis."""
    run_id: str
    upload_id: str
    status: str
    message: str = "Analysis pipeline started."


class AnalysisStatusResponse(BaseModel):
    """Current status of an AI analysis execution."""
    run_id: str
    upload_id: str
    analysis_type: str
    status: str
    model: str
    provider: str
    prompt_version: Optional[int] = None
    extraction_prompt_version: Optional[int] = None
    analysis_prompt_version: Optional[int] = None
    risk_score: Optional[float] = None
    findings_count: int = 0
    redlines_count: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None


# ── Structured AI Outputs ──────────────────────────────────────────

# ── Legal ontology — canonical clause types ────────────────────────────────
# Maps LLM-returned clause_type strings → canonical domain keys.
# Prevents collapse into "other" for legitimate IP/ownership/feedback variants.

_CLAUSE_TYPE_CANONICALIZATION: dict[str, str] = {
    # Intellectual Property / Ownership
    "intellectual_property": "intellectual_property",
    "ip": "intellectual_property",
    "ip_ownership": "intellectual_property",
    "ip_rights": "intellectual_property",
    "proprietary_rights": "intellectual_property",
    "license": "intellectual_property",
    "licensing": "intellectual_property",
    "feedback_rights": "intellectual_property",
    "feedback_ownership": "intellectual_property",
    "feedback": "intellectual_property",
    "ownership_rights": "intellectual_property",
    "derivative_works": "intellectual_property",
    "work_product": "intellectual_property",
    "ip_transfer": "intellectual_property",
    "no_license": "intellectual_property",
    "no_licence": "intellectual_property",
    # Liability
    "liability": "liability",
    "limitation_of_liability": "liability",
    "cap_on_liability": "liability",
    "limitation": "liability",
    # Payment / Fees
    "payment": "payment",
    "fees": "payment",
    "compensation": "payment",
    "pricing": "payment",
    "fee_increase": "payment",
    "fee_cap": "payment",
    "refund": "payment",
    "subscription_fees": "payment",
    # Data Privacy
    "data_privacy": "data_privacy",
    "data_protection": "data_privacy",
    "privacy": "data_privacy",
    "gdpr": "data_privacy",
    "personal_data": "data_privacy",
    "data_processing": "data_privacy",
    # Compliance
    "compliance": "compliance",
    "regulatory_compliance": "compliance",
    "legal_compliance": "compliance",
    # Indemnification
    "indemnification": "indemnification",
    "indemnity": "indemnification",
    "indemnify": "indemnification",
    # Termination
    "termination": "termination",
    "cancellation": "termination",
    "termination_rights": "termination",
    # Confidentiality
    "confidentiality": "confidentiality",
    "non_disclosure": "confidentiality",
    "nda": "confidentiality",
    "confidential_information": "confidentiality",
    "return_of_information": "confidentiality",
    "return_of_materials": "confidentiality",
    "return_of_confidential_information": "confidentiality",
    "remedies": "confidentiality",
    "exclusions": "confidentiality",
    "residual_knowledge": "confidentiality",
    "residuals": "confidentiality",
    # Insurance
    "insurance": "insurance",
    # Force Majeure
    "force_majeure": "force_majeure",
    "act_of_god": "force_majeure",
    # Governing Law
    "governing_law": "governing_law",
    "choice_of_law": "governing_law",
    "applicable_law": "governing_law",
    "jurisdiction": "governing_law",
    # Non-Compete
    "non_compete": "non_compete",
    "non_solicit": "non_compete",
    "exclusivity": "non_compete",
    "non_solicitation": "non_compete",
    # Assignment
    "assignment": "assignment",
    "delegation": "assignment",
    # Dispute Resolution
    "dispute_resolution": "dispute_resolution",
    "arbitration": "dispute_resolution",
    "mediation": "dispute_resolution",
    # Warranty
    "warranty": "warranty",
    "warranties": "warranty",
    "representations": "warranty",
    "representations_and_warranties": "warranty",
    # Renewal / Term
    "renewal": "renewal",
    "auto_renewal": "renewal",
    "term": "term",
    "duration": "term",
    # Security
    "security": "security",
    "data_security": "security",
    "information_security": "security",
    "breach_notification": "security",
}

_CANONICAL_CLAUSE_TYPES = frozenset({
    "liability", "payment", "data_privacy", "compliance",
    "indemnification", "termination", "confidentiality",
    "intellectual_property", "insurance", "force_majeure",
    "governing_law", "non_compete", "assignment",
    "dispute_resolution", "warranty", "renewal", "term",
    "security", "other",
})


def _canonicalize_clause_type(v: str) -> str:
    """Map any LLM-returned clause_type to a canonical domain. Never returns 'other' for known types."""
    if not v:
        return "other"
    normalized = v.lower().strip().replace(" ", "_").replace("-", "_")
    # Direct hit in canonicalization map
    if normalized in _CLAUSE_TYPE_CANONICALIZATION:
        return _CLAUSE_TYPE_CANONICALIZATION[normalized]
    # Direct hit in canonical set
    if normalized in _CANONICAL_CLAUSE_TYPES:
        return normalized
    # Fuzzy: check if any canonical key is a substring match
    for key, canonical in _CLAUSE_TYPE_CANONICALIZATION.items():
        if key in normalized or normalized in key:
            return canonical
    return "other"


class RiskFinding(BaseModel):
    """A single risk finding from AI analysis."""
    clause_type: str
    severity: SeverityLevel = SeverityLevel.INFO
    title: str
    description: str
    recommendation: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    chunk_indices: list[int] = Field(default_factory=list)

    @field_validator("clause_type")
    @classmethod
    def validate_clause_type(cls, v: str) -> str:
        return _canonicalize_clause_type(v)


class ClauseClassification(BaseModel):
    """Classification result for a single clause."""
    clause_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    explanation: str = ""

    @field_validator("clause_type")
    @classmethod
    def validate_clause_type(cls, v: str) -> str:
        return _canonicalize_clause_type(v)


class Obligation(BaseModel):
    """Extracted obligation from a contract clause."""
    obligation_type: ObligationType = ObligationType.COMPLIANCE
    description: str
    party: ObligationParty = ObligationParty.BOTH
    due_date_text: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class RiskTraceability(BaseModel):
    """Audit-grade risk chain: detected risk → business impact → mitigation."""
    detected_risk: str = ""
    business_impact: str = ""
    mitigation_strategy: str = ""


class RedlineSuggestion(BaseModel):
    """AI-generated redline suggestion."""
    clause_type: str
    original_text: str = ""
    proposed_text: str
    operation: str = "modification"
    anchor_text: str = ""
    rationale: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    confidence: float = Field(ge=0.0, le=1.0)
    chunk_indices: list[int] = Field(default_factory=list)
    # Risk traceability chain (populated from v3 prompt)
    traceability: Optional[RiskTraceability] = None

    @field_validator("clause_type")
    @classmethod
    def validate_clause_type(cls, v: str) -> str:
        return _canonicalize_clause_type(v)


class AnalysisResult(BaseModel):
    """Complete structured output from AI analysis."""
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""
    findings: list[RiskFinding] = Field(default_factory=list)
    classifications: list[ClauseClassification] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    redlines: list[RedlineSuggestion] = Field(default_factory=list)
    guardrail_violations: list[AIGuardrailViolation] = Field(default_factory=list)
    execution_context: Optional[AIExecutionContext] = None
    model_used: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class AIGuardrailViolation(BaseModel):
    """A guardrail check that influenced the AI recommendation."""
    rule_id: str
    message: str
    severity: SeverityLevel = SeverityLevel.MEDIUM


class AIExecutionContext(BaseModel):
    """Execution metadata persisted for AI run traceability and replay."""
    provider: str
    model: str
    prompt_version: Optional[int] = None
    analysis_prompt_version: Optional[int] = None
    guardrail_rule_ids: list[str] = Field(default_factory=list)
    source: str = "ai_analysis_service"
    trace_id: Optional[str] = None
    execution_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_chain_id: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)


class AIReviewSuggestion(BaseModel):
    """A single AI review suggestion for the reviewer."""
    suggestion_id: str
    title: str
    suggestion: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    guardrail_violations: list[AIGuardrailViolation] = Field(default_factory=list)


class AIReviewCopilotRequest(BaseModel):
    """Request payload for the reviewer AI copilot."""
    review_id: str
    prompt: Optional[str] = None
    max_suggestions: int = Field(default=3, ge=1, le=10)
    correlation_id: Optional[str] = None


class AIReviewCopilotResponse(BaseModel):
    """Response payload for reviewer AI suggestions."""
    review_id: str
    suggestions: list[AIReviewSuggestion] = Field(default_factory=list)
    model: str
    prompt_version: Optional[int] = None
    correlation_id: str


class AIReviewFeedbackRequest(BaseModel):
    """Reviewer feedback submitted against a Copilot suggestion."""
    review_id: str
    suggestion_id: str
    helpful: bool
    feedback: Optional[str] = None
    correlation_id: Optional[str] = None


class AIReviewFeedbackResponse(BaseModel):
    """Acknowledges reviewer feedback recording."""
    status: str
