"""Contract review API router — full set of review management endpoints."""

from __future__ import annotations

import logging
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import Response
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission, require_any_permission
from app.kernel.security.permissions import Permissions
from app.kernel.web.pagination import PaginatedResponse, PaginationMeta
from app.domains.review.schemas import (
    ReviewDetail, ReviewFilterParams, FindingItem, RedlineItem,
    CommentItem, CommentCreate, AssignRequest, RedlineAssignRequest, EscalateRequest,
    ApproveRequest, FindingResolveRequest, RedlineUpdateRequest,
    GenerateMitigationRedlineRequest, GenerateMitigationRedlineResponse,
    RegenerateRedlineRequest,
    ReviewDashboardResponse, DashboardStats, FindingsBySeverity,
    FindingsByClauseType, ReviewsByStatus, RecentActivity,
    ReviewStatusResponse, ReAnalysisRequest, ReAnalysisResponse,
    ReviewDeleteRequest, ReviewArchiveRequest,
    BulkAssignRequest, BulkEscalateRequest, BulkApproveRequest, BulkExportRequest,
    BulkRedlineIdsRequest,
    DocumentVersionItem, CreateDocumentVersionRequest,
    FindingFeedbackRequest, FindingFeedbackResponse,
)
from app.domains.review.service import ReviewService
from app.domains.review.utils import build_source_location, enum_value as _enum_value, redline_to_item
from app.domains.review.repository import ReviewRepository
from app.domains.review.workflow import ImmutableReviewError
from app.domains.ai.repository import AIRepository
from app.domains.notify.repository import NotificationRepository
from app.domains.notify.service import NotificationService
from app.kernel.events.bus import EventBus
from app.kernel.web.exceptions import ConflictError

router = APIRouter(prefix="/reviews", tags=["Contract Review"])

logger = logging.getLogger(__name__)


async def get_review_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    request: Request = None,
) -> ReviewService:
    # Use the shared application event bus so domain event handlers
    # registered at startup (e.g. on_review_finalized) receive events.
    event_bus = getattr(request.app.state, "event_bus", None) if request else None
    if event_bus is None:
        event_bus = EventBus()
    return ReviewService(
        review_repo=ReviewRepository(db, tenant_id=tenant_id),
        ai_repo=AIRepository(db, tenant_id=tenant_id),
        event_bus=event_bus,
        user=user,
        tenant_id=tenant_id,
        notify_service=NotificationService(
            repo=NotificationRepository(db, tenant_id=tenant_id),
            event_bus=event_bus,
            tenant_id=tenant_id,
        ),
    )


