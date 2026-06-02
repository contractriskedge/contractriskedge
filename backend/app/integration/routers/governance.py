"""
Governance API router.

Endpoints for integration approval, tenant restrictions, and compliance.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

from app.integration.routers.dependencies import (
    get_audit_service,
    get_db,
    get_governance_service,
    get_tenant_id,
    get_user_id,
)
from app.integration.schemas.governance import (
    ConnectorAccessPolicy,
    IntegrationApprovalRequest,
    IntegrationApprovalResponse,
    TenantRestrictionConfig,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.governance_service import GovernanceService

router = APIRouter(prefix="/governance", tags=["Governance"], dependencies=[Depends(require_permission(Permissions.CONTRACTS_READ))])



@router.post(
    "/approve",
    response_model=IntegrationApprovalResponse,
    summary="Approve an integration",
)
async def approve_integration(
    body: IntegrationApprovalRequest,
    request: Request,
    governance: GovernanceService = Depends(get_governance_service),
):
    """Approve or reject an integration."""
    try:
        integration = await governance.approve_integration(
            integration_id=body.integration_id,
            approved_by=body.approved_by,
            notes=body.approval_notes,
        )

        return IntegrationApprovalResponse(
            integration_id=integration.id,
            is_approved=integration.is_approved,
            approved_by=integration.approved_by,
            approved_at=integration.approved_at,
            approval_notes=body.approval_notes,
            status=integration.status.value,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/disable/{integration_id}",
    summary="Disable an integration",
)
async def disable_integration(
    integration_id: uuid.UUID,
    request: Request,
    reason: str = "Manually disabled via API",
    governance: GovernanceService = Depends(get_governance_service),
):
    """Disable an integration with an audit reason."""
    try:
        integration = await governance.disable_integration(
            integration_id=integration_id,
            reason=reason,
        )
        return {
            "status": "disabled",
            "integration_id": str(integration_id),
            "reason": reason,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/restrictions",
    summary="Set tenant restrictions",
)
async def set_tenant_restrictions(
    body: TenantRestrictionConfig,
    request: Request,
    governance: GovernanceService = Depends(get_governance_service),
):
    """Configure tenant-level integration restrictions."""
    from app.integration.services.governance_service import TenantRestrictions

    restrictions = TenantRestrictions(
        allowed_providers=body.allowed_providers,
        blocked_providers=body.blocked_providers or [],
        max_integrations=body.max_integrations,
        require_approval=body.require_approval,
        max_sync_frequency_minutes=body.max_sync_frequency_minutes,
        allowed_ip_ranges=body.allowed_ip_ranges,
    )

    governance.set_tenant_restrictions(body.tenant_id, restrictions)

    return {"status": "configured", "tenant_id": str(body.tenant_id)}


@router.get(
    "/connectors",
    response_model=list[ConnectorAccessPolicy],
    summary="List connector access policies",
)
async def list_connector_policies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """List connector access policies for the tenant."""
    from app.integration.services.connector_registry import get_connector_registry

    registry = get_connector_registry()
    providers = registry.list_providers()

    policies = []
    for provider in providers:
        policies.append(
            ConnectorAccessPolicy(
                tenant_id=tenant_id,
                provider=provider.provider,
                allowed_actions=[
                    "create", "read", "update", "delete", "sync"
                ],
                denied_actions=[],
                require_audit=True,
                auto_disable_on_failure=True,
                max_consecutive_failures=5,
            )
        )

    return policies
