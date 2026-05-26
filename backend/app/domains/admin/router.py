"""Admin API router — user management, roles, tenant settings, system health."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.admin.repository import AdminRepository
from app.domains.admin.service import AdminService
from app.domains.admin.schemas import (
    AdminUserCreate, AdminUserUpdate, AdminUserResponse,
    AdminRoleCreate, AdminRoleUpdate, AdminRoleResponse,
    TenantSettingsUpdate, TenantSettingsResponse,
    SystemHealthResponse
)

router = APIRouter(prefix="/admin", tags=["Admin"])


async def get_admin_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
) -> AdminService:
    return AdminService(
        repo=AdminRepository(db, tenant_id=tenant_id),
        tenant_id=tenant_id,
        user_id=user.id,
        session=db
)


# ── Users ────────────────────────────────────────────────────────


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    service: AdminService = Depends(get_admin_service),
    _: None = Depends(require_permission(Permissions.USERS_READ)),
):
    """List all users for the current tenant."""
    return await service.list_users(
)


@router.get("/users/{user_id}", response_model=AdminUserResponse
)
async def get_user(
    user_id: str,
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.USERS_READ)),
):
    """Get a specific user by ID."""
    user = await service.get_user(user_id
)
    if not user:
        raise HTTPException(status_code=404, detail="User not found"
)
    return user


@router.post("/users", response_model=AdminUserResponse
)
async def create_user(
    body: AdminUserCreate,
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.USERS_WRITE)),
):
    """Create/invite a new user."""
    return await service.create_user(body
)


@router.put("/users/{user_id}", response_model=AdminUserResponse
)
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.USERS_WRITE)),
):
    """Update a user's role, name, or status."""
    user = await service.update_user(user_id, body
)
    if not user:
        raise HTTPException(status_code=404, detail="User not found"
)
    return user


@router.delete("/users/{user_id}"
)
async def delete_user(
    user_id: str,
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.USERS_DELETE)),
):
    """Remove a user from the tenant."""
    deleted = await service.delete_user(user_id
)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found"
)
    return {"status": "deleted"}


# ── Roles ────────────────────────────────────────────────────────


@router.get("/roles", response_model=list[AdminRoleResponse]
)
async def list_roles(
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """List all available roles."""
    return await service.list_roles(
)


@router.post("/roles", response_model=AdminRoleResponse
)
async def create_role(
    body: AdminRoleCreate,
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Create a custom role with specific permissions."""
    return await service.create_role(body
)


@router.put("/roles/{role_id}", response_model=AdminRoleResponse
)
async def update_role(
    role_id: str,
    body: AdminRoleUpdate,
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Update a role's permissions."""
    role = await service.update_role(role_id, body
)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found"
)
    return role


@router.delete("/roles/{role_id}"
)
async def delete_role(
    role_id: str,
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Delete a custom role (system roles cannot be deleted
)."""
    try:
        deleted = await service.delete_role(role_id
)
        if not deleted:
            raise HTTPException(status_code=404, detail="Role not found"
)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)
)


# ── Tenant Settings ──────────────────────────────────────────────


@router.get("/settings", response_model=TenantSettingsResponse
)
async def get_settings(
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get tenant configuration settings."""
    return await service.get_settings(
)


@router.put("/settings", response_model=TenantSettingsResponse
)
async def update_settings(
    body: TenantSettingsUpdate,
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Update tenant configuration settings."""
    return await service.update_settings(body
)


# ── System Health ────────────────────────────────────────────────


@router.get("/health", response_model=SystemHealthResponse
)
async def get_system_health(
    service: AdminService = Depends(get_admin_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Get comprehensive system health status.

    Returns database, Redis, Celery, WebSocket, AI, and storage health.
    Requires admin:system permission.
    """
    return await service.get_system_health(
)
