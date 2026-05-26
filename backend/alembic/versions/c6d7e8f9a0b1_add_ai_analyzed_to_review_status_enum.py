"""add_ai_analyzed_to_review_status_enum

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-05-25 22:05:00.000000

Adds 'ai_analyzed' to the review_status PostgreSQL enum type.
This is a legacy status value that exists in the database but was
missing from the Python enum definition, causing LookupError when
SQLAlchemy tries to deserialize rows with this status.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'ai_analyzed'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    pass
