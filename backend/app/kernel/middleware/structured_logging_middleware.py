"""Enhanced structured logging middleware — replaces old LoggingMiddleware.

Logs every request/response with full structured context:
  - timestamp, method, path, status, duration_ms
  - correlation_id, tenant_id, user_id, request_id
  - module, action, outcome
  - error details on failure
"""

from __future__ import annotations

import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.kernel.telemetry.structured_logging import (
    get_logger,
    get_correlation_id,
    get_tenant_id,
    get_user_id,
    get_request_id,
    set_tenant_id,
    set_user_id,
    set_request_id,
)

logger = get_logger("http.api")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Logs structured request/response records with full observability context."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.time()

        # Sync contextvars from request.state (set by earlier middleware)
        if hasattr(request.state, "correlation_id"):
            from app.kernel.telemetry.structured_logging import set_correlation_id
            set_correlation_id(request.state.correlation_id)
        if hasattr(request.state, "tenant_id"):
            set_tenant_id(request.state.tenant_id)
        if hasattr(request.state, "user_id"):
            set_user_id(request.state.user_id)
        if hasattr(request.state, "request_id"):
            set_request_id(request.state.request_id)

        # Extract tenant/user from state if available
        tenant_id = getattr(request.state, "tenant_id", None) or get_tenant_id() or ""
        user_id = getattr(request.state, "user_id", None) or get_user_id() or ""
        correlation_id = getattr(request.state, "correlation_id", None) or get_correlation_id() or ""
        request_id = getattr(request.state, "request_id", None) or get_request_id() or ""

        # Determine action from path
        action = f"{request.method} {request.url.path}"

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start) * 1000

            outcome = "success" if response.status_code < 400 else "error" if response.status_code >= 500 else "warning"

            logger.info(
                "Request completed",
                action=action,
                outcome=outcome,
                duration_ms=duration_ms,
                tenant_id=tenant_id,
                user_id=user_id,
                correlation_id=correlation_id,
                request_id=request_id,
                status=response.status_code,
                method=request.method,
                path=request.url.path,
            )
            return response

        except Exception as exc:
            duration_ms = (time.time() - start) * 1000
            logger.error(
                "Request failed",
                action=action,
                outcome="error",
                duration_ms=duration_ms,
                tenant_id=tenant_id,
                user_id=user_id,
                correlation_id=correlation_id,
                request_id=request_id,
                error=str(exc),
                method=request.method,
                path=request.url.path,
            )
            raise
