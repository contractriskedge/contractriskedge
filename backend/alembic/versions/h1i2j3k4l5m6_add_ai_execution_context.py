"""Add AI execution context metadata to analysis runs.

This migration adds a JSONB column to persist model, prompt version,
execution context, and guardrail metadata for AI analysis replay and auditing.

Revision ID: h1i2j3k4l5m6
Revises: f5e6d7c8b9a1
Create Date: 2026-05-27 12:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "h1i2j3k4l5m6"
down_revision: Union[str, None] = "f5e6d7c8b9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_execution_runs",
        sa.Column("execution_context", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("ai_execution_runs", "execution_context")
