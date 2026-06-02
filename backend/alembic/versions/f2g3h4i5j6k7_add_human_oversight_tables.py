"""add_human_oversight_tables

Revision ID: f2g3h4i5j6k7
Revises: e950eeefc32f
Create Date: 2026-06-01 10:00:00.000000

Creates tables:
- ai_approvals: AI recommendation approval workflows
- policy_exceptions: Structured policy exception requests
- acknowledgment_requirements: Reviewer acknowledgment of AI findings
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f2g3h4i5j6k7"
down_revision: Union[str, Sequence[str], None] = "e950eeefc32f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create human oversight tables."""

    # ── ai_approvals ──────────────────────────────────────────────
    op.create_table(
        "ai_approvals",
        sa.Column("approval_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("review_id", sa.Text(), nullable=False),
        sa.Column("upload_id", sa.Text(), nullable=False),
        sa.Column("approval_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("ai_recommendation", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("risk_impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="normal"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("finding_ids", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("redline_ids", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("rule_ids", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("required_approvers", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("required_roles", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("approval_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("approval_id"),
    )
    op.create_index(op.f("ix_ai_approvals_tenant_id"), "ai_approvals", ["tenant_id"])

    # ── policy_exceptions ─────────────────────────────────────────
    op.create_table(
        "policy_exceptions",
        sa.Column("exception_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("review_id", sa.Text(), nullable=False),
        sa.Column("upload_id", sa.Text(), nullable=False),
        sa.Column("rule_id", sa.Text(), nullable=True),
        sa.Column("rule_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("policy_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("clause_category", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("proposed_alternative", sa.Text(), nullable=True),
        sa.Column("risk_assessment", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("approval_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("previous_exception_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("exception_id"),
    )
    op.create_index(op.f("ix_policy_exceptions_tenant_id"), "policy_exceptions", ["tenant_id"])

    # ── acknowledgment_requirements ───────────────────────────────
    op.create_table(
        "acknowledgment_requirements",
        sa.Column("ack_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("review_id", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("mandatory", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("acknowledged_by", sa.Text(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ack_id"),
    )
    op.create_index(op.f("ix_acknowledgment_requirements_tenant_id"), "acknowledgment_requirements", ["tenant_id"])


def downgrade() -> None:
    """Downgrade schema — drop human oversight tables."""
    op.drop_table("acknowledgment_requirements")
    op.drop_table("policy_exceptions")
    op.drop_table("ai_approvals")
