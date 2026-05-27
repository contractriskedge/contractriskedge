"""Add recovery_actions audit table for recovery governance.

This migration creates the ``recovery_actions`` table which provides:

- Audit trail: Every recovery action is recorded with timestamps,
  action type, previous/new state, and outcome
- Cooldown enforcement: ``cooldown_until`` column prevents re-recovering
  the same entity within the cooldown window
- Escalation governance: ``escalation_count`` column tracks how many
  times an entity has been recovered, with configurable max limits
- Operational observability: Full context for every recovery decision

Revision ID: f7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-26 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "f7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recovery_actions",
        sa.Column("action_id", UUID, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("entity_id", sa.Text, nullable=False, index=True),
        sa.Column("action_type", sa.Text, nullable=False),
        sa.Column("previous_state", sa.Text, nullable=True),
        sa.Column("new_state", sa.Text, nullable=True),
        sa.Column("escalation_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("action_id"),
    )

    # Indexes for efficient recovery governance queries
    op.create_index(
        "ix_recovery_actions_entity",
        "recovery_actions",
        ["entity_type", "entity_id", "created_at"],
    )
    op.create_index(
        "ix_recovery_actions_tenant_entity",
        "recovery_actions",
        ["tenant_id", "entity_type", "entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_recovery_actions_tenant_entity", table_name="recovery_actions")
    op.drop_index("ix_recovery_actions_entity", table_name="recovery_actions")
    op.drop_table("recovery_actions")

