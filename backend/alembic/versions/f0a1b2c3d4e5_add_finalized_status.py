"""add_finalized_review_status

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-05-19 14:00:00.000000

Adds FINALIZED status to the review_status enum and the new redline
statuses to redline_status enum. Does NOT autogenerate — manual only.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = ["e9f0a1b2c3d4", "f1a2b3c4d5e6"]
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add FINALIZED to review_status enum
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'finalized'")
    # Add new redline statuses to redline_status enum
    op.execute("ALTER TYPE redline_status ADD VALUE IF NOT EXISTS 'needs_legal_review'")
    op.execute("ALTER TYPE redline_status ADD VALUE IF NOT EXISTS 'customer_requested'")
    op.execute("ALTER TYPE redline_status ADD VALUE IF NOT EXISTS 'fallback_language'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    # The new values will remain in the enum type but won't be used.
    pass
