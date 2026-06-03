"""add_email_queue_table

Adds the email_queue table for async email delivery via Resend.
Stores pending emails with retry tracking and provider message IDs.

Revision ID: df2e1aba9afc
Revises: cacd9f177b1a
Create Date: 2026-06-03 13:26:30.997264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'df2e1aba9afc'
down_revision: Union[str, Sequence[str], None] = 'cacd9f177b1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_queue",
        sa.Column("email_id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("notification_id", UUID, sa.ForeignKey("notifications.notification_id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient_email", sa.Text, nullable=False, index=True),
        sa.Column("subject", sa.Text, nullable=False),
        sa.Column("template_name", sa.Text, nullable=False),
        sa.Column("template_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("provider_message_id", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default=sa.text("3")),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_queue_status_retry", "email_queue", ["status", "next_retry_at"])
    op.create_index("ix_email_queue_created", "email_queue", ["created_at"])

    # Verification SQL (run after migration):
    # SELECT status, COUNT(*) FROM email_queue GROUP BY status;
    # SELECT * FROM email_queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT 10;


def downgrade() -> None:
    op.drop_table("email_queue")
