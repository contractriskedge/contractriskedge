"""Task/Case management API router."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.cases.repository import CaseRepository
from app.domains.cases.service import CaseService
from app.domains.cases.schemas import (
    CaseCreate, CaseUpdate, CaseResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    CaseCommentCreate, CaseCommentResponse
)

router = APIRouter(prefix="/cases", tags=["Cases & Tasks"])


async def get_case_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
) -> CaseService:
    return CaseService(
        repo=CaseRepository(db, tenant_id=tenant_id),
        tenant_id=tenant_id,
        user_id=user.id
)


# ── Cases ────────────────────────────────────────────────────────


@router.post("", response_model=CaseResponse)
async def create_case(
    body: CaseCreate,
    service: CaseService = Depends(get_case_service),
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Create a new remediation case."""
    return await service.create_case(body
)


@router.get("", response_model=list[CaseResponse]
)
async def list_cases(
    status: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_READ)),
):
    """List cases with optional status and assignee filters."""
    return await service.list_cases(status, assignee_id
)


@router.get("/counts"
)
async def get_case_counts(
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_READ)),
):
    """Get case counts grouped by status."""
    return await service.get_case_counts(
)


@router.get("/{case_id}", response_model=CaseResponse
)
async def get_case(
    case_id: str,
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_READ)),
):
    """Get a case with its tasks."""
    case = await service.get_case(case_id
)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found"
)
    return case


@router.put("/{case_id}", response_model=CaseResponse
)
async def update_case(
    case_id: str,
    body: CaseUpdate,
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Update a case's status, priority, or assignee."""
    case = await service.update_case(case_id, body
)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found"
)
    return case


@router.delete("/{case_id}"
)
async def delete_case(
    case_id: str,
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Delete a case."""
    deleted = await service.delete_case(case_id
)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found"
)
    return {"status": "deleted"}


# ── Tasks ────────────────────────────────────────────────────────


@router.post("/{case_id}/tasks", response_model=TaskResponse
)
async def create_task(
    case_id: str,
    body: TaskCreate,
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Create a task within a case."""
    body.case_id = case_id
    return await service.create_task(body
)


@router.get("/{case_id}/tasks", response_model=list[TaskResponse]
)
async def list_tasks(
    case_id: str,
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_READ)),
):
    """List tasks for a case."""
    return await service.list_tasks(case_id
)


@router.put("/{case_id}/tasks/{task_id}", response_model=TaskResponse
)
async def update_task(
    case_id: str,
    task_id: str,
    body: TaskUpdate,
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Update a task's status or assignee."""
    task = await service.update_task(task_id, body
)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found"
)
    return task


# ── Comments ─────────────────────────────────────────────────────


@router.post("/{case_id}/comments", response_model=CaseCommentResponse
)
async def create_comment(
    case_id: str,
    body: CaseCommentCreate,
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_WRITE)),
):
    """Add a comment to a case."""
    body.case_id = case_id
    return await service.create_comment(body
)


@router.get("/{case_id}/comments", response_model=list[CaseCommentResponse]
)
async def list_comments(
    case_id: str,
    service: CaseService = Depends(get_case_service)
,
    _: None = Depends(require_permission(Permissions.WORKFLOWS_READ)),
):
    """List comments on a case."""
    return await service.list_comments(case_id
)
