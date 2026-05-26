"""Notifications, workflow automation, SLA tracking, and escalation SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


class NotificationType(str, PyEnum):
    REVIEW_ASSIGNED = "review.assigned"
    REVIEW_ESCALATED = "review.escalated"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_COMPLETED = "approval.completed"
    FINDING_RESOLVED = "finding.resolved"
    REDLINE_ACCEPTED = "redline.accepted"
    REDLINE_REJECTED = "redline.rejected"
    SLA_BREACH_WARNING = "sla.breach_warning"
    OVERDUE_REVIEW = "review.overdue"
    WORKFLOW_COMPLETED = "workflow.completed"
    AI_ANALYSIS_COMPLETE = "ai.analysis_complete"
    UPLOAD_COMPLETE = "upload.complete"
    INGESTION_FAILED = "ingestion.failed"


class NotificationChannel(str, PyEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    BOTH = "both"


class DeliveryStatus(str, PyEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Notification(Base):
    """In-app notification with delivery tracking and deep-link support."""
    __tablename__ = "notifications"

    notification_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Text, nullable=False, index=True)

    type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=True)
    severity = Column(Text, nullable=False, default="info")  # 'critical', 'high', 'medium', 'low', 'info'

    # Polymorphic entity reference
    entity_type = Column(Text, nullable=True)
    entity_id = Column(UUID, nullable=True)
    action_url = Column(Text, nullable=True)

    channel = Column(Text, nullable=False, default="in_app")
    delivery_status = Column(Text, nullable=False, default="pending")

    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Deduplication
    dedup_key = Column(Text, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class NotificationDelivery(Base):
    """Tracks delivery attempts for each notification channel."""
    __tablename__ = "notification_deliveries"

    delivery_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID, ForeignKey("notifications.notification_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    channel = Column(Text, nullable=False)  # 'in_app', 'email'
    status = Column(Text, nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NotificationPreference(Base):
    """Per-user notification channel and digest preferences."""
    __tablename__ = "notification_preferences"

    preference_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False, index=True)

    notification_type = Column(Text, nullable=False)
    channel = Column(Text, nullable=False, default="in_app")  # 'in_app', 'email', 'both', 'none'
    digest_frequency = Column(Text, nullable=True)  # 'instant', 'hourly', 'daily', 'never'
    is_muted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "notification_type", name="uq_notify_pref_tenant_user_type"),
    )


class WorkflowEvent(Base):
    """Records workflow events for audit and automation triggers."""
    __tablename__ = "workflow_events"

    event_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(Text, nullable=False, index=True)
    source = Column(Text, nullable=False)  # Service that generated the event
    correlation_id = Column(Text, nullable=True)

    entity_type = Column(Text, nullable=True)
    entity_id = Column(UUID, nullable=True)
    actor_id = Column(Text, nullable=True)

    payload = Column(JSONB, nullable=False, default=dict)
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkflowTimer(Base):
    """Scheduled timer for workflow actions (reminders, SLA checks, escalations)."""
    __tablename__ = "workflow_timers"

    timer_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    timer_type = Column(Text, nullable=False)  # 'sla_warning', 'overdue', 'reminder', 'escalation'
    entity_type = Column(Text, nullable=False)
    entity_id = Column(UUID, nullable=False)
    target_time = Column(DateTime(timezone=True), nullable=False, index=True)

    action = Column(Text, nullable=False)  # What to do when timer fires
    action_payload = Column(JSONB, nullable=False, default=dict)

    fired = Column(Boolean, nullable=False, default=False)
    fired_at = Column(DateTime(timezone=True), nullable=True)
    cancelled = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EscalationRule(Base):
    """Defines escalation rules: conditions, chain, and actions."""
    __tablename__ = "escalation_rules"

    rule_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    name = Column(Text, nullable=False)
    trigger_event = Column(Text, nullable=False)  # 'sla_breach', 'overdue', 'manual_escalation'
    condition = Column(JSONB, nullable=True)  # Optional condition expression

    escalation_chain = Column(JSONB, nullable=False)
    # [{"level": 1, "assignee": "role:legal_reviewer", "timeout_minutes": 120},
    #  {"level": 2, "assignee": "user:senior-reviewer-uuid", "timeout_minutes": 60},
    #  {"level": 3, "assignee": "role:legal_director"}]

    max_escalation_level = Column(Integer, nullable=False, default=3)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EscalationEvent(Base):
    """Records each escalation occurrence for audit and tracking."""
    __tablename__ = "escalation_events"

    escalation_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(UUID, ForeignKey("escalation_rules.rule_id", ondelete="SET NULL"), nullable=True)

    entity_type = Column(Text, nullable=False)
    entity_id = Column(UUID, nullable=False)
    level = Column(Integer, nullable=False)
    escalated_by = Column(Text, nullable=True)
    escalated_to = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)

    status = Column(Text, nullable=False, default="open")  # 'open', 'acknowledged', 'resolved'
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SLAPolicy(Base):
    """SLA policy definitions for different workflow types and priorities."""
    __tablename__ = "sla_policies"

    policy_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    name = Column(Text, nullable=False)
    workflow_type = Column(Text, nullable=False)  # 'legal_review', 'approval'
    priority = Column(Text, nullable=False, default="normal")  # 'urgent', 'high', 'normal', 'low'

    target_minutes = Column(Integer, nullable=False)
    warning_threshold_percent = Column(Float, nullable=False, default=0.8)
    escalation_after_minutes = Column(Integer, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "workflow_type", "priority", name="uq_notify_workflow_tenant_type_priority"),
    )
