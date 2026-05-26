"""add_contract_document_versions

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-05-19 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = ["c3d4e5f6a7b8", "e8f9a0b1c2d3"]
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_document_versions",
        sa.Column("version_id", UUID, primary_key=True),
        sa.Column("review_id", UUID, sa.ForeignKey("contract_reviews.review_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("source_document_id", UUID, nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("accepted_redline_ids", ARRAY(UUID), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True, server_default="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        sa.Column("checksum_sha256", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("review_id", "version_number", name="uq_version_per_review"),
    )


def downgrade() -> None:
    op.drop_table("contract_document_versions")
