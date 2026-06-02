"""Extend review_status enum with workflow states.

Revision ID: p4q5r6s7t8u9
Revises: 246c2ccbd7ed
Create Date: 2026-05-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "p4q5r6s7t8u9"
down_revision: Union[str, None] = "246c2ccbd7ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# New values used by ReviewStatus but missing from initial schema enum.
NEW_STATUSES = (
    "review_ready",
    "changes_requested",
    "legal_approval",
    "exec_approval",
)


def upgrade() -> None:
    for value in NEW_STATUSES:
        op.execute(f"ALTER TYPE review_status ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    pass
