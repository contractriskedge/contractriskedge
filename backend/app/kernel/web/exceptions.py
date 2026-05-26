"""Domain exception hierarchy with structured error codes.

All domain-specific exceptions should extend AppError.
FastAPI error handlers convert these to standardized JSON responses
with error_code for programmatic handling.

Usage:
    raise NotFoundError(error_code=ErrorCode.REVIEW_NOT_FOUND)
    raise AppError(error_code=ErrorCode.OCR_FAILURE, message="Custom message")
"""

from __future__ import annotations

from typing import Optional

from app.kernel.web.error_codes import ErrorCode, get_error_info, make_error_response


class AppError(Exception):
    """Base application error with structured error code support.

    Attributes:
        status_code: HTTP status code (default 500)
        code: Legacy string code (default "internal_error")
        error_code: Structured ErrorCode enum value
        message: Human-readable error message
        details: Optional additional error context
    """
    status_code: int = 500
    code: str = "internal_error"
    error_code: Optional[ErrorCode] = None
    message: str = "Internal server error"
    details: Optional[dict] = None

    def __init__(self, error_code: Optional[ErrorCode] = None,
                 message: Optional[str] = None,
                 details: Optional[dict] = None,
                 status_code: Optional[int] = None):
        # Legacy: raise NotFoundError("human-readable message")
        if isinstance(error_code, str) and message is None:
            try:
                error_code = ErrorCode(error_code)
            except ValueError:
                message = error_code
                error_code = None

        if error_code:
            self.error_code = error_code
            info = get_error_info(error_code)
            self.status_code = status_code or info["status_code"]
            self.code = info["error_code"]
            self.message = message or info["message"]
        else:
            self.message = message or self.message
            if status_code:
                self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert to standardized error response dict."""
        if self.error_code:
            return make_error_response(
                self.error_code,
                message=self.message,
                details=self.details,
            )
        return {
            "error_code": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "category": "unknown",
            "retryable": False,
            "details": self.details,
        }


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"

    def __init__(self, error_code: Optional[ErrorCode] = None,
                 message: Optional[str] = None,
                 details: Optional[dict] = None):
        super().__init__(
            error_code=error_code or ErrorCode.ENTITY_NOT_FOUND,
            message=message,
            details=details,
        )


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"

    def __init__(self, error_code: Optional[ErrorCode] = None,
                 message: Optional[str] = None,
                 details: Optional[dict] = None):
        super().__init__(
            error_code=error_code or ErrorCode.VALIDATION_FAILURE,
            message=message,
            details=details,
        )


class AuthorizationError(AppError):
    status_code = 403
    code = "forbidden"

    def __init__(self, error_code: Optional[ErrorCode] = None,
                 message: Optional[str] = None,
                 details: Optional[dict] = None):
        super().__init__(
            error_code=error_code or ErrorCode.UNAUTHORIZED,
            message=message,
            details=details,
        )


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthorized"

    def __init__(self, error_code: Optional[ErrorCode] = None,
                 message: Optional[str] = None,
                 details: Optional[dict] = None):
        super().__init__(
            error_code=error_code or ErrorCode.UNAUTHENTICATED,
            message=message,
            details=details,
        )


class ConflictError(AppError):
    status_code = 409
    code = "conflict"

    def __init__(self, error_code: Optional[ErrorCode] = None,
                 message: Optional[str] = None,
                 details: Optional[dict] = None):
        super().__init__(
            error_code=error_code or ErrorCode.DUPLICATE_ENTITY,
            message=message,
            details=details,
        )


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limit_exceeded"

    def __init__(self, error_code: Optional[ErrorCode] = None,
                 message: Optional[str] = None,
                 details: Optional[dict] = None):
        super().__init__(
            error_code=error_code or ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details,
        )


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"

    def __init__(self, error_code: Optional[ErrorCode] = None,
                 message: Optional[str] = None,
                 details: Optional[dict] = None):
        super().__init__(
            error_code=error_code or ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            details=details,
        )
