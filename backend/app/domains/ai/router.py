"""AI analysis API router — trigger analysis, check status, retrieve findings and redlines."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id, get_event_bus
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.ai.schemas import (
    AIReviewCopilotRequest,
    AIReviewCopilotResponse,
    AIReviewFeedbackRequest,
    AIReviewFeedbackResponse,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
)
from app.domains.ai.service import AIService
from app.domains.ai.copilot import ReviewCopilotService
from app.domains.ai.repository import AIRepository
from app.domains.vectors.repository import VectorRepository
from app.domains.ingestion.repository import IngestionRepository
from app.domains.review.audit_trail import AuditTrailService
from app.kernel.events.bus import EventBus

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


async def get_ai_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    event_bus: EventBus = Depends(get_event_bus)
) -> AIService:
    return AIService(
        ai_repo=AIRepository(db, tenant_id=tenant_id),
        vector_repo=VectorRepository(db, tenant_id=tenant_id),
        ingest_repo=IngestionRepository(db, tenant_id=tenant_id),
        event_bus=event_bus,
        user=user,
        tenant_id=tenant_id
)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_contract(
    body: AnalysisRequest,
    service: AIService = Depends(get_ai_service),
    _: None = Depends(require_permission(Permissions.AI_ANALYZE)),
):
    """Trigger AI analysis on an upload's chunks.

    Runs risk analysis, clause classification, obligation extraction,
    and redline generation. Results are stored and accessible via
    the findings and redlines endpoints.
    """
    from workers.ai_worker import analyze_contract_task
    analyze_contract_task.delay(
        upload_id=body.upload_id,
        tenant_id=service.tenant_id,
        user_id=service.user.id if service.user else None,
        analysis_type=body.analysis_type
)
    return AnalysisResponse(
        run_id="pending",
        upload_id=body.upload_id,
        status="processing",
        message="Analysis pipeline dispatched to worker."
)


async def get_review_copilot_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    event_bus: EventBus = Depends(get_event_bus),
) -> ReviewCopilotService:
    ai_service = AIService(
        ai_repo=AIRepository(db, tenant_id=tenant_id),
        vector_repo=VectorRepository(db, tenant_id=tenant_id),
        ingest_repo=IngestionRepository(db, tenant_id=tenant_id),
        event_bus=event_bus,
        user=user,
        tenant_id=tenant_id,
    )
    return ReviewCopilotService(
        ai_service=ai_service,
        audit_trail=AuditTrailService(db, tenant_id=tenant_id),
        user=user,
        tenant_id=tenant_id,
    )


@router.post("/copilot/suggest", response_model=AIReviewCopilotResponse)
async def suggest_review_actions(
    body: AIReviewCopilotRequest,
    service: ReviewCopilotService = Depends(get_review_copilot_service),
    _: None = Depends(require_permission(Permissions.AI_VIEW)),
):
    """Generate AI review suggestions and record audit-grade trace data."""
    return await service.suggest(body)


@router.post("/copilot/feedback", response_model=AIReviewFeedbackResponse)
async def submit_review_feedback(
    body: AIReviewFeedbackRequest,
    service: ReviewCopilotService = Depends(get_review_copilot_service),
    _: None = Depends(require_permission(Permissions.AI_VIEW)),
):
    """Capture reviewer feedback on AI Copilot suggestions."""
    return await service.record_feedback(body)


@router.get("/runs", response_model=dict
)
async def list_analysis_runs(
    upload_id: str = Query(..., description="Filter runs by upload ID"),
    service: AIService = Depends(get_ai_service)
,
    _: None = Depends(require_permission(Permissions.AI_VIEW)),
):
    """List all AI analysis runs for an upload, ordered by recency."""
    runs = await service.list_runs_by_upload(upload_id
)
    return {
        "runs": [
            AnalysisStatusResponse(
                run_id=str(r.run_id),
                upload_id=str(r.upload_id),
                analysis_type=r.analysis_type,
                status=r.status.value if hasattr(r.status, 'value') else r.status,
                model=r.model,
                provider=r.provider,
                prompt_version=r.prompt_version,
                extraction_prompt_version=r.extraction_prompt_version,
                analysis_prompt_version=r.analysis_prompt_version,
                risk_score=r.risk_score,
                findings_count=r.findings_count,
                redlines_count=r.redlines_count,
                total_tokens=r.total_tokens,
                cost_usd=r.cost_usd,
                latency_ms=r.latency_ms,
                error_message=r.error_message,
                retry_count=r.retry_count,
                created_at=r.created_at,
                completed_at=r.completed_at
)
            for r in runs
        ],
        "total": len(runs
),
    }


@router.get("/runs/{run_id}", response_model=AnalysisStatusResponse
)
async def get_analysis_status(
    run_id: str,
    service: AIService = Depends(get_ai_service)
,
    _: None = Depends(require_permission(Permissions.AI_VIEW)),
):
    """Get the status and results of an AI analysis run."""
    run = await service.get_status(run_id
)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found"
)
    return AnalysisStatusResponse(
        run_id=str(run.run_id),
        upload_id=str(run.upload_id),
        analysis_type=run.analysis_type,
        status=run.status.value,
        model=run.model,
        provider=run.provider,
        prompt_version=run.prompt_version,
        extraction_prompt_version=run.extraction_prompt_version,
        analysis_prompt_version=run.analysis_prompt_version,
        risk_score=run.risk_score,
        findings_count=run.findings_count,
        redlines_count=run.redlines_count,
        total_tokens=run.total_tokens,
        cost_usd=run.cost_usd,
        latency_ms=run.latency_ms,
        error_message=run.error_message,
        retry_count=run.retry_count,
        created_at=run.created_at,
        completed_at=run.completed_at
)


@router.get("/runs/{run_id}/findings"
)
async def get_findings(
    run_id: str,
    service: AIService = Depends(get_ai_service)
,
    _: None = Depends(require_permission(Permissions.AI_VIEW)),
):
    """Get all findings for an analysis run."""
    findings = await service.get_findings(run_id
)
    return {"findings": [
        {
            "finding_id": str(f.finding_id
),
            "finding_type": f.finding_type.value,
            "severity": f.severity.value,
            "clause_type": f.clause_type,
            "title": f.title,
            "description": f.description,
            "recommendation": f.recommendation,
            "confidence": f.confidence,
            "risk_score": f.risk_score,
        }
        for f in findings
    ]}


@router.get("/runs/{run_id}/redlines"
)
async def get_redlines(
    run_id: str,
    service: AIService = Depends(get_ai_service)
,
    _: None = Depends(require_permission(Permissions.AI_VIEW)),
):
    """Get all redline suggestions for an analysis run."""
    redlines = await service.get_redlines(run_id
)
    return {"redlines": [
        {
            "redline_id": str(r.redline_id
),
            "clause_type": r.clause_type,
            "original_text": r.original_text,
            "proposed_text": r.proposed_text,
            "rationale": r.rationale,
            "risk_level": r.risk_level,
            "confidence": r.confidence,
        }
        for r in redlines
    ]}
