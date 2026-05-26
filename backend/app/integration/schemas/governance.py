"""Pydantic v2 schemas for integration governance and compliance."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class IntegrationApprovalRequest(BaseModel):
    integration_id: uuid.UUID
    approved: bool = True
    approved_by: uuid.UUID
    approval_notes: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class IntegrationApprovalResponse(BaseModel):
    integration_id: uuid.UUID
    is_approved: bool
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    status: str


class TenantRestrictionConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    tenant_id: uuid.UUID
    allowed_providers: Optional[list[str]] = Field(
        None, description="List of allowed connector providers. None = all allowed."
    )
    blocked_providers: Optional[list[str]] = Field(
        default_factory=list, description="List of blocked connector providers."
    )
    max_integrations: Optional[int] = Field(
        None, ge=1, le=1000, description="Max integrations per tenant."
    )
    require_approval: bool = Field(
        True, description="Require admin approval for new integrations."
    )
    max_sync_frequency_minutes: Optional[int] = Field(
        None, ge=1, description="Minimum interval between syncs in minutes."
    )
    allowed_ip_ranges: Optional[list[str]] = Field(
        None, description="CIDR ranges allowed for webhook endpoints."
    )
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class ConnectorAccessPolicy(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    policy_id: Optional[uuid.UUID] = None
    tenant_id: uuid.UUID
    provider: str
    allowed_actions: list[str]
    denied_actions: list[str] = Field(default_factory=list)
    max_rate_per_minute: Optional[int] = Field(None, ge=1)
    require_audit: bool = True
    auto_disable_on_failure: bool = True
    max_consecutive_failures: int = Field(5, ge=1, le=100)
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)
