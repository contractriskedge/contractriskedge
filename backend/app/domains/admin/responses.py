"""Standard admin API response envelope.

Endpoints currently return bare lists/objects for frontend compatibility.
Use these types for new endpoints and when migrating the admin console client.
"""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class AdminMeta(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    filters: dict[str, Any] = Field(default_factory=dict)


class AdminApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: AdminMeta = Field(default_factory=AdminMeta)
    error: Optional[str] = None


def admin_ok(data: T, *, total: Optional[int] = None, page: int = 1, page_size: int = 20) -> AdminApiResponse[T]:
    """Build a successful admin envelope."""
    meta = AdminMeta(page=page, page_size=page_size)
    if total is not None:
        meta.total = total
    elif isinstance(data, list):
        meta.total = len(data)
    return AdminApiResponse(success=True, data=data, meta=meta, error=None)
