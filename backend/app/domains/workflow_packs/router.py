"""Enterprise Workflow Packs API router — pack management, activation, built-in packs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.workflow_packs.schemas import (
    WorkflowPackCategory,
    WorkflowPackCreate, WorkflowPackResponse, WorkflowPackSummary,
    PackActivation, PackActivateRequest,
    WorkflowVersionSummary,
)
from app.domains.workflow_packs.service import WorkflowPackService

router = APIRouter(prefix="/workflow-packs", tags=["Enterprise Workflow Packs"], redirect_slashes=False)


# ── Dependencies ────────────────────────────────────────────────────


async def get_pack_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> WorkflowPackService:
    return WorkflowPackService(session=db, tenant_id=tenant_id)


# ── Pack Management ─────────────────────────────────────────────────


@router.get("")
@router.get("/", response_model=list[WorkflowPackSummary])
async def list_workflow_packs(
    category: Optional[WorkflowPackCategory] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    include_builtin: bool = Query(True),
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List available workflow packs, including built-in and tenant-created."""
    return await service.list_packs(category=category, status=status, search=search, include_builtin=include_builtin)


@router.get("/{pack_id}", response_model=WorkflowPackResponse)
async def get_workflow_pack(
    pack_id: str,
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a workflow pack by ID (built-in or custom)."""
    pack = await service.get_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Workflow pack '{pack_id}' not found")
    return pack


@router.post("")
@router.post("/", response_model=WorkflowPackResponse, status_code=201)
async def create_workflow_pack(
    pack: WorkflowPackCreate,
    service: WorkflowPackService = Depends(get_pack_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a custom workflow pack."""
    return await service.create_pack(pack, actor=user.id)


@router.delete("/{pack_id}")
async def delete_workflow_pack(
    pack_id: str,
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Delete a custom workflow pack."""
    deleted = await service.delete_pack(pack_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow pack not found")
    return {"status": "deleted"}


# ── Versions ─────────────────────────────────────────────────────────


@router.get("/{pack_id}/versions", response_model=list[WorkflowVersionSummary])
async def list_workflow_versions(
    pack_id: str,
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all versions of a workflow pack."""
    return await service.list_versions(pack_id)


@router.post("/{pack_id}/versions", response_model=dict, status_code=201)
async def create_workflow_version(
    pack_id: str,
    data: dict,
    service: WorkflowPackService = Depends(get_pack_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new version for a workflow pack."""
    return await service.create_version(pack_id, data, actor=user.id)


@router.post("/{pack_id}/versions/{version_id}/publish", response_model=dict)
async def publish_workflow_version(
    pack_id: str,
    version_id: str,
    data: Optional[dict] = None,
    service: WorkflowPackService = Depends(get_pack_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Publish a workflow version."""
    effective_date = None
    if data and "effective_date" in data:
        from datetime import datetime
        effective_date = datetime.fromisoformat(data["effective_date"].replace("Z", "+00:00"))
    return await service.publish_version(pack_id, version_id, actor=user.id, effective_date=effective_date)


@router.get("/{pack_id}/versions/{version_id}/validate", response_model=dict)
async def validate_workflow_version(
    pack_id: str,
    version_id: str,
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Validate a workflow version."""
    return await service.validate_version(pack_id, version_id)


@router.get("/{pack_id}/versions/{version_id}/impact", response_model=dict)
async def impact_workflow_version(
    pack_id: str,
    version_id: str,
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Analyze impact of a workflow version."""
    return await service.impact_analysis(pack_id, version_id)


@router.post("/{pack_id}/versions/{version_id}/simulate", response_model=dict)
async def simulate_workflow_version(
    pack_id: str,
    version_id: str,
    input_data: dict,
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Simulate a workflow version with test input."""
    return await service.simulate_version(pack_id, version_id, input_data)


@router.get("/{pack_id}/versions/{version_id_a}/compare/{version_id_b}", response_model=dict)
async def compare_workflow_versions(
    pack_id: str,
    version_id_a: str,
    version_id_b: str,
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Compare two versions of a workflow pack."""
    return await service.compare_versions(pack_id, version_id_a, version_id_b)


@router.get("/{pack_id}/analytics", response_model=dict)
async def get_pack_analytics(
    pack_id: str,
    days: int = Query(30, ge=1, le=365),
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get analytics for a workflow pack."""
    return await service.get_pack_analytics(pack_id, days=days)


# ── Pack Activation ─────────────────────────────────────────────────


@router.post("/activate", response_model=PackActivation)
async def activate_workflow_pack(
    request: PackActivateRequest,
    service: WorkflowPackService = Depends(get_pack_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Activate a workflow pack for the tenant."""
    try:
        return await service.activate_pack(request, actor=user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{pack_id}/deactivate")
async def deactivate_workflow_pack(
    pack_id: str,
    business_unit: Optional[str] = Query(None),
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Deactivate a workflow pack for the tenant."""
    deactivated = await service.deactivate_pack(pack_id, business_unit=business_unit)
    if not deactivated:
        raise HTTPException(status_code=404, detail="Active pack activation not found")
    return {"status": "deactivated"}


@router.get("/activations/active", response_model=list[PackActivation])
async def get_active_packs(
    service: WorkflowPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get all currently active workflow packs for the tenant."""
    return await service.get_active_packs()
