"""Admin domain models — users, roles, permissions, tenant settings."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.kernel.database.base import Base


class AdminUser(Base):
    """Platform user with role assignments and account status."""
    __tablename__ = "admin_users"

    user_id = Column(Text, primary_key=True)  # Maps to auth provider user ID
    tenant_id = Column(UUID, nullable=False, index=True)
    email = Column(Text, nullable=False)
    name = Column(Text, nullable=True)
    role = Column(Text, nullable=False, default="viewer")  # admin, legal_ops, reviewer, compliance, executive, viewer, ai_ops
    business_unit = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_invited = Column(Boolean, nullable=False, default=False)
    invited_by = Column(Text, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    preferences = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AdminRole(Base):
    """Predefined roles with associated permissions."""
    __tablename__ = "admin_roles"

    role_id = Column(Text, primary_key=True)  # admin, legal_ops, reviewer, etc.
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSONB, nullable=False, default=list)  # List of permission strings
    is_system = Column(Boolean, nullable=False, default=False)  # System roles cannot be deleted
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TenantSettings(Base):
    """Per-tenant configuration for branding, AI, notifications, etc."""
    __tablename__ = "tenant_settings"

    settings_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, unique=True, index=True)

    # Branding
    brand_name = Column(Text, nullable=True)
    brand_logo_url = Column(Text, nullable=True)
    brand_primary_color = Column(Text, nullable=True, default="#1B3A6B")
    brand_accent_color = Column(Text, nullable=True, default="#C9A84C")

    # AI Configuration
    ai_model = Column(Text, nullable=True, default="gpt-4o")
    ai_temperature = Column(Integer, nullable=True, default=10)  # 0-100
    ai_max_tokens = Column(Integer, nullable=True, default=4096)
    ai_embedding_model = Column(Text, nullable=True, default="text-embedding-3-small")
    ai_token_budget_daily = Column(Integer, nullable=True, default=1000000)
    ai_token_budget_monthly = Column(Integer, nullable=True, default=30000000)

    # Risk Thresholds
    risk_threshold_critical = Column(Integer, nullable=True, default=70)  # >= 70% = critical
    risk_threshold_high = Column(Integer, nullable=True, default=50)       # >= 50% = high
    risk_threshold_medium = Column(Integer, nullable=True, default=30)     # >= 30% = medium

    # SLA Configuration (hours)
    sla_critical_hours = Column(Integer, nullable=True, default=24)
    sla_high_hours = Column(Integer, nullable=True, default=48)
    sla_medium_hours = Column(Integer, nullable=True, default=72)
    sla_low_hours = Column(Integer, nullable=True, default=168)  # 7 days

    # Notification Defaults
    default_notification_channel = Column(Text, nullable=True, default="in_app")
    digest_frequency = Column(Text, nullable=True, default="instant")

    # Data Retention
    retention_days = Column(Integer, nullable=True, default=365)
    audit_retention_days = Column(Integer, nullable=True, default=730)

    # Features
    features_enabled = Column(JSONB, nullable=False, default=lambda: {
        "ai_analysis": True,
        "redlines": True,
        "semantic_search": True,
        "bulk_operations": True,
        "exports": True,
        "notifications": True,
        "automation": False,
    })

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
