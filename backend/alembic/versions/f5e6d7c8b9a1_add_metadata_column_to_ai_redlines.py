"""Add metadata JSONB column to ai_redlines for traceability data.

Revision ID: f5e6d7c8b9a1
Revises: f1a2b3c4d5e6
Create Date: 2026-05-21 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f5e6d7c8b9a1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_redlines",
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_redlines", "metadata")
