"""Human Oversight Layer schemas — approval workflows, policy exceptions, decision impact."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ApprovalType(str, Enum):
    AI_RECOMMENDATION = "ai_recommendation"       # AI suggested action needs human OK
    POLICY_EXCEPTION = "policy_exception"          # Exception to a policy rule
    ESCALATION_REVIEW = "escalation_review"        # Escalated decision needs review
    MANUAL_APPROVAL = "manual_approval"            # Explicit approval gate
    COMPLIANCE_CHECK = "compliance_check"          # Compliance-mandated approval
    EXECUTIVE_SIGN_OFF = "executive_sign_off"      # Executive-level approval


class ApprovalPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class ExceptionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AcknowledgmentStatus(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DISPUTED = "disputed"
    ESCALATED = "escalated"


# ── AI Recommendation Approval ──────────────────────────────────────


class AIRecommendationApproval(BaseModel):
    """An approval request for an AI-generated recommendation."""
    approval_id: str = ""
    review_id: str
    upload_id: str
    approval_type: ApprovalType
    title: str
    description: str = ""
    ai_recommendation: str = ""
    proposed_action: str = ""
    risk_impact: str = ""  # Description of risk impact if approved/rejected
    confidence: float = 0.0
    priority: ApprovalPriority = ApprovalPriority.NORMAL
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str = ""
    requested_at: datetime
    expires_at: Optional[datetime] = None
    # Linked entities
    finding_ids: list[str] = Field(default_factory=list)
    redline_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    # Approval chain
    required_approvers: list[str] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)
    approval_level: int = 1
    # Decision
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    decision_notes: Optional[str] = None
    conditions: Optional[dict[str, Any]] = None
    # Audit
    correlation_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    """Decision on an approval request."""
    decision: ApprovalStatus  # approved, rejected, conditionally_approved
    notes: Optional[str] = Field(None, max_length=5000)
    conditions: Optional[dict[str, Any]] = None


class ApprovalRequestCreate(BaseModel):
    """Create an approval request for an AI recommendation."""
    review_id: str
    upload_id: str
    approval_type: ApprovalType
    title: str = Field(..., min_length=1, max_length=300)
    description: str = ""
    ai_recommendation: str = ""
    proposed_action: str = ""
    risk_impact: str = ""
    confidence: float = 0.0
    priority: ApprovalPriority = ApprovalPriority.NORMAL
    expires_at: Optional[datetime] = None
    finding_ids: list[str] = Field(default_factory=list)
    redline_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    required_approvers: list[str] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)
    approval_level: int = 1


class ApprovalSummary(BaseModel):
    """Summary of an approval request for listing."""
    approval_id: str
    review_id: str
    approval_type: ApprovalType
    title: str
    status: ApprovalStatus
    priority: ApprovalPriority
    confidence: float = 0.0
    requested_by: str = ""
    requested_at: datetime
    expires_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    approval_level: int = 1


# ── Policy Exception Workflows ──────────────────────────────────────


class PolicyExceptionRequest(BaseModel):
    """A structured request for a policy exception."""
    exception_id: str = ""
    review_id: str
    upload_id: str
    rule_id: Optional[str] = None
    rule_name: str = ""
    policy_name: str = ""
    clause_category: str = ""
    severity: ExceptionSeverity = ExceptionSeverity.MEDIUM
    justification: str = Field(..., min_length=10, max_length=10000)
    proposed_alternative: Optional[str] = None
    risk_assessment: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str = ""
    requested_at: datetime
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    # Approval
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    approval_level: int = 1
    # Audit lineage
    previous_exception_id: Optional[str] = None
    correlation_id: Optional[str] = None


class PolicyExceptionCreate(BaseModel):
    """Create a policy exception request."""
    review_id: str
    upload_id: str
    rule_id: Optional[str] = None
    rule_name: str = ""
    policy_name: str = ""
    clause_category: str = ""
    severity: ExceptionSeverity = ExceptionSeverity.MEDIUM
    justification: str = Field(..., min_length=10, max_length=10000)
    proposed_alternative: Optional[str] = None
    risk_assessment: str = ""
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class PolicyExceptionReview(BaseModel):
    """Review decision for a policy exception."""
    decision: ApprovalStatus  # approved or rejected
    review_notes: Optional[str] = Field(None, max_length=5000)
    expiration_date: Optional[datetime] = None


# ── Reviewer Acknowledgment ─────────────────────────────────────────


class AcknowledgmentRequirement(BaseModel):
    """A requirement for a reviewer to acknowledge an AI finding or recommendation."""
    ack_id: str = ""
    review_id: str
    entity_type: str  # 'finding', 'redline', 'risk_score', 'policy_deviation'
    entity_id: str
    title: str = ""
    description: str = ""
    mandatory: bool = True  # If True, review cannot proceed without acknowledgment
    status: AcknowledgmentStatus = AcknowledgmentStatus.PENDING
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


class AcknowledgmentAction(BaseModel):
    """Action to acknowledge or dispute an AI finding."""
    status: AcknowledgmentStatus  # acknowledged or disputed
    notes: Optional[str] = Field(None, max_length=5000)


class AcknowledgmentSummary(BaseModel):
    """Summary of acknowledgment status for a review."""
    review_id: str
    total_requirements: int = 0
    acknowledged: int = 0
    disputed: int = 0
    pending: int = 0
    all_acknowledged: bool = False
    blocking_requirements: int = 0  # mandatory items not yet acknowledged


# ── Decision Impact Preview ─────────────────────────────────────────


class DecisionImpactPreview(BaseModel):
    """Preview of the impact of approving or rejecting an AI decision."""
    decision_type: str  # 'approve_redline', 'reject_finding', 'grant_exception', etc.
    entity_id: str
    entity_type: str
    risk_score_current: Optional[float] = None
    risk_score_after: Optional[float] = None
    risk_delta: Optional[float] = None
    exposure_change: Optional[float] = None
    affected_findings: int = 0
    affected_clauses: list[str] = Field(default_factory=list)
    compliance_impact: Optional[str] = None
    summary: str = ""


class BulkDecisionRequest(BaseModel):
    """Request to apply a decision to multiple items."""
    entity_type: str  # 'finding', 'redline'
    entity_ids: list[str]
    decision: str  # 'accept_all', 'reject_all', 'apply_template'
    notes: Optional[str] = None
    template_id: Optional[str] = None


class BulkDecisionResult(BaseModel):
    """Result of a bulk decision operation."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)
    risk_delta: Optional[float] = None


# ── Oversight Dashboard ─────────────────────────────────────────────


class HumanOversightDashboard(BaseModel):
    """Dashboard for human oversight activities."""
    pending_approvals: int = 0
    pending_exceptions: int = 0
    pending_acknowledgments: int = 0
    overdue_approvals: int = 0
    total_decisions_today: int = 0
    approval_slat_breaches: int = 0
    recent_approvals: list[ApprovalSummary] = Field(default_factory=list)
    recent_exceptions: list[PolicyExceptionRequest] = Field(default_factory=list)
    by_type: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
