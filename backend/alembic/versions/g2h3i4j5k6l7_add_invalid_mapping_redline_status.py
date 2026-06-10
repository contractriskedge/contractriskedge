"""add invalid_mapping redline status

Revision ID: g2h3i4j5k6l7
Revises: 00a60a2d2bd4
Create Date: 2026-06-08 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "g2h3i4j5k6l7"
down_revision: Union[str, Sequence[str], None] = "00a60a2d2bd4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE redline_status ADD VALUE IF NOT EXISTS 'invalid_mapping'")


def downgrade() -> None:
    pass
