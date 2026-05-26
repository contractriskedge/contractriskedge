"""Add finding_id column to review_redlines for finding→redline linkage.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-21 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_redlines",
        sa.Column("finding_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_review_redlines_finding_id"),
        "review_redlines",
        ["finding_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_redlines_finding_id"), table_name="review_redlines")
    op.drop_column("review_redlines", "finding_id")
