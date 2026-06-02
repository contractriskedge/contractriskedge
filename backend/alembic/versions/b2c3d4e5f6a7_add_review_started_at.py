"""add_review_started_at

Revision ID: b2c3d4e5f6a7
Revises: p4q5r6s7t8u9
Create Date: 2026-05-18 18:45:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "p4q5r6s7t8u9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contract_reviews", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("contract_reviews", "started_at")
