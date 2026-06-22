"""Add coverage_snapshots table for analytics trends.

Revision ID: 002_add_coverage_snapshots
Revises: 34fb461caf36
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_add_coverage_snapshots"
down_revision: Union[str, None] = "34fb461caf36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coverage_snapshots",
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("total_findings", sa.Integer(), nullable=False),
        sa.Column("total_templates", sa.Integer(), nullable=False),
        sa.Column("templates_used", sa.Integer(), nullable=False),
        sa.Column("templates_missing", sa.Integer(), nullable=False),
        sa.Column("coverage_pct", sa.Float(), nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("snapshot_id"),
    )
    op.create_index(op.f("ix_coverage_snapshots_tenant_id"), "coverage_snapshots", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_coverage_snapshots_date"), "coverage_snapshots", ["snapshot_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_coverage_snapshots_date"), table_name="coverage_snapshots")
    op.drop_index(op.f("ix_coverage_snapshots_tenant_id"), table_name="coverage_snapshots")
    op.drop_table("coverage_snapshots")
