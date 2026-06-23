"""Negotiation ORM models — sessions, versions, redlines, issues, comments, participants.

Architecture decisions (validated June 3, 2026):
1. contract_id = real FK to contract_reviews.review_id (UUID, ON DELETE SET NULL)
2. clauses = JSONB on versions table (snapshot data, not normalized)
3. Audit = reuse governance_audit_events (no separate audit table)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.kernel.database.base import Base


# ── Enums ──────────────────────────────────────────────────────────

class NegotiationStage(str, PyEnum):
    DRAFTING = "drafting"
    REVIEW = "review"
    NEGOTIATING = "negotiating"
    APPROVED = "approved"
    EXECUTED = "executed"
    ESCALATED = "escalated"


class RedlineType(str, PyEnum):
    ADDITION = "addition"
    DELETION = "deletion"
    MODIFICATION = "modification"
    COMMENT = "comment"
    SUGGESTION = "suggestion"


class RedlineStatus(str, PyEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class IssueSeverity(str, PyEnum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class IssueStatus(str, PyEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    ACCEPTED = "accepted"


class CommentStatus(str, PyEnum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class ParticipantRole(str, PyEnum):
    OWNER = "owner"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    VIEWER = "viewer"
    EXTERNAL = "external"


class RiskLevel(str, PyEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VersionStatus(str, PyEnum):
    DRAFT = "draft"
    CURRENT = "current"
    SUPERSEDED = "superseded"
    APPROVED = "approved"


# ── Negotiation Session (Aggregate Root) ──────────────────────────

class NegotiationSession(Base):
    """A negotiation session tied to a contract review.

    FK to contract_reviews.review_id is ON DELETE SET NULL so that
    negotiations can outlive a deleted review reference.
    """
    __tablename__ = "negotiation_sessions"

    session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    contract_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("contract_reviews.review_id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    contract_title: Mapped[str] = mapped_column(String(500), nullable=False)
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(
        String(30), nullable=False, default=NegotiationStage.DRAFTING.value, index=True,
    )
    health_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    versions: Mapped[list["NegotiationVersion"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        passive_deletes=True,
    )
    redlines: Mapped[list["NegotiationRedline"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        passive_deletes=True,
    )
    issues: Mapped[list["NegotiationIssue"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        passive_deletes=True,
    )
    comments: Mapped[list["NegotiationComment"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        passive_deletes=True,
    )
    participants: Mapped[list["NegotiationParticipant"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        passive_deletes=True,
    )
    votes: Mapped[list["NegotiationVote"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_neg_sessions_tenant_stage", "tenant_id", "stage"),
        Index("ix_neg_sessions_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<NegotiationSession {self.session_id[:8]} stage={self.stage}>"


# ── Document Versions ─────────────────────────────────────────────

class NegotiationVersion(Base):
    """A version/snapshot of the contract document within a negotiation.

    clauses is JSONB — a snapshot of ClauseContent[] at this version.
    Not normalized because clauses are always loaded/saved as a set
    and never queried individually across versions.
    """
    __tablename__ = "negotiation_versions"

    version_id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    author_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VersionStatus.DRAFT.value,
    )
    clauses: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["NegotiationSession"] = relationship(back_populates="versions")

    __table_args__ = (
        Index("ix_neg_versions_session", "session_id", "version_number"),
    )

    def __repr__(self) -> str:
        return f"<NegotiationVersion {self.version_id[:8]} v{self.version_number}>"


# ── Redlines (Proposed Changes) ───────────────────────────────────

class NegotiationRedline(Base):
    """A proposed change to a clause — addition, deletion, modification, etc."""
    __tablename__ = "negotiation_redlines"

    redline_id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    clause_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=RedlineType.MODIFICATION.value,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    modified_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    author_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RiskLevel.MEDIUM.value,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=RedlineStatus.PENDING.value,
    )
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    negotiation_impact: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    benchmark_deviation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["NegotiationSession"] = relationship(back_populates="redlines")
    comments: Mapped[list["NegotiationComment"]] = relationship(
        back_populates="redline", cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="NegotiationComment.redline_id",
    )

    __table_args__ = (
        Index("ix_neg_redlines_session_clause", "session_id", "clause_id"),
        Index("ix_neg_redlines_session_status", "session_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<NegotiationRedline {self.redline_id[:8]} type={self.type}>"


# ── Issues ─────────────────────────────────────────────────────────

class NegotiationIssue(Base):
    """An issue or ticket raised during negotiation."""
    __tablename__ = "negotiation_issues"

    issue_id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    clause_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default=IssueSeverity.MAJOR.value,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=IssueStatus.OPEN.value,
    )
    assignee: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assignee_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, default="legal",
    )
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["NegotiationSession"] = relationship(back_populates="issues")
    comments: Mapped[list["NegotiationComment"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="NegotiationComment.issue_id",
    )

    __table_args__ = (
        Index("ix_neg_issues_session_status", "session_id", "status"),
        Index("ix_neg_issues_session_severity", "session_id", "severity"),
    )

    def __repr__(self) -> str:
        return f"<NegotiationIssue {self.issue_id[:8]} severity={self.severity}>"


# ── Comments ───────────────────────────────────────────────────────

class NegotiationComment(Base):
    """Comments with nested replies, attachable to redlines or issues."""
    __tablename__ = "negotiation_comments"

    comment_id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("negotiation_comments.comment_id", ondelete="CASCADE"),
        nullable=True,
    )
    redline_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("negotiation_redlines.redline_id", ondelete="CASCADE"),
        nullable=True,
    )
    issue_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("negotiation_issues.issue_id", ondelete="CASCADE"),
        nullable=True,
    )
    clause_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    author_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CommentStatus.ACTIVE.value,
    )
    mentions: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["NegotiationSession"] = relationship(back_populates="comments")
    redline: Mapped[Optional["NegotiationRedline"]] = relationship(
        back_populates="comments",
        foreign_keys=[redline_id],
    )
    issue: Mapped[Optional["NegotiationIssue"]] = relationship(
        back_populates="comments",
        foreign_keys=[issue_id],
    )
    replies: Mapped[list["NegotiationComment"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="NegotiationComment.parent_id",
    )
    parent: Mapped[Optional["NegotiationComment"]] = relationship(
        back_populates="replies",
        remote_side="NegotiationComment.comment_id",
        foreign_keys=[parent_id],
    )

    __table_args__ = (
        Index("ix_neg_comments_session", "session_id"),
        Index("ix_neg_comments_redline", "redline_id"),
        Index("ix_neg_comments_issue", "issue_id"),
    )

    def __repr__(self) -> str:
        return f"<NegotiationComment {self.comment_id[:8]} by {self.author}>"


# ── Participants ───────────────────────────────────────────────────

class NegotiationParticipant(Base):
    """A person involved in the negotiation session."""
    __tablename__ = "negotiation_participants"

    participant_id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ParticipantRole.VIEWER.value,
    )
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_clauses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["NegotiationSession"] = relationship(back_populates="participants")

    __table_args__ = (
        Index("ix_neg_participants_session_role", "session_id", "role"),
    )

    def __repr__(self) -> str:
        return f"<NegotiationParticipant {self.name} role={self.role}>"


# ── Votes ──────────────────────────────────────────────────────────

class NegotiationVote(Base):
    """A vote on a clause or finding within a negotiation session.

    Supports voting on both clauses and individual findings, with
    role-based tracking for governance and approval workflows.
    """
    __tablename__ = "negotiation_votes"

    vote_id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("negotiation_sessions.session_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    clause_id: Mapped[str] = mapped_column(String(255), nullable=False)
    finding_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    voter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    voter_role: Mapped[str] = mapped_column(String(100), nullable=False)
    vote: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["NegotiationSession"] = relationship(back_populates="votes")

    __table_args__ = (
        Index("ix_neg_votes_session_clause", "session_id", "clause_id"),
        Index("ix_neg_votes_session_voter", "session_id", "voter_name"),
    )

    def __repr__(self) -> str:
        return f"<NegotiationVote {self.vote_id[:8]} clause={self.clause_id[:20]} vote={self.vote}>"
