"""Compliance domain Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Framework ──────────────────────────────────────────────────────

class ComplianceFrameworkCreate(BaseModel):
    name: str
    version: str = "1.0"
    description: str = ""
    category: str = "general"
    is_active: bool = True
    control_count: int = 0
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class ComplianceFrameworkResponse(BaseModel):
    framework_id: str
    tenant_id: str
    name: str
    version: str
    description: str
    category: str
    is_active: bool
    control_count: int
    extra_metadata: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Control ────────────────────────────────────────────────────────

class ComplianceControlCreate(BaseModel):
    framework_id: str
    control_id_str: str
    name: str
    description: str = ""
    category: str = "general"
    risk_level: str = "medium"
    is_active: bool = True
    sort_order: int = 0
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class ComplianceControlResponse(BaseModel):
    control_id: str
    framework_id: str
    tenant_id: str
    control_id_str: str
    name: str
    description: str
    category: str
    risk_level: str
    is_active: bool
    sort_order: int
    extra_metadata: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Assessment ─────────────────────────────────────────────────────

class ComplianceAssessmentCreate(BaseModel):
    framework_id: str
    name: str
    description: str = ""
    status: str = "draft"


class ComplianceAssessmentResponse(BaseModel):
    assessment_id: str
    framework_id: str
    tenant_id: str
    name: str
    description: str
    status: str
    score: Optional[float] = None
    total_controls: int = 0
    passed_controls: int = 0
    failed_controls: int = 0
    compliance_percentage: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    extra_metadata: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Finding ────────────────────────────────────────────────────────

class ComplianceFindingCreate(BaseModel):
    assessment_id: str
    control_id: Optional[str] = None
    title: str
    description: str = ""
    severity: str = "medium"
    status: str = "open"
    risk_score: Optional[float] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None
    remediation_notes: Optional[str] = None


class ComplianceFindingResponse(BaseModel):
    finding_id: str
    assessment_id: str
    control_id: Optional[str] = None
    tenant_id: str
    title: str
    description: str
    severity: str
    status: str
    risk_score: Optional[float] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None
    remediation_notes: Optional[str] = None
    extra_metadata: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Exception ──────────────────────────────────────────────────────

class ComplianceExceptionCreate(BaseModel):
    control_id: str
    title: str
    justification: str
    risk_assessment: Optional[str] = None
    expires_at: Optional[datetime] = None


class ComplianceExceptionResponse(BaseModel):
    exception_id: str
    control_id: str
    tenant_id: str
    title: str
    justification: str
    risk_assessment: Optional[str] = None
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    extra_metadata: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Evidence ───────────────────────────────────────────────────────

class ComplianceEvidenceCreate(BaseModel):
    evidence_id: str
    evidence_type: str
    framework: str
    control_id: str
    description: str = ""
    status: str = "collected"
    data: dict[str, Any] = Field(default_factory=dict)
    checksum: Optional[str] = None
    expires_at: Optional[datetime] = None
    storage_path: Optional[str] = None


class ComplianceEvidenceResponse(BaseModel):
    evidence_id: str
    tenant_id: str
    evidence_type: str
    framework: str
    control_id: str
    description: str
    status: str
    data: dict[str, Any]
    checksum: Optional[str] = None
    collected_at: datetime
    expires_at: Optional[datetime] = None
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    storage_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Pagination ─────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel):
    data: list
    pagination: PaginationMeta
