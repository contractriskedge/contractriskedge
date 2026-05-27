"""Add event_outbox, assignment_audit, and assignment_locks tables.

This migration creates three new tables for enterprise governance:

1. ``event_outbox`` — Persistent event store with delivery tracking,
   dead-letter queue, and replay capability for reliable async events.

2. ``assignment_audit`` — Immutable audit trail for all review
   assignment and reassignment events with explainability metadata.

3. ``assignment_locks`` — Temporary locks to prevent conflicting
   auto-assignments from multiple automated processes.

Revision ID: a1b2c3d4e5f6
Revises: f7b8c9d0e1f2
Create Date: 2026-05-26 14:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Event Outbox ──────────────────────────────────────────────
    op.create_table(
        "event_outbox",
        sa.Column("event_id", UUID, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False, index=True),
        sa.Column("event_type", sa.Text, nullable=False, index=True),
        sa.Column("correlation_id", sa.Text, nullable=True, index=True),
        sa.Column("actor_id", sa.Text, nullable=True),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("delivery_state", sa.Text, nullable=False, server_default=sa.text("'pending'"), index=True),
        sa.Column("delivery_attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_letter_reason", sa.Text, nullable=True),
        sa.Column("dead_letter_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sequence_id", sa.Integer, nullable=False, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column("ttl_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )

    # ── Assignment Audit ──────────────────────────────────────────
    op.create_table(
        "assignment_audit",
        sa.Column("audit_id", UUID, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_id", UUID, nullable=False, index=True),
        sa.Column("tenant_id", UUID, nullable=False, index=True),
        sa.Column("previous_assignee", sa.Text, nullable=True),
        sa.Column("new_assignee", sa.Text, nullable=False),
        sa.Column("assigned_by", sa.Text, nullable=False),
        sa.Column("assignment_source", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("is_override", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("override_previous_assignee", sa.Text, nullable=True),
        sa.Column("override_justification", sa.Text, nullable=True),
        sa.Column("reviewer_active_count", sa.Integer, nullable=True),
        sa.Column("reviewer_max_capacity", sa.Integer, nullable=True),
        sa.Column("explainability", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["contract_reviews.review_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("audit_id"),
    )

    op.create_index(
        "ix_assignment_audit_review",
        "assignment_audit",
        ["review_id", "created_at"],
    )
    op.create_index(
        "ix_assignment_audit_assignee",
        "assignment_audit",
        ["tenant_id", "new_assignee", "created_at"],
    )

    # ── Assignment Locks ──────────────────────────────────────────
    op.create_table(
        "assignment_locks",
        sa.Column("lock_id", UUID, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_id", UUID, nullable=False, unique=True, index=True),
        sa.Column("tenant_id", UUID, nullable=False, index=True),
        sa.Column("lock_state", sa.Text, nullable=False, server_default=sa.text("'active'")),
        sa.Column("assignee_id", sa.Text, nullable=False),
        sa.Column("acquired_by", sa.Text, nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("overridden_by", sa.Text, nullable=True),
        sa.Column("override_reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["contract_reviews.review_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("lock_id"),
    )

    op.create_index(
        "ix_assignment_locks_state",
        "assignment_locks",
        ["lock_state", "tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_assignment_locks_state", table_name="assignment_locks")
    op.drop_table("assignment_locks")
    op.drop_index("ix_assignment_audit_assignee", table_name="assignment_audit")
    op.drop_index("ix_assignment_audit_review", table_name="assignment_audit")
    op.drop_table("assignment_audit")
    op.drop_table("event_outbox")

