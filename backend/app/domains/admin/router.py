"""Admin API router — user management, roles, tenant settings, system health, diagnostics."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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
    SystemHealthResponse,
    DiagnosticsResponse,
    EventChainResponse,
    OutboxDiagnosticsResponse,
    WorkerDiagnosticsResponse,
)
from app.kernel.telemetry.diagnostics import diagnostics_service

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


# ── Diagnostics ─────────────────────────────────────────────────


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def get_diagnostics(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Get aggregate system diagnostics for the observability dashboard.

    Returns live Prometheus metric snapshots, WebSocket health,
    reconnect storm status, and database diagnostics.
    """
    from app import main

    db_factory = getattr(main.app.state, "db_factory", None)
    return await diagnostics_service.get_system_diagnostics(db_factory=db_factory)


@router.get("/diagnostics/events", response_model=list[EventChainResponse])
async def get_event_chain(
    correlation_id: str = Query(..., description="Correlation ID to trace"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Get the full event chain for a correlation ID.

    Traces all outbox events sharing the correlation_id, ordered by
    sequence_id. Used by the correlation timeline viewer.
    """
    return await diagnostics_service.get_event_chain(db, correlation_id)


@router.get("/diagnostics/outbox", response_model=OutboxDiagnosticsResponse)
async def get_outbox_diagnostics(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    state: Optional[str] = Query(None, description="Filter by delivery state"),
    limit: int = Query(50, description="Max events to return"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Get outbox diagnostics for the audit explorer.

    Returns counts by delivery state, recent events, and dead-letter details.
    """
    return await diagnostics_service.get_outbox_diagnostics(
        db, tenant_id=tenant_id, state_filter=state, limit=limit,
    )


@router.get("/diagnostics/workers", response_model=WorkerDiagnosticsResponse)
async def get_worker_diagnostics(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Get worker diagnostics — heartbeats, queue depths, stuck jobs.

    Returns active workers by queue, queue depths from Redis,
    recent stuck job counts, and worker heartbeat freshness.
    """
    return await diagnostics_service.get_worker_diagnostics(db)


# ── Worker Heartbeat ────────────────────────────────────────────


class HeartbeatRequest(BaseModel):
    """Worker heartbeat request payload."""
    worker_id: str
    queue: str
    status: str = "active"
    tasks_completed: int = 0
    tasks_failed: int = 0


@router.post("/workers/heartbeat")
async def worker_heartbeat(
    body: HeartbeatRequest,
    service: AdminService = Depends(get_admin_service),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Record a worker heartbeat (called periodically by workers).

    This endpoint is intentionally low-auth (requires any valid
    API token) so workers can report without full admin privileges.
    """
    return await service.record_heartbeat(
        worker_id=body.worker_id,
        queue=body.queue,
        status=body.status,
        tasks_completed=body.tasks_completed,
        tasks_failed=body.tasks_failed,
    )
