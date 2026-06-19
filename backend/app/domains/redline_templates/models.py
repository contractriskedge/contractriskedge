"""RedlineTemplate ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, Text, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RedlineTemplate(Base):
    __tablename__ = "redline_templates"

    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    clause_type = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    industry = Column(Text, nullable=True)
    language = Column(Text, nullable=False, default="en")
    risk_level = Column(Text, nullable=True)
    template_text = Column(Text, nullable=False)
    variables = Column(JSONB, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(Text, nullable=False, default="active")
    playbook_id = Column(UUID(as_uuid=True), ForeignKey("clause_standards.clause_id", ondelete="SET NULL"), nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    accept_rate = Column(Float, nullable=False, default=0.0)
    created_by = Column(Text, nullable=True)
    approved_by = Column(Text, nullable=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    retired_date = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)

    __table_args__ = (
        Index("ix_redline_templates_tenant_id", "tenant_id"),
        Index("ix_redline_templates_clause_type", "clause_type"),
        Index("ix_redline_templates_playbook_id", "playbook_id"),
    )
