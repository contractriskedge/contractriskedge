"""Review domain Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo


class ReviewSummary(BaseModel):
    review_id: str
    upload_id: str
    contract_id: Optional[str] = None
    review_number: str = ""
    status: str
    assigned_to: Optional[str] = None
    # Friendly display name of the assignee, resolved server-side from
    # admin_users via the repository's LEFT JOIN. FastAPI would otherwise
    # strip this field from the JSON response because it is not declared
    # on the response_model.
    assigned_to_name: Optional[str] = None
    priority: str = "normal"
    finding_count: int = 0
    redline_count: int = 0
    comment_count: int = 0
    escalation_count: int = 0
    is_favorite: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime
    # Document metadata (joined from upload_sessions)
    document_name: Optional[str] = None
    original_filename: Optional[str] = None
    document_type: Optional[str] = None
    # Risk score from AI analysis
    risk_score: Optional[float] = None
    version: int = 1


class ReviewDetail(ReviewSummary):
    sla_deadline: Optional[datetime] = None
    sla_due_at: Optional[datetime] = None
    sla_breached: bool = False
    sla_status: str = "on_track"
    overdue_hours: float = 0.0
    completed_at: Optional[datetime] = None
    assigned_by: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    workflow_stage: Optional[str] = None
    # Rejection metadata
    rejection_reason: Optional[str] = None
    rejection_category: Optional[str] = None
    rejection_severity: Optional[str] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    # Approved version reference
    approved_version_id: Optional[str] = None
    approved_version_number: Optional[int] = None
    # Contract number from document metadata
    contract_number: Optional[str] = None
    critical_finding_count: int = 0


class ReviewFilterParams(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class SourceLocation(BaseModel):
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    paragraph_index: Optional[int] = None
    source_text: Optional[str] = None
    source_start_offset: Optional[int] = None
    source_end_offset: Optional[int] = None
    confidence_score: Optional[float] = None
    chunk_id: Optional[str] = None


class FindingItem(BaseModel):
    finding_id: str
    finding_number: Optional[str] = None
    clause_type: Optional[str] = None
    severity: str
    title: str
    description: str
    recommendation: Optional[str] = None
    confidence: Optional[float] = None
    risk_score: Optional[float] = None
    page_numbers: list[int] = Field(default_factory=list)
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    paragraph_index: Optional[int] = None
    source_text: Optional[str] = None
    source_start_offset: Optional[int] = None
    source_end_offset: Optional[int] = None
    confidence_score: Optional[float] = None
    source_location: Optional[SourceLocation] = None
    resolution: Optional[str] = None
    resolution_note: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    feedback_type: Optional[str] = None
    feedback_note: Optional[str] = None
    feedback_at: Optional[datetime] = None
    playbook_id: Optional[str] = None
    rule_id: Optional[str] = None
    evaluation_id: Optional[str] = None
    clause_standard_id: Optional[str] = None
    policy_owner: Optional[str] = None
    policy_name: Optional[str] = None
    policy_rule_name: Optional[str] = None
    policy_version: Optional[str] = None


class FindingResolveRequest(BaseModel):
    resolution: str = Field(..., pattern="^(acknowledged|resolved|dismissed|false_positive|escalated)$")
    note: Optional[str] = Field(None, max_length=2000)


class FindingFeedbackRequest(BaseModel):
    type: str = Field(..., pattern="^(correct|incorrect|partial|unsure)$")
    reviewer_note: Optional[str] = Field(None, max_length=2000)
    retraining_priority: Optional[str] = Field("medium", pattern="^(low|medium|high)$")


class FindingFeedbackResponse(BaseModel):
    finding_id: str
    feedback_type: str
    reviewer_note: Optional[str] = None
    retraining_priority: str = "medium"
    created_at: datetime


class LocatorResponse(BaseModel):
    """Structured locator result — replaces old chunk-based locate."""
    status: str = "unresolved"  # resolved | partial | unresolved
    anchor_type: str = "none"   # exact_span | fuzzy | semantic | insertion | none
    confidence: float = 0.0
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    insert_position: Optional[str] = None  # after_section | before_section | within_section | append_document
    matched_text: Optional[str] = None
    chunk_id: Optional[str] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None


class WordDiffSegment(BaseModel):
    tag: str
    text: str


class RiskTraceabilityItem(BaseModel):
    """Audit-grade risk chain surfaced in the review UI.

    For AI-generated findings, shows the original risk detection chain.
    For mitigation-generated redlines, shows the remediation traceability.
    """
    detected_risk: str = ""
    business_impact: str = ""
    mitigation_strategy: str = ""
    # Extended fields for mitigation-generated redlines
    mitigation_type: Optional[str] = None
    estimated_reduction_pct: Optional[float] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    generated_from: Optional[str] = None  # "mitigation_recommendation" | "ai_analysis"


class ConfidenceLabel(BaseModel):
    """Semantic confidence label — replaces raw numeric percentage."""
    label: str          # "Very High" | "High" | "Medium" | "Low" | "Uncertain"
    tier: str           # "very_high" | "high" | "medium" | "low" | "uncertain"
    numeric: float      # underlying float, 0.0–1.0 (for sorting / filtering)


class RedlineMappingDetails(BaseModel):
    """Redline ↔ finding mapping integrity for reviewer validation."""
    finding_title: Optional[str] = None
    redline_title: Optional[str] = None
    category: Optional[str] = None
    finding_category: Optional[str] = None
    redline_category: Optional[str] = None


class RedlineItem(BaseModel):
    redline_id: str
    clause_type: Optional[str] = None
    original_text: str
    proposed_text: str
    ai_proposed_text: Optional[str] = None
    finding_id: Optional[str] = None
    finding_category: Optional[str] = None
    finding_title: Optional[str] = None
    finding_recommendation: Optional[str] = None
    redline_title: Optional[str] = None
    redline_category: Optional[str] = None
    mapping_valid: bool = True
    mapping_status: str = "valid"
    mapping_warning: Optional[str] = None
    mapping_details: Optional[RedlineMappingDetails] = None
    operation: Optional[str] = None
    anchor_text: Optional[str] = None
    context_excerpt: Optional[str] = None
    chunk_ids: list[str] = Field(default_factory=list)
    word_diff: list[WordDiffSegment] = Field(default_factory=list)
    rationale: Optional[str] = None
    risk_level: Optional[str] = None
    confidence: Optional[float] = None
    confidence_label: Optional[ConfidenceLabel] = None
    status: str = "proposed"
    reviewer_modified_text: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    # New structured locator — replaces old chunk-based locate
    locator: Optional[LocatorResponse] = None
    source_location: Optional[SourceLocation] = None
    # Risk traceability chain (from v3 prompt)
    traceability: Optional[RiskTraceabilityItem] = None


class RedlineUpdateRequest(BaseModel):
    status: str  # 'accepted', 'rejected', 'modified'
    modified_text: Optional[str] = None
    review_notes: Optional[str] = None


class GenerateMitigationRedlineRequest(BaseModel):
    """Request to generate a redline from a mitigation recommendation."""
    mitigation_type: str = Field(..., description="Mitigation type key (e.g. 'restricting_derivative_works')")
    clause_category: str = Field(..., description="Canonical clause category (e.g. 'intellectual_property')")
    finding_ids: list[str] = Field(default_factory=list, description="Optional finding IDs to link")


class GenerateMitigationRedlineResponse(BaseModel):
    """Response after generating a redline from a mitigation."""
    redline_id: str
    clause_type: Optional[str] = None
    proposed_text: str
    rationale: Optional[str] = None
    risk_level: Optional[str] = None
    status: str = "proposed"
    traceability: Optional[dict] = None
    finding_ids: list[str] = Field(default_factory=list)
    mitigation_type: str
    mitigation_label: str
    estimated_reduction_pct: float = 0.0
    confidence: float = 0.0


class RegenerateRedlineRequest(BaseModel):
    """Request to regenerate a redline using the finding's category as mandatory filter."""
    finding_id: str = Field(..., description="The finding ID to regenerate the redline for")
    finding_category: str = Field(..., description="The finding's clause_type — used as mandatory category filter")
    redline_id: str = Field(..., description="The existing invalid redline ID to replace")


