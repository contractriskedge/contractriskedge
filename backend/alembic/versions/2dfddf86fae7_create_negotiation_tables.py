"""create negotiation tables

Revision ID: 2dfddf86fae7
Revises: 6ff4692ea980
Create Date: 2026-06-03 18:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2dfddf86fae7"
down_revision: Union[str, Sequence[str], None] = "6ff4692ea980"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create negotiation tables."""
    # ── negotiation_sessions ─────────────────────────────────────
    op.create_table(
        "negotiation_sessions",
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("contract_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("contract_title", sa.String(500), nullable=False),
        sa.Column("counterparty", sa.String(255), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False, server_default="drafting"),
        sa.Column("health_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["contract_id"], ["contract_reviews.review_id"],
                                ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"],
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_neg_sessions_tenant_id", "negotiation_sessions", ["tenant_id"])
    op.create_index("ix_neg_sessions_stage", "negotiation_sessions", ["stage"])
    op.create_index("ix_neg_sessions_contract_id", "negotiation_sessions", ["contract_id"])
    op.create_index("ix_neg_sessions_tenant_stage", "negotiation_sessions",
                    ["tenant_id", "stage"])
    op.create_index("ix_neg_sessions_tenant_created", "negotiation_sessions",
                    ["tenant_id", "created_at"])

    # ── negotiation_versions ─────────────────────────────────────
    op.create_table(
        "negotiation_versions",
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("author_avatar", sa.String(500), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("clauses", postgresql.JSONB, nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["negotiation_sessions.session_id"],
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("version_id"),
    )
    op.create_index("ix_neg_versions_session_id", "negotiation_versions", ["session_id"])
    op.create_index("ix_neg_versions_session", "negotiation_versions",
                    ["session_id", "version_number"])

    # ── negotiation_redlines ─────────────────────────────────────
    op.create_table(
        "negotiation_redlines",
        sa.Column("redline_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("clause_id", sa.String(100), nullable=False),
        sa.Column("type", sa.String(30), nullable=False, server_default="modification"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("modified_text", sa.Text(), nullable=True),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("author_avatar", sa.String(500), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("negotiation_impact", sa.String(20), nullable=True),
        sa.Column("benchmark_deviation", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["negotiation_sessions.session_id"],
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("redline_id"),
    )
    op.create_index("ix_neg_redlines_session_id", "negotiation_redlines", ["session_id"])
    op.create_index("ix_neg_redlines_clause_id", "negotiation_redlines", ["clause_id"])
    op.create_index("ix_neg_redlines_session_clause", "negotiation_redlines",
                    ["session_id", "clause_id"])
    op.create_index("ix_neg_redlines_session_status", "negotiation_redlines",
                    ["session_id", "status"])

    # ── negotiation_issues ───────────────────────────────────────
    op.create_table(
        "negotiation_issues",
        sa.Column("issue_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("clause_id", sa.String(100), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(20), nullable=False, server_default="major"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("assignee", sa.String(255), nullable=True),
        sa.Column("assignee_avatar", sa.String(500), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("category", sa.String(30), nullable=False, server_default="legal"),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["negotiation_sessions.session_id"],
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("issue_id"),
    )
    op.create_index("ix_neg_issues_session_id", "negotiation_issues", ["session_id"])
    op.create_index("ix_neg_issues_session_status", "negotiation_issues",
                    ["session_id", "status"])
    op.create_index("ix_neg_issues_session_severity", "negotiation_issues",
                    ["session_id", "severity"])

    # ── negotiation_comments ─────────────────────────────────────
    op.create_table(
        "negotiation_comments",
        sa.Column("comment_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("redline_id", sa.String(36), nullable=True),
        sa.Column("issue_id", sa.String(36), nullable=True),
        sa.Column("clause_id", sa.String(100), nullable=True),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("author_avatar", sa.String(500), nullable=True),
        sa.Column("author_role", sa.String(50), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("mentions", postgresql.JSONB, nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["negotiation_sessions.session_id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["negotiation_comments.comment_id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["redline_id"], ["negotiation_redlines.redline_id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["negotiation_issues.issue_id"],
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_index("ix_neg_comments_session_id", "negotiation_comments", ["session_id"])
    op.create_index("ix_neg_comments_session", "negotiation_comments", ["session_id"])
    op.create_index("ix_neg_comments_redline", "negotiation_comments", ["redline_id"])
    op.create_index("ix_neg_comments_issue", "negotiation_comments", ["issue_id"])

    # ── negotiation_participants ─────────────────────────────────
    op.create_table(
        "negotiation_participants",
        sa.Column("participant_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar", sa.String(500), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_clauses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_approvals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["negotiation_sessions.session_id"],
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("participant_id"),
    )
    op.create_index("ix_neg_participants_session_id", "negotiation_participants", ["session_id"])
    op.create_index("ix_neg_participants_session_role", "negotiation_participants",
                    ["session_id", "role"])


def downgrade() -> None:
    """Drop negotiation tables."""
    op.drop_table("negotiation_participants")
    op.drop_table("negotiation_comments")
    op.drop_table("negotiation_issues")
    op.drop_table("negotiation_redlines")
    op.drop_table("negotiation_versions")
    op.drop_table("negotiation_sessions")
