"""add_approved_version_id_to_reviews

Revision ID: e9f0a1b2c3d4
Revises: d5e6f7a8b9c0
Create Date: 2026-05-19 13:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contract_reviews",
        sa.Column("approved_version_id", UUID, sa.ForeignKey("contract_document_versions.version_id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contract_reviews", "approved_version_id")
