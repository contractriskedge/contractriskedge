"""Pydantic v2 schemas for connector permission management."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PermissionCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    role_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    integration_id: Optional[uuid.UUID] = None
    provider: Optional[str] = Field(None, max_length=100)
    action: str = Field(..., description="create | read | update | delete | sync | admin | approve | disable | manage_credentials | view_audit")
    effect: str = Field("allow", description="allow | deny")
    resource_type: Optional[str] = Field(None, max_length=100)
    conditions: Optional[dict[str, Any]] = Field(default_factory=dict)
    priority: int = Field(0, ge=0, le=1000)
    expires_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    role_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    integration_id: Optional[uuid.UUID] = None
    provider: Optional[str] = None
    action: str
    effect: str
    resource_type: Optional[str] = None
    conditions: Optional[dict[str, Any]] = None
    priority: int
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PermissionListResponse(BaseModel):
    items: list[PermissionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PermissionEvaluateRequest(BaseModel):
    user_id: uuid.UUID
    integration_id: Optional[uuid.UUID] = None
    provider: Optional[str] = None
    action: str
    resource_type: Optional[str] = None


class PermissionEvaluateResult(BaseModel):
    allowed: bool
    effect: Optional[str] = None
    matched_permission_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
