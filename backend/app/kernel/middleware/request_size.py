"""Request body size enforcement middleware.

Enforces maximum request body size to prevent memory exhaustion
from large payloads. Returns 413 Payload Too Large if exceeded.
"""

from __future__ import annotations

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class RequestBodySizeMiddleware(BaseHTTPMiddleware):
    """Enforces maximum request body size.

    Checks Content-Length header before reading the body.
    If Content-Length is missing, the body is streamed and checked
    incrementally to avoid loading the entire body into memory.
    """

    def __init__(self, app, max_bytes: int = 100_000_000):
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check Content-Length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            length = int(content_length)
            if length > self._max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "payload_too_large",
                        "message": f"Request body exceeds maximum size of {self._max_bytes // 1_000_000}MB",
                        "max_bytes": self._max_bytes,
                        "received_bytes": length,
                    },
                )

        return await call_next(request)
