"""add policy linkage columns to review_findings

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2026-06-08 14:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h3i4j5k6l7m8"
down_revision: Union[str, Sequence[str], None] = "g2h3i4j5k6l7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "review_findings",
        sa.Column("playbook_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "review_findings",
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "review_findings",
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "review_findings",
        sa.Column("clause_standard_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("review_findings", sa.Column("policy_owner", sa.Text(), nullable=True))
    op.create_index("ix_review_findings_playbook_id", "review_findings", ["playbook_id"])
    op.create_index("ix_review_findings_rule_id", "review_findings", ["rule_id"])
    op.create_foreign_key(
        "fk_review_findings_playbook_id",
        "review_findings",
        "legal_playbooks",
        ["playbook_id"],
        ["playbook_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_review_findings_rule_id",
        "review_findings",
        "policy_rules",
        ["rule_id"],
        ["rule_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_review_findings_evaluation_id",
        "review_findings",
        "policy_evaluations",
        ["evaluation_id"],
        ["evaluation_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_review_findings_evaluation_id", "review_findings", type_="foreignkey")
    op.drop_constraint("fk_review_findings_rule_id", "review_findings", type_="foreignkey")
    op.drop_constraint("fk_review_findings_playbook_id", "review_findings", type_="foreignkey")
    op.drop_index("ix_review_findings_rule_id", table_name="review_findings")
    op.drop_index("ix_review_findings_playbook_id", table_name="review_findings")
    op.drop_column("review_findings", "policy_owner")
    op.drop_column("review_findings", "clause_standard_id")
    op.drop_column("review_findings", "evaluation_id")
    op.drop_column("review_findings", "rule_id")
    op.drop_column("review_findings", "playbook_id")
