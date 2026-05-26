"""Kernel-level ORM models shared across domains (e.g., Tenant)."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


class Tenant(Base):
    """Multi-tenant root entity — every domain model references this via FK."""
    __tablename__ = "tenants"

    tenant_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    domain = Column(Text, nullable=True)
    plan = Column(Text, nullable=False, default="starter")
    is_active = Column(Boolean, nullable=False, default=True)
    max_users = Column(Integer, nullable=False, default=10)
    max_documents = Column(Integer, nullable=False, default=1000)
    features = Column(ARRAY(Text), nullable=False, default=[])
    settings = Column(JSONB, nullable=False, default=dict)
    created_at = Column(Text, server_default=func.now(), nullable=False)
    updated_at = Column(Text, server_default=func.now(), nullable=False)
