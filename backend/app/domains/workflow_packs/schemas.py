"""Enterprise Workflow Packs schemas — workflow templates, stage definitions, compliance bundles."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────


class WorkflowPackCategory(str, Enum):
    PROCUREMENT = "procurement"
    HEALTHCARE = "healthcare"
    SAAS_VENDOR = "saas_vendor"
    FINANCE_LEGAL = "finance_legal"
    REGIONAL_COMPLIANCE = "regional_compliance"
    CUSTOM = "custom"


class WorkflowStageType(str, Enum):
    INGESTION = "ingestion"
    AI_ANALYSIS = "ai_analysis"
    REVIEW = "review"
    NEGOTIATION = "negotiation"
    APPROVAL = "approval"
    COMPLIANCE_CHECK = "compliance_check"
    EXECUTIVE_SIGN_OFF = "executive_sign_off"
    FINALIZATION = "finalization"


class StageAction(str, Enum):
    AUTO_PROCEED = "auto_proceed"
    REQUIRE_REVIEW = "require_review"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"
    NOTIFY = "notify"
    ESCALATE = "escalate"


# ── Workflow Pack Definition ────────────────────────────────────────


class WorkflowPackCreate(BaseModel):
    """Create a workflow pack definition."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: WorkflowPackCategory
    industry: Optional[str] = None
    region: Optional[str] = None
    jurisdiction: Optional[str] = None
    stages: list[WorkflowStageDef] = Field(default_factory=list)
    rules: list[WorkflowPackRule] = Field(default_factory=list)
    compliance_requirements: list[ComplianceRequirement] = Field(default_factory=list)
    clause_requirements: list[ClauseRequirement] = Field(default_factory=list)
    approval_chains: list[ApprovalChainDef] = Field(default_factory=list)
    notification_templates: list[NotificationTemplate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class WorkflowStageDef(BaseModel):
    """Definition of a workflow stage."""
    stage_type: WorkflowStageType
    name: str
    description: Optional[str] = None
    order: int = 0
    on_entry: list[StageAction] = Field(default_factory=list)
    on_exit: list[StageAction] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    sla_hours: Optional[int] = None
    required_role: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowVersionSummary(BaseModel):
    """Summary of a workflow version."""
    version_id: str
    pack_id: str
    version_number: int
    status: str
    stage_count: int = 0
    rule_count: int = 0
    health_score: int = 0
    change_summary: Optional[str] = None
    published_by: Optional[str] = None
    published_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime


class WorkflowPackRule(BaseModel):
    """A rule specific to this workflow pack."""
    rule_name: str
    description: str = ""
    conditions: dict[str, Any] = Field(default_factory=dict)
    effect: str = "flag_for_review"
    priority: int = 100
    target_category: Optional[str] = None


class ComplianceRequirement(BaseModel):
    """A compliance requirement enforced by this pack."""
    regulation: str  # e.g., 'hipaa', 'gdpr', 'sox', 'pci_dss'
    provision: str = ""
    requirement: str = ""
    severity: str = "high"
    check_type: str = "clause_presence"  # 'clause_presence', 'language_check', 'value_threshold'


class ClauseRequirement(BaseModel):
    """A clause requirement for this pack."""
    clause_category: str
    requirement_type: str  # 'required', 'forbidden', 'recommended'
    severity_if_missing: str = "high"
    description: str = ""


class ApprovalChainDef(BaseModel):
    """An approval chain definition."""
    name: str
    stages: list[ApprovalStage] = Field(default_factory=list)
    trigger_conditions: dict[str, Any] = Field(default_factory=dict)


class ApprovalStage(BaseModel):
    """A single stage in an approval chain."""
    order: int = 1
    required_role: str
    required_if: Optional[str] = None  # condition expression
    sla_hours: int = 24
    escalation_after_hours: Optional[int] = None
    escalation_to_role: Optional[str] = None


class NotificationTemplate(BaseModel):
    """A notification template for this pack."""
    trigger_event: str
    subject: str = ""
    body: str = ""
    channel: str = "in_app"
    recipient_role: Optional[str] = None


class WorkflowPackResponse(BaseModel):
    """A complete workflow pack definition."""
    pack_id: str
    name: str
    description: Optional[str] = None
    category: WorkflowPackCategory
    industry: Optional[str] = None
    region: Optional[str] = None
    jurisdiction: Optional[str] = None
    stages: list[WorkflowStageDef] = Field(default_factory=list)
    rules: list[WorkflowPackRule] = Field(default_factory=list)
    compliance_requirements: list[ComplianceRequirement] = Field(default_factory=list)
    clause_requirements: list[ClauseRequirement] = Field(default_factory=list)
    approval_chains: list[ApprovalChainDef] = Field(default_factory=list)
    notification_templates: list[NotificationTemplate] = Field(default_factory=list)
    is_active: bool = True
    version: int = 1
    usage_count: int = 0
    created_by: str = ""
    created_at: datetime
    updated_at: datetime


class WorkflowPackSummary(BaseModel):
    """Summary of a workflow pack for listing."""
    pack_id: str
    name: str
    description: Optional[str] = None
    category: WorkflowPackCategory
    industry: Optional[str] = None
    region: Optional[str] = None
    is_active: bool = True
    status: str = "draft"
    version: int = 1
    health_score: int = 100
    usage_count: int = 0
    running_instances: int = 0
    stage_count: int = 0
    warning_count: int = 0
    last_published: Optional[datetime] = None
    owner: Optional[str] = None
    created_at: datetime


# ── Pack Activation ─────────────────────────────────────────────────


class PackActivation(BaseModel):
    """Activation of a workflow pack for a tenant."""
    activation_id: str = ""
    pack_id: str
    tenant_id: str
    business_unit: Optional[str] = None
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    activated_by: str = ""
    activated_at: datetime
    deactivated_at: Optional[datetime] = None


class PackActivateRequest(BaseModel):
    """Request to activate a workflow pack."""
    pack_id: str
    business_unit: Optional[str] = None
    config_overrides: dict[str, Any] = Field(default_factory=dict)


# ── Pre-built Pack Definitions ──────────────────────────────────────


BUILTIN_PACKS: dict[str, dict[str, Any]] = {
    "procurement_standard": {
        "name": "Procurement Contract Review",
        "description": "Standard workflow for procurement contract review with approval chains for value thresholds",
        "category": WorkflowPackCategory.PROCUREMENT,
        "health_score": 96,
        "usage_count": 142,
        "running_instances": 7,
        "warning_count": 0,
        "last_published": "2026-06-25T10:30:00Z",
        "owner": "Sarah Chen",
        "stages": [
            {"stage_type": "ingestion", "name": "Document Ingestion", "order": 1, "on_entry": ["auto_proceed"]},
            {"stage_type": "ai_analysis", "name": "AI Risk Analysis", "order": 2, "on_entry": ["auto_proceed"]},
            {"stage_type": "review", "name": "Procurement Review", "order": 3, "on_entry": ["require_review"], "sla_hours": 48, "required_role": "procurement_officer"},
            {"stage_type": "approval", "name": "Value-Based Approval", "order": 4, "on_entry": ["require_approval"], "sla_hours": 24},
            {"stage_type": "executive_sign_off", "name": "Executive Sign-Off", "order": 5, "on_entry": ["require_approval"], "sla_hours": 72, "required_role": "procurement_director"},
        ],
        "clause_requirements": [
            {"clause_category": "payment_terms", "requirement_type": "required", "severity_if_missing": "high"},
            {"clause_category": "liability", "requirement_type": "required", "severity_if_missing": "critical"},
            {"clause_category": "termination", "requirement_type": "required", "severity_if_missing": "high"},
            {"clause_category": "confidentiality", "requirement_type": "required", "severity_if_missing": "medium"},
        ],
        "approval_chains": [
            {"name": "Value Escalation", "stages": [
                {"order": 1, "required_role": "procurement_manager", "sla_hours": 24, "escalation_after_hours": 48, "escalation_to_role": "procurement_director"},
                {"order": 2, "required_role": "procurement_director", "sla_hours": 48, "escalation_after_hours": 72, "escalation_to_role": "cfo"},
                {"order": 3, "required_role": "cfo", "sla_hours": 72},
            ]},
        ],
    },
    "healthcare_compliance": {
        "name": "Healthcare Compliance Review",
        "description": "HIPAA-compliant contract review workflow with mandatory compliance checks",
        "category": WorkflowPackCategory.HEALTHCARE,
        "industry": "healthcare",
        "health_score": 88,
        "usage_count": 89,
        "running_instances": 3,
        "warning_count": 2,
        "last_published": "2026-06-22T14:00:00Z",
        "owner": "Dr. Michael Torres",
        "stages": [
            {"stage_type": "ingestion", "name": "Document Ingestion", "order": 1, "on_entry": ["auto_proceed"]},
            {"stage_type": "ai_analysis", "name": "AI Risk + HIPAA Analysis", "order": 2, "on_entry": ["auto_proceed"]},
            {"stage_type": "compliance_check", "name": "HIPAA Compliance Check", "order": 3, "on_entry": ["require_review"], "sla_hours": 24, "required_role": "compliance_officer"},
            {"stage_type": "review", "name": "Legal Review", "order": 4, "on_entry": ["require_review"], "sla_hours": 48, "required_role": "healthcare_attorney"},
            {"stage_type": "approval", "name": "Compliance Approval", "order": 5, "on_entry": ["require_approval"], "sla_hours": 24, "required_role": "compliance_director"},
        ],
        "compliance_requirements": [
            {"regulation": "hipaa", "provision": "164.502(a)", "requirement": "Permitted uses and disclosures", "severity": "critical"},
            {"regulation": "hipaa", "provision": "164.504(e)", "requirement": "Business associate contracts", "severity": "critical"},
            {"regulation": "hipaa", "provision": "164.308", "requirement": "Administrative safeguards", "severity": "high"},
        ],
        "clause_requirements": [
            {"clause_category": "data_privacy", "requirement_type": "required", "severity_if_missing": "critical"},
            {"clause_category": "security", "requirement_type": "required", "severity_if_missing": "critical"},
            {"clause_category": "confidentiality", "requirement_type": "required", "severity_if_missing": "high"},
            {"clause_category": "indemnification", "requirement_type": "required", "severity_if_missing": "high"},
        ],
    },
    "saas_vendor_standard": {
        "name": "SaaS Vendor Review",
        "description": "Standard workflow for SaaS vendor contract review with SLA and data protection focus",
        "category": WorkflowPackCategory.SAAS_VENDOR,
        "health_score": 72,
        "usage_count": 56,
        "running_instances": 1,
        "warning_count": 3,
        "last_published": "2026-06-18T09:15:00Z",
        "owner": "Alex Nakamura",
        "stages": [
            {"stage_type": "ingestion", "name": "Document Ingestion", "order": 1, "on_entry": ["auto_proceed"]},
            {"stage_type": "ai_analysis", "name": "AI Risk Analysis", "order": 2, "on_entry": ["auto_proceed"]},
            {"stage_type": "review", "name": "Vendor Review", "order": 3, "on_entry": ["require_review"], "sla_hours": 72, "required_role": "vendor_manager"},
            {"stage_type": "approval", "name": "Vendor Approval", "order": 4, "on_entry": ["require_approval"], "sla_hours": 48, "required_role": "vendor_director"},
        ],
        "clause_requirements": [
            {"clause_category": "sla", "requirement_type": "required", "severity_if_missing": "critical"},
            {"clause_category": "data_privacy", "requirement_type": "required", "severity_if_missing": "critical"},
            {"clause_category": "liability", "requirement_type": "required", "severity_if_missing": "high"},
            {"clause_category": "termination", "requirement_type": "required", "severity_if_missing": "high"},
            {"clause_category": "renewal", "requirement_type": "recommended", "severity_if_missing": "medium"},
        ],
    },
    "finance_legal_standard": {
        "name": "Finance & Legal Review",
        "description": "SOX-compliant contract review with financial controls and legal approval chains",
        "category": WorkflowPackCategory.FINANCE_LEGAL,
        "health_score": 94,
        "usage_count": 203,
        "running_instances": 12,
        "warning_count": 0,
        "last_published": "2026-06-27T16:45:00Z",
        "owner": "James O'Brien",
        "stages": [
            {"stage_type": "ingestion", "name": "Document Ingestion", "order": 1, "on_entry": ["auto_proceed"]},
            {"stage_type": "ai_analysis", "name": "AI Risk + SOX Analysis", "order": 2, "on_entry": ["auto_proceed"]},
            {"stage_type": "review", "name": "Legal Review", "order": 3, "on_entry": ["require_review"], "sla_hours": 48, "required_role": "legal_counsel"},
            {"stage_type": "compliance_check", "name": "SOX Compliance Check", "order": 4, "on_entry": ["require_review"], "sla_hours": 24, "required_role": "compliance_officer"},
            {"stage_type": "approval", "name": "Financial Approval", "order": 5, "on_entry": ["require_approval"], "sla_hours": 72, "required_role": "cfo"},
        ],
        "compliance_requirements": [
            {"regulation": "sox", "provision": "§302", "requirement": "Corporate responsibility for financial reports", "severity": "critical"},
            {"regulation": "sox", "provision": "§404", "requirement": "Internal control assessments", "severity": "critical"},
        ],
        "clause_requirements": [
            {"clause_category": "payment_terms", "requirement_type": "required", "severity_if_missing": "critical"},
            {"clause_category": "liability", "requirement_type": "required", "severity_if_missing": "high"},
            {"clause_category": "warranty", "requirement_type": "required", "severity_if_missing": "high"},
            {"clause_category": "indemnification", "requirement_type": "required", "severity_if_missing": "high"},
        ],
    },
}
