"""Pydantic v2 schemas for webhook and webhook event management."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    provider: str = Field(..., max_length=100)
    webhook_id: str = Field(..., max_length=255)
    secret: Optional[str] = None
    signature_header: Optional[str] = Field(None, max_length=255)
    verification_token: Optional[str] = Field(None, max_length=512)
    events_subscribed: Optional[list[str]] = Field(default_factory=list)
    endpoint_url: Optional[str] = Field(None, max_length=1024)
    api_version: Optional[str] = Field(None, max_length=50)
    allowed_ips: Optional[list[str]] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    integration_id: uuid.UUID
    tenant_id: uuid.UUID
    provider: str
    webhook_id: str
    status: str
    events_subscribed: Optional[list[str]] = None
    endpoint_url: Optional[str] = None
    api_version: Optional[str] = None
    require_signature: bool
    last_event_at: Optional[datetime] = None
    event_count: int
    failure_count: int
    created_at: datetime
    updated_at: datetime


class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    webhook_id: uuid.UUID
    integration_id: uuid.UUID
    tenant_id: uuid.UUID
    idempotency_key: str
    event_id: str
    event_type: str
    parsed_payload: Optional[dict[str, Any]] = None
    status: str
    processing_attempts: int
    max_retries: int
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None
    received_at: datetime
    timestamp: Optional[datetime] = None
    correlation_id: Optional[uuid.UUID] = None
    source_ip: Optional[str] = None
    signature_valid: Optional[bool] = None
    processed_at: Optional[datetime] = None
    created_at: datetime


class WebhookEventListResponse(BaseModel):
    items: list[WebhookEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class WebhookVerificationResult(BaseModel):
    verified: bool
    signature_valid: Optional[bool] = None
    timestamp_valid: Optional[bool] = None
    replay_detected: bool = False
    reason: Optional[str] = None
