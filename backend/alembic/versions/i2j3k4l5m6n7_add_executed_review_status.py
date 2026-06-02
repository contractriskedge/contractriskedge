"""add_executed_review_status

Revision ID: i2j3k4l5m6n7
Revises: a7b8c9d0e1f2, f7b8c9d0e1f2
Create Date: 2026-05-27 23:30:00.000000

Adds EXECUTED to the review_status PostgreSQL enum (used after FINALIZED).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "i2j3k4l5m6n7"
down_revision: Union[str, Sequence[str], None] = ("a7b8c9d0e1f2", "f7b8c9d0e1f2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'executed'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    pass
