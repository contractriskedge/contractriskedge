"""Enable RLS on upload_sessions for tenant isolation.

Revision ID: f4a1c8e2b9d0
Revises: 3a8f6d9e1b2c
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "f4a1c8e2b9d0"
down_revision: Union[str, None] = "3a8f6d9e1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE upload_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE upload_sessions FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS upload_sessions_tenant_isolation ON upload_sessions")
    op.execute("""
        CREATE POLICY upload_sessions_tenant_isolation ON upload_sessions
        FOR ALL
        USING (
            NULLIF(current_setting('app.tenant_id', true), '') IS NOT NULL
            AND tenant_id::text = current_setting('app.tenant_id', true)
        )
        WITH CHECK (
            NULLIF(current_setting('app.tenant_id', true), '') IS NOT NULL
            AND tenant_id::text = current_setting('app.tenant_id', true)
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS upload_sessions_tenant_isolation ON upload_sessions")
    op.execute("ALTER TABLE upload_sessions NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE upload_sessions DISABLE ROW LEVEL SECURITY")
