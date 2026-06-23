"""Negotiation domain Pydantic schemas — matching frontend TypeScript interfaces.

Every field name and type maps 1:1 to the frontend types in:
  frontend/components/dashboard/negotiation/types.ts
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums (string-based, matching frontend union types) ──────────

NEGOTIATION_STAGES = ("drafting", "review", "negotiating", "approved", "executed", "escalated")
REDLINE_TYPES = ("addition", "deletion", "modification", "comment", "suggestion")
REDLINE_STATUSES = ("pending", "accepted", "rejected", "superseded")
ISSUE_SEVERITIES = ("blocker", "critical", "major", "minor", "info")
ISSUE_STATUSES = ("open", "in_review", "resolved", "escalated", "accepted")
COMMENT_STATUSES = ("active", "resolved", "archived")
PARTICIPANT_ROLES = ("owner", "reviewer", "approver", "viewer", "external")
RISK_LEVELS = ("critical", "high", "medium", "low", "info")
VERSION_STATUSES = ("draft", "current", "superseded", "approved")


# ── Version / Clause ─────────────────────────────────────────────

class ClauseContentSchema(BaseModel):
    clause_id: str = Field(alias="clauseId")
    title: str
    section_number: str = Field(alias="sectionNumber")
    content: str
    risk_level: str = Field(alias="riskLevel")
    category: str
    negotiability_score: Optional[float] = Field(None, alias="negotiabilityScore")
    readability_score: Optional[float] = Field(None, alias="readabilityScore")
    market_standard_score: Optional[float] = Field(None, alias="marketStandardScore")

    model_config = {"populate_by_name": True}


class DocumentVersionSchema(BaseModel):
    id: str
    label: str
    timestamp: datetime
    author: str
    author_avatar: Optional[str] = Field(None, alias="authorAvatar")
    status: str
    content: list[ClauseContentSchema]
    word_count: int = Field(alias="wordCount")
    change_summary: Optional[str] = Field(None, alias="changeSummary")

    model_config = {"populate_by_name": True}


# ── Redline ──────────────────────────────────────────────────────

class CommentItemSchema(BaseModel):
    id: str
    author: str
    author_avatar: Optional[str] = Field(None, alias="authorAvatar")
    author_role: Optional[str] = Field(None, alias="authorRole")
    content: str
    timestamp: datetime
    status: str
    mentions: list[str] = Field(default_factory=list)
    replies: list[CommentItemSchema] = Field(default_factory=list)
    attachment_url: Optional[str] = Field(None, alias="attachmentUrl")
    clause_id: Optional[str] = Field(None, alias="clauseId")
    finding_id: Optional[str] = Field(None, alias="findingId")
    resolved_by: Optional[str] = Field(None, alias="resolvedBy")
    resolved_at: Optional[datetime] = Field(None, alias="resolvedAt")

    model_config = {"populate_by_name": True}


class RedlineEntrySchema(BaseModel):
    id: str
    type: str
    clause_id: str = Field(alias="clauseId")
    section_number: str = Field(alias="sectionNumber")
    title: str
    original_text: str = Field(alias="originalText")
    modified_text: Optional[str] = Field(None, alias="modifiedText")
    author: str
    author_avatar: Optional[str] = Field(None, alias="authorAvatar")
    timestamp: datetime
    risk_level: str = Field(alias="riskLevel")
    category: str
    status: str
    ai_generated: bool = Field(alias="aiGenerated")
    ai_confidence: Optional[float] = Field(None, alias="aiConfidence")
    negotiation_impact: Optional[str] = Field(None, alias="negotiationImpact")
    benchmark_deviation: Optional[float] = Field(None, alias="benchmarkDeviation")
    comments: list[CommentItemSchema] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ── Issue ────────────────────────────────────────────────────────

class NegotiationIssueSchema(BaseModel):
    id: str
    title: str
    description: str
    clause_id: Optional[str] = Field(None, alias="clauseId")
    section_number: str = Field("", alias="sectionNumber")
    severity: str
    status: str
    assignee: Optional[str] = None
    assignee_avatar: Optional[str] = Field(None, alias="assigneeAvatar")
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    category: str
    escalation_level: int = Field(0, alias="escalationLevel")
    comments: list[CommentItemSchema] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ── Participant ──────────────────────────────────────────────────

class ParticipantSchema(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    role: str
    department: Optional[str] = None
    is_online: bool = Field(alias="isOnline")
    last_active: Optional[datetime] = Field(None, alias="lastActive")
    reviewed_clauses: int = Field(0, alias="reviewedClauses")
    pending_approvals: int = Field(0, alias="pendingApprovals")

    model_config = {"populate_by_name": True}


# ── Activity / Audit ─────────────────────────────────────────────

class ActivityEntrySchema(BaseModel):
    id: str
    type: str
    user: str
    user_avatar: Optional[str] = Field(None, alias="userAvatar")
    action: str
    description: str
    timestamp: datetime
    clause_id: Optional[str] = Field(None, alias="clauseId")
    version_id: Optional[str] = Field(None, alias="versionId")

    model_config = {"populate_by_name": True}


# ── Full Session (aggregate root) ────────────────────────────────

class NegotiationSessionResponse(BaseModel):
    id: str
    contract_title: str = Field(alias="contractTitle")
    counterparty: str
    stage: str
    current_round: int = Field(1, alias="currentRound")
    max_rounds: int = Field(3, alias="maxRounds")
    versions: list[DocumentVersionSchema] = Field(default_factory=list)
    current_version_id: Optional[str] = Field(None, alias="currentVersionId")
    redlines: list[RedlineEntrySchema] = Field(default_factory=list)
    issues: list[NegotiationIssueSchema] = Field(default_factory=list)
    participants: list[ParticipantSchema] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    playbooks: list[dict[str, Any]] = Field(default_factory=list)
    workflow: dict[str, Any] = Field(default_factory=dict)
    analytics: dict[str, Any] = Field(default_factory=dict)
    activities: list[ActivityEntrySchema] = Field(default_factory=list)
    health_score: float = Field(alias="healthScore")
    started_at: datetime = Field(alias="startedAt")
    updated_at: datetime = Field(alias="updatedAt")
    metadata: Optional[dict[str, Any]] = Field(None, alias="metadata")

    model_config = {"populate_by_name": True}


class NegotiationSessionSummary(BaseModel):
    """Lightweight list item — no nested children."""
    id: str
    contract_title: str = Field(alias="contractTitle")
    counterparty: str
    stage: str
    health_score: float = Field(alias="healthScore")
    current_round: int = Field(1, alias="currentRound")
    max_rounds: int = Field(3, alias="maxRounds")
    started_at: datetime = Field(alias="startedAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


# ── Request Schemas ──────────────────────────────────────────────

class NegotiationCreateRequest(BaseModel):
    contract_id: Optional[str] = Field(None, alias="contractId")
    contract_title: str = Field(..., alias="contractTitle")
    counterparty: str
    clauses: Optional[list[ClauseContentSchema]] = None

    model_config = {"populate_by_name": True}


class ResumeFromReviewRequest(BaseModel):
    review_id: str = Field(..., alias="reviewId")
    counterparty: Optional[str] = None

    model_config = {"populate_by_name": True}


class NegotiationUpdateRequest(BaseModel):
    stage: Optional[str] = None
    health_score: Optional[float] = Field(None, alias="healthScore")

    model_config = {"populate_by_name": True}


class RedlineCreateRequest(BaseModel):
    clause_id: str = Field(alias="clauseId")
    type: str = "modification"
    title: str
    original_text: str = Field(alias="originalText")
    modified_text: Optional[str] = Field(None, alias="modifiedText")
    risk_level: str = Field("medium", alias="riskLevel")

    model_config = {"populate_by_name": True}


class RedlineStatusUpdateRequest(BaseModel):
    status: str  # accepted | rejected | superseded


class IssueCreateRequest(BaseModel):
    clause_id: Optional[str] = Field(None, alias="clauseId")
    title: str
    description: str = ""
    severity: str = "major"
    assignee: Optional[str] = None
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    category: str = "legal"

    model_config = {"populate_by_name": True}


class IssueUpdateRequest(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    assignee: Optional[str] = None
    escalation_level: Optional[int] = Field(None, alias="escalationLevel")

    model_config = {"populate_by_name": True}


class CommentCreateRequest(BaseModel):
    redline_id: Optional[str] = Field(None, alias="redlineId")
    issue_id: Optional[str] = Field(None, alias="issueId")
    clause_id: Optional[str] = Field(None, alias="clauseId")
    finding_id: Optional[str] = Field(None, alias="findingId")
    parent_id: Optional[str] = Field(None, alias="parentId")
    content: str
    mentions: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ClauseCommentCreateRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)
    parent_comment_id: Optional[str] = Field(None, alias="parentCommentId")
    finding_id: Optional[str] = Field(None, alias="findingId")

    model_config = {"populate_by_name": True}


class ParticipantCreateRequest(BaseModel):
    name: str
    role: str = "viewer"
    department: Optional[str] = None


class ParticipantUpdateRequest(BaseModel):
    role: Optional[str] = None


# ── Pagination ───────────────────────────────────────────────────

class PaginatedNegotiationResponse(BaseModel):
    data: list[NegotiationSessionSummary]
    pagination: dict[str, Any]


# ── KPIs ─────────────────────────────────────────────────────────

class NegotiationKpiResponse(BaseModel):
    total_sessions: int = 0
    active_sessions: int = 0
    by_stage: dict[str, int] = Field(default_factory=dict)
    escalated_count: int = 0
    # Time-series data for KPI sparkline charts
    sparkline_data: dict[str, list[int]] = Field(default_factory=dict)


# ── Negotiation Strategy Config ───────────────────────────────────

class NegotiationStrategyConfig(BaseModel):
    strategy_id: str
    name: str
    description: str
    icon: str  # emoji
    prompt_template: str
    is_default: bool = False
    is_active: bool = True


DEFAULT_STRATEGIES: list[dict] = [
    {"strategy_id": "balanced", "name": "Balanced", "description": "Fair middle-ground language protecting both parties' interests", "icon": "⚖️", "prompt_template": "Rewrite the following clause to be balanced and commercially reasonable, protecting both parties' interests fairly.", "is_default": True},
    {"strategy_id": "customer_protective", "name": "Customer Protective", "description": "Maximizes protections for the customer", "icon": "🛡️", "prompt_template": "Rewrite the following clause to be customer-protective, maximizing protections and favorable terms for the customer while remaining enforceable.", "is_default": False},
    {"strategy_id": "supplier_protective", "name": "Supplier Protective", "description": "Pro-supplier wording minimizing liability", "icon": "🏢", "prompt_template": "Rewrite the following clause to be supplier-protective, minimizing the supplier's liability and obligations while remaining legally enforceable.", "is_default": False},
    {"strategy_id": "legal_standard", "name": "Legal Standard", "description": "Industry-standard neutral language", "icon": "📋", "prompt_template": "Rewrite the following clause to use industry-standard legal language that is neutral and commonly accepted in similar agreements.", "is_default": False},
    {"strategy_id": "aggressive", "name": "Aggressive", "description": "Maximally favorable to your side", "icon": "⚡", "prompt_template": "Rewrite the following clause to be maximally favorable to our position, pushing the boundaries of what is commercially acceptable while remaining legally defensible.", "is_default": False},
    {"strategy_id": "fallback", "name": "Fallback Position", "description": "Pre-approved compromise language", "icon": "🤝", "prompt_template": "Rewrite the following clause as a fallback compromise position that offers reasonable concessions while maintaining essential protections.", "is_default": False},
]
