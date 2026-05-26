"""Contract review domain — review sessions, findings, redlines, comments, assignments, escalations, approvals."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base

# Import FK target models to ensure SQLAlchemy can resolve all foreign keys
# in the review_redlines, review_findings, and contract_reviews tables.
# Without these imports, INSERT via ORM fails with NoReferencedTableError.
from app.domains.ingestion.models import UploadSession  # noqa: F401 — upload_sessions.upload_id
from app.domains.ai.models import AIFinding, AIRedline  # noqa: F401 — ai_findings.finding_id, ai_redlines.redline_id
from app.domains.tenants.models import Tenant  # noqa: F401 — tenants.tenant_id


class ReviewStatus(str, PyEnum):
    DRAFT = "draft"
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    AI_REVIEWED = "ai_reviewed"
    PROCUREMENT_REVIEW = "procurement_review"
    LEGAL_REVIEW = "legal_review"
    SECURITY_REVIEW = "security_review"
    NEGOTIATION = "negotiation"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    ESCALATED = "escalated"
    LEGAL_APPROVAL = "legal_approval"
    EXEC_APPROVAL = "exec_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FINALIZED = "finalized"
    EXECUTED = "executed"
    ARCHIVED = "archived"
    CLOSED = "closed"

    @classmethod
    def valid_transitions(cls) -> dict[ReviewStatus, set[ReviewStatus]]:
        return {
            cls.DRAFT: {cls.ANALYZING, cls.CLOSED},
            cls.UPLOADED: {cls.ANALYZING, cls.ARCHIVED, cls.CLOSED},
            cls.ANALYZING: {cls.AI_REVIEWED, cls.UPLOADED, cls.CLOSED},
            cls.AI_REVIEWED: {cls.PROCUREMENT_REVIEW, cls.LEGAL_REVIEW, cls.CLOSED},
            cls.PROCUREMENT_REVIEW: {
                cls.LEGAL_REVIEW, cls.SECURITY_REVIEW, cls.NEGOTIATION,
                cls.REJECTED, cls.CLOSED,
            },
            cls.LEGAL_REVIEW: {
                cls.APPROVED, cls.NEGOTIATION, cls.REJECTED,
                cls.PROCUREMENT_REVIEW, cls.ESCALATED, cls.CLOSED,
            },
            cls.SECURITY_REVIEW: {
                cls.LEGAL_REVIEW, cls.NEGOTIATION, cls.REJECTED,
                cls.PROCUREMENT_REVIEW, cls.ESCALATED, cls.CLOSED,
            },
            cls.NEGOTIATION: {
                cls.PROCUREMENT_REVIEW, cls.LEGAL_REVIEW,
                cls.APPROVED, cls.REJECTED, cls.CLOSED,
            },
            cls.IN_REVIEW: {
                cls.CHANGES_REQUESTED, cls.PROCUREMENT_REVIEW,
                cls.LEGAL_REVIEW, cls.SECURITY_REVIEW,
                cls.ESCALATED, cls.CLOSED,
            },
            cls.CHANGES_REQUESTED: {cls.IN_REVIEW, cls.ESCALATED, cls.CLOSED},
            cls.ESCALATED: {
                cls.IN_REVIEW, cls.PROCUREMENT_REVIEW, cls.LEGAL_REVIEW,
                cls.SECURITY_REVIEW, cls.LEGAL_APPROVAL,
                cls.EXEC_APPROVAL, cls.CLOSED,
            },
            cls.LEGAL_APPROVAL: {cls.EXEC_APPROVAL, cls.APPROVED, cls.REJECTED, cls.IN_REVIEW, cls.CLOSED},
            cls.EXEC_APPROVAL: {cls.APPROVED, cls.REJECTED, cls.IN_REVIEW, cls.CLOSED},
            cls.APPROVED: {cls.FINALIZED, cls.EXECUTED, cls.ARCHIVED, cls.CLOSED},
            cls.REJECTED: {cls.ARCHIVED, cls.CLOSED},
            cls.FINALIZED: {cls.EXECUTED, cls.ARCHIVED, cls.CLOSED},
            cls.EXECUTED: {cls.ARCHIVED, cls.CLOSED},
            cls.ARCHIVED: set(),
            cls.CLOSED: set(),
        }

    def can_transition_to(self, target: ReviewStatus) -> bool:
        return target in self.valid_transitions().get(self, set())


class FindingResolution(str, PyEnum):
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


class RedlineStatus(str, PyEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    SUPERSEDED = "superseded"
    NEEDS_LEGAL_REVIEW = "needs_legal_review"
    CUSTOMER_REQUESTED = "customer_requested"
    FALLBACK_LANGUAGE = "fallback_language"


class ContractReview(Base):
    """Tracks a complete contract review session for an upload."""
    __tablename__ = "contract_reviews"

    review_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id = Column(UUID, nullable=True)

    status = Column(
        SAEnum(
            ReviewStatus,
            name="review_status",
            create_type=False,
            values_callable=lambda states: [state.value for state in states],
        ),
        nullable=False,
        default=ReviewStatus.DRAFT,
    )
    assigned_to = Column(Text, nullable=True, index=True)
    assigned_by = Column(Text, nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)

    workflow_stage = Column(Text, nullable=True)  # 'reviewer', 'legal_ops', 'compliance', 'executive'
    priority = Column(Text, nullable=False, default="normal")  # 'urgent', 'high', 'normal', 'low'
    sla_deadline = Column(DateTime(timezone=True), nullable=True)
    sla_breached = Column(Boolean, nullable=False, default=False)
    sla_status = Column(Text, nullable=False, default="on_track")  # 'on_track', 'warning', 'overdue'
    overdue_hours = Column(Float, nullable=False, default=0.0)

    finding_count = Column(Integer, nullable=False, default=0)
    redline_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    escalation_count = Column(Integer, nullable=False, default=0)

    # Rejection metadata — captured when a review is rejected
    rejection_reason = Column(Text, nullable=True)
    rejection_category = Column(Text, nullable=True)  # 'legal_risk', 'compliance_issue', 'missing_clauses', 'unacceptable_liability', 'data_privacy_issue'
    rejection_severity = Column(Text, nullable=True)  # 'critical', 'high', 'medium', 'low'
    rejected_by = Column(Text, nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)

    # Review versioning — incremented on each re-analysis
    version = Column(Integer, nullable=False, default=1)
    previous_review_id = Column(UUID, nullable=True)  # Links to previous version

    # Soft delete support
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    delete_reason = Column(Text, nullable=True)

    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Links to the ContractDocumentVersion that was approved
    approved_version_id = Column(UUID, ForeignKey("contract_document_versions.version_id", ondelete="SET NULL"), nullable=True)


class ReviewFinding(Base):
    """An AI finding within a review context — tracks resolution and reviewer interaction."""
    __tablename__ = "review_findings"

    finding_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    ai_finding_id = Column(UUID, ForeignKey("ai_findings.finding_id", ondelete="SET NULL"), nullable=True)

    clause_type = Column(Text, nullable=True)
    severity = Column(Text, nullable=False)  # 'critical', 'high', 'medium', 'low', 'info'
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)

    chunk_ids = Column(ARRAY(UUID), nullable=False, default=list)
    page_numbers = Column(ARRAY(Integer), nullable=False, default=list)

    resolution = Column(SAEnum("acknowledged", "resolved", "dismissed", "false_positive", "escalated", name="finding_resolution", create_type=True), nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_by = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReviewRedline(Base):
    """A redline within a review context — tracks reviewer acceptance/modification."""
    __tablename__ = "review_redlines"

    redline_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    ai_redline_id = Column(UUID, ForeignKey("ai_redlines.redline_id", ondelete="SET NULL"), nullable=True)
    finding_id = Column(UUID, ForeignKey("review_findings.finding_id", ondelete="SET NULL"), nullable=True)

    clause_type = Column(Text, nullable=True)
    original_text = Column(Text, nullable=False)
    proposed_text = Column(Text, nullable=False)
    operation = Column(Text, nullable=True)  # insert, modification, delete, replace
    anchor_text = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)
    risk_level = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    # Stores: traceability {detected_risk, business_impact, mitigation_strategy}
    # Also: legal_domain, risk_type, ontology, insert_position from locator
    redline_metadata = Column("redline_metadata", JSONB, nullable=True, default=dict)

    status = Column(SAEnum("proposed", "accepted", "rejected", "modified", "superseded", "needs_legal_review", "customer_requested", "fallback_language", name="redline_status", create_type=True), nullable=False, default=RedlineStatus.PROPOSED)
    reviewer_modified_text = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_by = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReviewComment(Base):
    """Threaded comments on reviews, findings, or redlines."""
    __tablename__ = "review_comments"

    comment_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    entity_type = Column(Text, nullable=True)  # 'finding', 'redline', 'review'
    entity_id = Column(UUID, nullable=True)
    parent_comment_id = Column(UUID, ForeignKey("review_comments.comment_id", ondelete="CASCADE"), nullable=True)

    author_id = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    mentions = Column(ARRAY(Text), nullable=False, default=list)

    is_resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class ReviewAssignment(Base):
    """Tracks reviewer assignments with due dates and workload."""
    __tablename__ = "review_assignments"

    assignment_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    assignee_id = Column(Text, nullable=False, index=True)
    assigned_by = Column(Text, nullable=False)
    role = Column(Text, nullable=False, default="reviewer")  # 'reviewer', 'approver', 'observer'
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReviewEscalation(Base):
    """Tracks escalations with level and reason."""
    __tablename__ = "review_escalations"

    escalation_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    level = Column(Integer, nullable=False, default=1)
    escalated_by = Column(Text, nullable=False)
    escalated_to = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="open")  # 'open', 'acknowledged', 'resolved'
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReviewApproval(Base):
    """Tracks approval decisions with conditions."""
    __tablename__ = "review_approvals"

    approval_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    approver_id = Column(Text, nullable=False)
    decision = Column(Text, nullable=False)  # 'approved', 'rejected', 'conditionally_approved'
    comments = Column(Text, nullable=True)
    conditions = Column(JSONB, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReviewStatusHistory(Base):
    """Immutable audit trail of all review status changes."""
    __tablename__ = "review_status_history"

    history_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    from_status = Column(Text, nullable=False)
    to_status = Column(Text, nullable=False)
    changed_by = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RoutingRule(Base):
    """Automatic routing rules for review assignment based on contract attributes."""
    __tablename__ = "routing_rules"

    rule_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)

    # Condition fields (JSON logic)
    conditions = Column(JSONB, nullable=False, default=dict)

    # Action fields
    assign_to = Column(Text, nullable=False)  # reviewer/role to assign
    set_priority = Column(Text, nullable=True)  # 'urgent', 'high', 'normal', 'low'
    set_workflow_stage = Column(Text, nullable=True)  # 'reviewer', 'legal_ops', 'compliance', 'executive'
    sla_hours = Column(Integer, nullable=True)  # SLA deadline in hours

    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BulkAction(Base):
    """Tracks bulk operations on reviews for auditing."""
    __tablename__ = "bulk_actions"

    action_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(Text, nullable=False)  # 'assign', 'escalate', 'approve', 'export'
    review_ids = Column(ARRAY(UUID), nullable=False)
    params = Column(JSONB, nullable=True)
    triggered_by = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="completed")  # 'pending', 'processing', 'completed', 'failed'
    result = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ContractDocumentVersion(Base):
    """Immutable versioned contract document — tracks the full document lifecycle.

    Every time redlines are accepted or a review is approved, a new version
    is generated. Original uploads are never overwritten.

    Version lifecycle:
        v1 — Original uploaded contract
        v2 — AI redlines applied
        v3 — Legal review edits
        v4 — Final approved execution copy
    """
    __tablename__ = "contract_document_versions"

    version_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    version_number = Column(Integer, nullable=False)
    label = Column(Text, nullable=True)  # 'Original Upload', 'AI Redlines Applied', 'Legal Revision', 'Approved Copy'
    status = Column(Text, nullable=False, default="draft")  # 'draft', 'current', 'archived', 'signed'

    # Document references
    source_document_id = Column(UUID, nullable=True)  # Points to upload_sessions.upload_id for v1
    storage_key = Column(Text, nullable=True)  # MinIO/S3 key: contracts/{review_id}/versions/v{number}.docx

    # Change tracking
    change_summary = Column(Text, nullable=True)  # Human-readable description of what changed
    accepted_redline_ids = Column(ARRAY(UUID), nullable=True)  # Redline IDs applied in this version

    # Metadata
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(Text, nullable=True, default="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    checksum_sha256 = Column(Text, nullable=True)

    # Audit
    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("review_id", "version_number", name="uq_version_per_review"),
    )


class RiskDeltaEvent(Base):
    """Immutable record of a single risk delta event — one decision's impact on exposure.

    Each review decision (accept redline, reject, acknowledge finding, dismiss)
    produces exactly one RiskDeltaEvent. These form the risk timeline and are
    used to build the risk delta waterfall chart.

    Object chain:
        Finding → Suggested Mitigation → Review Decision → RiskDeltaEvent → Version Impact
    """
    __tablename__ = "risk_delta_events"

    delta_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    # Type of delta
    delta_type = Column(Text, nullable=False)  # 'mitigation', 'acceptance', 'dismissal', 'reversal', 'escalation', 'version_transition'

    # Links to the objects involved
    finding_id = Column(UUID, ForeignKey("review_findings.finding_id", ondelete="SET NULL"), nullable=True)
    redline_id = Column(UUID, ForeignKey("review_redlines.redline_id", ondelete="SET NULL"), nullable=True)

    # Numeric impact
    previous_risk = Column(Float, nullable=False, default=0.0)
    new_risk = Column(Float, nullable=False, default=0.0)
    delta_amount = Column(Float, nullable=False, default=0.0)
    delta_pct = Column(Float, nullable=False, default=0.0)

    # Who decided
    actor_id = Column(Text, nullable=True)
    actor_name = Column(Text, nullable=True)
    decision = Column(Text, nullable=True)     # 'accepted', 'rejected', 'modified', 'acknowledged', 'dismissed'
    rationale = Column(Text, nullable=True)

    # Version context
    version_number = Column(Integer, nullable=True)
    version_id = Column(UUID, ForeignKey("contract_document_versions.version_id", ondelete="SET NULL"), nullable=True)

    # Traceability enrichment
    clause_category = Column(Text, nullable=True)
    severity = Column(Text, nullable=True)
    finding_title = Column(Text, nullable=True)
    mitigation_type = Column(Text, nullable=True)
    mitigation_effectiveness = Column(Float, nullable=True)

    # Flexible metadata
    extra_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    # Immutable audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("delta_id", name="uq_risk_delta_event"),
    )
