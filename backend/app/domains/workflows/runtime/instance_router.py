"""Workflow Instances API router — alias for /workflows endpoints.

Provides /workflow-instances/* endpoints that delegate to the same
logic as /workflows/* for frontend compatibility.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db, get_tenant_id
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.workflow_packs.repository import WorkflowRepository
from app.domains.workflows.runtime.router import get_repo

router = APIRouter(prefix="/workflow-instances", tags=["Workflow Instances"])


@router.get("")
@router.get("/")
async def list_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    workflow_type: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    repo: WorkflowRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List workflow instances (alias for /workflows)."""
    from app.domains.workflows.runtime.router import list_workflows
    return await list_workflows(
        status=status,
        workflow_type=workflow_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        repo=repo,
        _=_,
    )


@router.get("/{workflow_id}")
async def get_instance(
    workflow_id: str,
    repo: WorkflowRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a workflow instance by ID (alias for /workflows/{id})."""
    from app.domains.workflows.runtime.router import get_workflow
    return await get_workflow(workflow_id=workflow_id, repo=repo, _=_)
