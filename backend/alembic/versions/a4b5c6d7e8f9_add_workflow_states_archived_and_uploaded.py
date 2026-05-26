"""add_workflow_states_archived_and_uploaded

Revision ID: a4b5c6d7e8f9
Revises: f0a1b2c3d4e5
Create Date: 2026-05-19 23:00:00.000000

Adds ARCHIVED and UPLOADED statuses to the review_status enum
to complete the strict workflow lifecycle.

The full lifecycle is now:
UPLOADED → AI_ANALYZED → REVIEW_READY → IN_REVIEW → APPROVED → FINALIZED → ARCHIVED
                                                          → REJECTED ↗
                                              → ESCALATED →
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ARCHIVED to review_status enum
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'archived'")
    # Add UPLOADED to review_status enum
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'uploaded'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    pass
