"""add clause recommendation rules and audit tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-27 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create clause_recommendation_rules table
    op.create_table(
        "clause_recommendation_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("clause_id", sa.String(36), nullable=False),
        sa.Column("clause_version", sa.Integer(), server_default="1"),
        sa.Column("recommendation_type", sa.String(20), server_default="recommended"),
        sa.Column("variable_key", sa.String(200), nullable=False),
        sa.Column("operator", sa.String(20), nullable=False),
        sa.Column("condition_value", JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("template_id", sa.String(36), nullable=True),
        sa.Column("business_unit", sa.String(100), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_recommendation_rules_tenant_active",
        "clause_recommendation_rules",
        ["tenant_id", "is_active"],
    )
    op.create_index(
        "ix_recommendation_rules_variable",
        "clause_recommendation_rules",
        ["tenant_id", "variable_key"],
    )

    # Create clause_recommendation_audit table
    op.create_table(
        "clause_recommendation_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("review_id", sa.String(36), nullable=True),
        sa.Column("generated_contract_id", sa.String(36), nullable=True),
        sa.Column("template_id", sa.String(36), nullable=True),
        sa.Column("variable_values", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("rules_evaluated", sa.Integer(), server_default="0"),
        sa.Column("rules_matched", sa.Integer(), server_default="0"),
        sa.Column("suggested_clauses", JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("accepted_clause_ids", JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("rejected_clause_ids", JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_recommendation_audit_review",
        "clause_recommendation_audit",
        ["review_id"],
    )
    op.create_index(
        "ix_recommendation_audit_tenant_created",
        "clause_recommendation_audit",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("clause_recommendation_audit")
    op.drop_table("clause_recommendation_rules")
