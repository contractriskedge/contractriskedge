"""add_compliance_domain_tables

Revision ID: e950eeefc32f
Revises: 64b88a831ccb
Create Date: 2026-06-01 09:05:52.972729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e950eeefc32f'
down_revision: Union[str, Sequence[str], None] = '64b88a831ccb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_frameworks",
        sa.Column("framework_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False, server_default="1.0"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.Text(), nullable=False, server_default="general"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("control_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.Text(), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("framework_id"),
    )
    op.create_index(op.f("ix_compliance_frameworks_tenant_id"), "compliance_frameworks", ["tenant_id"])

    op.create_table(
        "compliance_controls",
        sa.Column("control_id", sa.UUID(), nullable=False),
        sa.Column("framework_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("control_id_str", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.Text(), nullable=False, server_default="general"),
        sa.Column("risk_level", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.Text(), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["framework_id"], ["compliance_frameworks.framework_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("control_id"),
    )
    op.create_index(op.f("ix_compliance_controls_framework_id"), "compliance_controls", ["framework_id"])
    op.create_index(op.f("ix_compliance_controls_tenant_id"), "compliance_controls", ["tenant_id"])

    op.create_table(
        "compliance_assessments",
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("framework_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("total_controls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_controls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_controls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("compliance_percentage", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.Text(), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["framework_id"], ["compliance_frameworks.framework_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("assessment_id"),
    )
    op.create_index(op.f("ix_compliance_assessments_framework_id"), "compliance_assessments", ["framework_id"])
    op.create_index(op.f("ix_compliance_assessments_tenant_id"), "compliance_assessments", ["tenant_id"])

    op.create_table(
        "compliance_findings",
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("control_id", sa.UUID(), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to", sa.Text(), nullable=True),
        sa.Column("remediation_notes", sa.Text(), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.Text(), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["compliance_assessments.assessment_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["control_id"], ["compliance_controls.control_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("finding_id"),
    )
    op.create_index(op.f("ix_compliance_findings_assessment_id"), "compliance_findings", ["assessment_id"])
    op.create_index(op.f("ix_compliance_findings_control_id"), "compliance_findings", ["control_id"])
    op.create_index(op.f("ix_compliance_findings_tenant_id"), "compliance_findings", ["tenant_id"])

    op.create_table(
        "compliance_exceptions",
        sa.Column("exception_id", sa.UUID(), nullable=False),
        sa.Column("control_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("risk_assessment", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.Text(), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["control_id"], ["compliance_controls.control_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("exception_id"),
    )
    op.create_index(op.f("ix_compliance_exceptions_control_id"), "compliance_exceptions", ["control_id"])
    op.create_index(op.f("ix_compliance_exceptions_tenant_id"), "compliance_exceptions", ["tenant_id"])

    op.create_table(
        "compliance_evidence",
        sa.Column("evidence_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("evidence_type", sa.Text(), nullable=False),
        sa.Column("framework", sa.Text(), nullable=False),
        sa.Column("control_id", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="collected"),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_by", sa.Text(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("evidence_id"),
    )
    op.create_index(op.f("ix_compliance_evidence_tenant_id"), "compliance_evidence", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("compliance_evidence")
    op.drop_table("compliance_exceptions")
    op.drop_table("compliance_findings")
    op.drop_table("compliance_assessments")
    op.drop_table("compliance_controls")
    op.drop_table("compliance_frameworks")
