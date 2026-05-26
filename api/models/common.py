"""Common Pydantic models shared across the API.

Provides base response schemas, pagination models, error
responses, and version information.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiVersion(BaseModel):
    """API version information."""

    version: str = Field(..., description="API version string")
    release_date: Optional[str] = Field(None, description="Release date")
    deprecation_date: Optional[str] = Field(None, description="Deprecation date")
    sunset_date: Optional[str] = Field(None, description="Sunset/removal date")


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall status (healthy/unhealthy)")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., ge=0, description="Uptime in seconds")
    environment: str = Field(..., description="Deployment environment")
    database: str = Field(..., description="Database connection status")
    redis: str = Field(..., description="Redis connection status")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error code/type")
    message: str = Field(..., description="Human-readable error message")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    results: List[T] = Field(..., description="List of items")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=200, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class SortParams(BaseModel):
    """Sort parameters for list endpoints."""

    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort direction"
    )


class DateRange(BaseModel):
    """Date range filter."""

    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
