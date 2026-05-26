"""Pydantic v2 schemas for credential and OAuth management."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CredentialCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    credential_type: str = Field(..., description="oauth2 | api_key | basic_auth | bearer_token | custom")
    encrypted_api_key: Optional[str] = None
    encrypted_client_secret: Optional[str] = None
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class CredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    integration_id: uuid.UUID
    credential_type: str
    oauth_provider: Optional[str] = None
    oauth_scopes: Optional[list[str]] = None
    oauth_access_token_expires_at: Optional[datetime] = None
    oauth_refresh_token_expires_at: Optional[datetime] = None
    is_expired: bool
    is_revoked: bool
    rotation_count: int
    last_rotated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    version: int
    created_at: datetime
    updated_at: datetime

    # NEVER expose tokens in responses


class OAuthCallbackRequest(BaseModel):
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="CSRF state token")
    redirect_uri: Optional[str] = Field(None, max_length=1024)


class TokenRefreshRequest(BaseModel):
    integration_id: uuid.UUID
    force: bool = Field(False, description="Force refresh even if token is still valid")
