"""
Permission management API router.

Endpoints for managing connector-level permissions and evaluating access.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.models.permission import ConnectorPermission, PermissionAction, PermissionEffect
from app.integration.routers.dependencies import (
    get_audit_service,
    get_db,
    get_permission_evaluator,
    get_tenant_id,
)
from app.integration.schemas.permission import (
    PermissionCreate,
    PermissionEvaluateRequest,
    PermissionEvaluateResult,
    PermissionListResponse,
    PermissionResponse,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.governance_service import PermissionEvaluator

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a permission",
)
async def create_permission(
    body: PermissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
):
    """Create a new connector permission rule."""
    permission = ConnectorPermission(
        tenant_id=tenant_id,
        role_id=body.role_id,
        user_id=body.user_id,
        integration_id=body.integration_id,
        provider=body.provider,
        action=PermissionAction(body.action),
        effect=PermissionEffect(body.effect),
        resource_type=body.resource_type,
        conditions=body.conditions or {},
        priority=body.priority,
        expires_at=body.expires_at,
        metadata_=body.metadata or {},
    )

    db.add(permission)
    await db.flush()
    await db.refresh(permission)

    await audit.log_event(
        action="permission_created",
        resource_type="connector_permission",
        resource_id=str(permission.id),
        new_state={"action": body.action, "effect": body.effect},
        change_summary=f"Permission {body.effect} for {body.action}",
        success=True,
    )

    return permission


@router.get(
    "",
    response_model=PermissionListResponse,
    summary="List permissions",
)
async def list_permissions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[uuid.UUID] = Query(None),
    role_id: Optional[uuid.UUID] = Query(None),
    action: Optional[str] = Query(None),
):
    """List permissions with pagination and filtering."""
    query = select(ConnectorPermission).where(
        ConnectorPermission.tenant_id == tenant_id,
    )

    if user_id:
        query = query.where(ConnectorPermission.user_id == user_id)
    if role_id:
        query = query.where(ConnectorPermission.role_id == role_id)
    if action:
        query = query.where(ConnectorPermission.action == action)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(ConnectorPermission.priority.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return PermissionListResponse(
        items=[PermissionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete permission",
)
async def delete_permission(
    permission_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
):
    """Delete a permission rule."""
    result = await db.execute(
        select(ConnectorPermission).where(
            ConnectorPermission.id == permission_id,
            ConnectorPermission.tenant_id == tenant_id,
        )
    )
    permission = result.scalar_one_or_none()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    await db.delete(permission)
    await db.flush()

    await audit.log_event(
        action="permission_deleted",
        resource_type="connector_permission",
        resource_id=str(permission_id),
        change_summary="Permission deleted",
        success=True,
    )


@router.post(
    "/evaluate",
    response_model=PermissionEvaluateResult,
    summary="Evaluate permission",
)
async def evaluate_permission(
    body: PermissionEvaluateRequest,
    request: Request,
    evaluator: PermissionEvaluator = Depends(get_permission_evaluator),
):
    """Evaluate whether a user has permission to perform an action."""
    result = await evaluator.evaluate(
        user_id=body.user_id,
        action=body.action,
        integration_id=body.integration_id,
        provider=body.provider,
        resource_type=body.resource_type,
    )

    return PermissionEvaluateResult(
        allowed=result.allowed,
        effect=result.effect.value if result.effect else None,
        matched_permission_id=result.matched_permission_id,
        reason=result.reason,
    )
