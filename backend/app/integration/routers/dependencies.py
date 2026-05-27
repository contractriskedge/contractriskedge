"""
Shared dependencies for integration routers.

Provides tenant context, database sessions, and service factories.
Uses the kernel's TenantAwareSessionFactory for tenant-safe session management.
"""

import uuid
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.kernel.database.session import TenantAwareSessionFactory
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


# Reuse the kernel's database factory from app state (set during lifespan)
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a tenant-isolated database session using the kernel factory."""
    factory: TenantAwareSessionFactory = request.app.state.db_factory
    if not factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized",
        )
    # Extract tenant context from the authenticated request
    user = getattr(request.state, "user", None)
    tenant_id = getattr(user, "tenant_id", settings.dev_tenant_id) if user else settings.dev_tenant_id
    user_id = getattr(user, "id", "system") if user else "system"
    user_role = getattr(user, "role", "viewer") if user else "viewer"

    session = await factory.create_session(
        tenant_id=str(tenant_id),
        user_id=str(user_id),
        user_role=user_role,
    )
    try:
        yield session
    finally:
        await session.close()


async def get_tenant_id(request: Request) -> uuid.UUID:
    """
    Extract tenant ID from the authenticated user context.

    In production, this comes from the JWT token validated by AuthContextMiddleware.
    """
    user = getattr(request.state, "user", None)
    if user and getattr(user, "tenant_id", None):
        try:
            return uuid.UUID(user.tenant_id)
        except ValueError:
            pass
    # Fallback to header for backward compatibility
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context not found. Authenticate or provide X-Tenant-ID header.",
        )
    try:
        return uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID format",
        )


async def get_user_id(request: Request) -> Optional[uuid.UUID]:
    """Extract user ID from the authenticated user context."""
    user = getattr(request.state, "user", None)
    if user and getattr(user, "id", None):
        try:
            return uuid.UUID(user.id) if isinstance(user.id, str) else user.id
        except (ValueError, AttributeError):
            pass
    # Fallback to header
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