class CommentCreate(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    parent_comment_id: Optional[str] = None
    body: str = Field(..., min_length=1, max_length=5000)
    mentions: list[str] = Field(default_factory=list)


class CommentItem(BaseModel):
    comment_id: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    parent_comment_id: Optional[str] = None
    author_id: str
    author_name: Optional[str] = None
    body: str
    mentions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AssignRequest(BaseModel):
    assignee_id: str
    role: str = Field(default="reviewer", pattern="^(reviewer|approver|observer|legal_ops|compliance|executive|security|procurement)$")
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class AssigneeItem(BaseModel):
    """Minimal user record for workflow assignment pickers."""
    user_id: str
    email: str
    name: str
    role: str
    business_unit: Optional[str] = None
    is_active: bool = True


class RedlineAssignRequest(BaseModel):
    assignee_id: str
    role: str = Field(default="legal_review", pattern="^(legal_review|procurement_review|security_review|business_review|reviewer|approver|observer)$")


class FavoriteToggleRequest(BaseModel):
    is_favorite: bool


class EscalateRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=2000)
    escalated_to: Optional[str] = None
    raise_priority: Optional[bool] = False
    target_workflow_stage: Optional[str] = None  # 'legal_approval', 'exec_approval', 'compliance'


class ApproveRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected|conditionally_approved)$")
    comments: Optional[str] = None
    conditions: Optional[dict] = None
    override_reason: Optional[str] = None

    @field_validator("comments")
    @classmethod
    def require_comments_for_rejection(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if info.data.get("decision") == "rejected" and not (v and v.strip()):
            raise ValueError("Rejection reason (comments) is required when decision is 'rejected'")
        return v


# ── Dashboard Schemas ──────────────────────────────────────────────

class DashboardStats(BaseModel):
    """Aggregated dashboard statistics for the review domain."""
    total_reviews: int = 0
    total_findings: int = 0
    total_redlines: int = 0
    average_risk_score: Optional[float] = None
    average_confidence: Optional[float] = None
    sla_breach_count: int = 0
    pending_reviews: int = 0
    completed_reviews: int = 0
    escalated_count: int = 0
    total_escalation_events: int = 0
    resolved_escalations: int = 0
    escalation_resolution_rate: float = 0.0
    unassigned_count: int = 0
    overdue_count: int = 0
    completed_7d: int = 0
    avg_review_age_hours: float = 0.0


class FindingsBySeverity(BaseModel):
    """Finding counts grouped by severity level."""
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class FindingsByClauseType(BaseModel):
    """Finding counts grouped by clause type."""
    liability: int = 0
    payment: int = 0
    data_privacy: int = 0
    compliance: int = 0
    indemnification: int = 0
    termination: int = 0
    confidentiality: int = 0
    intellectual_property: int = 0
    insurance: int = 0
    force_majeure: int = 0
    governing_law: int = 0
    non_compete: int = 0
    other: int = 0


class ReviewsByStatus(BaseModel):
    """Review counts grouped by status."""
    draft: int = 0
    ai_analyzed: int = 0
    in_review: int = 0
    pending_approval: int = 0
    approved: int = 0
    rejected: int = 0
    escalated: int = 0
    closed: int = 0


class RecentActivity(BaseModel):
    """A single recent activity entry for the dashboard."""
    activity_type: str  # 'review_created', 'finding_resolved', 'review_approved', 'review_escalated', etc.
    review_id: str
    upload_id: Optional[str] = None
    description: str
    actor: Optional[str] = None
    timestamp: datetime


class ReviewDashboardResponse(BaseModel):
    """Complete dashboard aggregation response."""
    stats: DashboardStats
    findings_by_severity: FindingsBySeverity
    findings_by_clause_type: FindingsByClauseType
    reviews_by_status: ReviewsByStatus
    recent_activity: list[RecentActivity] = Field(default_factory=list)
    sla_at_risk: int = 0


# ── Status Polling ─────────────────────────────────────────────────

class ReviewStatusResponse(BaseModel):
    """Standardized async status contract for frontend polling.

    Provides a unified view of where a review is in its lifecycle,
    including ingestion, AI analysis, and review stages.

    The computed_status field is the SINGLE AUTHORITATIVE status.
    All frontend components must use this field for display.
    """
    review_id: str
    upload_id: str
    status: str  # Overall status: 'uploading', 'validating', 'processing', 'analyzing', 'review_ready', 'in_review', 'completed', 'failed'
    ingestion_state: Optional[str] = None
    ai_status: Optional[str] = None
    review_status: Optional[str] = None
    progress: int = Field(default=0, ge=0, le=100, description="Overall progress percentage")
    current_step: Optional[str] = Field(None, description="Human-readable current step description")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Structured error code for programmatic handling")
    can_retry: bool = False
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    # ── Authoritative computed status (Phase 1) ──
    computed_status: str = Field(
        default="unassigned",
        description="Single authoritative status: unassigned|assigned|in_review|pending_approval|approved|rejected|escalated|overdue|completed"
    )
    sla_status: str = Field(default="on_track", description="green|amber|red")
    sla_remaining_hours: Optional[float] = None
    age_hours: Optional[float] = Field(None, description="Hours since review creation")
    pipeline_phase: Optional[str] = None
    """Pipeline phase: queued | ingesting | analyzing | ready | failed"""
    estimated_seconds_remaining: Optional[int] = Field(
        None, description="Rough ETA in seconds until findings/redlines are ready",
    )
    eta_label: Optional[str] = Field(None, description="Human-readable ETA, e.g. ~2 min")
    finding_count: int = 0
    redline_count: int = 0
    analysis_source: Optional[str] = Field(
        None, description="template_generation | upload | etc. from review metadata",
    )


# ── Re-analysis ────────────────────────────────────────────────────

class ReAnalysisRequest(BaseModel):
    """Request to re-run AI analysis on an existing review."""
    review_id: str
    analysis_type: str = Field(default="full", pattern="^(full|risk_only|redline_only)$")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for re-analysis")


class ReAnalysisResponse(BaseModel):
    """Response after triggering re-analysis."""
    review_id: str
    run_id: str
    status: str = "processing"
    message: str = "Re-analysis pipeline started."
    previous_run_id: Optional[str] = None
    version: int = 1


# ── Soft Delete ────────────────────────────────────────────────────

class ReviewDeleteRequest(BaseModel):
    """Request to soft-delete a review."""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for deletion")


class ReviewArchiveRequest(BaseModel):
    """Request to archive reviews based on criteria."""
    older_than_days: int = Field(default=90, ge=30, description="Archive reviews older than this many days")
    status_filter: Optional[str] = Field(None, description="Only archive reviews with this status")
    dry_run: bool = Field(default=False, description="If true, only return count without archiving")


# ── SLA / Workload / Routing ─────────────────────────────────────

class SLAInfo(BaseModel):
    sla_deadline: Optional[datetime] = None
    sla_status: str = "on_track"  # 'on_track', 'warning', 'overdue'
    overdue_hours: float = 0.0
    sla_breached: bool = False


class WorkloadMetrics(BaseModel):
    """Operational workload metrics for the review queue."""
    total: int = 0
    unassigned: int = 0
    in_review: int = 0
    overdue: int = 0
    escalated: int = 0
    critical: int = 0
    sla_at_risk: int = 0
    completed_today: int = 0


class RoutingRuleSchema(BaseModel):
    """A single routing rule for automatic review assignment."""
    rule_id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    priority: int = 0
    conditions: dict = Field(default_factory=dict)
    assign_to: str
    set_priority: Optional[str] = None
    set_workflow_stage: Optional[str] = None
    sla_hours: Optional[int] = None
    created_by: str
    created_at: datetime


class RoutingRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: int = 0
    conditions: dict = Field(default_factory=dict)
    assign_to: str
    set_priority: Optional[str] = None
    set_workflow_stage: Optional[str] = None
    sla_hours: Optional[int] = None


class BulkAssignRequest(BaseModel):
    review_ids: list[str] = Field(..., min_length=1)
    assignee_id: str
    role: str = "reviewer"
    due_date: Optional[datetime] = None


class BulkEscalateRequest(BaseModel):
    review_ids: list[str] = Field(..., min_length=1)
    reason: str
    escalated_to: Optional[str] = None


class BulkApproveRequest(BaseModel):
    review_ids: list[str] = Field(..., min_length=1)
    decision: str = "approved"
    comments: Optional[str] = None


class BulkExportRequest(BaseModel):
    review_ids: list[str] = Field(..., min_length=1, max_length=500)


class BulkRedlineIdsRequest(BaseModel):
    redline_ids: list[str] = Field(..., min_length=1, max_length=500)


class BulkActionResponse(BaseModel):
    action_id: str
    action_type: str
    total: int
    succeeded: int
    failed: int
    errors: list[str] = Field(default_factory=list)


# ── Document Versions ─────────────────────────────────────────────

class DocumentVersionItem(BaseModel):
    version_id: str
    review_id: str
    version_number: int
    label: Optional[str] = None
    status: str = "draft"
    source_document_id: Optional[str] = None
    storage_key: Optional[str] = None
    change_summary: Optional[str] = None
    accepted_redline_ids: Optional[list[str]] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    checksum_sha256: Optional[str] = None
    created_by: str
    created_at: datetime


class CreateDocumentVersionRequest(BaseModel):
    review_id: str
    label: Optional[str] = None
    change_summary: Optional[str] = None
    accepted_redline_ids: Optional[list[str]] = None


# ── Workspace Hydration ────────────────────────────────────────────


class WorkspaceHydration(BaseModel):
    """Unified workspace payload — replaces parallel REST fanout.

    Returns everything needed to render a review workspace in a single
    response, eliminating the need for 10+ parallel API calls.

    Frontend should call this once instead of:
        GET /reviews/{id}
        GET /reviews/{id}/status
        GET /reviews/{id}/findings
        GET /reviews/{id}/risk-breakdown
        GET /reviews/{id}/versions
        GET /reviews/{id}/risk-delta-timeline
        GET /reviews/{id}/comments
        GET /reviews/{id}/history
        GET /notifications?entity_id={id}
    """
    # Core review data
    review: ReviewDetail

    # Lifecycle status
    status: ReviewStatusResponse

    # Findings (paginated, first page)
    findings: list[FindingItem] = Field(default_factory=list)
    total_findings: int = 0

    # Risk intelligence
    risk_breakdown: Optional[dict] = None
    risk_score: Optional[float] = None

    # Document versions
    versions: list[DocumentVersionItem] = Field(default_factory=list)
    current_version: Optional[DocumentVersionItem] = None

    # Workflow state
    workflow_stage: Optional[str] = None
    escalation_count: int = 0
    sla_status: str = "on_track"
    sla_deadline: Optional[datetime] = None

    # Reviewer context
    assigned_to: Optional[str] = None
    reviewer_active_count: int = 0  # How many active reviews this reviewer has

    # Recent activity
    recent_activity: list[dict] = Field(default_factory=list)

    # Notifications summary
    unread_notifications: int = 0

    # Recovery governance (if any recovery actions were taken)
    last_recovery_action: Optional[dict] = None

    # Metadata
    hydrated_at: datetime = Field(default_factory=datetime.utcnow)
    response_size_estimate_bytes: int = 0


# ── Reviewer Ops Schemas ──────────────────────────────────────────

class MyWorkItem(BaseModel):
    """A single review item for the My Work endpoint."""
    review_id: str
    contract_name: Optional[str] = None
    status: str
    risk_score: Optional[float] = None
    sla_deadline: Optional[datetime] = None
    assigned_to: Optional[str] = None
    created_at: datetime


class QueueFilterParams(BaseModel):
    """Filters for the operational review queue."""
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    risk_min: Optional[float] = None
    risk_max: Optional[float] = None
    age_min_hours: Optional[float] = None
    age_max_hours: Optional[float] = None
    escalated_only: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class RecommendationItem(BaseModel):
    """A recommendation derived from review findings with actual recommendation content."""
    finding_id: str
    review_id: str
    clause_type: Optional[str] = None
    severity: str
    title: str
    description: str
    recommendation: str
    confidence: float
    risk_score: Optional[float] = None
    created_at: datetime
