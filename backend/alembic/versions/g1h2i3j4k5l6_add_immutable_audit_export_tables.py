"""Add immutable audit export job and artifact tables.

This migration adds two new tables:

- audit_export_jobs: append-only export job metadata, filter predicates,
  status, manifest signature, and chain-of-custody details.
- audit_export_artifacts: artifact metadata for each export file, including
  storage key and SHA256 hash for integrity verification.

Revision ID: g1h2i3j4k5l6
Revises: f7b8c9d0e1f2
Create Date: 2026-05-27 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "f7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_export_jobs",
        sa.Column("job_id", UUID, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("actor_role", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("output_format", sa.Text(), nullable=False),
        sa.Column("filter_params", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("export_reason", sa.Text(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("artifact_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("manifest_hash", sa.Text(), nullable=True),
        sa.Column("manifest_signature", sa.Text(), nullable=True),
        sa.Column("chain_of_custody", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        "ix_audit_export_jobs_tenant_id",
        "audit_export_jobs",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_export_jobs_status",
        "audit_export_jobs",
        ["status"],
        unique=False,
    )
    op.create_table(
        "audit_export_artifacts",
        sa.Column("artifact_id", UUID, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("content_length", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["audit_export_jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index(
        "ix_audit_export_artifacts_job_id",
        "audit_export_artifacts",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_export_artifacts_tenant_id",
        "audit_export_artifacts",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_export_artifacts_tenant_id", table_name="audit_export_artifacts")
    op.drop_index("ix_audit_export_artifacts_job_id", table_name="audit_export_artifacts")
    op.drop_table("audit_export_artifacts")
    op.drop_index("ix_audit_export_jobs_status", table_name="audit_export_jobs")
    op.drop_index("ix_audit_export_jobs_tenant_id", table_name="audit_export_jobs")
    op.drop_table("audit_export_jobs")
