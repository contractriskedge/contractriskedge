"""Compliance domain SQLAlchemy models.

Tables:
- compliance_frameworks: regulatory frameworks (SOC 2, ISO 27001, GDPR, HIPAA, NIST CSF)
- compliance_controls: individual controls within each framework
- compliance_assessments: assessment runs against frameworks
- compliance_findings: findings discovered during assessments
- compliance_exceptions: approved exceptions to compliance controls
- compliance_evidence: evidence collected for compliance verification
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


class ComplianceFrameworkModel(Base):
    """A regulatory compliance framework (SOC 2, ISO 27001, etc.)."""
    __tablename__ = "compliance_frameworks"

    framework_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    version = Column(Text, nullable=False, default="1.0")
    description = Column(Text, nullable=False, default="")
    category = Column(Text, nullable=False, default="general")  # e.g. "security", "privacy", "quality"
    is_active = Column(Boolean, nullable=False, default=True)
    control_count = Column(Integer, nullable=False, default=0)
    extra_metadata = Column(JSONB, nullable=False, default=dict)
    created_by = Column(Text, nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ComplianceControlModel(Base):
    """An individual control within a compliance framework."""
    __tablename__ = "compliance_controls"

    control_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    framework_id = Column(UUID, ForeignKey("compliance_frameworks.framework_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    control_id_str = Column(Text, nullable=False)  # e.g. "CC6.1", "A.9.1.2"
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(Text, nullable=False, default="general")
    risk_level = Column(Text, nullable=False, default="medium")  # critical, high, medium, low
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    extra_metadata = Column(JSONB, nullable=False, default=dict)
    created_by = Column(Text, nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ComplianceAssessmentModel(Base):
    """A compliance assessment run against a framework."""
    __tablename__ = "compliance_assessments"

    assessment_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    framework_id = Column(UUID, ForeignKey("compliance_frameworks.framework_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(Text, nullable=False, default="draft")  # draft, in_progress, completed, failed
    score = Column(Float, nullable=True)
    total_controls = Column(Integer, nullable=False, default=0)
    passed_controls = Column(Integer, nullable=False, default=0)
    failed_controls = Column(Integer, nullable=False, default=0)
    compliance_percentage = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, nullable=False, default=dict)
    created_by = Column(Text, nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ComplianceFindingModel(Base):
    """A finding discovered during a compliance assessment."""
    __tablename__ = "compliance_findings"

    finding_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID, ForeignKey("compliance_assessments.assessment_id", ondelete="CASCADE"), nullable=False, index=True)
    control_id = Column(UUID, ForeignKey("compliance_controls.control_id", ondelete="CASCADE"), nullable=True, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, default="")
    severity = Column(Text, nullable=False, default="medium")  # critical, high, medium, low, info
    status = Column(Text, nullable=False, default="open")  # open, in_progress, remediated, waived, closed
    risk_score = Column(Float, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    assigned_to = Column(Text, nullable=True)
    remediation_notes = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, nullable=False, default=dict)
    created_by = Column(Text, nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ComplianceExceptionModel(Base):
    """An approved exception to a compliance control."""
    __tablename__ = "compliance_exceptions"

    exception_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    control_id = Column(UUID, ForeignKey("compliance_controls.control_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    justification = Column(Text, nullable=False)
    risk_assessment = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="open")  # open, approved, rejected, expired
    approved_by = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, nullable=False, default=dict)
    created_by = Column(Text, nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ComplianceEvidenceModel(Base):
    """Evidence collected for compliance verification."""
    __tablename__ = "compliance_evidence"

    evidence_id = Column(Text, primary_key=True)  # prefix_uuid format from existing service
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type = Column(Text, nullable=False)
    framework = Column(Text, nullable=False)
    control_id = Column(Text, nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(Text, nullable=False, default="collected")
    data = Column(JSONB, nullable=False, default=dict)
    checksum = Column(Text, nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    validated_by = Column(Text, nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    storage_path = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
