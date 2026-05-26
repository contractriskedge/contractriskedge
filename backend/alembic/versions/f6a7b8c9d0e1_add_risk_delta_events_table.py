"""add_risk_delta_events_table

Revision ID: f6a7b8c9d0e1
Revises: f0a1b2c3d4e5
Create Date: 2026-05-25 10:00:00.000000

Adds the risk_delta_events table for tracking how review decisions
change risk exposure over time. This is the persistence layer for
the RiskDeltaEngine.

Object chain:
  Finding → Suggested Mitigation → Review Decision → RiskDeltaEvent → Version Impact
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_delta_events",
        sa.Column("delta_id", UUID, nullable=False),
        sa.Column("review_id", UUID, sa.ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("delta_type", sa.Text, nullable=False),
        sa.Column("finding_id", UUID, sa.ForeignKey("review_findings.finding_id", ondelete="SET NULL"), nullable=True),
        sa.Column("redline_id", UUID, sa.ForeignKey("review_redlines.redline_id", ondelete="SET NULL"), nullable=True),
        sa.Column("previous_risk", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("new_risk", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("delta_amount", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("delta_pct", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("actor_id", sa.Text, nullable=True),
        sa.Column("actor_name", sa.Text, nullable=True),
        sa.Column("decision", sa.Text, nullable=True),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("version_number", sa.Integer, nullable=True),
        sa.Column("version_id", UUID, sa.ForeignKey("contract_document_versions.version_id", ondelete="SET NULL"), nullable=True),
        sa.Column("clause_category", sa.Text, nullable=True),
        sa.Column("severity", sa.Text, nullable=True),
        sa.Column("finding_title", sa.Text, nullable=True),
        sa.Column("mitigation_type", sa.Text, nullable=True),
        sa.Column("mitigation_effectiveness", sa.Float, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.PrimaryKeyConstraint("delta_id"),
        sa.UniqueConstraint("delta_id", name="uq_risk_delta_event"),
    )

    op.create_index("ix_risk_delta_review_created", "risk_delta_events", ["review_id", "created_at"])
    op.create_index("ix_risk_delta_tenant_type", "risk_delta_events", ["tenant_id", "delta_type"])


def downgrade() -> None:
    op.drop_index("ix_risk_delta_tenant_type", table_name="risk_delta_events")
    op.drop_index("ix_risk_delta_review_created", table_name="risk_delta_events")
    op.drop_table("risk_delta_events")
