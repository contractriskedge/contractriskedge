"""Admin domain Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Users ────────────────────────────────────────────────────────

class AdminUserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    name: Optional[str] = None
    role: str = Field(default="viewer", pattern="^(admin|legal_ops|reviewer|compliance|executive|viewer|ai_ops)$")
    business_unit: Optional[str] = None


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|legal_ops|reviewer|compliance|executive|viewer|ai_ops)$")
    business_unit: Optional[str] = None
    is_active: Optional[bool] = None


class AdminUserResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    role: str
    business_unit: Optional[str] = None
    is_active: bool
    is_invited: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ── Roles ─────────────────────────────────────────────────────────

class AdminRoleCreate(BaseModel):
    role_id: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class AdminRoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[list[str]] = None


class AdminRoleResponse(BaseModel):
    role_id: str
    name: str
    description: Optional[str] = None
    permissions: list[str]
    is_system: bool
    created_at: datetime


# ── Tenant Settings ──────────────────────────────────────────────

class TenantSettingsUpdate(BaseModel):
    brand_name: Optional[str] = None
    brand_logo_url: Optional[str] = None
    brand_primary_color: Optional[str] = None
    brand_accent_color: Optional[str] = None
    ai_model: Optional[str] = None
    ai_temperature: Optional[int] = Field(None, ge=0, le=100)
    ai_max_tokens: Optional[int] = Field(None, ge=256, le=128000)
    risk_threshold_critical: Optional[int] = Field(None, ge=0, le=100)
    risk_threshold_high: Optional[int] = Field(None, ge=0, le=100)
    risk_threshold_medium: Optional[int] = Field(None, ge=0, le=100)
    sla_critical_hours: Optional[int] = Field(None, ge=1)
    sla_high_hours: Optional[int] = Field(None, ge=1)
    sla_medium_hours: Optional[int] = Field(None, ge=1)
    sla_low_hours: Optional[int] = Field(None, ge=1)
    features_enabled: Optional[dict] = None


class TenantSettingsResponse(BaseModel):
    brand_name: Optional[str] = None
    brand_logo_url: Optional[str] = None
    brand_primary_color: Optional[str] = "#1B3A6B"
    brand_accent_color: Optional[str] = "#C9A84C"
    ai_model: str = "gpt-4o"
    ai_temperature: int = 10
    ai_max_tokens: int = 4096
    ai_embedding_model: str = "text-embedding-3-small"
    ai_token_budget_daily: int = 1000000
    ai_token_budget_monthly: int = 30000000
    risk_threshold_critical: int = 70
    risk_threshold_high: int = 50
    risk_threshold_medium: int = 30
    sla_critical_hours: int = 24
    sla_high_hours: int = 48
    sla_medium_hours: int = 72
    sla_low_hours: int = 168
    default_notification_channel: str = "in_app"
    features_enabled: dict = Field(default_factory=lambda: {
        "ai_analysis": True,
        "redlines": True,
        "semantic_search": True,
        "bulk_operations": True,
        "exports": True,
        "notifications": True,
        "automation": False,
    })
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── System Health ────────────────────────────────────────────────

class SystemHealthResponse(BaseModel):
    """Comprehensive system health status for the admin console."""
    status: str = "healthy"  # healthy, degraded, unhealthy
    database: dict = Field(default_factory=lambda: {"connected": True, "pool_size": 0, "active_connections": 0})
    redis: dict = Field(default_factory=lambda: {"connected": False, "queue_depth": 0, "memory_used_mb": 0})
    celery: dict = Field(default_factory=lambda: {"worker_count": 0, "active_tasks": 0, "queue_sizes": {}})
    websocket: dict = Field(default_factory=lambda: {"active_connections": 0, "messages_sent": 0})
    ai: dict = Field(default_factory=lambda: {"model": "gpt-4o", "avg_latency_ms": 0, "failures_24h": 0, "tokens_24h": 0, "cost_24h": 0})
    storage: dict = Field(default_factory=lambda: {"total_documents": 0, "total_chunks": 0, "storage_bytes": 0})
    uptime_seconds: float = 0
