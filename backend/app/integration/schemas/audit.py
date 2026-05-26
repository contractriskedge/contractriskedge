"""Pydantic v2 schemas for integration audit events."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    integration_id: Optional[uuid.UUID] = None
    tenant_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor_type: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    previous_state: Optional[dict[str, Any]] = None
    new_state: Optional[dict[str, Any]] = None
    change_summary: Optional[str] = None
    correlation_id: Optional[uuid.UUID] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    occurred_at: datetime
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
