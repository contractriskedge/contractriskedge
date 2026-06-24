"""create_signature_tables

Revision ID: 945eb119ab75
Revises: 52233979c668
Create Date: 2026-06-24 13:41:46.858539

Manually written — only creates signature_requests, signature_signers,
and signature_audit_events tables. Does NOT use autogenerate to avoid
accidental DROP of existing tables.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "945eb119ab75"
down_revision: Union[str, Sequence[str], None] = "52233979c668"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create signature_requests, signature_signers, signature_audit_events."""
    # ── signature_requests ──────────────────────────────────────
    op.create_table(
        "signature_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("contract_id", sa.String(36), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="draft", index=True),
        sa.Column("provider", sa.String(50), nullable=False, index=True),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB, default=dict),
        sa.Column("email_subject", sa.String(500), nullable=True),
        sa.Column("email_message", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_days", sa.Integer, nullable=False, default=3),
        sa.Column("allow_decline", sa.Boolean, nullable=False, default=True),
        sa.Column("allow_print", sa.Boolean, nullable=False, default=True),
        sa.Column("require_identity_verification", sa.Boolean, nullable=False, default=False),
        sa.Column("timezone", sa.String(50), nullable=False, default="UTC"),
        sa.Column("language", sa.String(10), nullable=False, default="en"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, default=dict),
    )
    op.create_index("idx_sig_req_tenant", "signature_requests", ["tenant_id"])
    op.create_index("idx_sig_req_contract", "signature_requests", ["contract_id"])
    op.create_index("idx_sig_req_status", "signature_requests", ["status"])
    op.create_index("idx_sig_req_provider", "signature_requests", ["provider"])

    # ── signature_signers ───────────────────────────────────────
    op.create_table(
        "signature_signers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("signature_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, default="signer"),
        sa.Column("signing_order", sa.Integer, nullable=False, default=1),
        sa.Column("routing_order", sa.Integer, nullable=False, default=1),
        sa.Column("authentication_type", sa.String(50), nullable=False, default="none"),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("access_code", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="awaiting", index=True),
        sa.Column("provider_recipient_id", sa.String(255), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_sig_signer_request", "signature_signers", ["request_id"])
    op.create_index("idx_sig_signer_email", "signature_signers", ["email"])

    # ── signature_audit_events ──────────────────────────────────
    op.create_table(
        "signature_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("signature_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB, default=dict),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("raw_payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_sig_audit_request", "signature_audit_events", ["request_id"])


def downgrade() -> None:
    """Drop signature tables."""
    op.drop_table("signature_audit_events")
    op.drop_table("signature_signers")
    op.drop_table("signature_requests")
