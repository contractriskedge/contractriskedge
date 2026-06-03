"""add_email_redirect_tenant_settings

Adds email_redirect_enabled and email_redirect_to columns to tenant_settings.
When enabled, all outgoing emails are redirected to the specified address
(useful for testing/demo environments).

Revision ID: 8d458e3067ef
Revises: df2e1aba9afc
Create Date: 2026-06-03 13:48:21.721660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d458e3067ef'
down_revision: Union[str, Sequence[str], None] = 'df2e1aba9afc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenant_settings", sa.Column("email_redirect_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.add_column("tenant_settings", sa.Column("email_redirect_to", sa.Text, nullable=True))

    # Set default redirect for dev tenant
    op.execute("""
        UPDATE tenant_settings
        SET email_redirect_enabled = false,
            email_redirect_to = 'pgskannan@gmail.com'
        WHERE email_redirect_to IS NULL
    """)

    # Verification SQL:
    # SELECT tenant_id, email_redirect_enabled, email_redirect_to FROM tenant_settings;


def downgrade() -> None:
    op.drop_column("tenant_settings", "email_redirect_to")
    op.drop_column("tenant_settings", "email_redirect_enabled")
