"""Pydantic models for risk analysis entities.

Defines the data structures for risk reports, findings,
risk categories, and severity levels.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskSeverity(str, Enum):
    """Severity level of a risk finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RiskCategory(str, Enum):
    """Category of risk in contract analysis."""

    INDEMNIFICATION = "indemnification"
    LIABILITY_LIMITATION = "liability_limitation"
    TERMINATION = "termination"
    CONFIDENTIALITY = "confidentiality"
    DATA_PRIVACY = "data_privacy"
    COMPLIANCE = "compliance"
    PAYMENT_TERMS = "payment_terms"
    FORCE_MAJEURE = "force_majeure"
    ASSIGNMENT = "assignment"
    GOVERNING_LAW = "governing_law"
    NON_COMPETE = "non_compete"
    INTELLECTUAL_PROPERTY = "intellectual_property"


class RiskFinding(BaseModel):
    """A single risk finding within a risk report."""

    finding_id: str = Field(..., description="Unique finding identifier")
    category: RiskCategory = Field(..., description="Risk category")
    severity: RiskSeverity = Field(..., description="Severity level")
    title: str = Field(..., description="Short title of the finding")
    description: str = Field(..., description="Detailed description")
    clause_reference: Optional[str] = Field(
        None, description="Reference to affected clause"
    )
    clause_text: Optional[str] = Field(
        None, description="Excerpt of affected clause text"
    )
    recommendation: Optional[str] = Field(
        None, description="Recommended remediation"
    )
    score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Risk score (0-1)"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RiskReport(BaseModel):
    """Complete risk analysis report for a contract."""

    report_id: str = Field(..., description="Unique report identifier")
    contract_id: str = Field(..., description="Analyzed contract identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User who requested analysis")
    status: str = Field(default="pending", description="Report status")
    overall_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall risk score (0=low risk)"
    )
    findings: List[RiskFinding] = Field(
        default_factory=list, description="Risk findings"
    )
    summary: Optional[str] = Field(None, description="Executive summary")
    categories_analyzed: List[RiskCategory] = Field(
        default_factory=list, description="Categories included in analysis"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
