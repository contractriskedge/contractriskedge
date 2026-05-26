"""Pydantic models for user and tenant entities.

Defines the data structures for authenticated users, user
sessions, and multi-tenant organization management.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """User role within a tenant."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API = "api"


class Tenant(BaseModel):
    """Multi-tenant organization model."""

    tenant_id: str = Field(..., description="Unique tenant identifier")
    name: str = Field(..., description="Organization name")
    domain: Optional[str] = Field(None, description="Organization domain")
    plan: str = Field(default="starter", description="Subscription plan")
    is_active: bool = Field(default=True, description="Whether tenant is active")
    max_users: int = Field(default=10, ge=1, description="Maximum number of users")
    max_documents: int = Field(
        default=1000, ge=1, description="Maximum document storage"
    )
    features: List[str] = Field(
        default_factory=list, description="Enabled feature flags"
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Tenant-specific settings"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(BaseModel):
    """User model with profile and role information."""

    user_id: str = Field(..., description="Unique user identifier (Auth0 sub)")
    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="Display name")
    tenant_id: str = Field(..., description="Primary tenant identifier")
    role: UserRole = Field(default=UserRole.VIEWER, description="User role")
    is_active: bool = Field(default=True, description="Whether user is active")
    permissions: List[str] = Field(
        default_factory=list, description="Granular permissions"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="User metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(None, description="Last login time")


class UserSession(BaseModel):
    """Active user session information."""

    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    token_jti: str = Field(..., description="JWT token ID")
    expires_at: datetime = Field(..., description="Session expiry time")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, description="Whether session is active")
