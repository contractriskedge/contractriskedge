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
    parent_id: Optional[str] = Field(None, alias="parentId")
    content: str
    mentions: list[str] = Field(default_factory=list)

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
