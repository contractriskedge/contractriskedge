"""add_approval_override_columns

Revision ID: 3e41978fb1e2
Revises: c96a5c4d44ec
Create Date: 2026-06-10 09:40:25.041650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e41978fb1e2'
down_revision: Union[str, Sequence[str], None] = '7d8e9f0a1b2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add approval_override columns to contract_reviews."""
    op.add_column("contract_reviews", sa.Column("approval_override_reason", sa.Text(), nullable=True))
    op.add_column("contract_reviews", sa.Column("approval_override_by", sa.Text(), nullable=True))
    op.add_column("contract_reviews", sa.Column("approval_override_timestamp", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove approval_override columns from contract_reviews."""
    op.drop_column("contract_reviews", "approval_override_timestamp")
    op.drop_column("contract_reviews", "approval_override_by")
    op.drop_column("contract_reviews", "approval_override_reason")
