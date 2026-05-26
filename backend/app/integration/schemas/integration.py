"""Pydantic v2 schemas for Integration management APIs."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., description="Connector provider name")
    integration_type: str = Field(..., description="oauth2 | api_key | webhook | basic_auth")
    description: Optional[str] = Field(None, max_length=2000)
    config: Optional[dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)
    scopes: Optional[list[str]] = Field(default_factory=list)
    webhook_url: Optional[str] = Field(None, max_length=1024)
    rate_limit_max: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_window_seconds: Optional[int] = Field(None, ge=1, le=86400)
    organization_id: Optional[uuid.UUID] = None


class IntegrationUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    config: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    scopes: Optional[list[str]] = None
    webhook_url: Optional[str] = Field(None, max_length=1024)
    rate_limit_max: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_window_seconds: Optional[int] = Field(None, ge=1, le=86400)


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    name: str
    provider: str
    integration_type: str
    status: str
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    scopes: Optional[list[str]] = None
    webhook_url: Optional[str] = None
    is_approved: bool
    rate_limit_max: Optional[int] = None
    rate_limit_window_seconds: Optional[int] = None
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    error_message: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class IntegrationListResponse(BaseModel):
    items: list[IntegrationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class IntegrationStatusUpdate(BaseModel):
    status: str = Field(..., description="active | disabled | revoked")
    reason: Optional[str] = Field(None, max_length=1000)


class IntegrationApproveRequest(BaseModel):
    approved: bool = True
    approval_notes: Optional[str] = Field(None, max_length=2000)
