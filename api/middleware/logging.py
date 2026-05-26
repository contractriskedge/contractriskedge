"""Request logging middleware for FastAPI.

Provides structured request/response logging with timing,
request ID tracking, and configurable log levels.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for structured request logging.

    Logs each request with a unique request ID, method, path,
    status code, duration, and user information. Adds the
    request ID to the response headers.
    """

    # Paths to exclude from logging (health checks, etc.)
    EXCLUDED_PATHS = {"/api/v1/health", "/favicon.ico"}

    def __init__(self, app: Any) -> None:
        """Initialize the logging middleware.

        Args:
            app: The ASGI application.
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process the request with structured logging.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with X-Request-ID header.
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Skip detailed logging for health checks
        is_excluded = request.url.path in self.EXCLUDED_PATHS

        start_time = time.time()

        # Log request
        if not is_excluded:
            user_info = ""
            user = getattr(request.state, "user", None)
            if user and hasattr(user, "sub"):
                user_info = f" user={user.sub}"
            tenant = getattr(request.state, "tenant_id", None)
            tenant_info = f" tenant={tenant}" if tenant else ""

            logger.info(
                "request_id=%s method=%s path=%s%s%s",
                request_id,
                request.method,
                request.url.path,
                user_info,
                tenant_info,
            )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration = time.time() - start_time
            logger.error(
                "request_id=%s method=%s path=%s duration_ms=%.0f error=%s",
                request_id,
                request.method,
                request.url.path,
                duration * 1000,
                str(exc),
            )
            raise

        duration = time.time() - start_time

        # Add request ID to response
        response.headers["X-Request-ID"] = request_id

        # Log response
        if not is_excluded:
            log_level = (
                logger.warning if response.status_code >= 400 else logger.info
            )
            log_level(
                "request_id=%s method=%s path=%s status=%d duration_ms=%.0f",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration * 1000,
            )

        return response
