"""Audit response middleware — persist auth failures, permission denials, and server errors."""

from __future__ import annotations

import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.domains.audit.recorder import AuditRecorder

logger = logging.getLogger(__name__)

_AUDIT_STATUS_CODES = {401, 403, 500, 502, 503}


class AuditResponseMiddleware(BaseHTTPMiddleware):
    """Record security-relevant HTTP outcomes to the governance audit log."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        if response.status_code not in _AUDIT_STATUS_CODES:
            return response
        if request.url.path.startswith("/api/v1/health"):
            return response

        try:
            await self._record(request, response.status_code)
        except Exception as exc:
            logger.debug("Audit response middleware skipped: %s", exc)
        return response

    async def _record(self, request: Request, status_code: int) -> None:
        tenant_id = self._resolve_tenant_id(request)
        if not tenant_id:
            return

        factory = getattr(request.app.state, "db_factory", None)
        if factory is None:
            return

        user = getattr(request.state, "user", None)
        actor_id = getattr(user, "id", None) or "anonymous"
        actor_role = getattr(user, "role", None)
        request_id = getattr(request.state, "request_id", None)
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        if status_code == 401:
            event_type = "auth.login.failure"
            status = "failure"
            severity = "medium"
            description = f"Authentication failed: {request.method} {request.url.path}"
        elif status_code == 403:
            event_type = "auth.permission.denied"
            status = "blocked"
            severity = "high"
            description = f"Permission denied: {request.method} {request.url.path}"
        else:
            event_type = "api.error"
            status = "failure"
            severity = "critical"
            description = f"Server error {status_code}: {request.method} {request.url.path}"

        session = await factory.create_session(
            tenant_id=tenant_id,
            user_id=actor_id,
            user_role=actor_role or "viewer",
        )
        try:
            recorder = AuditRecorder(session, tenant_id)
            await recorder.record(
                event_type=event_type,
                actor_id=actor_id,
                actor_role=actor_role,
                description=description,
                status=status,
                severity=severity,
                correlation_id=request_id,
                request_id=request_id,
                source="http_middleware",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=description,
                metadata={"http_status": status_code, "path": request.url.path, "method": request.method},
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @staticmethod
    def _resolve_tenant_id(request: Request) -> Optional[str]:
        user = getattr(request.state, "user", None)
        if user and getattr(user, "tenant_id", None):
            return str(user.tenant_id)
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            return str(tenant_id)
        if settings.environment == "development":
            return settings.dev_tenant_id
        return None
