"""Add AI governance prompt registry, evaluation, and audit tables.

This migration creates the following tables:

- prompt_templates: prompt registry with versioning and active/draft states
- eval_datasets: evaluation datasets containing test cases for prompts
- eval_runs: recorded evaluation runs for prompt datasets
- model_audit_log: model audit events for prompt executions

Revision ID: j0a1b2c3d4e5
Revises: bbd84d9c7ee9
Create Date: 2026-06-01 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "j0a1b2c3d4e5"
down_revision: Union[str, None] = "bbd84d9c7ee9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("version_id", sa.Text, nullable=False),
        sa.Column("prompt_key", sa.Text, nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("template", sa.Text, nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("default_model", sa.Text, nullable=True),
        sa.Column("default_temperature", sa.Float, nullable=True),
        sa.Column("default_max_tokens", sa.Integer, nullable=True),
        sa.Column("response_schema", JSONB, nullable=True),
        sa.Column("tags", JSONB, nullable=True),
        sa.Column("state", sa.Text, nullable=False),
        sa.Column("diff_from_previous", sa.Text, nullable=True),
        sa.Column("previous_version_id", sa.Text, nullable=True),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("version_id"),
    )
    op.create_index("ix_prompt_templates_prompt_key", "prompt_templates", ["prompt_key"])
    op.create_index(
        "ix_prompt_templates_prompt_key_version",
        "prompt_templates",
        ["prompt_key", "version_number"],
        unique=False,
    )

    op.create_table(
        "eval_datasets",
        sa.Column("dataset_id", sa.Text, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("prompt_key", sa.Text, nullable=False),
        sa.Column("test_cases", JSONB, nullable=True),
        sa.Column("tags", JSONB, nullable=True),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("dataset_id"),
    )
    op.create_index("ix_eval_datasets_tenant_id", "eval_datasets", ["tenant_id"])
    op.create_index("ix_eval_datasets_prompt_key", "eval_datasets", ["prompt_key"])

    op.create_table(
        "eval_runs",
        sa.Column("run_id", sa.Text, nullable=False),
        sa.Column("dataset_id", sa.Text, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("prompt_key", sa.Text, nullable=True),
        sa.Column("prompt_version", sa.Integer, nullable=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("total_tests", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("passed", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("failed", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("warnings", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("pass_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_latency_ms", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["eval_datasets.dataset_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_eval_runs_dataset_id", "eval_runs", ["dataset_id"])
    op.create_index("ix_eval_runs_tenant_id", "eval_runs", ["tenant_id"])

    op.create_table(
        "model_audit_log",
        sa.Column("event_id", sa.Text, nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("prompt_key", sa.Text, nullable=True),
        sa.Column("prompt_version", sa.Integer, nullable=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("provider", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("error_type", sa.Text, nullable=True),
        sa.Column("request_id", sa.Text, nullable=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_model_audit_log_tenant_id", "model_audit_log", ["tenant_id"])
    op.create_index("ix_model_audit_log_created_at", "model_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_audit_log_created_at", table_name="model_audit_log")
    op.drop_index("ix_model_audit_log_tenant_id", table_name="model_audit_log")
    op.drop_table("model_audit_log")

    op.drop_index("ix_eval_runs_tenant_id", table_name="eval_runs")
    op.drop_index("ix_eval_runs_dataset_id", table_name="eval_runs")
    op.drop_table("eval_runs")

    op.drop_index("ix_eval_datasets_prompt_key", table_name="eval_datasets")
    op.drop_index("ix_eval_datasets_tenant_id", table_name="eval_datasets")
    op.drop_table("eval_datasets")

    op.drop_index("ix_prompt_templates_prompt_key_version", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_prompt_key", table_name="prompt_templates")
    op.drop_table("prompt_templates")
