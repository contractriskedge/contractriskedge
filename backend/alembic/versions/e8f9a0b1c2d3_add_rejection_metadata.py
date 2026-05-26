"""add_rejection_metadata_to_contract_reviews

Revision ID: e8f9a0b1c2d3
Revises: b2c3d4e5f6a7
Create Date: 2026-05-18 19:30:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contract_reviews", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("contract_reviews", sa.Column("rejection_category", sa.Text(), nullable=True))
    op.add_column("contract_reviews", sa.Column("rejection_severity", sa.Text(), nullable=True))
    op.add_column("contract_reviews", sa.Column("rejected_by", sa.Text(), nullable=True))
    op.add_column("contract_reviews", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("contract_reviews", "rejected_at")
    op.drop_column("contract_reviews", "rejected_by")
    op.drop_column("contract_reviews", "rejection_severity")
    op.drop_column("contract_reviews", "rejection_category")
    op.drop_column("contract_reviews", "rejection_reason")
