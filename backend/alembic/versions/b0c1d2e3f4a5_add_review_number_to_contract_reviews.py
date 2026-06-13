"""Add review_number to contract_reviews

Revision ID: b0c1d2e3f4a5
Revises: a9b8c7d6e5f4
Create Date: 2026-06-12 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b0c1d2e3f4a5"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contract_reviews",
        sa.Column("review_number", sa.String(50), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("contract_reviews", "review_number")
