"""Add batch_uploads table and batch_id column to upload_sessions

Revision ID: a7b8c9d0e1f2
Revises: c6d7e8f9a0b1, f6a7b8c9d0e1
Create Date: 2026-05-26 16:30:00.000000

Adds:
  - batch_uploads table for tracking groups of uploaded files
  - batch_id FK column on upload_sessions linking to batch_uploads
  - batch_status enum type

This enables the batch upload workflow where multiple contract documents
are uploaded together and tracked as a single batch operation.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = (
    "c6d7e8f9a0b1",
    "f6a7b8c9d0e1",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add batch_uploads table and batch_id column to upload_sessions."""

    # Create batch_status enum type
    batch_status_values = (
        "pending",
        "uploading",
        "processing",
        "completed",
        "partial",
        "failed",
        "cancelled",
    )
    sa.Enum(*batch_status_values, name="batch_status").create(op.get_bind())

    # Create batch_uploads table
    op.create_table(
        "batch_uploads",
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_files", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_files", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "status",
            sa.Enum(
                *batch_status_values,
                name="batch_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("batch_id"),
        sa.UniqueConstraint("tenant_id", "batch_id", name="uq_batch_tenant"),
    )
    op.create_index(
        op.f("ix_batch_uploads_tenant_id"),
        "batch_uploads",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_batch_uploads_status"),
        "batch_uploads",
        ["status"],
        unique=False,
    )

    # Add batch_id column to upload_sessions
    op.add_column(
        "upload_sessions",
        sa.Column(
            "batch_id",
            sa.UUID(),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_upload_sessions_batch_id"),
        "upload_sessions",
        ["batch_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_upload_sessions_batch_id",
        "upload_sessions",
        "batch_uploads",
        ["batch_id"],
        ["batch_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove batch_id from upload_sessions and drop batch_uploads table."""
    # Remove FK and column from upload_sessions
    op.drop_constraint(
        "fk_upload_sessions_batch_id",
        "upload_sessions",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_upload_sessions_batch_id"),
        table_name="upload_sessions",
    )
    op.drop_column("upload_sessions", "batch_id")

    # Drop batch_uploads table
    op.drop_index(
        op.f("ix_batch_uploads_status"),
        table_name="batch_uploads",
    )
    op.drop_index(
        op.f("ix_batch_uploads_tenant_id"),
        table_name="batch_uploads",
    )
    op.drop_table("batch_uploads")

    # Drop batch_status enum type
    sa.Enum(name="batch_status").drop(op.get_bind())
