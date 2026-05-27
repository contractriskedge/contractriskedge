"""Auth middleware — validates JWT on every request (except excluded paths)."""

from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.kernel.dev_context import dev_tenant_id, dev_user_id
from app.kernel.security.auth import JWTValidator, TokenValidationError, UserContext
from app.kernel.security.events import (
    log_security_event,
    SecurityEventType,
    SecurityEventSeverity,
)
from app.kernel.security.permissions import Permissions
from app.kernel.middleware.excluded_paths import is_path_excluded

logger = logging.getLogger(__name__)


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Validates JWT on every request (except excluded paths).

    Sets request.state.user with the validated UserContext.
    Logs security events for auth failures.
    """

    def __init__(self, app):
        super().__init__(app)
        self.validator = JWTValidator(
            domain=settings.auth0_domain,
            audience=settings.auth0_audience,
            issuer=settings.auth0_issuer or f"https://{settings.auth0_domain}/",
            dev_secret=settings.dev_jwt_secret,
            environment=settings.environment,
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if is_path_excluded(request.url.path) or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        request_id = getattr(request.state, "request_id", "")

        # ── Determine if auth bypass is allowed ──────────────────────
        # Bypass is ONLY permitted when ALL of the following are true:
        #   1. environment == "development"
        #   2. dev_auth_bypass config flag is explicitly set to true
        #   3. The host is localhost (not a deployed staging/production URL)
        #
        # This triple gate prevents accidental bypass in deployed environments
        # even if the .env file is misconfigured.
        _is_local_dev = settings.environment == "development" and settings.dev_auth_bypass
        _host = request.url.hostname or ""
        _bypass_allowed = _is_local_dev and _host in ("localhost", "127.0.0.1", "0.0.0.0")

        # Development-only: act as a scoped dev user when no Bearer token is sent.
        # Never enable outside local dev — send a real JWT to test auth in any other environment.
        # NOTE: Dev bypass uses a restricted role (not admin) to prevent automation
        # actions from accidentally succeeding without real auth validation.
        if (
            _bypass_allowed
            and not auth_header.startswith("Bearer ")
        ):
            from app.kernel.security.roles import Roles
            request.state.user = UserContext(
                id=dev_user_id(),
                email="dev@localhost",
                tenant_id=dev_tenant_id(),
                role=Roles.DEVELOPER,
                permissions=list(Roles._PERMISSIONS.get(Roles.DEVELOPER, set())),
            )
            logger.debug("DEV auth bypass (no token): %s %s", request.method, request.url.path)
            return await call_next(request)

        if not auth_header.startswith("Bearer "):
            log_security_event(
                SecurityEventType.AUTH_FAILURE,
                severity=SecurityEventSeverity.INFO,
                message="Missing Bearer token",
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
            )
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "Missing Bearer token"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            user = await self.validator.validate(token)
        except TokenValidationError as exc:
            # Stale/invalid localStorage tokens are common in dev — fall back to dev user.
            # This fallback is ONLY active in local development with bypass enabled.
            # NOTE: Uses restricted DEVELOPER role, NOT admin, to prevent automation
            # actions from accidentally succeeding without real auth validation.
            if _bypass_allowed:
                logger.warning(
                    "DEV auth bypass (invalid token): %s for %s %s",
                    exc,
                    request.method,
                    request.url.path,
                )
                from app.kernel.security.roles import Roles
                request.state.user = UserContext(
                    id=dev_user_id(),
                    email="dev@localhost",
                    tenant_id=dev_tenant_id(),
                    role=Roles.DEVELOPER,
                    permissions=list(Roles._PERMISSIONS.get(Roles.DEVELOPER, set())),
                )
                return await call_next(request)

            error_str = str(exc)
            if "expired" in error_str.lower():
                event_type = SecurityEventType.TOKEN_EXPIRED
            else:
                event_type = SecurityEventType.TOKEN_INVALID

            log_security_event(
                event_type,
                severity=SecurityEventSeverity.WARNING,
                message=error_str,
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
                details={"error": error_str},
            )
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": error_str},
            )

        # Resolve server-side permissions from role (supplements JWT permissions)
        from app.kernel.security.roles import resolve_permissions
        user.permissions = resolve_permissions(user)

        request.state.user = user
        return await call_next(request)
