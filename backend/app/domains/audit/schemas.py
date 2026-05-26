"""Audit schemas — audit trail query and event models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class AuditEventItem(BaseModel):
    """A single audit event entry."""
    event_id: str
    event_type: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    actor_id: Optional[str] = None
    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime


class AuditQueryParams(BaseModel):
    """Parameters for querying audit events."""
    event_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    actor_id: Optional[str] = None
    action: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class AuditQueryResponse(BaseModel):
    """Paginated audit event list."""
    events: list[AuditEventItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditEventTypeCount(BaseModel):
    """Count of events by type."""
    event_type: str
    count: int


class AuditSummaryResponse(BaseModel):
    """Summary of audit activity."""
    total_events: int = 0
    events_by_type: list[AuditEventTypeCount] = Field(default_factory=list)
    unique_actors: int = 0
    unique_resources: int = 0
    period_days: int = 7
