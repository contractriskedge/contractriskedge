"""Tenant context middleware.

CRITICAL: Tenant ID comes EXCLUSIVELY from the JWT token.
The X-Tenant-ID header is NEVER trusted from clients.
"""

from __future__ import annotations

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.kernel.security.events import (
    log_security_event,
    SecurityEventType,
    SecurityEventSeverity,
)
from app.kernel.middleware.excluded_paths import is_path_excluded


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Resolves tenant ID from JWT and sets it on request.state.

    Tenant ID comes from the validated JWT token ONLY.
    X-Tenant-ID header is accepted ONLY for users with admin:system permission
    (platform support debugging), and the override is audit-logged.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for excluded paths (docs, health, etc.)
        if is_path_excluded(request.url.path) or request.method == "OPTIONS":
            return await call_next(request)

        user = getattr(request.state, "user", None)
        request_id = getattr(request.state, "request_id", "")

        if not user or not user.tenant_id:
            log_security_event(
                SecurityEventType.RLS_CONTEXT_MISSING,
                severity=SecurityEventSeverity.ERROR,
                message="Tenant context missing from JWT token",
                actor_id=user.id if user else None,
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthorized",
                    "message": "Tenant context not found in authentication token.",
                },
            )

        # Default: tenant from JWT. Never from client headers.
        tenant_id = user.tenant_id

        # Admin override: ONLY for users with admin:system permission
        header_tenant = request.headers.get("X-Tenant-ID")
        if header_tenant and header_tenant != user.tenant_id:
            if "admin:system" not in user.permissions:
                log_security_event(
                    SecurityEventType.TENANT_ACCESS_DENIED,
                    severity=SecurityEventSeverity.WARNING,
                    message="X-Tenant-ID override attempted without admin:system permission",
                    actor_id=user.id,
                    tenant_id=user.tenant_id,
                    request_id=request_id,
                    details={
                        "requested_tenant": header_tenant,
                        "user_tenant": user.tenant_id,
                    },
                )
                raise HTTPException(
                    status_code=403,
                    detail="X-Tenant-ID override requires admin:system permission",
                )
            log_security_event(
                SecurityEventType.ADMIN_OVERRIDE,
                severity=SecurityEventSeverity.WARNING,
                message=f"Admin tenant override: {user.tenant_id} -> {header_tenant}",
                actor_id=user.id,
                tenant_id=user.tenant_id,
                request_id=request_id,
                details={
                    "original_tenant": user.tenant_id,
                    "override_tenant": header_tenant,
                    "path": request.url.path,
                },
            )
            tenant_id = header_tenant

        request.state.tenant_id = tenant_id
        return await call_next(request)
