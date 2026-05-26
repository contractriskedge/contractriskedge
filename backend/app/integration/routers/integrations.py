"""
Integration management API router.

Endpoints for creating, listing, updating, and disabling integrations.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.models.integration import (
    ConnectorProvider,
    Integration,
    IntegrationStatus,
    IntegrationType,
)
from app.integration.routers.dependencies import (
    get_audit_service,
    get_db,
    get_governance_service,
    get_permission_evaluator,
    get_tenant_id,
    get_user_id,
)
from app.integration.schemas.integration import (
    IntegrationCreate,
    IntegrationListResponse,
    IntegrationResponse,
    IntegrationStatusUpdate,
    IntegrationUpdate,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.connector_registry import get_connector_registry
from app.integration.services.governance_service import (
    GovernanceService,
    PermissionEvaluator,
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.post(
    "",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new integration",
)
async def create_integration(
    body: IntegrationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: Optional[uuid.UUID] = Depends(get_user_id),
    governance: GovernanceService = Depends(get_governance_service),
    audit: IntegrationAuditService = Depends(get_audit_service),
    permissions: PermissionEvaluator = Depends(get_permission_evaluator),
):
    """Create a new connector integration for the tenant."""
    # Validate provider
    registry = get_connector_registry()
    if not registry.is_supported(body.provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported connector provider: {body.provider}",
        )

    # Check tenant restrictions
    restriction_error = await governance.check_tenant_restrictions(body.provider)
    if restriction_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=restriction_error,
        )

    # Check user permissions
    if user_id:
        eval_result = await permissions.evaluate(
            user_id=user_id,
            action="create",
            provider=body.provider,
        )
        if not eval_result.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create integration",
            )

    # Determine initial status
    require_approval = await governance.require_approval()
    initial_status = (
        IntegrationStatus.PENDING_APPROVAL
        if require_approval
        else IntegrationStatus.PENDING
    )

    integration = Integration(
        tenant_id=tenant_id,
        organization_id=body.organization_id,
        name=body.name,
        provider=ConnectorProvider(body.provider),
        integration_type=IntegrationType(body.integration_type),
        status=initial_status,
        description=body.description,
        config=body.config or {},
        metadata_=body.metadata or {},
        scopes=body.scopes or [],
        webhook_url=body.webhook_url,
        rate_limit_max=body.rate_limit_max,
        rate_limit_window_seconds=body.rate_limit_window_seconds,
        created_by=user_id,
    )

    db.add(integration)
    await db.flush()
    await db.refresh(integration)

    await audit.log_integration_created(
        integration_id=integration.id,
        actor_id=user_id,
        metadata={"provider": body.provider, "name": body.name},
    )

    return integration


@router.get(
    "",
    response_model=IntegrationListResponse,
    summary="List integrations",
)
async def list_integrations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name"),
):
    """List integrations with pagination and filtering."""
    query = select(Integration).where(
        Integration.tenant_id == tenant_id,
        Integration.is_deleted == False,
    )

    if provider:
        query = query.where(Integration.provider == provider)
    if status:
        query = query.where(Integration.status == status)
    if search:
        query = query.where(Integration.name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Integration.created_at.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return IntegrationListResponse(
        items=[IntegrationResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Get integration details",
)
async def get_integration(
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Get details of a specific integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.tenant_id == tenant_id,
            Integration.is_deleted == False,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    return integration


@router.patch(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Update integration",
)
async def update_integration(
    integration_id: uuid.UUID,
    body: IntegrationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
):
    """Update an integration's configuration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.tenant_id == tenant_id,
            Integration.is_deleted == False,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    previous_state = {
        "name": integration.name,
        "config": integration.config,
        "scopes": integration.scopes,
    }

    for field, value in update_data.items():
        if field == "metadata":
            setattr(integration, "metadata_", value)
        elif hasattr(integration, field):
            setattr(integration, field, value)

    await db.flush()
    await db.refresh(integration)

    await audit.log_event(
        integration_id=integration_id,
        action="integration_updated",
        resource_type="integration",
        resource_id=str(integration_id),
        previous_state=previous_state,
        new_state={"name": integration.name, "config": integration.config},
        change_summary="Integration configuration updated",
        success=True,
    )

    return integration


@router.post(
    "/{integration_id}/status",
    response_model=IntegrationResponse,
    summary="Update integration status",
)
async def update_integration_status(
    integration_id: uuid.UUID,
    body: IntegrationStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    governance: GovernanceService = Depends(get_governance_service),
):
    """Enable or disable an integration."""
    if body.status == "disabled":
        integration = await governance.disable_integration(
            integration_id=integration_id,
            reason=body.reason or "Manually disabled",
        )
    elif body.status == "active":
        result = await db.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.tenant_id == tenant_id,
                Integration.is_deleted == False,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found",
            )
        integration.status = IntegrationStatus.ACTIVE
        await db.flush()
        await db.refresh(integration)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {body.status}",
        )

    return integration


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete integration",
)
async def delete_integration(
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
):
    """Soft-delete an integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.tenant_id == tenant_id,
            Integration.is_deleted == False,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    integration.is_deleted = True
    integration.status = IntegrationStatus.DISABLED
    await db.flush()

    await audit.log_event(
        integration_id=integration_id,
        action="integration_deleted",
        resource_type="integration",
        resource_id=str(integration_id),
        previous_state={"is_deleted": False},
        new_state={"is_deleted": True},
        change_summary="Integration soft-deleted",
        success=True,
    )
