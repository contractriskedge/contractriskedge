"""Standardized API response envelope.

All API responses should use these wrappers to ensure consistent
frontend parsing and error handling.

Usage:
    return success_response(data=result)
    return error_response(message="Not found", code="NOT_FOUND", status_code=404)
"""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class ApiMeta(BaseModel):
    page: Optional[int] = None
    page_size: Optional[int] = None
    total: Optional[int] = None
    total_pages: Optional[int] = None
    request_id: Optional[str] = None


class ApiError(BaseModel):
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"
    details: Optional[dict[str, Any]] = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    meta: Optional[ApiMeta] = None
    error: Optional[ApiError] = None


def success_response(
    data: Any = None,
    meta: Optional[ApiMeta] = None,
    status_code: int = 200,
) -> JSONResponse:
    """Return a standardized success response."""
    return JSONResponse(
        content=ApiResponse(success=True, data=data, meta=meta).model_dump(exclude_none=True),
        status_code=status_code,
    )


def error_response(
    message: str = "An unexpected error occurred",
    code: str = "INTERNAL_ERROR",
    status_code: int = 400,
    details: Optional[dict[str, Any]] = None,
) -> JSONResponse:
    """Return a standardized error response."""
    return JSONResponse(
        content=ApiResponse(
            success=False,
            error=ApiError(code=code, message=message, details=details),
        ).model_dump(exclude_none=True),
        status_code=status_code,
    )


def paginated_response(
    data: list[Any],
    total: int,
    page: int,
    page_size: int,
) -> JSONResponse:
    """Return a standardized paginated response."""
    return success_response(
        data=data,
        meta=ApiMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )
