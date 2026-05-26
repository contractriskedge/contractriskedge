"""Workspace API router — dashboard views, action jobs, recommendation feedback."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.workspace.repository import WorkspaceRepository
from app.domains.workspace.service import WorkspaceService
from app.domains.workspace.schemas import (
    DashboardViewCreate, DashboardViewUpdate, DashboardViewResponse,
    ActionJobCreate, ActionJobResponse, ActionJobListResponse,
    RecommendationFeedbackCreate, RecommendationFeedbackResponse
)

router = APIRouter(prefix="/workspace", tags=["Workspace"])


async def get_workspace_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
) -> WorkspaceService:
    return WorkspaceService(
        repo=WorkspaceRepository(db, tenant_id=tenant_id),
        tenant_id=tenant_id,
        user_id=user.id
)


# ── Dashboard Views ──────────────────────────────────────────────


@router.post("/views", response_model=DashboardViewResponse)
async def create_view(
    body: DashboardViewCreate,
    service: WorkspaceService = Depends(get_workspace_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Save a new dashboard view configuration."""
    return await service.create_view(body
)


@router.get("/views", response_model=list[DashboardViewResponse]
)
async def list_views(
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List saved dashboard views for the current user."""
    return await service.list_views(
)


@router.get("/views/{view_id}", response_model=DashboardViewResponse
)
async def get_view(
    view_id: str,
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a saved dashboard view by ID."""
    view = await service.get_view(view_id
)
    if not view:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="View not found"
)
    return view


@router.put("/views/{view_id}", response_model=DashboardViewResponse
)
async def update_view(
    view_id: str,
    body: DashboardViewUpdate,
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Update a saved dashboard view."""
    view = await service.update_view(view_id, body
)
    if not view:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="View not found"
)
    return view


@router.delete("/views/{view_id}"
)
async def delete_view(
    view_id: str,
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_DELETE)),
):
    """Delete a saved dashboard view."""
    deleted = await service.delete_view(view_id
)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="View not found"
)
    return {"status": "deleted"}


# ── Action Jobs ──────────────────────────────────────────────────


@router.post("/jobs", response_model=ActionJobResponse
)
async def create_job(
    body: ActionJobCreate,
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Create a new async action job (assign, escalate, re-analyze, export, notify
)."""
    return await service.create_job(body
)


@router.get("/jobs", response_model=ActionJobListResponse
)
async def list_jobs(
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_READ)),
):
    """List action jobs for the current user."""
    return await service.list_jobs(
)


@router.get("/jobs/{job_id}", response_model=ActionJobResponse
)
async def get_job(
    job_id: str,
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_READ)),
):
    """Get the status of an action job."""
    job = await service.get_job(job_id
)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found"
)
    return job


# ── Recommendation Feedback ──────────────────────────────────────


@router.post("/recommendations/feedback", response_model=RecommendationFeedbackResponse
)
async def create_feedback(
    body: RecommendationFeedbackCreate,
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Submit feedback on an AI recommendation (accept, dismiss, snooze, resolve
)."""
    return await service.create_feedback(body
)


@router.get("/recommendations/feedback", response_model=list[RecommendationFeedbackResponse]
)
async def list_feedback(
    service: WorkspaceService = Depends(get_workspace_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List recommendation feedback for the current user."""
    return await service.list_feedback(
)
