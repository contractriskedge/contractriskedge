"""Obligation Management — SQLAlchemy ORM models for obligation tracking, SLA monitoring,
vendor performance, financial exposure, and audit logging.

Tables:
- obligations: Core obligation records with risk scoring, AI predictions, and metadata
- obligation_instances: Recurring or multi-instance obligation tracking
- obligation_reminders: Reminder scheduling per obligation
- obligation_escalations: Escalation tracking for overdue or at-risk obligations
- obligation_evidence: Supporting evidence files per obligation
- sla_metrics: SLA performance tracking per vendor/contract
- vendor_performance: Vendor performance scoring and risk assessment
- financial_exposure: Financial exposure aggregation by category
- obligation_audit_log: Audit trail for obligation lifecycle events
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.session import Base


# ── Obligation ──────────────────────────────────────────────────────


class Obligation(Base):
    """Core obligation record with risk scoring, AI predictions, and metadata."""
    __tablename__ = "obligations"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    obligation_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    contract_id = Column(String(255), nullable=True)
    contract_uuid_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="SET NULL"), nullable=True, index=True)
    contract_name = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    owner = Column(String(255), nullable=True)
    assignee = Column(String(255), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    risk_score = Column(Float, nullable=False, default=0)
    risk_level = Column(String(20), nullable=False, default="medium")
    sla_status = Column(String(50), nullable=False, default="on_track")
    sla_remaining_hours = Column(Float, nullable=False, default=0)
    financial_impact = Column(Float, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="USD")
    escalation_level = Column(Integer, nullable=False, default=0)
    ai_risk_prediction = Column(Float, nullable=False, default=0)
    ai_confidence = Column(Float, nullable=False, default=0)
    clause_reference = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    business_unit = Column(String(255), nullable=True)
    geography = Column(String(255), nullable=True)
    is_recurring = Column(Boolean, nullable=False, default=False)
    recurrence_pattern = Column(String(50), nullable=True)
    recurrence_next_date = Column(DateTime(timezone=True), nullable=True)
    attachments_count = Column(Integer, nullable=False, default=0)
    reminders_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    is_favorite = Column(Boolean, nullable=False, default=False)
    tags = Column(ARRAY(String), nullable=False, default=list)
    extra_metadata = Column("metadata", JSONB, nullable=True)
    # Completion auditability fields (V1.1)
    completion_notes = Column(Text, nullable=True)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(UUID, nullable=True)
    evidence_attachment_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Obligation id={self.id} name={self.name!r} status={self.status!r}>"


# ── ObligationInstance ──────────────────────────────────────────────


class ObligationInstance(Base):
    """Recurring or multi-instance obligation tracking."""
    __tablename__ = "obligation_instances"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    obligation_id = Column(UUID, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False, index=True)
    instance_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False)
    financial_impact = Column(Float, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ObligationInstance id={self.id} obligation_id={self.obligation_id!r}>"


# ── ObligationReminder ──────────────────────────────────────────────


class ObligationReminder(Base):
    """Reminder scheduling per obligation."""
    __tablename__ = "obligation_reminders"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    obligation_id = Column(UUID, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False, index=True)
    reminder_type = Column(String(50), nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ObligationReminder id={self.id} type={self.reminder_type!r}>"


# ── ObligationEscalation ────────────────────────────────────────────


class ObligationEscalation(Base):
    """Escalation tracking for overdue or at-risk obligations."""
    __tablename__ = "obligation_escalations"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    obligation_id = Column(UUID, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False, index=True)
    escalation_level = Column(Integer, nullable=False)
    escalated_to = Column(String(255), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ObligationEscalation id={self.id} level={self.escalation_level}>"


# ── ObligationEvidence ──────────────────────────────────────────────


class ObligationEvidence(Base):
    """Supporting evidence files per obligation."""
    __tablename__ = "obligation_evidence"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    obligation_id = Column(UUID, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False, index=True)
    instance_id = Column(UUID, ForeignKey("obligation_instances.id", ondelete="CASCADE"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_url = Column(Text, nullable=True)
    uploaded_by = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ObligationEvidence id={self.id} file={self.file_name!r}>"


# ── SlaMetric ───────────────────────────────────────────────────────


class SlaMetric(Base):
    """SLA performance tracking per vendor/contract."""
    __tablename__ = "sla_metrics"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    obligation_id = Column(UUID, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=True, index=True)
    vendor = Column(String(255), nullable=False)
    contract_type = Column(String(255), nullable=True)
    sla_target = Column(String(50), nullable=False)
    performance = Column(Float, nullable=False)
    trend = Column(Float, nullable=False, default=0)
    breach_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="on_track")
    measured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<SlaMetric id={self.id} vendor={self.vendor!r} status={self.status!r}>"


# ── VendorPerformance ───────────────────────────────────────────────


class VendorPerformance(Base):
    """Vendor performance scoring and risk assessment."""
    __tablename__ = "vendor_performance"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    vendor = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    score = Column(Float, nullable=False)
    trend = Column(Float, nullable=False, default=0)
    contract_count = Column(Integer, nullable=False, default=0)
    breach_count = Column(Integer, nullable=False, default=0)
    risk_level = Column(String(20), nullable=False)
    predicted_risk = Column(Float, nullable=False, default=0)
    last_assessed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<VendorPerformance id={self.id} vendor={self.vendor!r} score={self.score}>"


# ── FinancialExposure ───────────────────────────────────────────────


class FinancialExposure(Base):
    """Financial exposure aggregation by category."""
    __tablename__ = "financial_exposure"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    category = Column(String(50), nullable=False)
    total_exposure = Column(Float, nullable=False, default=0)
    overdue_amount = Column(Float, nullable=False, default=0)
    at_risk_amount = Column(Float, nullable=False, default=0)
    recovered_amount = Column(Float, nullable=False, default=0)
    trend = Column(Float, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="USD")
    as_of_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<FinancialExposure id={self.id} category={self.category!r}>"


# ── ObligationAuditLog ──────────────────────────────────────────────


class ObligationAuditLog(Base):
    """Audit trail for obligation lifecycle events with direct contract traceability."""
    __tablename__ = "obligation_audit_log"

    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    obligation_id = Column(UUID, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_uuid_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    actor = Column(String(255), nullable=True)
    changes = Column(JSONB, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ObligationAuditLog id={self.id} action={self.action!r}>"
