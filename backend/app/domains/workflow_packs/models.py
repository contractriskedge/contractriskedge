"""Workflow ORM models — packs, activations, instances, steps, execution logs.

Compatible with the existing raw SQL schema used by WorkflowPackService.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Optional

from sqlalchemy import (
    Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.kernel.database.base import Base


# ── Enums ──────────────────────────────────────────────────────────

class WorkflowPackCategory(str, PyEnum):
    PROCUREMENT = "procurement"
    HEALTHCARE = "healthcare"
    SAAS = "saas"
    FINANCE = "finance"
    LEGAL = "legal"
    COMPLIANCE = "compliance"
    VENDOR = "vendor"
    CUSTOM = "custom"


class WorkflowStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class WorkflowStepStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPENSATED = "compensated"
    WAITING_APPROVAL = "waiting_approval"


# ── Workflow Pack Definitions ──────────────────────────────────────

class WorkflowPack(Base):
    """Workflow pack definition — the blueprint for a workflow type."""

    __tablename__ = "workflow_packs"

    pack_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    stages: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    rules: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    compliance_requirements: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    clause_requirements: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    approval_chains: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    notification_templates: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=list)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    activations: Mapped[list["PackActivation"]] = relationship(
        "PackActivation", back_populates="pack", cascade="all, delete-orphan"
    )
    versions: Mapped[list["WorkflowVersion"]] = relationship(
        "WorkflowVersion", back_populates="pack", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_workflow_packs_tenant_category", "tenant_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowPack {self.pack_id} '{self.name}' v{self.version}>"


class WorkflowVersion(Base):
    """Versioned snapshot of a workflow pack definition.

    Tracks changes to pack configurations over time for audit and rollback.
    """

    __tablename__ = "workflow_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    pack_id: Mapped[str] = mapped_column(String(64), ForeignKey("workflow_packs.pack_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    pack: Mapped["WorkflowPack"] = relationship("WorkflowPack", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("pack_id", "version_number", name="uq_pack_version"),
        Index("idx_workflow_versions_pack", "pack_id", "version_number"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowVersion {self.pack_id} v{self.version_number}>"


# ── Pack Activations ───────────────────────────────────────────────

class PackActivation(Base):
    """Tenant-level activation of a workflow pack with config overrides."""

    __tablename__ = "pack_activations"

    activation_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    pack_id: Mapped[str] = mapped_column(String(64), ForeignKey("workflow_packs.pack_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    business_unit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    config_overrides: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    activated_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    pack: Mapped["WorkflowPack"] = relationship("WorkflowPack", back_populates="activations")

    __table_args__ = (
        Index("idx_pack_activations_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<PackActivation {self.activation_id} pack={self.pack_id} active={self.is_active}>"


# ── Workflow Instances ─────────────────────────────────────────────

class WorkflowInstance(Base):
    """A running or completed instance of a workflow."""

    __tablename__ = "workflow_instances"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pack_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    context_data: Mapped[Optional[dict[str, Any]]] = mapped_column("context", JSONB, nullable=True, default=dict)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    steps: Mapped[list["WorkflowInstanceStep"]] = relationship(
        "WorkflowInstanceStep", back_populates="workflow_instance",
        cascade="all, delete-orphan", order_by="WorkflowInstanceStep.step_order"
    )
    execution_logs: Mapped[list["WorkflowExecutionLog"]] = relationship(
        "WorkflowExecutionLog", back_populates="workflow_instance",
        cascade="all, delete-orphan", order_by="WorkflowExecutionLog.created_at"
    )

    __table_args__ = (
        Index("idx_workflow_instances_tenant_status", "tenant_id", "status"),
        Index("idx_workflow_instances_correlation", "correlation_id"),
    )

    def __repr__(self) -> str:
        wid = self.workflow_id[:8] if self.workflow_id else "?"
        return f"<WorkflowInstance {wid} type={self.workflow_type} status={self.status}>"


class WorkflowInstanceStep(Base):
    """Individual step execution within a workflow instance."""

    __tablename__ = "workflow_instance_steps"

    step_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    workflow_id: Mapped[str] = mapped_column(String(64), ForeignKey("workflow_instances.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    result_data: Mapped[Optional[dict[str, Any]]] = mapped_column("result", JSONB, nullable=True)
    error_data: Mapped[Optional[dict[str, Any]]] = mapped_column("error", JSONB, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    sla_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    approval_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workflow_instance: Mapped["WorkflowInstance"] = relationship("WorkflowInstance", back_populates="steps")

    __table_args__ = (
        Index("idx_workflow_steps_instance_order", "workflow_id", "step_order"),
    )

    def __repr__(self) -> str:
        sid = self.step_id[:8] if self.step_id else "?"
        return f"<WorkflowInstanceStep {sid} '{self.step_name}' status={self.status}>"


class WorkflowExecutionLog(Base):
    """Audit log for workflow execution events."""

    __tablename__ = "workflow_execution_logs"

    log_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    workflow_id: Mapped[str] = mapped_column(String(64), ForeignKey("workflow_instances.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    step_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    previous_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workflow_instance: Mapped["WorkflowInstance"] = relationship("WorkflowInstance", back_populates="execution_logs")

    __table_args__ = (
        Index("idx_workflow_logs_workflow_event", "workflow_id", "event_type"),
        Index("idx_workflow_logs_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        lid = self.log_id[:8] if self.log_id else "?"
        return f"<WorkflowExecutionLog {lid} event={self.event_type}>"
