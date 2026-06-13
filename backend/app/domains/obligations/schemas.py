"""Obligation Management — Pydantic v2 schemas for obligation tracking, SLA monitoring,
vendor performance, financial exposure, and audit logging.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Validated Obligation Types ──────────────────────────────────────

VALID_OBLIGATION_TYPES = [
    "payment", "renewal", "notice", "insurance",
    "audit_rights", "data_retention", "data_deletion",
]


# ── Request Schemas ─────────────────────────────────────────────────


class ObligationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    obligation_type: str
    status: Optional[str] = None
    contract_id: Optional[str] = None
    contract_uuid_id: Optional[str] = None
    contract_name: Optional[str] = None
    vendor: Optional[str] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    financial_impact: Optional[float] = None
    currency: Optional[str] = None
    clause_reference: Optional[str] = None
    department: Optional[str] = None
    business_unit: Optional[str] = None
    geography: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None

    @field_validator("obligation_type")
    @classmethod
    def validate_obligation_type(cls, v):
        if v and v.lower() not in VALID_OBLIGATION_TYPES:
            raise ValueError(
                f"Invalid obligation_type '{v}'. Must be one of: {', '.join(VALID_OBLIGATION_TYPES)}"
            )
        return v.lower() if v else v

    @field_validator("due_date")
    @classmethod
    def validate_due_date_not_past(cls, v):
        if v is not None:
            from datetime import timezone
            if v.replace(tzinfo=v.tzinfo or timezone.utc) < datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ):
                raise ValueError("Due date cannot be in the past.")
        return v


class ObligationUpdate(BaseModel):
    model_config = {"populate_by_name": True}

    name: Optional[str] = None
    description: Optional[str] = None
    obligation_type: Optional[str] = None
    status: Optional[str] = None
    contract_id: Optional[str] = None
    contract_uuid_id: Optional[str] = None
    contract_name: Optional[str] = None
    vendor: Optional[str] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    # Admin override MUST be declared before due_date so the validator
    # can access it via info.data (Pydantic v2 processes fields in order).
    admin_override_due_date: Optional[bool] = Field(False, alias="_admin_override_due_date")
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    sla_status: Optional[str] = None
    sla_remaining_hours: Optional[float] = None
    financial_impact: Optional[float] = None
    currency: Optional[str] = None
    escalation_level: Optional[int] = None
    clause_reference: Optional[str] = None
    department: Optional[str] = None
    business_unit: Optional[str] = None
    geography: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = None
    recurrence_next_date: Optional[datetime] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None
    tags: Optional[list[str]] = None

    @field_validator("obligation_type")
    @classmethod
    def validate_obligation_type(cls, v):
        if v and v.lower() not in VALID_OBLIGATION_TYPES:
            raise ValueError(
                f"Invalid obligation_type '{v}'. Must be one of: {', '.join(VALID_OBLIGATION_TYPES)}"
            )
        return v.lower() if v else v

    # ── Due date validation (update, with admin override) ─────────
    @field_validator("due_date")
    @classmethod
    def validate_due_date_not_past(cls, v, info):
        if v is not None:
            # Check admin override — Pydantic v2 validators see field names
            # before alias resolution, so check both possibilities
            override = info.data.get("admin_override_due_date") or info.data.get("_admin_override_due_date")
            if override:
                return v
            from datetime import timezone
            if v.replace(tzinfo=v.tzinfo or timezone.utc) < datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ):
                raise ValueError("Due date cannot be in the past.")
        return v


class SlaMetricCreate(BaseModel):
    vendor: str
    contract_type: Optional[str] = None
    sla_target: str
    performance: float
    trend: Optional[float] = None
    breach_count: Optional[int] = None
    status: Optional[str] = None


class FinancialExposureCreate(BaseModel):
    category: str
    total_exposure: float
    overdue_amount: Optional[float] = None
    at_risk_amount: Optional[float] = None
    recovered_amount: Optional[float] = None
    trend: Optional[float] = None
    currency: Optional[str] = None


class ObligationReminderCreate(BaseModel):
    obligation_id: str
    reminder_type: str
    remind_at: datetime
    message: Optional[str] = None


class ObligationEscalationCreate(BaseModel):
    obligation_id: str
    escalation_level: int
    escalated_to: str
    reason: Optional[str] = None


class AiReviewRequest(BaseModel):
    obligation_id: str
    include_predictions: Optional[bool] = None


# ── Completion Request (V1.1) ──────────────────────────────────────


class ObligationCompleteRequest(BaseModel):
    """Request payload for completing an obligation with audit evidence."""
    completion_notes: str = Field(..., min_length=1, description="Required notes explaining how the obligation was satisfied")
    completion_date: Optional[datetime] = None
    evidence_attachment_ids: Optional[list[str]] = None


# ── Response Schemas ────────────────────────────────────────────────


class ObligationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    obligation_number: str = ""
    name: str
    description: Optional[str] = None
    obligation_type: str
    status: str
    contract_id: Optional[str] = None
    contract_uuid_id: Optional[str] = None
    contract_name: Optional[str] = None
    contract_number: Optional[str] = None
    vendor: Optional[str] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    risk_score: float
    risk_level: str
    sla_status: str
    sla_remaining_hours: float
    financial_impact: float
    currency: str
    escalation_level: int
    ai_risk_prediction: float
    ai_confidence: float
    clause_reference: Optional[str] = None
    department: Optional[str] = None
    business_unit: Optional[str] = None
    geography: Optional[str] = None
    is_recurring: bool
    recurrence_pattern: Optional[str] = None
    recurrence_next_date: Optional[datetime] = None
    attachments_count: int
    reminders_count: int
    notes: Optional[str] = None
    is_favorite: bool
    tags: list[str] = []
    extra_metadata: Optional[dict] = None
    # Completion auditability fields (V1.1)
    completion_notes: Optional[str] = None
    completion_date: Optional[datetime] = None
    completed_by: Optional[str] = None
    evidence_attachment_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ObligationInstanceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    obligation_id: str
    instance_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    status: str
    financial_impact: float
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ObligationReminderResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    obligation_id: str
    reminder_type: str
    remind_at: datetime
    sent_at: Optional[datetime] = None
    message: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ObligationEscalationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    obligation_id: str
    escalation_level: int
    escalated_to: str
    reason: Optional[str] = None
    status: str
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ObligationEvidenceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    obligation_id: str
    instance_id: Optional[str] = None
    file_name: str
    file_type: str
    file_url: Optional[str] = None
    uploaded_by: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class SlaMetricResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    obligation_id: Optional[str] = None
    vendor: str
    contract_type: Optional[str] = None
    sla_target: str
    performance: float
    trend: float
    breach_count: int
    status: str
    measured_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class VendorPerformanceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    vendor: str
    category: str
    score: float
    trend: float
    contract_count: int
    breach_count: int
    risk_level: str
    predicted_risk: float
    last_assessed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FinancialExposureResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    category: str
    total_exposure: float
    overdue_amount: float
    at_risk_amount: float
    recovered_amount: float
    trend: float
    currency: str
    as_of_date: Optional[datetime] = None


class ObligationAuditLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    tenant_id: Optional[str] = None
    obligation_id: str
    contract_uuid_id: Optional[str] = None
    action: str
    actor: Optional[str] = None
    changes: Optional[dict] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class ObligationKpiResponse(BaseModel):
    total_obligations: int
    active_count: int
    overdue_count: int
    escalated_count: int
    completed_count: int
    breached_count: int
    avg_risk_score: float
    total_exposure: float
    at_risk_amount: float
    pending_review: int
    upcoming_due: int
    compliance_rate: float


class SlaBreachResponse(BaseModel):
    id: str
    vendor: str
    contract_type: Optional[str] = None
    performance: float
    target: str
    breached_at: datetime
    status: str


class VendorRiskResponse(BaseModel):
    vendor: str
    score: float
    risk_level: str
    breach_count: int
    contract_count: int
    trend: float
    predicted_risk: float


class SlaPredictionResponse(BaseModel):
    vendor: str
    current_performance: float
    predicted_performance: float
    breach_probability: float
    risk_level: str
    recommendation: str


class TimelineEventResponse(BaseModel):
    id: str
    obligation_id: str
    title: str
    description: Optional[str] = None
    event_type: str
    event_date: datetime
    status: str
    vendor: Optional[str] = None


class FinancialExposureSummaryResponse(BaseModel):
    total_exposure: float
    overdue_amount: float
    at_risk_amount: float
    recovered_amount: float
    by_category: list[FinancialExposureResponse]
    trend: float


class ValueAtRiskResponse(BaseModel):
    total_var: float
    probability: float
    confidence_level: float
    by_category: list[dict]


class RiskAnalysisResponse(BaseModel):
    obligation_id: str
    risk_score: float
    risk_level: str
    breach_probability: float
    escalation_recommended: bool
    recommended_action: str
    confidence: float
    analysis: str


class AnomalyResponse(BaseModel):
    id: str
    obligation_id: str
    anomaly_type: str
    severity: str
    description: str
    detected_at: datetime
    score: float


class NotificationHistoryResponse(BaseModel):
    id: str
    notification_type: str
    recipient: str
    message: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime


# ── List Wrappers ───────────────────────────────────────────────────


class PaginatedObligations(BaseModel):
    data: list[ObligationResponse]
    pagination: dict
