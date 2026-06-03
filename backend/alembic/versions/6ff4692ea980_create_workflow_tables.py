"""create workflow tables (packs, versions, activations, instances, steps, logs)

Revision ID: 6ff4692ea980
Revises: 8d458e3067ef
Create Date: 2026-06-03 17:39:32.811070

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "6ff4692ea980"
down_revision: Union[str, Sequence[str], None] = "8d458e3067ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create workflow tables."""

    # ── workflow_packs ──────────────────────────────────────────
    op.create_table(
        "workflow_packs",
        sa.Column("pack_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("region", sa.String(50), nullable=True),
        sa.Column("jurisdiction", sa.String(50), nullable=True),
        sa.Column("stages", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("compliance_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("clause_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("approval_chains", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notification_templates", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("pack_id"),
    )
    op.create_index("idx_workflow_packs_tenant_category", "workflow_packs", ["tenant_id", "category"])
    op.create_index(op.f("ix_workflow_packs_tenant_id"), "workflow_packs", ["tenant_id"])

    # ── workflow_versions ───────────────────────────────────────
    op.create_table(
        "workflow_versions",
        sa.Column("version_id", sa.String(64), nullable=False),
        sa.Column("pack_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pack_id"], ["workflow_packs.pack_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("version_id"),
        sa.UniqueConstraint("pack_id", "version_number", name="uq_pack_version"),
    )
    op.create_index("idx_workflow_versions_pack", "workflow_versions", ["pack_id", "version_number"])
    op.create_index(op.f("ix_workflow_versions_pack_id"), "workflow_versions", ["pack_id"])
    op.create_index(op.f("ix_workflow_versions_tenant_id"), "workflow_versions", ["tenant_id"])

    # ── pack_activations ────────────────────────────────────────
    op.create_table(
        "pack_activations",
        sa.Column("activation_id", sa.String(64), nullable=False),
        sa.Column("pack_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("business_unit", sa.String(100), nullable=True),
        sa.Column("config_overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("activated_by", sa.String(64), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pack_id"], ["workflow_packs.pack_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("activation_id"),
    )
    op.create_index("idx_pack_activations_tenant_active", "pack_activations", ["tenant_id", "is_active"])
    op.create_index(op.f("ix_pack_activations_pack_id"), "pack_activations", ["pack_id"])
    op.create_index(op.f("ix_pack_activations_tenant_id"), "pack_activations", ["tenant_id"])

    # ── workflow_instances ──────────────────────────────────────
    op.create_table(
        "workflow_instances",
        sa.Column("workflow_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("pack_id", sa.String(64), nullable=True),
        sa.Column("workflow_type", sa.String(100), nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pack_id"], ["workflow_packs.pack_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("workflow_id"),
    )
    op.create_index("idx_workflow_instances_tenant_status", "workflow_instances", ["tenant_id", "status"])
    op.create_index("idx_workflow_instances_correlation", "workflow_instances", ["correlation_id"])
    op.create_index(op.f("ix_workflow_instances_correlation_id"), "workflow_instances", ["correlation_id"])
    op.create_index(op.f("ix_workflow_instances_pack_id"), "workflow_instances", ["pack_id"])
    op.create_index(op.f("ix_workflow_instances_status"), "workflow_instances", ["status"])
    op.create_index(op.f("ix_workflow_instances_tenant_id"), "workflow_instances", ["tenant_id"])
    op.create_index(op.f("ix_workflow_instances_workflow_type"), "workflow_instances", ["workflow_type"])

    # ── workflow_instance_steps ─────────────────────────────────
    op.create_table(
        "workflow_instance_steps",
        sa.Column("step_id", sa.String(64), nullable=False),
        sa.Column("workflow_id", sa.String(64), nullable=False),
        sa.Column("step_name", sa.String(255), nullable=False),
        sa.Column("step_type", sa.String(50), nullable=True),
        sa.Column("step_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("sla_seconds", sa.Integer(), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("approval_status", sa.String(30), nullable=True),
        sa.Column("approved_by", sa.String(64), nullable=True),
        sa.Column("approval_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow_instances.workflow_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("step_id"),
    )
    op.create_index("idx_workflow_steps_instance_order", "workflow_instance_steps", ["workflow_id", "step_order"])
    op.create_index(op.f("ix_workflow_instance_steps_workflow_id"), "workflow_instance_steps", ["workflow_id"])

    # ── workflow_execution_logs ─────────────────────────────────
    op.create_table(
        "workflow_execution_logs",
        sa.Column("log_id", sa.String(64), nullable=False),
        sa.Column("workflow_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("step_name", sa.String(255), nullable=True),
        sa.Column("actor_id", sa.String(64), nullable=True),
        sa.Column("previous_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow_instances.workflow_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index("idx_workflow_logs_workflow_event", "workflow_execution_logs", ["workflow_id", "event_type"])
    op.create_index("idx_workflow_logs_tenant_created", "workflow_execution_logs", ["tenant_id", "created_at"])
    op.create_index(op.f("ix_workflow_execution_logs_event_type"), "workflow_execution_logs", ["event_type"])
    op.create_index(op.f("ix_workflow_execution_logs_tenant_id"), "workflow_execution_logs", ["tenant_id"])
    op.create_index(op.f("ix_workflow_execution_logs_workflow_id"), "workflow_execution_logs", ["workflow_id"])


def downgrade() -> None:
    """Drop workflow tables."""
    op.drop_table("workflow_execution_logs")
    op.drop_table("workflow_instance_steps")
    op.drop_table("workflow_instances")
    op.drop_table("pack_activations")
    op.drop_table("workflow_versions")
    op.drop_table("workflow_packs")
