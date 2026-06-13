"""Add is_favorite column to contract_reviews

Revision ID: f7e8d9a0b1c2
Revises: 1fdd3cc759de
Create Date: 2026-06-12 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f7e8d9a0b1c2"
down_revision = "1fdd3cc759de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contract_reviews",
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("contract_reviews", "is_favorite")
