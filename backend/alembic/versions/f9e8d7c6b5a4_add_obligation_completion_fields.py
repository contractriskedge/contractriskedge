"""add_obligation_completion_fields

Revision ID: f9e8d7c6b5a4
Revises: c96a5c4d44ec
Create Date: 2026-06-10 12:00:00.000000

Adds completion_notes, completion_date, completed_by, and
evidence_attachment_count columns to the obligations table
to support the Obligation Completion Auditability Enhancement (V1.1).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "f9e8d7c6b5a4"
down_revision: Union[str, Sequence[str], None] = "c96a5c4d44ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("obligations", sa.Column("completion_notes", sa.Text(), nullable=True))
    op.add_column("obligations", sa.Column("completion_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("obligations", sa.Column("completed_by", UUID(as_uuid=True), nullable=True))
    op.add_column("obligations", sa.Column("evidence_attachment_count", sa.Integer(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    op.drop_column("obligations", "evidence_attachment_count")
    op.drop_column("obligations", "completed_by")
    op.drop_column("obligations", "completion_date")
    op.drop_column("obligations", "completion_notes")
