"""Add risk_score column to review_findings.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-05-21 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_findings",
        sa.Column("risk_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("review_findings", "risk_score")