@router.get("", response_model=PaginatedResponse[ReviewDetail], include_in_schema=False)
@router.get("/", response_model=PaginatedResponse[ReviewDetail])
async def list_reviews(
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List contract reviews with filtering and pagination."""
    filters = ReviewFilterParams(
        status=status, assigned_to=assigned_to, priority=priority,
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order,
    )
    items, total = await service.list_reviews(filters)
    data = [service._review_to_detail(r) for r in items]
    return PaginatedResponse(
        data=data,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=max(1, (total + page_size - 1) // page_size)),
    )


@router.get("/upload/{upload_id}", response_model=ReviewDetail)
async def get_or_create_review(
    upload_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get existing review for an upload or create one from AI results."""
    return await service.get_or_create_review(upload_id)


@router.get("/dashboard", response_model=ReviewDashboardResponse)
async def get_review_dashboard(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get aggregated dashboard statistics for contract reviews.

    Returns:
        - Overall stats (totals, averages, SLA breaches)
        - Findings grouped by severity and clause type
        - Reviews grouped by status
        - Recent activity feed
        - SLA at-risk count
    """
    repo = ReviewRepository(db, tenant_id=tenant_id)

    stats_data = await repo.get_dashboard_stats(tenant_id)
    findings_by_severity_data = await repo.get_findings_by_severity(tenant_id)
    findings_by_clause_data = await repo.get_findings_by_clause_type(tenant_id)
    reviews_by_status_data = await repo.get_reviews_by_status(tenant_id)
    recent_activity_data = await repo.get_recent_activity(tenant_id, limit=10)

    # Build response with defaults for missing keys
    stats = DashboardStats(
        total_reviews=stats_data.get("total_reviews", 0),
        total_findings=stats_data.get("total_findings", 0),
        total_redlines=stats_data.get("total_redlines", 0),
        average_risk_score=stats_data.get("average_risk_score"),
        average_confidence=stats_data.get("average_confidence"),
        sla_breach_count=stats_data.get("sla_breach_count", 0),
        pending_reviews=stats_data.get("pending_reviews", 0),
        completed_reviews=stats_data.get("completed_reviews", 0),
        escalated_count=stats_data.get("escalated_count", 0),
        total_escalation_events=stats_data.get("total_escalation_events", 0),
        resolved_escalations=stats_data.get("resolved_escalations", 0),
        escalation_resolution_rate=stats_data.get("escalation_resolution_rate", 0.0),
        unassigned_count=stats_data.get("unassigned_count", 0),
        overdue_count=stats_data.get("overdue_count", 0),
        completed_7d=stats_data.get("completed_7d", 0),
        avg_review_age_hours=stats_data.get("avg_review_age_hours", 0.0),
    )

    severity = FindingsBySeverity(
        critical=findings_by_severity_data.get("critical", 0),
        high=findings_by_severity_data.get("high", 0),
        medium=findings_by_severity_data.get("medium", 0),
        low=findings_by_severity_data.get("low", 0),
        info=findings_by_severity_data.get("info", 0),
    )

    clause = FindingsByClauseType(
        liability=findings_by_clause_data.get("liability", 0),
        payment=findings_by_clause_data.get("payment", 0),
        data_privacy=findings_by_clause_data.get("data_privacy", 0),
        compliance=findings_by_clause_data.get("compliance", 0),
        indemnification=findings_by_clause_data.get("indemnification", 0),
        termination=findings_by_clause_data.get("termination", 0),
        confidentiality=findings_by_clause_data.get("confidentiality", 0),
        intellectual_property=findings_by_clause_data.get("intellectual_property", 0),
        insurance=findings_by_clause_data.get("insurance", 0),
        force_majeure=findings_by_clause_data.get("force_majeure", 0),
        governing_law=findings_by_clause_data.get("governing_law", 0),
        non_compete=findings_by_clause_data.get("non_compete", 0),
        other=findings_by_clause_data.get("other", 0),
    )

    status_counts = ReviewsByStatus(
        draft=reviews_by_status_data.get("draft", 0),
        ai_analyzed=reviews_by_status_data.get("ai_analyzed", 0),
        in_review=reviews_by_status_data.get("in_review", 0),
        pending_approval=reviews_by_status_data.get("pending_approval", 0),
        approved=reviews_by_status_data.get("approved", 0),
        rejected=reviews_by_status_data.get("rejected", 0),
        escalated=reviews_by_status_data.get("escalated", 0),
        closed=reviews_by_status_data.get("closed", 0),
    )

    from datetime import datetime

    activity = [
        RecentActivity(
            activity_type=a.get("activity_type", "unknown"),
            review_id=str(a.get("review_id", "")),
            upload_id=str(a.get("upload_id")) if a.get("upload_id") else None,
            description=a.get("description", ""),
            actor=a.get("actor"),
            timestamp=a.get("timestamp", datetime.utcnow()),
        )
        for a in recent_activity_data
    ]

    return ReviewDashboardResponse(
        stats=stats,
        findings_by_severity=severity,
        findings_by_clause_type=clause,
        reviews_by_status=status_counts,
        recent_activity=activity,
        sla_at_risk=stats_data.get("sla_at_risk", 0),
    )


@router.get("/governance-analytics")
async def get_governance_analytics(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get governance-specific analytics for executive reporting.

    Returns:
        - avg_review_time_hours, approval_rate, rejection_rate
        - sla_breach_count, avg_overdue_hours
        - escalation_frequency
        - reviewer_workload (active + completed per reviewer)
        - top_failing_clauses (from rejected reviews)
    """
    repo = ReviewRepository(db, tenant_id=tenant_id)
    return await repo.get_governance_analytics(tenant_id)


@router.get("/recovery-audit")
async def get_recovery_audit(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    entity_type: Optional[str] = Query(None, description="Filter by entity type: upload, ai_run, review"),
    action_type: Optional[str] = Query(None, description="Filter by action type: re-queued, marked_failed, priority_bump, max_escalation_reached"),
    limit: int = Query(50, ge=1, le=200),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get recovery action audit trail for operational visibility.

    Returns recovery actions taken by the automated recovery daemon,
    including cooldown state, escalation counts, and outcomes.

    This endpoint enables:
    - Operational dashboards showing recovery activity
    - Auditing recovery decisions and their outcomes
    - Monitoring cooldown state and escalation saturation
    - Detecting recurring failure patterns
    """
    from sqlalchemy import text as sa_text

    conditions = ["ra.tenant_id = :tenant_id"]
    params = {"tenant_id": tenant_id}

    if entity_type:
        conditions.append("ra.entity_type = :entity_type")
        params["entity_type"] = entity_type
    if action_type:
        conditions.append("ra.action_type = :action_type")
        params["action_type"] = action_type

    where_clause = " AND ".join(conditions)

    query = sa_text(f"""
        SELECT
            ra.action_id,
            ra.entity_type,
            ra.entity_id,
            ra.action_type,
            ra.previous_state,
            ra.new_state,
            ra.escalation_count,
            ra.cooldown_until,
            ra.success,
            ra.message,
            ra.created_at,
            CASE
                WHEN ra.cooldown_until IS NULL THEN 'expired'
                WHEN ra.cooldown_until > NOW() THEN 'active'
                ELSE 'expired'
            END AS cooldown_status
        FROM recovery_actions ra
        WHERE {where_clause}
        ORDER BY ra.created_at DESC
        LIMIT :limit
    """).bindparams(**params, limit=limit)

    result = await db.execute(query)
    rows = result.fetchall()

    # Get summary stats
    stats_query = sa_text(f"""
        SELECT
            COUNT(*)::int AS total_actions,
            COUNT(*) FILTER (WHERE success = true)::int AS successful_actions,
            COUNT(*) FILTER (WHERE success = false)::int AS failed_actions,
            COUNT(*) FILTER (WHERE cooldown_until > NOW())::int AS active_cooldowns,
            COUNT(*) FILTER (WHERE action_type = 'max_escalation_reached')::int AS max_escalation_events
        FROM recovery_actions
        WHERE {where_clause}
    """)
    stats_result = await db.execute(stats_query, params)
    stats = stats_result.fetchone()

    return {
        "actions": [
            {
                "action_id": str(row.action_id),
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id)[:8] + "..." if row.entity_id else None,
                "action_type": row.action_type,
                "previous_state": row.previous_state,
                "new_state": row.new_state,
                "escalation_count": row.escalation_count,
                "cooldown_until": row.cooldown_until.isoformat() if row.cooldown_until else None,
                "cooldown_status": row.cooldown_status,
                "success": row.success,
                "message": row.message,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
        "summary": {
            "total_actions": stats.total_actions if stats else 0,
            "successful_actions": stats.successful_actions if stats else 0,
            "failed_actions": stats.failed_actions if stats else 0,
            "active_cooldowns": stats.active_cooldowns if stats else 0,
            "max_escalation_events": stats.max_escalation_events if stats else 0,
        },
    }


@router.get("/{review_id}", response_model=ReviewDetail)
async def get_review(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get review details by ID."""
    review = await service.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


# ── Workspace Hydration ────────────────────────────────────────────


@router.get("/{review_id}/workspace")
async def hydrate_workspace(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Hydrate a complete review workspace in a single request.

    Replaces 10+ parallel API calls with one unified response.
    Returns review details, status, findings, risk breakdown,
    versions, workflow state, notifications, and recovery audit.

    Frontend should call this once on workspace load instead of:
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
    from datetime import datetime
    from app.domains.review.repository import ReviewRepository
    from app.domains.ingestion.repository import IngestionRepository
    from app.domains.ai.repository import AIRepository
    from app.domains.review.utils import build_source_location, enum_value as _enum_value
    from sqlalchemy import text as sa_text, select
    from app.domains.review.models import ContractReview
    from app.domains.vectors.models import Chunk

    review_repo = ReviewRepository(db, tenant_id=tenant_id)
    ingest_repo = IngestionRepository(db, tenant_id=tenant_id)
    ai_repo = AIRepository(db, tenant_id=tenant_id)

    # ── 1. Get review ────────────────────────────────────────────
    service = ReviewService(
        review_repo=review_repo,
        ai_repo=ai_repo,
        event_bus=__import__('app.kernel.events.bus', fromlist=['EventBus']).EventBus(),
        user=user,
        tenant_id=tenant_id,
    )
    review = await service.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    def _r(key: str, default=None):
        return review.get(key, default) if isinstance(review, dict) else getattr(review, key, default)

    # ── 2. Get status ────────────────────────────────────────────
    upload = await ingest_repo.get_by_id(str(_r("upload_id")))
    ingestion_state = None
    ingestion_error = None
    if upload:
        raw_state = upload.ingestion_state
        ingestion_state = raw_state.value if hasattr(raw_state, 'value') else str(raw_state) if raw_state else None
        ingestion_error = upload.ingestion_error

    ai_run = await ai_repo.get_latest_run_for_upload(str(_r("upload_id")))
    ai_status = None
    ai_error = None
    if ai_run:
        raw_status = ai_run.status
        ai_status = raw_status.value if hasattr(raw_status, 'value') else raw_status
        ai_error = ai_run.error_message

    progress, current_step, overall_status, error, error_code, can_retry = _compute_review_status(
        review_status=_enum_value(_r("status")),
        ingestion_state=ingestion_state,
        ai_status=ai_status,
        ingestion_error=ingestion_error,
        ai_error=ai_error,
    )

    status_response = {
        "review_id": review_id,
        "upload_id": str(_r("upload_id")),
        "status": overall_status,
        "ingestion_state": ingestion_state,
        "ai_status": ai_status,
        "review_status": _enum_value(_r("status")),
        "progress": progress,
        "current_step": current_step,
        "error": error,
        "error_code": error_code,
        "can_retry": can_retry,
        "created_at": _r("created_at"),
        "updated_at": _r("updated_at"),
        "completed_at": _r("completed_at"),
    }

    # ── 3. Get findings (first page) ─────────────────────────────
    findings_data, _ = await review_repo.get_findings(review_id, tenant_id)
    chunk_ids = [cid for f in (findings_data or []) for cid in (f.chunk_ids or [])]
    chunks_by_id = {}
    if chunk_ids:
        chunk_result = await db.execute(
            select(Chunk).where(Chunk.chunk_id.in_(chunk_ids), Chunk.tenant_id == tenant_id)
        )
        chunks_by_id = {str(c.chunk_id): c for c in chunk_result.scalars().all()}

    def _source_payload(f):
        source = build_source_location(f, chunk=chunks_by_id.get(str((f.chunk_ids or [None])[0])))
        return source.model_dump() if source else None

    findings = [
        {
            "finding_id": str(f.finding_id),
            "clause_type": f.clause_type,
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "recommendation": f.recommendation,
            "confidence": f.confidence,
            "risk_score": f.risk_score,
            "page_numbers": f.page_numbers or [],
            "page_number": f.page_number,
            "section_heading": f.section_heading,
            "paragraph_index": f.paragraph_index,
            "source_text": f.source_text,
            "source_start_offset": f.source_start_offset,
            "source_end_offset": f.source_end_offset,
            "confidence_score": f.confidence_score,
            "source_location": _source_payload(f),
            "resolution": f.resolution.value if hasattr(f.resolution, 'value') else f.resolution,
            "resolution_note": f.resolution_note,
            "resolved_by": f.resolved_by,
            "resolved_at": f.resolved_at,
            "created_at": f.created_at,
        }
        for f in (findings_data or [])
    ]

    # ── 4. Get risk breakdown ────────────────────────────────────
    risk_breakdown = None
    try:
        from app.domains.review.risk_scoring import compute_risk_breakdown
        risk_breakdown = await compute_risk_breakdown(review_id, tenant_id, db)
    except Exception:
        pass

    # ── 5. Get document versions ─────────────────────────────────
    versions_result = await db.execute(
        sa_text("""
            SELECT version_id, review_id, version_number, label, status,
                   source_document_id, storage_key, change_summary,
                   accepted_redline_ids, file_size_bytes, mime_type,
                   checksum_sha256, created_by, created_at
            FROM contract_document_versions
            WHERE review_id = :review_id AND tenant_id = :tenant_id
            ORDER BY version_number DESC
        """), {"review_id": review_id, "tenant_id": tenant_id}
    )
    version_rows = versions_result.fetchall()
    versions = [
        {
            "version_id": str(v.version_id),
            "review_id": str(v.review_id),
            "version_number": v.version_number,
            "label": v.label,
            "status": v.status,
            "source_document_id": str(v.source_document_id) if v.source_document_id else None,
            "storage_key": v.storage_key,
            "change_summary": v.change_summary,
            "accepted_redline_ids": list(v.accepted_redline_ids) if v.accepted_redline_ids else None,
            "file_size_bytes": v.file_size_bytes,
            "mime_type": v.mime_type,
            "checksum_sha256": v.checksum_sha256,
            "created_by": v.created_by,
            "created_at": v.created_at,
        }
        for v in version_rows
    ]
    current_version = versions[0] if versions else None

    # ── 6. Get recent activity ───────────────────────────────────
    activity_result = await db.execute(
        sa_text("""
            SELECT h.history_id, h.from_status, h.to_status, h.changed_by,
                   h.reason, h.created_at
            FROM review_status_history h
            WHERE h.review_id = :review_id AND h.tenant_id = :tenant_id
            ORDER BY h.created_at DESC
            LIMIT 10
        """), {"review_id": review_id, "tenant_id": tenant_id}
    )
    recent_activity = [
        {
            "activity_id": str(a.history_id),
            "from_status": a.from_status,
            "to_status": a.to_status,
            "changed_by": a.changed_by,
            "reason": a.reason,
            "created_at": a.created_at,
        }
        for a in activity_result.fetchall()
    ]

    # ── 7. Get unread notifications ──────────────────────────────
    notif_result = await db.execute(
        sa_text("""
            SELECT COUNT(*)::int AS unread_count
            FROM notifications
            WHERE tenant_id = :tenant_id
              AND user_id = :user_id
              AND entity_id = :entity_id
              AND is_read = FALSE
        """), {"tenant_id": tenant_id, "user_id": user.id, "entity_id": review_id}
    )
    unread_count = notif_result.scalar() or 0

    # ── 8. Get reviewer workload ─────────────────────────────────
    reviewer_workload = 0
    if _r("assigned_to"):
        workload_result = await db.execute(
            sa_text("""
                SELECT COUNT(*)::int AS active_count
                FROM contract_reviews
                WHERE assigned_to = :assignee
                  AND tenant_id = :tenant_id
                  AND is_deleted = FALSE
                  AND status::text NOT IN ('approved', 'rejected', 'closed', 'archived', 'finalized', 'executed')
            """), {"assignee": _r("assigned_to"), "tenant_id": tenant_id}
        )
        reviewer_workload = workload_result.scalar() or 0

    # ── 9. Get last recovery action ──────────────────────────────
    recovery_result = await db.execute(
        sa_text("""
            SELECT action_type, escalation_count, cooldown_until, success, message, created_at
            FROM recovery_actions
            WHERE entity_type = 'review'
              AND entity_id = :review_id
              AND tenant_id = :tenant_id
            ORDER BY created_at DESC
            LIMIT 1
        """), {"review_id": review_id, "tenant_id": tenant_id}
    )
    last_recovery = recovery_result.fetchone()
    last_recovery_action = None
    if last_recovery:
        last_recovery_action = {
            "action_type": last_recovery.action_type,
            "escalation_count": last_recovery.escalation_count,
            "cooldown_until": last_recovery.cooldown_until.isoformat() if last_recovery.cooldown_until else None,
            "success": last_recovery.success,
            "message": last_recovery.message,
            "created_at": last_recovery.created_at,
        }

    # ── Assemble response ────────────────────────────────────────
    import json
    response = {
        "review": review,
        "status": status_response,
        "findings": findings,
        "total_findings": len(findings),
        "risk_breakdown": risk_breakdown,
        "risk_score": _r("risk_score"),
        "versions": versions,
        "current_version": current_version,
        "workflow_stage": _r("workflow_stage"),
        "escalation_count": _r("escalation_count", 0),
        "sla_status": _r("sla_status", "on_track"),
        "sla_deadline": _r("sla_deadline"),
        "assigned_to": _r("assigned_to"),
        "reviewer_active_count": reviewer_workload,
        "recent_activity": recent_activity,
        "unread_notifications": unread_count,
        "last_recovery_action": last_recovery_action,
        "hydrated_at": datetime.utcnow(),
        "response_size_estimate_bytes": len(json.dumps({
            "review": str(review_id),
            "findings_count": len(findings),
            "versions_count": len(versions),
        })),
    }

    return response


# ── Status Polling ─────────────────────────────────────────────────


@router.get("/{review_id}/status", response_model=ReviewStatusResponse)
async def get_review_status(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get standardized async status for frontend polling.

    Returns a unified status contract combining ingestion, AI analysis,
    and review lifecycle states. Designed for frontend polling loops.
    """
    from app.domains.review.repository import ReviewRepository
    from app.domains.ingestion.repository import IngestionRepository
    from app.domains.ai.repository import AIRepository

    review_repo = ReviewRepository(db, tenant_id=tenant_id)
    ingest_repo = IngestionRepository(db, tenant_id=tenant_id)
    ai_repo = AIRepository(db, tenant_id=tenant_id)

    review = await review_repo.get_review(review_id, tenant_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Get ingestion status
    upload = await ingest_repo.get_by_id(str(review.upload_id))
    if upload:
        raw_state = upload.ingestion_state
        ingestion_state = raw_state.value if hasattr(raw_state, 'value') else str(raw_state) if raw_state else None
        ingestion_error = upload.ingestion_error
    else:
        ingestion_state = None
        ingestion_error = None

    # Get AI analysis status
    ai_run = await ai_repo.get_latest_run_for_upload(str(review.upload_id))
    if ai_run:
        raw_status = ai_run.status
        ai_status = raw_status.value if hasattr(raw_status, 'value') else raw_status
        ai_error = ai_run.error_message
    else:
        ai_status = None
        ai_error = None

    # Compute overall progress and current step
    progress, current_step, overall_status, error, error_code, can_retry = _compute_review_status(
        review_status=_enum_value(review.status),
        ingestion_state=ingestion_state,
        ai_status=ai_status,
        ingestion_error=ingestion_error,
        ai_error=ai_error,
    )

    # ── Compute authoritative status (Phase 1: OVERDUE supersedes all) ──
    from datetime import datetime as _dt
    raw_status = _enum_value(review.status)
    is_completed = raw_status in ("completed", "approved", "closed")
    is_overdue = bool(review.overdue_hours and review.overdue_hours > 0) and not is_completed
    is_escalated = raw_status == "escalated"
    is_assigned = bool(review.assigned_to)
    is_in_review = raw_status in ("in_review", "ai_analyzed", "review_ready")

    if is_completed:
        computed_status = "completed"
    elif is_escalated:
        computed_status = "escalated"
    elif is_overdue:
        computed_status = "overdue"
    elif is_in_review and is_assigned:
        computed_status = "in_review"
    elif is_assigned:
        computed_status = "assigned"
    else:
        computed_status = "unassigned"

    # ── SLA status (Phase 2) ──
    sla_remaining = None
    sla_status = "on_track"
    if review.sla_deadline and not is_completed:
        now = _dt.now(tz=review.sla_deadline.tzinfo) if review.sla_deadline.tzinfo else _dt.utcnow()
        remaining = (review.sla_deadline - now).total_seconds() / 3600
        sla_remaining = max(0, remaining)
        total_sla = 72  # default 72h; could be computed from priority
        if review.priority == "critical":
            total_sla = 4
        elif review.priority == "high":
            total_sla = 24
        elif review.priority == "medium":
            total_sla = 48
        pct_remaining = (sla_remaining / total_sla * 100) if total_sla > 0 else 0
        if remaining <= 0:
            sla_status = "red"
        elif pct_remaining <= 25:
            sla_status = "amber"
        else:
            sla_status = "green"
    elif is_completed:
        sla_status = "on_track"

    # ── Age in queue ──
    now_utc = _dt.now(tz=review.created_at.tzinfo) if review.created_at and review.created_at.tzinfo else _dt.utcnow()
    age_hours = (now_utc - review.created_at).total_seconds() / 3600 if review.created_at else None

    # ── Assignment status ──
    assignment_status = "assigned" if review.assigned_to else "unassigned"

    return ReviewStatusResponse(
        review_id=str(review.review_id),
        upload_id=str(review.upload_id),
        status=overall_status,
        ingestion_state=ingestion_state,
        ai_status=ai_status,
        review_status=raw_status,
        progress=progress,
        current_step=current_step,
        error=error,
        error_code=error_code,
        can_retry=can_retry,
        created_at=review.created_at,
        updated_at=review.updated_at,
        completed_at=review.completed_at,
        computed_status=computed_status,
        sla_status=sla_status,
        sla_remaining_hours=sla_remaining,
        age_hours=age_hours,
        assignment_status=assignment_status,
    )


def _compute_review_status(
    review_status: str,
    ingestion_state: Optional[str] = None,
    ai_status: Optional[str] = None,
    ingestion_error: Optional[str] = None,
    ai_error: Optional[str] = None,
) -> tuple:
    """Compute overall progress, current step, and status from pipeline states.

    Returns (progress: int, current_step: str, status: str, error: Optional[str],
             error_code: Optional[str], can_retry: bool).
    """
    # Ingestion pipeline stages (0-40%)
    ingestion_progress_map = {
        "uploaded": (5, "Uploading file"),
        "validating": (10, "Validating file"),
        "validated": (15, "File validated"),
        "storage_confirmed": (20, "Storing file"),
        "ocr_pending": (22, "OCR pending"),
        "ocr_processing": (25, "Running OCR extraction"),
        "ocr_complete": (30, "OCR complete"),
        "chunking_pending": (32, "Chunking pending"),
        "embedding_pending": (35, "Generating embeddings"),
        "analysis_pending": (38, "AI analysis pending"),
    }

    # AI analysis stages (40-70%)
    ai_progress_map = {
        "pending": (42, "AI analysis pending"),
        "processing": (50, "Running AI analysis"),
        "completed": (70, "AI analysis complete"),
    }

    # Check for failures first
    if ingestion_state == "failed":
        return (40, "Ingestion failed", "failed", ingestion_error or "Ingestion pipeline failed", "INGESTION_FAILURE", True)
    if ai_status == "failed":
        return (65, "AI analysis failed", "failed", ai_error or "AI analysis failed", "ANALYSIS_FAILURE", True)

    if ingestion_state and ingestion_state in ingestion_progress_map:
        progress, step = ingestion_progress_map[ingestion_state]
        return (progress, step, "processing", None, None, False)

    if ai_status and ai_status in ai_progress_map:
        progress, step = ai_progress_map[ai_status]
        return (progress, step, "analyzing" if ai_status == "processing" else "processing", None, None, False)

    # Review lifecycle stages (70-100%)
    review_progress_map = {
        "draft": (70, "Preparing review"),
        "ai_analyzed": (75, "AI analysis ready for review"),
        "in_review": (85, "Under review"),
        "pending_approval": (90, "Pending approval"),
        "approved": (100, "Review completed — approved"),
        "rejected": (100, "Review completed — rejected"),
        "escalated": (80, "Review escalated"),
        "closed": (100, "Review closed"),
    }

    if review_status in review_progress_map:
        progress, step = review_progress_map[review_status]
        overall = "completed" if progress == 100 else "in_review" if progress >= 85 else "review_ready"
        return (progress, step, overall, None, None, False)

    return (0, "Unknown", "unknown", None, None, False)


# ── Re-analysis ────────────────────────────────────────────────────


@router.post("/{review_id}/re-analyze", response_model=ReAnalysisResponse)
async def re_analyze_review(
    review_id: str,
    body: ReAnalysisRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.AI_ANALYZE)),
):
    """Re-run AI analysis on an existing review.

    Creates a new AI analysis run and links it to the review.
    Previous findings are preserved for comparison.
    """
    result = await service.re_analyze(review_id, body.analysis_type, body.reason)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReAnalysisResponse(
        review_id=review_id,
        run_id=result["run_id"],
        status="processing",
        message="Re-analysis pipeline started.",
        previous_run_id=result.get("previous_run_id"),
        version=result.get("version", 1),
    )


# ── Soft Delete & Archive ──────────────────────────────────────────


@router.delete("/{review_id}")
async def soft_delete_review(
    review_id: str,
    body: Optional[ReviewDeleteRequest] = None,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Soft-delete a review. Sets is_deleted flag without removing data."""
    result = await service.soft_delete(review_id, body.reason if body else None)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"review_id": review_id, "status": "deleted", "message": "Review soft-deleted."}


@router.post("/archive")
async def archive_reviews(
    body: ReviewArchiveRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Archive old reviews based on age and status criteria."""
    from app.domains.review.repository import ReviewRepository
    repo = ReviewRepository(db, tenant_id=tenant_id)
    result = await repo.archive_old_reviews(
        tenant_id=tenant_id,
        older_than_days=body.older_than_days,
        status_filter=body.status_filter,
        dry_run=body.dry_run,
    )
    return {
        "archived_count": result.get("archived_count", 0),
        "dry_run": body.dry_run,
        "message": f"{'Would archive' if body.dry_run else 'Archived'} {result.get('archived_count', 0)} reviews."
    }


# ── Status Transitions ─────────────────────────────────────────────


@router.post("/{review_id}/status")
async def update_review_status(
    review_id: str,
    status: str = Query(...),
    reason: Optional[str] = Query(None),
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_any_permission(Permissions.WORKFLOWS_WRITE, Permissions.CONTRACTS_APPROVE)),
):
    """Update review status with transition validation."""
    try:
        result = await service.update_status(review_id, status, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    return result


@router.get("/{review_id}/findings")
async def list_findings(
    review_id: str,
    severity: Optional[str] = Query(None),
    resolution: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List AI findings for a review with filtering."""
    from sqlalchemy import select
    from app.domains.vectors.models import Chunk

    items, total = await service.get_findings(review_id, severity, resolution, page, page_size)

    playbook_names: dict[str, str] = {}
    rule_names: dict[str, str] = {}
    version_labels: dict[str, str] = {}
    pb_ids = {str(f.playbook_id) for f in items if getattr(f, "playbook_id", None)}
    rule_ids = {str(f.rule_id) for f in items if getattr(f, "rule_id", None)}
    if pb_ids or rule_ids:
        from sqlalchemy import text as sa_text
        if pb_ids:
            r = await service.review_repo.session.execute(
                sa_text("""
                    SELECT lp.playbook_id, lp.name, pv.version_label
                    FROM legal_playbooks lp
                    LEFT JOIN playbook_versions pv ON pv.version_id = lp.active_version_id
                    WHERE lp.tenant_id = :tenant_id AND lp.playbook_id = ANY(CAST(:ids AS uuid[]))
                """),
                {"tenant_id": service.tenant_id, "ids": list(pb_ids)},
            )
            for row in r.fetchall():
                playbook_names[str(row.playbook_id)] = row.name
                if row.version_label:
                    version_labels[str(row.playbook_id)] = row.version_label
        if rule_ids:
            r = await service.review_repo.session.execute(
                sa_text("""
                    SELECT rule_id, name FROM policy_rules
                    WHERE tenant_id = :tenant_id AND rule_id = ANY(CAST(:ids AS uuid[]))
                """),
                {"tenant_id": service.tenant_id, "ids": list(rule_ids)},
            )
            for row in r.fetchall():
                rule_names[str(row.rule_id)] = row.name

    chunk_ids = [cid for f in items for cid in (f.chunk_ids or [])]
    chunks_by_id = {}
    if chunk_ids:
        result = await service.review_repo.session.execute(
            select(Chunk).where(
                Chunk.chunk_id.in_(chunk_ids),
                Chunk.tenant_id == service.tenant_id,
            )
        )
        chunks_by_id = {str(c.chunk_id): c for c in result.scalars().all()}

    data = [
        FindingItem(
            finding_id=str(f.finding_id), clause_type=f.clause_type,
            severity=f.severity, title=f.title, description=f.description,
            recommendation=f.recommendation, confidence=f.confidence,
            risk_score=f.risk_score,
            page_numbers=f.page_numbers,
            page_number=f.page_number,
            section_heading=f.section_heading,
            paragraph_index=f.paragraph_index,
            source_text=f.source_text,
            source_start_offset=f.source_start_offset,
            source_end_offset=f.source_end_offset,
            confidence_score=f.confidence_score,
            source_location=build_source_location(
                f,
                chunk=chunks_by_id.get(str((f.chunk_ids or [None])[0])),
            ),
            resolution=_enum_value(f.resolution),
            resolution_note=f.resolution_note,
            resolved_by=f.resolved_by,
            resolved_at=f.resolved_at.isoformat() if f.resolved_at else None,
            created_at=f.created_at,
            feedback_type=f.feedback_type,
            feedback_note=f.feedback_note,
            feedback_at=f.feedback_at.isoformat() if f.feedback_at else None,
            playbook_id=str(f.playbook_id) if getattr(f, "playbook_id", None) else None,
            rule_id=str(f.rule_id) if getattr(f, "rule_id", None) else None,
            evaluation_id=str(f.evaluation_id) if getattr(f, "evaluation_id", None) else None,
            clause_standard_id=str(f.clause_standard_id) if getattr(f, "clause_standard_id", None) else None,
            policy_owner=getattr(f, "policy_owner", None),
            policy_name=playbook_names.get(str(f.playbook_id)) if getattr(f, "playbook_id", None) else None,
            policy_rule_name=rule_names.get(str(f.rule_id)) if getattr(f, "rule_id", None) else None,
            policy_version=version_labels.get(str(f.playbook_id)) if getattr(f, "playbook_id", None) else None,
        )
        for f in items
    ]
    return {"findings": data, "total": total, "page": page, "page_size": page_size}


@router.get("/{review_id}/risk-breakdown")
async def get_risk_breakdown(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get decomposed risk score breakdown by clause category."""
    try:
        from app.domains.review.service import compute_risk_breakdown
        logger.info("Computing risk breakdown for review %s (tenant %s)", review_id, tenant_id)
        result = await compute_risk_breakdown(db, tenant_id, review_id)
        logger.info("Risk breakdown result status=%s", result.get("status", "none"))
        return result
    except Exception as exc:
        logger.warning("Risk breakdown failed for %s: %s", review_id, exc, exc_info=True)
        from app.domains.review.risk_scoring import risk_breakdown_shell
        return risk_breakdown_shell(0.0, status="error")


@router.get("/{review_id}/risk-delta-timeline")
async def get_risk_delta_timeline(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get the full ordered timeline of risk delta events for a review.

    Returns every decision that changed risk, ordered chronologically.
    Used by the Risk Delta Timeline widget on the frontend.
    """
    try:
        from app.domains.review.risk_delta_engine import RiskDeltaEngine

        engine = RiskDeltaEngine(db, tenant_id)
        deltas = await engine.get_risk_timeline(review_id)
        return {
            "review_id": review_id,
            "delta_count": len(deltas),
            "deltas": [d.to_dict() for d in deltas],
        }
    except Exception as exc:
        logger.warning("Risk delta timeline failed for %s: %s", review_id, exc, exc_info=True)
        return {"review_id": review_id, "delta_count": 0, "deltas": []}


@router.get("/{review_id}/risk-waterfall")
async def get_risk_waterfall(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Build a risk waterfall chart showing how decisions changed exposure.

    Returns:
    {
        "original_risk": 0.85,
        "current_risk": 0.45,
        "segments": [
            {"label": "Original AI Risk", "value": 0.85, "type": "start"},
            {"label": "Mitigated: Indemnification", "value": -0.20, "type": "mitigation"},
            ...
            {"label": "Remaining Exposure", "value": 0.45, "type": "end"},
        ]
    }
    """
    try:
        from app.domains.review.risk_delta_engine import RiskDeltaEngine
        from app.domains.review.models import ContractReview
        from sqlalchemy import select

        # Get original risk score from review metadata
        review_result = await db.execute(
            select(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == tenant_id,
            )
        )
        review = review_result.scalar_one_or_none()
        metadata = dict(review.document_metadata) if review and review.document_metadata else {}
        original_risk = metadata.get("risk_score", 0.0) or 0.0

        engine = RiskDeltaEngine(db, tenant_id)
        waterfall = await engine.get_risk_waterfall(review_id, original_risk=float(original_risk))
        return waterfall
    except Exception as exc:
        logger.warning("Risk waterfall failed for %s: %s", review_id, exc, exc_info=True)
        return {"original_risk": 0.0, "current_risk": 0.0, "segments": []}


@router.get("/{review_id}/version-impacts")
async def get_version_impacts(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get risk impacts grouped by document version.

    Returns a list of VersionImpact objects showing how risk changed
    between each version of the document.
    """
    try:
        from app.domains.review.risk_delta_engine import RiskDeltaEngine

        engine = RiskDeltaEngine(db, tenant_id)
        impacts = await engine.get_version_impacts(review_id)
        return {
            "review_id": review_id,
            "version_count": len(impacts),
            "impacts": [i.to_dict() for i in impacts],
        }
    except Exception as exc:
        logger.warning("Version impacts failed for %s: %s", review_id, exc, exc_info=True)
        return {"review_id": review_id, "version_count": 0, "impacts": []}


@router.post("/{review_id}/findings/{finding_id}/resolve")
async def resolve_finding(
    review_id: str, finding_id: str,
    body: FindingResolveRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Resolve an AI finding with a resolution type and optional note."""
    result = await service.resolve_finding(finding_id, body.resolution, body.note)
    if not result:
        raise HTTPException(status_code=404, detail="Finding not found")
    return result


@router.post("/{review_id}/findings/{finding_id}/feedback", response_model=FindingFeedbackResponse)
async def submit_finding_feedback(
    review_id: str, finding_id: str,
    body: FindingFeedbackRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Submit AI feedback (correct/incorrect/partial) for a finding."""
    result = await service.submit_finding_feedback(
        finding_id, body.type,
        reviewer_note=body.reviewer_note,
        retraining_priority=body.retraining_priority,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Finding not found")
    return result


@router.get("/{review_id}/redlines")
async def list_redlines(
    review_id: str,
    status: Optional[str] = Query(None),
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List redline suggestions for a review."""
    from sqlalchemy import select
    from app.domains.ai.models import AIRedline
    from app.domains.review.models import ReviewFinding
    from app.domains.vectors.models import Chunk

    redlines = await service.get_redlines(review_id, status)
    ai_ids = [r.ai_redline_id for r in redlines if r.ai_redline_id]
    chunk_map: dict[str, list[str]] = {}
    if ai_ids:
        result = await service.review_repo.session.execute(
            select(AIRedline.redline_id, AIRedline.chunk_ids).where(
                AIRedline.redline_id.in_(ai_ids),
                AIRedline.tenant_id == service.tenant_id,
            )
        )
        for rid, cids in result.all():
            chunk_map[str(rid)] = [str(c) for c in (cids or [])]

    linked_finding_ids = [r.finding_id for r in redlines if r.finding_id]
    findings_by_id = {}
    chunks_by_id = {}
    if linked_finding_ids:
        finding_result = await service.review_repo.session.execute(
            select(ReviewFinding).where(
                ReviewFinding.finding_id.in_(linked_finding_ids),
                ReviewFinding.tenant_id == service.tenant_id,
            )
        )
        findings_by_id = {str(f.finding_id): f for f in finding_result.scalars().all()}
        finding_chunk_ids = [cid for f in findings_by_id.values() for cid in (f.chunk_ids or [])]
        if finding_chunk_ids:
            chunk_result = await service.review_repo.session.execute(
                select(Chunk).where(
                    Chunk.chunk_id.in_(finding_chunk_ids),
                    Chunk.tenant_id == service.tenant_id,
                )
            )
            chunks_by_id = {str(c.chunk_id): c for c in chunk_result.scalars().all()}

    # Compute locator for each redline using structural section parser.
    # Wrapped in try/except — locator failure must never suppress the redlines themselves.
    try:
        locator_results = await _compute_redline_locators(redlines, service)
    except Exception as _loc_err:
        import logging as _log
        _log.getLogger(__name__).warning(
            "Locator failed for review %s (%s); redlines will be returned without placement data.",
            review_id, _loc_err,
        )
        locator_results = {}

    from app.domains.review.mapping_validation import validate_redline_finding_mapping
    from app.domains.review.models import RedlineStatus

    # Build response: strip synthetic numbering from INSERT_NEW proposed_text
    items = []
    for r in redlines:
        rid = str(r.redline_id)
        loc = locator_results.get(rid, {})
        linked_finding = findings_by_id.get(str(r.finding_id)) if r.finding_id else None
        source_location = None
        if linked_finding:
            source_location = build_source_location(
                linked_finding,
                chunk=chunks_by_id.get(str((linked_finding.chunk_ids or [None])[0])),
            )
        mapping = validate_redline_finding_mapping(
            r,
            linked_finding,
            locator_result=loc,
            displayed_finding_id=str(r.finding_id) if r.finding_id else None,
        )
        current_status = (
            r.status.value if hasattr(r.status, "value") else str(r.status)
        )
        if not mapping.valid:
            if current_status in (RedlineStatus.PROPOSED.value, RedlineStatus.INVALID_MAPPING.value):
                if current_status != RedlineStatus.INVALID_MAPPING.value:
                    await service.review_repo.update_redline(
                        rid,
                        service.tenant_id,
                        RedlineStatus.INVALID_MAPPING,
                        None,
                        service.user.id,
                        None,
                    )
                    await service.audit_trail.record_mapping_validation_failed(
                        redline_id=rid,
                        review_id=review_id,
                        actor_id=service.user.id,
                        mapping_warning=mapping.warning or "Invalid redline-to-finding mapping",
                        finding_id=mapping.finding_id,
                        finding_title=mapping.finding_title,
                        redline_title=mapping.redline_title,
                        finding_category=mapping.finding_category,
                        redline_category=mapping.redline_category,
                    )
        elif current_status == RedlineStatus.INVALID_MAPPING.value:
            await service.review_repo.update_redline(
                rid,
                service.tenant_id,
                RedlineStatus.PROPOSED,
                None,
                service.user.id,
                None,
            )
        item = redline_to_item(
            r,
            chunk_ids=chunk_map.get(str(r.ai_redline_id), []),
            locator_result=loc,
            source_location=source_location,
            finding_clause_type=linked_finding.clause_type if linked_finding else None,
            finding_title=linked_finding.title if linked_finding else None,
            finding_recommendation=linked_finding.recommendation if linked_finding else None,
            mapping=mapping,
        )
        # For INSERT_NEW: strip AI-generated section numbers from display text
        if loc.get("recommendation_type") == "insert" or loc.get("anchor_type") in (
            "structural_insertion", "semantic_clause_match"
        ):
            if item.proposed_text:
                item.proposed_text = _strip_synthetic_numbering(
                    item.proposed_text, clause_type=r.clause_type
                )
        items.append(item)

    return {"redlines": items}


def _strip_synthetic_numbering(text: str, clause_type: str | None = None) -> str:
    """Remove AI-generated section numbering from proposed clause text.

    Transforms:
      "10. Indemnification. Each party shall indemnify..."
    Into:
      "[Suggested New Clause: Indemnification]\nEach party shall indemnify..."

    Or if clause_type is available:
      "[Suggested New Clause: Indemnification]"

    The full text is preserved for export/reflow, but the display
    shows the clean version without synthetic numbering.
    """
    import re
    if not text:
        return text

    # Match leading section numbers like "10. Indemnification", "4.2 Title", "§10. Title"
    # Pattern: optional §, then digits.digits, then optional period, then title text
    # Title ends at the first sentence boundary (period followed by space or newline)
    m = re.match(r'^(?:§)?\s*(\d+(?:\.\d+)*)\.?\s+(.+?\.)(?:\s+(.+))?$', text.strip())
    if m:
        section_num = m.group(1)
        title = m.group(2).strip().rstrip(".")
        body = (m.group(3) or "").strip()
        label = clause_type.replace("_", " ").title() if clause_type else title
        if body:
            return f"[Suggested New Clause: {label}]\n\n{body}"
        return f"[Suggested New Clause: {label}]"

    # Fallback: number + title without trailing period (e.g., "10. Limitation of Liability")
    m = re.match(r'^(?:§)?\s*(\d+(?:\.\d+)*)\.?\s+(.+)$', text.strip())
    if m:
        title = m.group(2).strip()
        label = clause_type.replace("_", " ").title() if clause_type else title
        return f"[Suggested New Clause: {label}]"

    # Also match bare numbering like "10." without title
    m = re.match(r'^(?:§)?\s*\d+(?:\.\d+)*\s*[\.\)]\s*$', text.strip())
    if m:
        label = clause_type.replace("_", " ").title() if clause_type else "New Clause"
        return f"[Suggested New Clause: {label}]"

    return text


async def _compute_redline_locators(redlines, service) -> dict[str, dict]:
    """Compute structured locator results for all redlines.

    Parses the document section hierarchy once, then resolves each redline.
    """
    if not redlines:
        return {}

    from app.domains.review.locator import SectionParser, LocatorService
    from app.domains.vectors.repository import VectorRepository

    # Get the review to find upload_id
    review_id = str(redlines[0].review_id)
    review = await service.review_repo.get_review(review_id, service.tenant_id)
    if not review:
        return {}

    upload_id = str(review.upload_id)

    # Fetch chunks
    vector_repo = VectorRepository(service.review_repo.session, tenant_id=service.tenant_id)
    chunks = await vector_repo.get_chunks_by_upload(upload_id, service.tenant_id)
    if not chunks:
        return {}

    # Build full text from chunks
    full_text = "\n\n".join(c.text for c in chunks if c.text)

    # Parse section hierarchy
    parser = SectionParser()
    hierarchy = parser.parse(full_text, chunks=[
        {"chunk_id": str(c.chunk_id), "text": c.text,
         "page_numbers": list(c.page_numbers) if c.page_numbers else []}
        for c in chunks
    ])

    # Compute locator for each redline
    locator_service = LocatorService(hierarchy, full_text)
    results: dict[str, dict] = {}

    for r in redlines:
        rid = str(r.redline_id)
        proposed = (r.reviewer_modified_text or r.proposed_text or "").strip()
        original = (r.original_text or "").strip()
        operation = getattr(r, "operation", None)
        clause_type = getattr(r, "clause_type", None)
        anchor_text = getattr(r, "anchor_text", None) or ""

        locator_result = locator_service.locate(
            clause_type=clause_type,
            original_text=original,
            proposed_text=proposed,
            anchor_text=anchor_text,
            operation=operation,
        )
        results[rid] = locator_result.to_dict()

    return results


@router.put("/{review_id}/redlines/{redline_id}")
async def update_redline(
    review_id: str, redline_id: str,
    body: RedlineUpdateRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Accept, reject, or modify a redline suggestion."""
    try:
        result = await service.update_redline(
            redline_id, body.status, body.modified_text, body.review_notes
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=404, detail="Redline not found")
    return result


@router.post("/{review_id}/redlines/{redline_id}/escalate")
async def escalate_redline(
    review_id: str, redline_id: str,
    body: dict,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_ESCALATE)),
):
    """Escalate a redline to legal review.

    Marks the redline as needs_legal_review and records the escalation
    reason in the review notes.
    """
    reason = body.get("reason", "Escalated for legal review")
    result = await service.update_redline(
        redline_id,
        status="needs_legal_review",
        review_notes=f"Escalated: {reason}",
    )
    if not result:
        raise HTTPException(status_code=404, detail="Redline not found")

    # Record audit trail for the escalation
    await service.audit_trail.record_redline_action(
        redline_id=redline_id,
        review_id=review_id,
        actor_id=service.user.id,
        action="escalated",
        before_status="proposed",
        after_status="needs_legal_review",
        description=f"Redline escalated for legal review: {reason}",
    )

    return result


@router.post("/{review_id}/generate-mitigation-redline", response_model=GenerateMitigationRedlineResponse)
async def generate_mitigation_redline(
    review_id: str,
    body: GenerateMitigationRedlineRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Generate a redline from a mitigation recommendation.

    Creates a draft redline with pre-filled clause language, connects it to
    the specified findings, and attaches full mitigation traceability metadata.
    This is the core of closed-loop remediation:
        Mitigation recommendation → generated redline → review → accept → risk delta
    """
    result = await service.generate_mitigation_redline(
        review_id=review_id,
        mitigation_type=body.mitigation_type,
        clause_category=body.clause_category,
        finding_ids=body.finding_ids or [],
    )
    if not result:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to generate redline for mitigation '{body.mitigation_type}' in category '{body.clause_category}'. Verify the mitigation type is valid.",
        )
    return result


@router.post("/{review_id}/regenerate-redline")
async def regenerate_redline(
    review_id: str,
    body: RegenerateRedlineRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Regenerate a redline using the finding's category as a mandatory filter.

    When a redline has an invalid mapping (finding category != redline category),
    this endpoint:
    1. Marks the existing invalid redline as 'superseded'
    2. Generates a new redline using the finding's category as the clause_type
    3. Records audit events for both the superseded and new redline

    This ensures the regenerated redline always matches the finding category.
    """
    from app.domains.review.models import ReviewFinding, ReviewRedline as RRModel
    from sqlalchemy import select

    # 1. Fetch the finding to get its authoritative clause_type
    finding_result = await service.review_repo.session.execute(
        select(ReviewFinding).where(
            ReviewFinding.finding_id == body.finding_id,
            ReviewFinding.tenant_id == service.tenant_id,
        )
    )
    finding = finding_result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding {body.finding_id} not found")

    # 2. Fetch the existing invalid redline
    redline_result = await service.review_repo.session.execute(
        select(RRModel).where(
            RRModel.redline_id == body.redline_id,
            RRModel.tenant_id == service.tenant_id,
        )
    )
    existing_redline = redline_result.scalar_one_or_none()

    # 3. Supersede the existing redline if it exists
    if existing_redline:
        from app.domains.review.models import RedlineStatus
        await service.review_repo.update_redline(
            body.redline_id,
            service.tenant_id,
            RedlineStatus.SUPERSEDED,
            reviewed_by=service.user.id,
        )
        await service.audit_trail.record_redline_action(
            redline_id=body.redline_id,
            review_id=review_id,
            actor_id=service.user.id,
            action="superseded",
            before_status=str(existing_redline.status),
            after_status="superseded",
            description=f"Redline superseded by regeneration — finding category: {body.finding_category}",
        )

    # 4. Generate a new redline using the finding's clause_type
    # Use a generic mitigation approach to create a properly-categorized redline
    from app.domains.review.mitigation_effectiveness import get_mitigation_effectiveness

    effects = get_mitigation_effectiveness(body.finding_category, "general")
    if not effects:
        # Fallback: create a basic redline with the correct category
        proposed_text = f"[Regenerated clause for {body.finding_category.replace('_', ' ').title()} — please review and customize.]"
        rationale = f"Regenerated redline for finding: {finding.title}"
        traceability = {
            "detected_risk": finding.description or f"Risk in {body.finding_category}",
            "business_impact": finding.recommendation or "See finding for details",
            "mitigation_strategy": f"Regenerated from finding category: {body.finding_category}",
            "generated_from": "regeneration",
        }
    else:
        effect = effects[0]
        clause_templates = {
            "adding_indemnification": "The [Counterparty] shall indemnify, defend, and hold harmless [Company] from and against any and all losses...",
            "adding_liability_cap": "Notwithstanding anything to the contrary, [Counterparty]'s aggregate liability... shall not exceed [amount].",
            "adding_ip_ownership": "All intellectual property rights in and to the deliverables... shall be owned exclusively by [Company].",
            "adding_data_breach_protocol": "In the event of a data breach... [Counterparty] shall (a) notify [Company] within 24 hours...",
            "adding_compliance_language": "[Counterparty] shall comply with all applicable data protection laws...",
            "adding_security_requirements": "[Counterparty] shall maintain industry-standard security controls...",
            "adding_for_cause_termination": "Either party may terminate this agreement immediately upon written notice if...",
            "adding_dispute_resolution": "Any dispute arising out of or related to this agreement shall first be submitted to mediation...",
            "adding_audit_rights": "[Company] shall have the right... to audit [Counterparty]'s facilities...",
            "clarifying_governing_law": "This agreement shall be governed by and construed in accordance with the laws of...",
        }
        proposed_text = clause_templates.get(
            effect.get("mitigation_type", ""),
            f"[Regenerated clause for {body.finding_category.replace('_', ' ').title()} — please review and customize.]"
        )
        rationale = effect.get("description", f"Regenerated for finding: {finding.title}")
        traceability = {
            "detected_risk": f"Exposure in {body.finding_category} category",
            "business_impact": effect.get("description", ""),
            "mitigation_strategy": effect.get("label", ""),
            "generated_from": "regeneration",
        }

    redline_metadata = {
        "traceability": traceability,
        "legal_domain": body.finding_category,
        "risk_type": "regenerated",
        "generated_by": service.user.id,
        "regenerated_from": body.redline_id,
        "finding_category": body.finding_category,
    }

    new_redline = await service.review_repo.create_redline(
        review_id=review_id,
        tenant_id=service.tenant_id,
        upload_id=str(finding.upload_id),
        clause_type=body.finding_category,  # ← CRITICAL: uses finding's category, NOT caller's
        original_text="",
        proposed_text=proposed_text,
        operation="insert",
        rationale=rationale,
        risk_level=finding.severity or "medium",
        finding_id=body.finding_id,
        redline_metadata=redline_metadata,
    )

    # Record audit trail for the new redline
    await service.audit_trail.record_redline_action(
        redline_id=str(new_redline.redline_id),
        review_id=review_id,
        actor_id=service.user.id,
        action="regenerated",
        before_status="none",
        after_status="proposed",
        description=f"Redline regenerated for finding '{finding.title}' with category '{body.finding_category}'",
    )

    await service.review_repo.session.commit()

    return {
        "redline_id": str(new_redline.redline_id),
        "clause_type": new_redline.clause_type,
        "proposed_text": new_redline.proposed_text,
        "rationale": new_redline.rationale,
        "risk_level": new_redline.risk_level,
        "status": "proposed",
        "finding_id": body.finding_id,
        "finding_category": body.finding_category,
        "finding_title": finding.title,
        "message": f"Redline regenerated with category '{body.finding_category}' matching finding '{finding.title}'",
    }


@router.get("/{review_id}/comments")
async def list_comments(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List comments on a review."""
    comments = await service.get_comments(review_id)
    data = [
        CommentItem(
            comment_id=str(c.comment_id), entity_type=c.entity_type,
            entity_id=str(c.entity_id) if c.entity_id else None,
            parent_comment_id=str(c.parent_comment_id) if c.parent_comment_id else None,
            author_id=c.author_id, author_name=c.author_name if hasattr(c, 'author_name') else None,
            body=c.body, mentions=c.mentions,
            created_at=c.created_at, updated_at=c.updated_at,
        )
        for c in comments
    ]
    return {"comments": data}


@router.post("/{review_id}/comments")
async def add_comment(
    review_id: str,
    body: CommentCreate,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Add a comment to a review, finding, or redline."""
    return await service.add_comment(
        review_id, body.body, body.entity_type, body.entity_id,
        body.parent_comment_id, body.mentions,
    )


@router.get("/{review_id}/routing-recommendation")
async def get_routing_recommendation(
    review_id: str,
    preferred_role: Optional[str] = Query(None, description="Preferred reviewer role"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_READ)),
):
    """Get intelligent routing recommendation for a review.

    Scores eligible reviewers based on workload, historical speed,
    domain expertise, and escalation rate. Returns top candidate
    with explainability data.
    """
    from app.domains.review.routing_engine import RoutingEngine

    engine = RoutingEngine(db, tenant_id)
    return await engine.recommend_reviewer(
        review_id=review_id,
        preferred_role=preferred_role,
    )


@router.post("/{review_id}/assign")
async def assign_reviewer(
    review_id: str,
    body: AssignRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Assign a reviewer to the review."""
    try:
        return await service.assign_reviewer(
            review_id, body.assignee_id, body.role, body.due_date,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except ImmutableReviewError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{review_id}/escalate")
async def escalate_review(
    review_id: str,
    body: EscalateRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_ESCALATE)),
):
    """Escalate a review to a higher level."""
    return await service.escalate(
        review_id, body.reason, body.escalated_to,
        raise_priority=body.raise_priority or False,
        target_workflow_stage=body.target_workflow_stage,
    )


@router.post("/{review_id}/approve")
async def approve_review(
    review_id: str,
    body: ApproveRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_APPROVE)),
):
    """Approve, reject, or conditionally approve a review."""
    try:
        return await service.approve(review_id, body.decision, body.comments, body.conditions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{review_id}/finalize")
async def finalize_review(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_any_permission(Permissions.CONTRACTS_APPROVE, Permissions.WORKFLOWS_APPROVE)),
):
    """Finalize an approved review — locks the version and sets FINALIZED status.

    Only users with contracts:approve or workflows:approve can finalize.
    """
    return await service.finalize(review_id)


@router.get("/{review_id}/history")
async def get_status_history(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get the immutable status change history for a review."""
    history = await service.get_status_history(review_id)
    return {"history": [
        {"from_status": h.from_status, "to_status": h.to_status,
         "changed_by": h.changed_by, "reason": h.reason,
         "created_at": h.created_at.isoformat()}
        for h in history
    ]}


@router.get("/{review_id}/workflow-timeline")
async def get_workflow_timeline(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get a unified audit-grade timeline of all workflow events for a review.

    Combines:
      - Status history (transitions)
      - Reviewer assignments / reassignments
      - Escalations (level, reason, resolution)
      - Approvals / rejections (approver, conditions)

    Each event includes: id, type, timestamp, actor, role, previous_value,
    new_value, reason. The timeline is sorted newest-first and is suitable
    for the contract-detail Workflow tab.
    """
    events: list[dict] = []

    # 1) Status history
    for h in await service.get_status_history(review_id):
        events.append({
            "id": f"status-{h.history_id}",
            "type": "stage_changed",
            "timestamp": h.created_at.isoformat(),
            "actor": h.changed_by,
            "role": None,
            "previous_value": h.from_status,
            "new_value": h.to_status,
            "reason": h.reason,
        })

    # 2) Assignments — each row represents an assignment or reassignment
    try:
        assignments = await service.get_assignments(review_id)
        for a in assignments:
            events.append({
                "id": f"assign-{a.assignment_id}",
                "type": "assigned",
                "timestamp": a.created_at.isoformat() if a.created_at else None,
                "actor": a.assigned_by,
                "role": a.role,
                "previous_value": None,
                "new_value": a.assignee_id,
                "reason": a.notes,
            })
    except Exception:
        # If assignments aren't available, skip silently — the timeline
        # is best-effort.
        pass

    # 3) Escalations
    try:
        escalations = await service.get_escalations(review_id)
        for e in escalations:
            events.append({
                "id": f"esc-{e.escalation_id}",
                "type": "escalated",
                "timestamp": e.created_at.isoformat() if e.created_at else None,
                "actor": e.escalated_by,
                "role": None,
                "previous_value": None,
                "new_value": f"level {e.level} → {e.escalated_to or 'auto'}",
                "reason": e.reason,
            })
    except Exception:
        pass

    # 4) Approvals / rejections
    try:
        approvals = await service.get_approvals(review_id)
        for a in approvals:
            events.append({
                "id": f"approval-{a.approval_id}",
                "type": a.decision,  # 'approved' / 'rejected' / 'conditionally_approved'
                "timestamp": a.decided_at.isoformat() if a.decided_at else None,
                "actor": a.approver_id,
                "role": None,
                "previous_value": None,
                "new_value": a.decision,
                "reason": a.comments,
            })
    except Exception:
        pass

    # Sort newest-first
    events.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return {"events": events, "total": len(events)}


# ── Workload Metrics ──────────────────────────────────────────────


@router.get("/workload/metrics")
async def get_workload_metrics(
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get operational workload metrics for the review queue.

    Returns counts for: total, unassigned, in_review, overdue,
    escalated, critical, sla_at_risk, completed_today.
    """
    return await service.get_workload_metrics()


@router.get("/reviewers/workload", summary="Per-reviewer workload snapshot")
async def get_reviewers_workload(
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Return active workload for every reviewer in the current tenant.

    Response shape::

        {
          "reviewers": [
            {
              "user_id": "...",
              "name": "...",
              "email": "...",
              "role": "reviewer",
              "active_reviews": 4,
              "completed_today": 1,
              "overdue_reviews": 0,
              "avg_review_time_hours": 6.4,
              "workload_pct": 80,
              "sla_breaches": 0
            },
            ...
          ]
        }

    Used by the assign-reviewer modal to surface each user's current load
    and by the AI Workspace's reviewer-workload widget.
    """
    reviewers = await service.get_reviewer_workloads()
    return {"reviewers": reviewers}


# ── Routing Rules ─────────────────────────────────────────────────


@router.post("/routing/apply/{review_id}")
async def apply_routing_rules(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Evaluate and apply routing rules to a specific review."""
    result = await service.apply_routing_rules(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found or no matching rules")
    return {"matched": True, "action": result}


@router.post("/routing/apply-all")
async def apply_routing_rules_all(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Apply routing rules to all unassigned reviews in queue."""
    from app.domains.review.repository import ReviewRepository
    from app.domains.ai.repository import AIRepository
    from app.kernel.events.bus import EventBus

    service = ReviewService(
        review_repo=ReviewRepository(db, tenant_id=tenant_id),
        ai_repo=AIRepository(db, tenant_id=tenant_id),
        event_bus=EventBus(),
        user=user,
        tenant_id=tenant_id,
    )

    # Get all unassigned reviews that are review_ready or ai_analyzed
    from sqlalchemy import select
    from app.domains.review.models import ContractReview

    stmt = select(ContractReview).where(
        ContractReview.tenant_id == tenant_id,
        ContractReview.assigned_to.is_(None),
        ContractReview.status.in_(["review_ready", "ai_analyzed"]),
        ContractReview.is_deleted == False,
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    applied = 0
    for review in reviews:
        action = await service.evaluate_routing_rules(review)
        if action:
            await service.apply_routing_rules(str(review.review_id))
            applied += 1

    return {"total": len(reviews), "routed": applied}


# ── Bulk Operations ───────────────────────────────────────────────


@router.post("/bulk/assign")
async def bulk_assign(
    body: BulkAssignRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Assign multiple reviews to a reviewer in one operation."""
    return await service.bulk_assign(body.review_ids, body.assignee_id, body.role, body.due_date)


@router.post("/bulk/escalate")
async def bulk_escalate(
    body: BulkEscalateRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_ESCALATE)),
):
    """Escalate multiple reviews."""
    return await service.bulk_escalate(body.review_ids, body.reason, body.escalated_to)


@router.post("/bulk/approve")
async def bulk_approve(
    body: BulkApproveRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_APPROVE)),
):
    """Approve or reject multiple reviews."""
    return await service.bulk_approve(body.review_ids, body.decision, body.comments)


@router.post("/bulk/export")
async def bulk_export(
    body: BulkExportRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_any_permission(Permissions.AUDIT_EXPORT, Permissions.CONTRACTS_READ)),
):
    """Export selected reviews as CSV."""
    from fastapi.responses import StreamingResponse
    import csv, io

    reviews = []
    for rid in body.review_ids:
        review = await service.get_review(rid)
        if review:
            reviews.append(review)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["review_id", "status", "priority", "assigned_to", "risk_score",
                      "sla_status", "overdue_hours", "finding_count", "redline_count",
                      "created_at", "completed_at"])
    for r in reviews:
        writer.writerow([
            r.get("review_id"), r.get("status"), r.get("priority"),
            r.get("assigned_to"), r.get("risk_score"),
            r.get("sla_status"), r.get("overdue_hours"),
            r.get("finding_count"), r.get("redline_count"),
            r.get("created_at"), r.get("completed_at"),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reviews_export.csv"},
    )


# ── Bulk Redline Actions ─────────────────────────────────────────


@router.post("/{review_id}/redlines/bulk-accept")
async def bulk_accept_redlines(
    review_id: str,
    max_risk_level: str = Query("low", description="Maximum risk level to auto-accept (low, medium, high, critical)"),
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Accept all redlines up to a specified risk level.

    Useful for quickly accepting low-risk or informational redlines en masse.
    """
    return await service.bulk_accept_redlines(review_id, max_risk_level)


@router.post("/{review_id}/redlines/bulk-reject")
async def bulk_reject_redlines(
    review_id: str,
    severity: str = Query("informational", description="Reject redlines at this level (informational, low, medium)"),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
    service: ReviewService = Depends(get_review_service),
):
    """Reject all redlines matching a severity/risk level.

    Useful for quickly dismissing informational or low-risk redlines.
    """
    return await service.bulk_reject_redlines(review_id, severity)


@router.post("/{review_id}/redlines/bulk-accept-by-ids")
async def bulk_accept_redlines_by_ids(
    review_id: str,
    body: BulkRedlineIdsRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Accept specific redlines by their IDs."""
    results = []
    for rid in body.redline_ids:
        try:
            result = await service.update_redline(rid, "accepted")
            if result:
                results.append(rid)
        except Exception:
            continue
    return {"accepted": results, "count": len(results)}


@router.post("/{review_id}/redlines/bulk-reject-by-ids")
async def bulk_reject_redlines_by_ids(
    review_id: str,
    body: BulkRedlineIdsRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Reject specific redlines by their IDs."""
    results = []
    for rid in body.redline_ids:
        try:
            result = await service.update_redline(rid, "rejected")
            if result:
                results.append(rid)
        except Exception:
            continue
    return {"rejected": results, "count": len(results)}


@router.post("/{review_id}/redlines/{redline_id}/assign")
async def assign_redline(
    review_id: str,
    redline_id: str,
    body: RedlineAssignRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Assign a redline to a specific reviewer or team."""
    from app.domains.review.models import RedlineStatus
    result = await service.update_redline(redline_id, status=RedlineStatus.NEEDS_LEGAL_REVIEW, review_notes=f"Assigned to {body.assignee_id} ({body.role or 'reviewer'})")
    if not result:
        raise HTTPException(status_code=404, detail="Redline not found")
    return {**result, "assigned_to": body.assignee_id, "role": body.role or "reviewer"}


@router.post("/{review_id}/redlines/{redline_id}/escalate")
async def escalate_redline(
    review_id: str,
    redline_id: str,
    body: EscalateRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_ESCALATE)),
):
    """Escalate a redline for higher-level review."""
    result = await service.update_redline(redline_id, status=None, review_notes=f"Escalated: {body.reason}")
    if not result:
        raise HTTPException(status_code=404, detail="Redline not found")
    return {**result, "escalated": True, "reason": body.reason}


@router.post("/{review_id}/redlines/{redline_id}/counter-proposal")
async def counter_proposal_redline(
    review_id: str,
    redline_id: str,
    body: RedlineUpdateRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Submit a counter-proposal for a redline (modify with negotiation context)."""
    result = await service.update_redline(redline_id, "modified", body.modified_text, body.review_notes)
    if not result:
        raise HTTPException(status_code=404, detail="Redline not found")
    return {**result, "counter_proposal": True}


# ── Document Versions ─────────────────────────────────────────────


@router.get("/{review_id}/versions", response_model=list[DocumentVersionItem])
async def list_versions(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all document versions for a review."""
    return await service.get_versions(review_id)


@router.post("/{review_id}/versions", response_model=DocumentVersionItem)
async def create_version(
    review_id: str,
    body: CreateDocumentVersionRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_any_permission(Permissions.CONTRACTS_WRITE, Permissions.WORKFLOWS_WRITE)),
):
    """Create a new document version for a review."""
    return await service.create_version(
        review_id,
        label=body.label,
        change_summary=body.change_summary,
        accepted_redline_ids=body.accepted_redline_ids,
    )


@router.get("/{review_id}/versions/{version_id}/download")
async def download_version(
    review_id: str,
    version_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Download a generated document version (.docx)."""
    try:
        data, filename, mime = await service.download_version(review_id, version_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Version file not available")
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{review_id}/versions/{version_id}/export-tracked")
async def export_tracked_changes(
    review_id: str,
    version_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Export a tracked-changes DOCX showing redlines as visual markup.

    Uses red strikethrough for deleted text and green underline for inserted text,
    mimicking Microsoft Word's Track Changes.
    """
    try:
        data, filename, mime = await service.export_tracked_changes(review_id, version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="tracked_{filename}"'},
    )


@router.get("/{review_id}/versions/{version_id_a}/diff/{version_id_b}")
async def diff_versions(
    review_id: str,
    version_id_a: str,
    version_id_b: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get structured clause-level diff between two document versions."""
    try:
        return await service.diff_versions(review_id, version_id_a, version_id_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{review_id}/export-audit")
async def export_review_audit(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_any_permission(Permissions.AUDIT_EXPORT, Permissions.CONTRACTS_READ)),
):
    """Export a complete review audit package as ZIP.

    Contains:
    - Original contract (v1)
    - Final approved contract (latest version)
    - Review history (JSON)
    - Findings (JSON)
    - Redlines (JSON)
    - Comments (JSON)
    - Timeline (JSON)
    - Audit manifest (JSON)
    """
    import io, json, zipfile, logging
    from datetime import datetime

    logger = logging.getLogger(__name__)

    repo = ReviewRepository(db, tenant_id=tenant_id)

    # Gather data
    try:
        review = await repo.get_review(review_id, tenant_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("export-audit: failed to get review %s: %s", review_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to load review: {e}")

    try:
        history = await repo.get_status_history(review_id, tenant_id)
    except Exception:
        history = []

    try:
        findings, _ = await repo.get_findings(review_id, tenant_id, page=1, page_size=500)
    except Exception:
        findings = []

    try:
        redlines = await repo.get_redlines(review_id, tenant_id)
    except Exception:
        redlines = []

    try:
        comments = await repo.get_comments(review_id, tenant_id)
    except Exception:
        comments = []

    from app.domains.review.models import ContractDocumentVersion
    from sqlalchemy import select
    try:
        versions_result = await db.execute(
            select(ContractDocumentVersion).where(
                ContractDocumentVersion.review_id == review_id,
                ContractDocumentVersion.tenant_id == tenant_id,
            ).order_by(ContractDocumentVersion.version_number)
        )
        versions = versions_result.scalars().all()
    except Exception:
        versions = []

    # Build ZIP
    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # JSON exports
            zf.writestr("review.json", json.dumps({
                "review_id": str(review.review_id),
                "status": _enum_value(review.status) if hasattr(review, 'status') else str(review.status),
                "priority": review.priority,
                "risk_score": _extract_risk(review),
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "completed_at": review.completed_at.isoformat() if review.completed_at else None,
                "assigned_to": review.assigned_to,
                "workflow_stage": review.workflow_stage,
            }, indent=2, default=str))

            zf.writestr("findings.json", json.dumps([
                {
                    "finding_id": str(f.finding_id),
                    "clause_type": f.clause_type,
                    "severity": f.severity,
                    "title": f.title,
                    "resolution": _enum_value(f.resolution) if hasattr(f, 'resolution') else str(f.resolution),
                }
                for f in findings
            ], indent=2, default=str))

            zf.writestr("redlines.json", json.dumps([
                {
                    "redline_id": str(r.redline_id),
                    "clause_type": r.clause_type,
                    "status": _enum_value(r.status) if hasattr(r, 'status') else str(r.status),
                }
                for r in redlines
            ], indent=2, default=str))

            zf.writestr("comments.json", json.dumps([
                {
                    "comment_id": str(c.comment_id),
                    "author_id": c.author_id,
                    "body": c.body[:500] if c.body else "",
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in comments
            ], indent=2, default=str))

            zf.writestr("timeline.json", json.dumps([
                {
                    "from_status": h.from_status,
                    "to_status": h.to_status,
                    "changed_by": h.changed_by,
                    "reason": h.reason,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in history
            ], indent=2, default=str))

            zf.writestr("versions.json", json.dumps([
                {
                    "version_number": v.version_number,
                    "label": v.label,
                    "status": v.status,
                    "change_summary": v.change_summary,
                    "storage_key": v.storage_key,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in versions
            ], indent=2, default=str))

            zf.writestr("manifest.json", json.dumps({
                "exported_at": datetime.utcnow().isoformat(),
                "review_id": review_id,
                "tenant_id": tenant_id,
                "total_findings": len(findings),
                "total_redlines": len(redlines),
                "total_comments": len(comments),
                "total_versions": len(versions),
                "total_timeline_events": len(history),
            }, indent=2))

            # Include version documents if storage keys exist (gracefully handle storage failures)
            try:
                from app.integrations.storage.s3 import storage_service
                from app.config import settings
                for v in versions:
                    if v.storage_key:
                        try:
                            doc_data = await storage_service.download_fileobj(
                                settings.s3_bucket, v.storage_key,
                            )
                            fname = v.storage_key.rsplit("/", 1)[-1] or f"v{v.version_number}.docx"
                            zf.writestr(f"documents/{fname}", doc_data)
                        except Exception:
                            zf.writestr(f"documents/v{v.version_number}_unavailable.txt",
                                        f"Document v{v.version_number} could not be retrieved from storage.")
            except ImportError as e:
                logger.warning("export-audit: storage service not available: %s", e)
            except Exception as e:
                logger.warning("export-audit: storage error: %s", e)
    except Exception as e:
        logger.error("export-audit: failed to build ZIP for %s: %s", review_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to build export package: {e}")

    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="review_{review_id[:8]}_audit_{datetime.utcnow().strftime("%Y%m%d")}.zip"',
        },
    )


@router.get("/{review_id}/export-negotiation-package")
async def export_negotiation_package(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_any_permission(Permissions.AUDIT_EXPORT, Permissions.CONTRACTS_READ)),
):
    """Export a complete negotiation package as ZIP.

    Contains:
    - Contract_Final.docx — latest approved/current version
    - Contract_Tracked.docx — tracked-changes version
    - Negotiation_Summary.json — all redlines with decisions
    - Accepted_Redlines.csv — machine-readable change log
    - Audit_Timeline.json — full status history
    - Risk_Report.json — findings by severity
    """
    import io, json, csv, zipfile
    from datetime import datetime

    repo = ReviewRepository(db, tenant_id=tenant_id)
    review = await repo.get_review(review_id, tenant_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    from app.domains.review.models import ContractDocumentVersion, ReviewRedline, ReviewFinding, ReviewStatusHistory
    from sqlalchemy import select

    # Gather data
    versions_result = await db.execute(
        select(ContractDocumentVersion).where(
            ContractDocumentVersion.review_id == review_id,
            ContractDocumentVersion.tenant_id == tenant_id,
        ).order_by(ContractDocumentVersion.version_number)
    )
    versions = versions_result.scalars().all()

    redlines_result = await db.execute(
        select(ReviewRedline).where(
            ReviewRedline.review_id == review_id,
            ReviewRedline.tenant_id == tenant_id,
        )
    )
    redlines = redlines_result.scalars().all()

    findings, _ = await repo.get_findings(review_id, tenant_id, page=1, page_size=500)
    history = await repo.get_status_history(review_id, tenant_id)

    from app.integrations.storage.s3 import storage_service
    from app.config import settings
    bucket = settings.s3_bucket

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Latest version document
        latest = versions[-1] if versions else None
        if latest and latest.storage_key:
            try:
                doc_data = await storage_service.download_fileobj(bucket, latest.storage_key)
                zf.writestr("Contract_Final.docx", doc_data)
            except Exception:
                zf.writestr("Contract_Final_UNAVAILABLE.txt", "Could not retrieve final document.")

        # Tracked changes version
        try:
            from app.domains.review.service import ReviewService
            from app.domains.review.repository import ReviewRepository as RR
            svc = ReviewService(
                review_repo=RR(db, tenant_id=tenant_id),
                ai_repo=None, event_bus=None, user=None, tenant_id=tenant_id,
            )
            if latest:
                tracked_data, _, _ = await svc.export_tracked_changes(review_id, str(latest.version_id))
                zf.writestr("Contract_Tracked.docx", tracked_data)
        except Exception:
            zf.writestr("Contract_Tracked_UNAVAILABLE.txt", "Could not generate tracked-changes document.")

        # Negotiation summary (JSON)
        zf.writestr("Negotiation_Summary.json", json.dumps([
            {
                "redline_id": str(r.redline_id),
                "clause_type": r.clause_type,
                "status": _enum_value(r.status),
                "original_text": r.original_text[:500],
                "proposed_text": r.proposed_text[:500],
                "final_text": (r.reviewer_modified_text or r.proposed_text)[:500],
                "rationale": r.rationale,
                "risk_level": r.risk_level,
                "reviewed_by": r.reviewed_by,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            }
            for r in redlines
        ], indent=2, default=str))

        # Accepted redlines CSV
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["redline_id", "clause_type", "status", "risk_level", "reviewed_by", "reviewed_at"])
        for r in redlines:
            writer.writerow([str(r.redline_id), r.clause_type, _enum_value(r.status), r.risk_level, r.reviewed_by, r.reviewed_at])
        zf.writestr("Accepted_Redlines.csv", csv_buf.getvalue())

        # Audit timeline
        zf.writestr("Audit_Timeline.json", json.dumps([
            {
                "from_status": h.from_status,
                "to_status": h.to_status,
                "changed_by": h.changed_by,
                "reason": h.reason,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ], indent=2, default=str))

        # Risk report
        from collections import Counter
        severity_counts = Counter(f.severity for f in findings)
        zf.writestr("Risk_Report.json", json.dumps({
            "total_findings": len(findings),
            "by_severity": dict(severity_counts),
            "critical_findings": [
                {"title": f.title, "clause_type": f.clause_type, "description": f.description[:200]}
                for f in findings if f.severity == "critical"
            ],
            "high_findings": [
                {"title": f.title, "clause_type": f.clause_type}
                for f in findings if f.severity == "high"
            ],
        }, indent=2, default=str))

    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="negotiation_{review_id[:8]}_{datetime.utcnow().strftime("%Y%m%d")}.zip"',
        },
    )


@router.get("/{review_id}/export-executive-summary")
async def export_executive_summary(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_any_permission(Permissions.AUDIT_EXPORT, Permissions.CONTRACTS_READ)),
):
    """Export an executive summary package as ZIP.

    Contains:
    - Executive_Summary.json — high-level overview for leadership
    - Risk_Overview.json — risk scores and severity breakdown
    - Key_Findings.json — top critical and high findings
    - Timeline.json — review progress timeline
    """
    import io, json, zipfile
    from datetime import datetime

    repo = ReviewRepository(db, tenant_id=tenant_id)
    review = await repo.get_review(review_id, tenant_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    findings, _ = await repo.get_findings(review_id, tenant_id, page=1, page_size=500)
    history = await repo.get_status_history(review_id, tenant_id)

    from collections import Counter
    severity_counts = Counter(f.severity for f in findings)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Executive summary
        zf.writestr("Executive_Summary.json", json.dumps({
            "review_id": str(review.review_id),
            "contract_name": getattr(review, "contract_name", ""),
            "vendor": getattr(review, "vendor", ""),
            "status": _enum_value(review.status),
            "priority": review.priority,
            "risk_score": _extract_risk(review),
            "workflow_stage": review.workflow_stage,
            "total_findings": len(findings),
            "critical_findings": severity_counts.get("critical", 0),
            "high_findings": severity_counts.get("high", 0),
            "medium_findings": severity_counts.get("medium", 0),
            "low_findings": severity_counts.get("low", 0),
            "created_at": review.created_at.isoformat() if review.created_at else None,
            "completed_at": review.completed_at.isoformat() if review.completed_at else None,
            "exported_at": datetime.utcnow().isoformat(),
        }, indent=2, default=str))

        # Risk overview
        zf.writestr("Risk_Overview.json", json.dumps({
            "risk_score": _extract_risk(review),
            "risk_level": getattr(review, "risk_level", "unknown"),
            "severity_breakdown": dict(severity_counts),
            "total_findings": len(findings),
        }, indent=2, default=str))

        # Key findings (critical + high only)
        zf.writestr("Key_Findings.json", json.dumps([
            {
                "finding_id": str(f.finding_id),
                "title": f.title,
                "severity": f.severity,
                "clause_type": f.clause_type,
                "description": (f.description or "")[:300],
                "resolution": _enum_value(f.resolution),
                "status": f.status,
            }
            for f in findings if f.severity in ("critical", "high")
        ], indent=2, default=str))

        # Timeline
        zf.writestr("Timeline.json", json.dumps([
            {
                "from_status": h.from_status,
                "to_status": h.to_status,
                "changed_by": h.changed_by,
                "reason": h.reason,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ], indent=2, default=str))

    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="executive_summary_{review_id[:8]}_{datetime.utcnow().strftime("%Y%m%d")}.zip"',
        },
    )


def _extract_risk(review) -> float | None:
    metadata = getattr(review, "document_metadata", None) or {}
    return metadata.get("risk_score") if isinstance(metadata, dict) else None


# ── Policy Violations ─────────────────────────────────────────────

@router.get("/{review_id}/policy-violations")
async def list_policy_violations(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List policy violations for a review."""
    try:
        return await service.get_policy_violations(review_id)
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "list_policy_violations failed for review %s: %s", review_id, exc, exc_info=True
        )
        return {"violations": []}


class WaiveViolationRequest(BaseModel):
    rule_id: str
    justification: str
    risk_assessment: Optional[str] = None
    proposed_alternative: Optional[str] = None


@router.post("/{review_id}/policy-violations/waive")
async def waive_policy_violation(
    review_id: str,
    body: WaiveViolationRequest,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Waive a policy violation by recording a policy_override."""
    return await service.waive_policy_violation(
        review_id=review_id,
        rule_id=body.rule_id,
        justification=body.justification,
        risk_assessment=body.risk_assessment,
        proposed_alternative=body.proposed_alternative,
    )


# ── Missing Clauses ───────────────────────────────────────────────

@router.get("/{review_id}/missing-clauses")
async def list_missing_clauses(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List missing mandatory clauses for a review."""
    try:
        return await service.get_missing_clauses(review_id)
    except Exception:
        return {"missing_clauses": []}


# ── Recommendations ───────────────────────────────────────────────

@router.get("/{review_id}/recommendations")
async def list_recommendations(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List AI recommendations for a review."""
    try:
        return await service.get_recommendations(review_id)
    except Exception:
        return {"recommendations": []}


@router.post("/{review_id}/recommendations/{recommendation_id}/apply")
async def apply_recommendation(
    review_id: str,
    recommendation_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Apply a recommendation — generates a mitigation redline from the recommendation.

    The recommendation_id is derived from the finding_id (format: rec-{finding_id_prefix}).
    This endpoint resolves the finding, then delegates to generate_mitigation_redline.
    """
    # Resolve finding_id from recommendation_id (format: rec-{first8ofFindingId})
    from app.domains.review.models import ReviewFinding
    from sqlalchemy import select

    finding_prefix = recommendation_id.replace("rec-", "", 1)

    # Find the finding by matching the prefix
    stmt = (
        select(ReviewFinding)
        .where(
            ReviewFinding.review_id == review_id,
            ReviewFinding.tenant_id == service.tenant_id,
            ReviewFinding.recommendation.isnot(None),
            ReviewFinding.recommendation != "",
        )
        .order_by(ReviewFinding.created_at.desc())
    )
    result = await service.review_repo.session.execute(stmt)
    findings = result.scalars().all()

    target_finding = None
    for f in findings:
        if str(f.finding_id).startswith(finding_prefix):
            target_finding = f
            break

    if not target_finding:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")

    # Generate a mitigation redline from this finding's recommendation
    from app.domains.review.mitigation_effectiveness import MITIGATION_EFFECTIVENESS_REGISTRY

    raw_category = target_finding.clause_type or "other"

    # Map the finding's clause_type to a valid category key in the registry.
    # The registry uses compound keys like "liability_indemnity", "intellectual_property".
    # We try an exact match first, then a prefix match, then fall back to "other".
    category_map = {
        "liability": "liability_indemnity",
        "indemnification": "liability_indemnity",
        "confidentiality": "confidentiality",
        "data_privacy": "data_privacy",
        "data_protection": "data_privacy",
        "intellectual_property": "intellectual_property",
        "sla": "service_levels",
        "termination": "termination",
        "governing_law": "governing_law",
        "insurance": "insurance",
        "non_compete": "non_compete",
        "payment": "payment_terms",
        "limitation_of_liability": "liability_indemnity",
        "indemnification": "liability_indemnity",
    }
    clause_category = category_map.get(raw_category, raw_category)

    # Pick the first available mitigation type for this category as the default
    category_effects = MITIGATION_EFFECTIVENESS_REGISTRY.get(clause_category, {})
    if category_effects:
        # Use the first mitigation type as the default for generic apply actions
        first_type = next(iter(category_effects.keys()))
        mitigation_type = first_type
    else:
        # Fallback: construct a generic type
        mitigation_type = f"applying_recommendation_{raw_category}"

    redline_result = await service.generate_mitigation_redline(
        review_id=review_id,
        mitigation_type=mitigation_type,
        clause_category=clause_category,
        finding_ids=[str(target_finding.finding_id)],
    )

    if not redline_result:
        raise HTTPException(
            status_code=400,
            detail="Failed to generate redline from recommendation. The recommendation may not have a valid mitigation template.",
        )

    # Auto-resolve the finding since the recommendation was applied
    try:
        from app.domains.review.models import FindingResolution
        await service.resolve_finding(
            finding_id=str(target_finding.finding_id),
            resolution="resolved",
            note=f"Recommendation applied: mitigation redline generated",
        )
    except Exception:
        pass  # Non-blocking — redline was created even if auto-resolve fails

    # Record audit trail for the apply action
    await service.audit_trail.record(
        event_type="recommendation.applied",
        entity_type="finding",
        entity_id=str(target_finding.finding_id),
        actor_id=service.user.id,
        action="apply",
        before_state={"status": "pending"},
        after_state={"status": "applied", "redline_id": redline_result.get("redline_id")},
        description=f"Recommendation applied: generated mitigation redline for {target_finding.title}",
        metadata={
            "review_id": review_id,
            "recommendation_id": recommendation_id,
            "finding_id": str(target_finding.finding_id),
            "redline_id": redline_result.get("redline_id"),
            "mitigation_type": mitigation_type,
        },
    )

    return {
        "status": "applied",
        "finding_id": str(target_finding.finding_id),
        "redline_id": redline_result.get("redline_id"),
        "message": f"Recommendation applied — mitigation redline generated for '{target_finding.title}'",
    }


@router.post("/{review_id}/recommendations/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    review_id: str,
    recommendation_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Dismiss a recommendation — marks the associated finding as dismissed."""
    from app.domains.review.models import ReviewFinding
    from sqlalchemy import select

    finding_prefix = recommendation_id.replace("rec-", "", 1)

    stmt = (
        select(ReviewFinding)
        .where(
            ReviewFinding.review_id == review_id,
            ReviewFinding.tenant_id == service.tenant_id,
        )
        .order_by(ReviewFinding.created_at.desc())
    )
    result = await service.review_repo.session.execute(stmt)
    findings = result.scalars().all()

    target_finding = None
    for f in findings:
        if str(f.finding_id).startswith(finding_prefix):
            target_finding = f
            break

    if not target_finding:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")

    # Dismiss the finding
    from app.domains.review.models import FindingResolution
    await service.resolve_finding(
        finding_id=str(target_finding.finding_id),
        resolution="dismissed",
        note="Recommendation dismissed by reviewer",
    )

    # Record audit trail
    await service.audit_trail.record(
        event_type="recommendation.dismissed",
        entity_type="finding",
        entity_id=str(target_finding.finding_id),
        actor_id=service.user.id,
        action="dismiss",
        before_state={"status": "pending"},
        after_state={"status": "dismissed"},
        description=f"Recommendation dismissed: {target_finding.title}",
        metadata={
            "review_id": review_id,
            "recommendation_id": recommendation_id,
            "finding_id": str(target_finding.finding_id),
        },
    )

    return {
        "status": "dismissed",
        "finding_id": str(target_finding.finding_id),
        "message": f"Recommendation dismissed: '{target_finding.title}'",
    }


# ── Workflow ──────────────────────────────────────────────────────

@router.get("/{review_id}/workflow")
async def get_workflow(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get workflow state for a review."""
    return await service.get_workflow(review_id)


@router.post("/{review_id}/workflow/advance")
async def advance_workflow(
    review_id: str,
    body: dict,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Advance workflow by performing an action from available_actions.

    Maps WorkflowState action names to ReviewStatus values and transitions
    the review through the standard update_status flow.

    Optionally assigns to a specific user and records a handoff note.

    Request body:
        { "action": "legal_review" }
        { "action": "exec_approval", "assignee_id": "user@example.com", "note": "Please review" }
    """
    action = body.get("action", "")
    if not action:
        raise HTTPException(status_code=400, detail="Action is required")

    assignee_id = body.get("assignee_id")
    note = body.get("note")

    # Map WorkflowState action names to ReviewStatus values
    action_to_status = {
        "legal_review": "legal_approval",
        "procurement_review": "procurement_review",
        "security_review": "security_review",
        "approved": "approved",
        "rejected": "rejected",
        "archived": "archived",
        "in_review": "in_review",
        "escalated": "escalated",
        "finalized": "finalized",
        "exec_approval": "exec_approval",
        "executed": "executed",
    }

    target_status = action_to_status.get(action)
    if not target_status:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown workflow action: '{action}'. "
                   f"Valid actions: {list(action_to_status.keys())}",
        )

    # If review is unassigned (ai_analyzed), auto-assign to current user first
    # so the status transition can proceed through the ReviewStatus matrix.
    from app.domains.review.models import ContractReview
    from sqlalchemy import select
    review_row = await service.review_repo.session.execute(
        select(ContractReview).where(
            ContractReview.review_id == review_id,
            ContractReview.tenant_id == service.tenant_id,
        )
    )
    review = review_row.scalar_one_or_none()
    if review:
        raw = review.status
        current_status_str = raw.value if hasattr(raw, 'value') else str(raw)
        if current_status_str == "ai_analyzed":
            # Auto-assign to the acting user so the review can be advanced
            effective_assignee = assignee_id or service.user.id
            try:
                await service.assign_reviewer(
                    review_id=review_id,
                    assignee_id=effective_assignee,
                    role="reviewer",
                    due_date=None,
                )
            except Exception:
                pass  # If assign fails, still try the transition

        # Skip transition if already in the target status.
        # Re-read current status after potential auto-assign above.
        review_row = await service.review_repo.session.execute(
            select(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == service.tenant_id,
            )
        )
        review = review_row.scalar_one_or_none()
        if review:
            raw = review.status
            current_status_str = raw.value if hasattr(raw, 'value') else str(raw)
        if current_status_str == target_status:
            # Still return the current state
            result = await service.get_review(review_id)
            if not result:
                raise HTTPException(status_code=404, detail="Review not found")
            return result

    # Perform status transition
    try:
        result = await service.update_status(review_id, target_status, reason=note or f"Workflow action: {action}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")

    # If assignee provided, assign the review
    if assignee_id:
        try:
            await service.assign_reviewer(
                review_id=review_id,
                assignee_id=assignee_id,
                role="reviewer",
                due_date=None,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Send notification if note provided
    if note and service.notify_service:
        try:
            await service.notify_service.send_notification(
                user_id=assignee_id or review_id,
                notif_type="workflow.transition",
                title=f"Review moved to {target_status.replace('_', ' ')}",
                body=note,
                severity="medium",
                entity_type="review",
                entity_id=review_id,
                action_url=f"/reviews/{review_id}",
                dedup_key=f"advance:{review_id}:{action}",
            )
        except Exception:
            pass

    return result


# ── Activity ──────────────────────────────────────────────────────

@router.get("/{review_id}/activity")
async def list_activity(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List activity events for a review."""
    try:
        return await service.get_activity(review_id)
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "list_activity failed for review %s: %s", review_id, exc, exc_info=True
        )
        return {"events": []}


# ── Document ──────────────────────────────────────────────────────

@router.get("/{review_id}/document")
async def get_document(
    review_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get document content/sections for a review."""
    try:
        return await service.get_document(review_id)
    except Exception:
        return {"sections": [], "total_pages": 0}


# ═══════════════════════════════════════════════════════════════════
# Reviewer Ops — Sprint 12
# ═══════════════════════════════════════════════════════════════════

@router.get("/my-work", summary="My Work — reviews assigned to current user")
async def get_my_work(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get all active reviews assigned to the current user.

    Returns reviews filtered by assigned_to = current_user AND is_deleted = FALSE.
    This is the real data source for the Reviewer Ops 'My Work' widget.
    """
    repo = ReviewRepository(db, tenant_id=tenant_id)
    reviews = await repo.get_my_work(tenant_id, user.id)
    from app.domains.review.service import ReviewService

    items = []
    for r in reviews:
        metadata = getattr(r, "document_metadata", None) or {}
        risk_score = metadata.get("risk_score") if isinstance(metadata, dict) else None
        contract_number = metadata.get("contract_number") if isinstance(metadata, dict) else None
        sla_deadline = r.sla_deadline.isoformat() if r.sla_deadline else None
        items.append({
            "review_id": str(r.review_id),
            "contract_name": getattr(r, "_document_filename", None),
            "contract_number": contract_number,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "risk_score": risk_score,
            "sla_deadline": sla_deadline,
            "assigned_to": r.assigned_to,
            "created_at": r.created_at.isoformat(),
        })
    return items


@router.get("/queue", summary="Queue — operational review workbench")
async def get_queue(
    status: Optional[str] = Query(None, description="Filter by review status"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    risk_min: Optional[float] = Query(None, ge=0, le=10, description="Minimum risk score"),
    risk_max: Optional[float] = Query(None, ge=0, le=10, description="Maximum risk score"),
    age_min_hours: Optional[float] = Query(None, ge=0, description="Minimum age in hours"),
    age_max_hours: Optional[float] = Query(None, ge=0, description="Maximum age in hours"),
    escalated_only: bool = Query(False, description="Show only escalated reviews"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="Sort column"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get the operational review queue with full filtering.

    Supports filters by:
    - status, reviewer (assigned_to), risk score range, age range, escalation flag
    - Pagination and sorting

    This is the real data source for the Reviewer Ops 'Queue' widget.
    """
    repo = ReviewRepository(db, tenant_id=tenant_id)
    reviews, total = await repo.get_queue(
        tenant_id=tenant_id,
        status=status,
        assigned_to=assigned_to,
        risk_min=risk_min,
        risk_max=risk_max,
        age_min_hours=age_min_hours,
        age_max_hours=age_max_hours,
        escalated_only=escalated_only,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    from app.domains.review.service import ReviewService

    svc = ReviewService.__new__(ReviewService)
    items = [svc._review_to_detail(r) for r in reviews]
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.get("/recommendations", summary="Recommendations — AI findings with actionable recommendations")
async def get_recommendations(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    clause_type: Optional[str] = Query(None, description="Filter by clause type"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence threshold"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get actionable AI recommendations from review findings.

    Only returns findings that contain actual recommendation, confidence,
    and severity data — no demo/synthetic recommendations.

    Source: review_findings table, joined with contract_reviews for status/is_deleted filtering.
    """
    from sqlalchemy import text as sa_text

    conditions = [
        "r.tenant_id = :tenant_id",
        "r.is_deleted = FALSE",
        "f.recommendation IS NOT NULL",
        "f.recommendation != ''",
        "f.confidence IS NOT NULL",
        "f.severity IS NOT NULL",
    ]
    params = {"tenant_id": tenant_id, "limit": limit}

    if severity:
        conditions.append("f.severity = :severity")
        params["severity"] = severity
    if clause_type:
        conditions.append("f.clause_type = :clause_type")
        params["clause_type"] = clause_type
    if min_confidence is not None:
        conditions.append("f.confidence >= :min_confidence")
        params["min_confidence"] = min_confidence

    where_clause = " AND ".join(conditions)

    sql = sa_text(f"""
        SELECT
            f.finding_id::text,
            f.review_id::text,
            f.clause_type,
            f.severity,
            f.title,
            f.description,
            f.recommendation,
            f.confidence::float,
            f.risk_score::float,
            f.created_at
        FROM review_findings f
        JOIN contract_reviews r ON r.review_id = f.review_id AND r.tenant_id = f.tenant_id
        WHERE {where_clause}
        ORDER BY f.confidence DESC, f.created_at DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, params)
    rows = result.fetchall()
    return [
        {
            "finding_id": str(row.finding_id),
            "review_id": str(row.review_id),
            "clause_type": row.clause_type,
            "severity": row.severity,
            "title": row.title,
            "description": row.description,
            "recommendation": row.recommendation,
            "confidence": row.confidence,
            "risk_score": row.risk_score,
            "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else str(row.created_at),
        }
        for row in rows
    ]
