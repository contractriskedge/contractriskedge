"""add_redline_operation_and_anchor

Revision ID: f1a2b3c4d5e6
Revises: e9f0a1b2c3d4
Create Date: 2026-05-19 22:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e9f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_redlines", sa.Column("operation", sa.Text(), nullable=True))
    op.add_column("ai_redlines", sa.Column("anchor_text", sa.Text(), nullable=True))
    op.add_column("review_redlines", sa.Column("operation", sa.Text(), nullable=True))
    op.add_column("review_redlines", sa.Column("anchor_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("review_redlines", "anchor_text")
    op.drop_column("review_redlines", "operation")
    op.drop_column("ai_redlines", "anchor_text")
    op.drop_column("ai_redlines", "operation")
