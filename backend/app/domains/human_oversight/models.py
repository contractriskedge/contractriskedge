"""Human Oversight domain SQLAlchemy ORM models.

Tables:
- ai_approvals: AI recommendation approval workflows
- policy_exceptions: Structured policy exception requests
- acknowledgment_requirements: Reviewer acknowledgment of AI findings
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
)
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


class AIApprovalModel(Base):
    """An approval request for an AI-generated recommendation."""
    __tablename__ = "ai_approvals"

    approval_id = Column(Text, primary_key=True)  # uuid4 hex[:12]
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    review_id = Column(Text, nullable=False)
    upload_id = Column(Text, nullable=False)
    approval_type = Column(Text, nullable=False)  # ApprovalType enum value
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, server_default="")
    ai_recommendation = Column(Text, nullable=False, server_default="")
    proposed_action = Column(Text, nullable=False, server_default="")
    risk_impact = Column(Text, nullable=False, server_default="")
    confidence = Column(Float, nullable=False, server_default="0")
    priority = Column(Text, nullable=False, server_default="normal")  # ApprovalPriority enum value
    status = Column(Text, nullable=False, server_default="pending")  # ApprovalStatus enum value
    requested_by = Column(Text, nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    decided_by = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_notes = Column(Text, nullable=True)
    conditions = Column(JSONB, nullable=True)
    finding_ids = Column(ARRAY(Text), nullable=False, server_default="{}")
    redline_ids = Column(ARRAY(Text), nullable=False, server_default="{}")
    rule_ids = Column(ARRAY(Text), nullable=False, server_default="{}")
    required_approvers = Column(ARRAY(Text), nullable=False, server_default="{}")
    required_roles = Column(ARRAY(Text), nullable=False, server_default="{}")
    approval_level = Column(Integer, nullable=False, server_default="1")
    correlation_id = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PolicyExceptionModel(Base):
    """A structured policy exception request."""
    __tablename__ = "policy_exceptions"

    exception_id = Column(Text, primary_key=True)  # uuid4 hex[:12]
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    review_id = Column(Text, nullable=False)
    upload_id = Column(Text, nullable=False)
    rule_id = Column(Text, nullable=True)
    rule_name = Column(Text, nullable=False, server_default="")
    policy_name = Column(Text, nullable=False, server_default="")
    clause_category = Column(Text, nullable=False, server_default="")
    severity = Column(Text, nullable=False, server_default="medium")  # ExceptionSeverity enum value
    justification = Column(Text, nullable=False)
    proposed_alternative = Column(Text, nullable=True)
    risk_assessment = Column(Text, nullable=False, server_default="")
    status = Column(Text, nullable=False, server_default="pending")  # ApprovalStatus enum value
    requested_by = Column(Text, nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    approval_level = Column(Integer, nullable=False, server_default="1")
    correlation_id = Column(Text, nullable=True)
    previous_exception_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AcknowledgmentRequirementModel(Base):
    """A requirement for a reviewer to acknowledge an AI finding or recommendation."""
    __tablename__ = "acknowledgment_requirements"

    ack_id = Column(Text, primary_key=True)  # uuid4 hex[:12]
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    review_id = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)  # 'finding', 'redline', 'risk_score', 'policy_deviation'
    entity_id = Column(Text, nullable=False)
    title = Column(Text, nullable=False, server_default="")
    description = Column(Text, nullable=False, server_default="")
    mandatory = Column(Boolean, nullable=False, server_default=sa.text("true"))
    status = Column(Text, nullable=False, server_default="pending")  # AcknowledgmentStatus enum value
    acknowledged_by = Column(Text, nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
