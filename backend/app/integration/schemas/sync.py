"""Pydantic v2 schemas for sync job management."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SyncJobCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    sync_type: str = Field("full", description="full | delta")
    trigger: str = Field("manual", description="manual | scheduled | webhook | retry | system")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class SyncJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    integration_id: uuid.UUID
    tenant_id: uuid.UUID
    correlation_id: uuid.UUID
    status: str
    trigger: str
    sync_type: str
    total_items: Optional[int] = None
    synced_items: Optional[int] = None
    failed_items: Optional[int] = None
    skipped_items: Optional[int] = None
    bytes_transferred: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    cursor: Optional[str] = None
    delta_token: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    next_retry_at: Optional[datetime] = None
    result_summary: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class SyncJobListResponse(BaseModel):
    items: list[SyncJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SyncConflictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    sync_job_id: uuid.UUID
    external_id: str
    local_entity_id: Optional[str] = None
    conflict_type: str
    field: Optional[str] = None
    local_value: Optional[dict[str, Any]] = None
    external_value: Optional[dict[str, Any]] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class SyncRetryRequest(BaseModel):
    max_retries: Optional[int] = Field(None, ge=1, le=10)
    force: bool = Field(False, description="Force retry even if max retries reached")
