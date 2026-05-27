"""Human Oversight API router — approval workflows, policy exceptions, decision impact."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.human_oversight.schemas import (
    ApprovalStatus, ApprovalType,
    AIRecommendationApproval, ApprovalDecision, ApprovalRequestCreate, ApprovalSummary,
    PolicyExceptionRequest, PolicyExceptionCreate, PolicyExceptionReview,
    AcknowledgmentRequirement, AcknowledgmentAction, AcknowledgmentSummary,
    DecisionImpactPreview, BulkDecisionRequest, BulkDecisionResult,
    HumanOversightDashboard,
)
from app.domains.human_oversight.service import (
    ApprovalService,
    PolicyExceptionService,
    AcknowledgmentService,
    DecisionImpactService,
)

router = APIRouter(prefix="/human-oversight", tags=["Human Oversight"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_approval_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ApprovalService:
    return ApprovalService(session=db, tenant_id=tenant_id)


async def get_exception_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> PolicyExceptionService:
    return PolicyExceptionService(session=db, tenant_id=tenant_id)


async def get_ack_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> AcknowledgmentService:
    return AcknowledgmentService(session=db, tenant_id=tenant_id)


async def get_impact_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> DecisionImpactService:
    return DecisionImpactService(session=db, tenant_id=tenant_id)


# ── AI Recommendation Approval ──────────────────────────────────────


@router.post("/approvals", response_model=AIRecommendationApproval, status_code=201)
async def create_approval_request(
    request: ApprovalRequestCreate,
    service: ApprovalService = Depends(get_approval_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create an approval request for an AI recommendation."""
    return await service.create_approval(request, actor=user.id)


@router.post("/approvals/{approval_id}/decide", response_model=AIRecommendationApproval)
async def decide_approval(
    approval_id: str,
    decision: ApprovalDecision,
    service: ApprovalService = Depends(get_approval_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_APPROVE)),
):
    """Approve, reject, or conditionally approve an AI recommendation."""
    try:
        return await service.decide(approval_id, decision, actor=user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/approvals/pending", response_model=list[ApprovalSummary])
async def list_pending_approvals(
    review_id: Optional[str] = Query(None),
    service: ApprovalService = Depends(get_approval_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List pending approval requests, optionally filtered by review."""
    return await service.list_pending(review_id=review_id)


# ── Policy Exceptions ───────────────────────────────────────────────


@router.post("/exceptions", response_model=PolicyExceptionRequest, status_code=201)
async def create_policy_exception(
    request: PolicyExceptionCreate,
    service: PolicyExceptionService = Depends(get_exception_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a policy exception request."""
    return await service.create_exception(request, actor=user.id)


@router.post("/exceptions/{exception_id}/review", response_model=PolicyExceptionRequest)
async def review_policy_exception(
    exception_id: str,
    review: PolicyExceptionReview,
    service: PolicyExceptionService = Depends(get_exception_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_APPROVE)),
):
    """Review and decide on a policy exception."""
    try:
        return await service.review_exception(exception_id, review, actor=user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/exceptions/pending", response_model=list[PolicyExceptionRequest])
async def list_pending_exceptions(
    service: PolicyExceptionService = Depends(get_exception_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List pending policy exceptions."""
    return await service.list_pending()


# ── Decision Impact Preview ─────────────────────────────────────────


@router.get("/impact/redline/{redline_id}", response_model=DecisionImpactPreview)
async def preview_redline_impact(
    redline_id: str,
    review_id: str = Query(...),
    service: DecisionImpactService = Depends(get_impact_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Preview the risk impact of approving a redline."""
    return await service.preview_redline_approval(redline_id, review_id)


@router.get("/impact/finding/{finding_id}", response_model=DecisionImpactPreview)
async def preview_finding_impact(
    finding_id: str,
    resolution: str = Query("resolved"),
    service: DecisionImpactService = Depends(get_impact_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Preview the risk impact of resolving a finding."""
    return await service.preview_finding_resolution(finding_id, resolution)


# ── Dashboard ───────────────────────────────────────────────────────


@router.get("/dashboard", response_model=HumanOversightDashboard)
async def get_human_oversight_dashboard(
    service: ApprovalService = Depends(get_approval_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get the human oversight dashboard with pending approvals, exceptions, and activity."""
    return await service.get_dashboard()
