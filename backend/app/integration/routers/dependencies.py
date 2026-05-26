"""
Shared dependencies for integration routers.

Provides tenant context, database sessions, and service factories.
"""

import uuid
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.governance_service import (
    GovernanceService,
    PermissionEvaluator,
)
from app.integration.services.oauth_service import OAuthService
from app.integration.services.rate_limiter import RateLimiter
from app.integration.services.sync_service import SyncOrchestrator
from app.integration.services.telemetry import IntegrationTelemetry, get_telemetry
from app.integration.services.webhook_service import WebhookService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield database session."""
    async with get_async_session() as session:
        yield session


async def get_tenant_id(request: Request) -> uuid.UUID:
    """
    Extract tenant ID from request context.

    In production, this comes from the auth token/JWT.
    """
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Tenant-ID header is required",
        )
    try:
        return uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID format",
        )


async def get_user_id(request: Request) -> Optional[uuid.UUID]:
    """Extract user ID from request context (from auth token)."""
    user_id = request.headers.get("X-User-ID")
    if user_id:
        try:
            return uuid.UUID(user_id)
        except ValueError:
            pass
    return None


async def get_audit_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> IntegrationAuditService:
    return IntegrationAuditService(db=db, tenant_id=tenant_id)


async def get_oauth_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
) -> OAuthService:
    return OAuthService(
        db=db,
        tenant_id=tenant_id,
        audit=audit,
        telemetry=get_telemetry(),
    )


async def get_webhook_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
) -> WebhookService:
    return WebhookService(
        db=db,
        tenant_id=tenant_id,
        audit=audit,
        telemetry=get_telemetry(),
    )


async def get_sync_orchestrator(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
) -> SyncOrchestrator:
    return SyncOrchestrator(
        db=db,
        tenant_id=tenant_id,
        audit=audit,
        telemetry=get_telemetry(),
    )


async def get_governance_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
) -> GovernanceService:
    return GovernanceService(
        db=db,
        tenant_id=tenant_id,
        audit=audit,
    )


async def get_permission_evaluator(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> PermissionEvaluator:
    return PermissionEvaluator(db=db, tenant_id=tenant_id)
