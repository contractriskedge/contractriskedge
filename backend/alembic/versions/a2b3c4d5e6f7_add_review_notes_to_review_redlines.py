"""Add review_notes column to review_redlines.

Revision ID: a2b3c4d5e6f7
Revises: f5e6d7c8b9a1
Create Date: 2026-05-21 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a2b3c4d5e6f7"
down_revision = "f5e6d7c8b9a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_redlines",
        sa.Column("review_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("review_redlines", "review_notes")
