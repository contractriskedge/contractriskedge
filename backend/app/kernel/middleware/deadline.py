"""Request deadline middleware with timeout and cancellation propagation.

Ensures every request has a bounded execution time. If the deadline
exceeds the configured timeout, the request is cancelled and a 503
is returned. This prevents resource exhaustion from slow clients.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings


class RequestDeadlineMiddleware(BaseHTTPMiddleware):
    """Enforces a maximum execution deadline on every request.

    If the request handler exceeds the deadline, the response is
    cancelled and a 503 Service Unavailable is returned. This
    prevents runaway requests from consuming worker threads.
    """

    def __init__(self, app, timeout_seconds: int = 30):
        super().__init__(app)
        self._timeout = timeout_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        deadline = time.monotonic() + self._timeout
        request.state.deadline = deadline
        request.state.request_timeout = self._timeout

        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self._timeout,
            )
            return response
        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - (deadline - self._timeout)) * 1000)
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "timeout",
                    "message": f"Request exceeded deadline of {self._timeout}s",
                    "elapsed_ms": elapsed,
                    "timeout_s": self._timeout,
                },
            )
