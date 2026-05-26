"""Contract review API router — full set of review management endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
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
    CommentItem, CommentCreate, AssignRequest, EscalateRequest,
    ApproveRequest, FindingResolveRequest, RedlineUpdateRequest,
    GenerateMitigationRedlineRequest, GenerateMitigationRedlineResponse,
    ReviewDashboardResponse, DashboardStats, FindingsBySeverity,
    FindingsByClauseType, ReviewsByStatus, RecentActivity,
    ReviewStatusResponse, ReAnalysisRequest, ReAnalysisResponse,
    ReviewDeleteRequest, ReviewArchiveRequest,
    BulkAssignRequest, BulkEscalateRequest, BulkApproveRequest, BulkExportRequest,
    DocumentVersionItem, CreateDocumentVersionRequest,
)
from app.domains.review.service import ReviewService
from app.domains.review.utils import enum_value as _enum_value, redline_to_item
from app.domains.review.repository import ReviewRepository
from app.domains.ai.repository import AIRepository
from app.domains.notify.repository import NotificationRepository
from app.domains.notify.service import NotificationService
from app.kernel.events.bus import EventBus

router = APIRouter(prefix="/reviews", tags=["Contract Review"])

logger = logging.getLogger(__name__)


async def get_review_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> ReviewService:
    return ReviewService(
        review_repo=ReviewRepository(db, tenant_id=tenant_id),
        ai_repo=AIRepository(db, tenant_id=tenant_id),
        event_bus=EventBus(),
        user=user,
        tenant_id=tenant_id,
        notify_service=NotificationService(
            repo=NotificationRepository(db, tenant_id=tenant_id),
            event_bus=EventBus(),
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

    return ReviewStatusResponse(
        review_id=str(review.review_id),
        upload_id=str(review.upload_id),
        status=overall_status,
        ingestion_state=ingestion_state,
        ai_status=ai_status,
        review_status=_enum_value(review.status),
        progress=progress,
        current_step=current_step,
        error=error,
        error_code=error_code,
        can_retry=can_retry,
        created_at=review.created_at,
        updated_at=review.updated_at,
        completed_at=review.completed_at,
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
    result = await service.update_status(review_id, status, reason)
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
    items, total = await service.get_findings(review_id, severity, resolution, page, page_size)
    data = [
        FindingItem(
            finding_id=str(f.finding_id), clause_type=f.clause_type,
            severity=f.severity, title=f.title, description=f.description,
            recommendation=f.recommendation, confidence=f.confidence,
            risk_score=f.risk_score,
            page_numbers=f.page_numbers,
            resolution=_enum_value(f.resolution),
            resolution_note=f.resolution_note,
            resolved_by=f.resolved_by,
            resolved_at=f.resolved_at.isoformat() if f.resolved_at else None,
            created_at=f.created_at,
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

    # Build response: strip synthetic numbering from INSERT_NEW proposed_text
    items = []
    for r in redlines:
        rid = str(r.redline_id)
        loc = locator_results.get(rid, {})
        item = redline_to_item(
            r,
            chunk_ids=chunk_map.get(str(r.ai_redline_id), []),
            locator_result=loc,
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
    result = await service.update_redline(redline_id, body.status, body.modified_text, body.review_notes)
    if not result:
        raise HTTPException(status_code=404, detail="Redline not found")
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
    return await service.approve(review_id, body.decision, body.comments, body.conditions)


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
    _: None = Depends(require_permission(Permissions.AUDIT_EXPORT)),
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
    _: None = Depends(require_permission(Permissions.AUDIT_EXPORT)),
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
    import io, json, zipfile
    from datetime import datetime

    repo = ReviewRepository(db, tenant_id=tenant_id)

    # Gather data
    review = await repo.get_review(review_id, tenant_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    history = await repo.get_status_history(review_id, tenant_id)
    findings, _ = await repo.get_findings(review_id, tenant_id, page=1, page_size=500)
    redlines = await repo.get_redlines(review_id, tenant_id)
    comments = await repo.get_comments(review_id, tenant_id)

    from app.domains.review.models import ContractDocumentVersion
    from sqlalchemy import select
    versions_result = await db.execute(
        select(ContractDocumentVersion).where(
            ContractDocumentVersion.review_id == review_id,
            ContractDocumentVersion.tenant_id == tenant_id,
        ).order_by(ContractDocumentVersion.version_number)
    )
    versions = versions_result.scalars().all()

    # Build ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # JSON exports
        zf.writestr("review.json", json.dumps({
            "review_id": str(review.review_id),
            "status": _enum_value(review.status),
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
                "resolution": _enum_value(f.resolution),
            }
            for f in findings
        ], indent=2, default=str))

        zf.writestr("redlines.json", json.dumps([
            {
                "redline_id": str(r.redline_id),
                "clause_type": r.clause_type,
                "status": _enum_value(r.status),
            }
            for r in redlines
        ], indent=2, default=str))

        zf.writestr("comments.json", json.dumps([
            {
                "comment_id": str(c.comment_id),
                "author_id": c.author_id,
                "body": c.body[:500],
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

        # Include version documents if storage keys exist
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
    _: None = Depends(require_permission(Permissions.AUDIT_EXPORT)),
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


def _extract_risk(review) -> float | None:
    metadata = getattr(review, "document_metadata", None) or {}
    return metadata.get("risk_score") if isinstance(metadata, dict) else None
