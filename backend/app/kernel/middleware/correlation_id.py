"""Correlation ID middleware — assigns and propagates correlation IDs.

Every request gets a correlation ID that propagates through:
  - API requests (via X-Correlation-ID header)
  - Background jobs (via Celery task context)
  - Workflow executions
  - AI analysis calls
  - Email notifications
  - DocuSign interactions
  - Audit events

One correlation ID traces an entire business transaction end-to-end.
"""

from __future__ import annotations

from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.kernel.telemetry.structured_logging import set_correlation_id, get_correlation_id


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Assigns and propagates correlation IDs across the request lifecycle.

    - If the client sends X-Correlation-ID, it is preserved.
    - Otherwise, a new UUID is generated.
    - The correlation ID is set in the contextvar for structured logging.
    - The correlation ID is added to the response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Accept correlation ID from client or generate new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        set_correlation_id(correlation_id)

        # Also set on request.state for downstream middleware/services
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
