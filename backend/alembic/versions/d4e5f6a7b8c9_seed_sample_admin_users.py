"""Seed sample admin users for each role.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEV_TENANT_ID = "00000000-0000-4000-8000-000000000001"

# One sample user per admin-console role (admin user already seeded in prior migration).
SAMPLE_USERS: list[tuple[str, str, str, str, str]] = [
    ("user-legal-ops", "sarah.chen@contractriskedge.local", "Sarah Chen", "legal_ops", "Legal"),
    ("user-reviewer", "mike.johnson@contractriskedge.local", "Mike Johnson", "reviewer", "Procurement"),
    ("user-compliance", "lisa.patel@contractriskedge.local", "Lisa Patel", "compliance", "Compliance"),
    ("user-executive", "david.williams@contractriskedge.local", "David Williams", "executive", "Executive"),
    ("user-viewer", "alex.kim@contractriskedge.local", "Alex Kim", "viewer", "Sales"),
    ("user-ai-ops", "jordan.taylor@contractriskedge.local", "Jordan Taylor", "ai_ops", "Engineering"),
]


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(f"SET LOCAL app.tenant_id = '{DEV_TENANT_ID}'"))
    for user_id, email, name, role, business_unit in SAMPLE_USERS:
        conn.execute(
            sa.text("""
                INSERT INTO admin_users (
                    user_id, tenant_id, email, name, role, business_unit,
                    is_active, is_invited, preferences
                )
                VALUES (
                    :user_id, CAST(:tenant_id AS uuid), :email, :name, :role, :business_unit,
                    true, false, '{}'::jsonb
                )
                ON CONFLICT (user_id) DO NOTHING
            """),
            {
                "user_id": user_id,
                "tenant_id": DEV_TENANT_ID,
                "email": email,
                "name": name,
                "role": role,
                "business_unit": business_unit,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(f"SET LOCAL app.tenant_id = '{DEV_TENANT_ID}'"))
    for user_id, *_ in SAMPLE_USERS:
        conn.execute(
            sa.text("DELETE FROM admin_users WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
