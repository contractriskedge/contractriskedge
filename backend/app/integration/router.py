"""
Integration subsystem main router.

Aggregates all integration-related API routers into a single mount point.
"""

from fastapi import APIRouter

from app.integration.routers import (
    audit_router,
    credentials_router,
    governance_router,
    integrations_router,
    oauth_router,
    permissions_router,
    sync_router,
    webhooks_router,
)

# Main integration router — mount under /api/v1/integration
integration_router = APIRouter(prefix="/integration")

# Include all sub-routers
integration_router.include_router(integrations_router)
integration_router.include_router(oauth_router)
integration_router.include_router(webhooks_router)
integration_router.include_router(sync_router)
integration_router.include_router(credentials_router)
integration_router.include_router(permissions_router)
integration_router.include_router(audit_router)
integration_router.include_router(governance_router)

__all__ = ["integration_router"]
