"""Add obligation_number to obligations

Revision ID: a9b8c7d6e5f4
Revises: f7e8d9a0b1c2
Create Date: 2026-06-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a9b8c7d6e5f4"
down_revision = "f7e8d9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "obligations",
        sa.Column("obligation_number", sa.String(50), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("obligations", "obligation_number")
