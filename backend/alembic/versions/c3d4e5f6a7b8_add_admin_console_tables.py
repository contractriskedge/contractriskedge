"""Add admin console tables and bootstrap seed data.

Revision ID: c3d4e5f6a7b8
Revises: f4a1c8e2b9d0
Create Date: 2026-05-18
"""

from __future__ import annotations

import json
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "f4a1c8e2b9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEV_TENANT_ID = "00000000-0000-4000-8000-000000000001"
DEV_USER_ID = "dev-user"

# Canonical admin-console roles (matches AdminUser.role / AdminUserCreate pattern).
ROLE_SEEDS: list[tuple[str, str, str, list[str]]] = [
    (
        "admin",
        "Administrator",
        "Full platform administration",
        [
            "contracts:read", "contracts:write", "contracts:delete", "contracts:approve",
            "ai:analyze", "ai:view", "ai:manage",
            "workflows:read", "workflows:write", "workflows:approve", "workflows:escalate",
            "vendors:read", "vendors:write",
            "audit:read", "audit:export",
            "users:read", "users:write", "users:delete",
            "admin:tenant", "admin:system",
        ],
    ),
    (
        "legal_ops",
        "Legal Operations",
        "Contract lifecycle and workflow management",
        [
            "contracts:read", "contracts:write", "contracts:approve",
            "workflows:read", "workflows:write", "workflows:approve", "workflows:escalate",
            "ai:view", "ai:analyze",
            "audit:read",
            "users:read",
        ],
    ),
    (
        "reviewer",
        "Reviewer",
        "Review and annotate contracts",
        [
            "contracts:read",
            "workflows:read", "workflows:write",
            "ai:view",
        ],
    ),
    (
        "compliance",
        "Compliance",
        "Audit, policy, and regulatory oversight",
        [
            "contracts:read",
            "audit:read", "audit:export",
            "workflows:read",
            "ai:view",
        ],
    ),
    (
        "executive",
        "Executive",
        "Read-only executive visibility",
        [
            "contracts:read",
            "workflows:read",
            "audit:read",
            "ai:view",
        ],
    ),
    (
        "viewer",
        "Viewer",
        "Read-only access",
        [
            "contracts:read",
            "workflows:read",
            "ai:view",
        ],
    ),
    (
        "ai_ops",
        "AI Operations",
        "AI pipeline and model administration",
        [
            "ai:analyze", "ai:view", "ai:manage",
            "contracts:read",
            "admin:tenant",
        ],
    ),
]


def upgrade() -> None:
    op.create_table(
        "admin_roles",
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("role_id"),
    )

    op.create_table(
        "admin_users",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False, server_default="viewer"),
        sa.Column("business_unit", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_invited", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("invited_by", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_admin_users_tenant_id"), "admin_users", ["tenant_id"], unique=False)

    op.create_table(
        "tenant_settings",
        sa.Column("settings_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("brand_name", sa.Text(), nullable=True),
        sa.Column("brand_logo_url", sa.Text(), nullable=True),
        sa.Column("brand_primary_color", sa.Text(), nullable=True, server_default="#1B3A6B"),
        sa.Column("brand_accent_color", sa.Text(), nullable=True, server_default="#C9A84C"),
        sa.Column("ai_model", sa.Text(), nullable=True, server_default="gpt-4o"),
        sa.Column("ai_temperature", sa.Integer(), nullable=True, server_default="10"),
        sa.Column("ai_max_tokens", sa.Integer(), nullable=True, server_default="4096"),
        sa.Column("ai_embedding_model", sa.Text(), nullable=True, server_default="text-embedding-3-small"),
        sa.Column("ai_token_budget_daily", sa.Integer(), nullable=True, server_default="1000000"),
        sa.Column("ai_token_budget_monthly", sa.Integer(), nullable=True, server_default="30000000"),
        sa.Column("risk_threshold_critical", sa.Integer(), nullable=True, server_default="70"),
        sa.Column("risk_threshold_high", sa.Integer(), nullable=True, server_default="50"),
        sa.Column("risk_threshold_medium", sa.Integer(), nullable=True, server_default="30"),
        sa.Column("sla_critical_hours", sa.Integer(), nullable=True, server_default="24"),
        sa.Column("sla_high_hours", sa.Integer(), nullable=True, server_default="48"),
        sa.Column("sla_medium_hours", sa.Integer(), nullable=True, server_default="72"),
        sa.Column("sla_low_hours", sa.Integer(), nullable=True, server_default="168"),
        sa.Column("default_notification_channel", sa.Text(), nullable=True, server_default="in_app"),
        sa.Column("digest_frequency", sa.Text(), nullable=True, server_default="instant"),
        sa.Column("retention_days", sa.Integer(), nullable=True, server_default="365"),
        sa.Column("audit_retention_days", sa.Integer(), nullable=True, server_default="730"),
        sa.Column(
            "features_enabled",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(
                """'{"ai_analysis": true, "redlines": true, "semantic_search": true, """
                """"bulk_operations": true, "exports": true, "notifications": true, """
                """"automation": false}'::jsonb"""
            ),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settings_id"),
        sa.UniqueConstraint("tenant_id"),
    )
    op.create_index(op.f("ix_tenant_settings_tenant_id"), "tenant_settings", ["tenant_id"], unique=True)

    conn = op.get_bind()

    for role_id, name, description, permissions in ROLE_SEEDS:
        conn.execute(
            sa.text("""
                INSERT INTO admin_roles (role_id, name, description, permissions, is_system)
                VALUES (:role_id, :name, :description, CAST(:permissions AS jsonb), true)
                ON CONFLICT (role_id) DO NOTHING
            """),
            {
                "role_id": role_id,
                "name": name,
                "description": description,
                "permissions": json.dumps(permissions),
            },
        )

    settings_id = str(uuid.uuid4())
    conn.execute(
        sa.text("""
            INSERT INTO tenant_settings (
                settings_id, tenant_id, brand_name,
                risk_threshold_critical, risk_threshold_high
            )
            VALUES (
                CAST(:settings_id AS uuid), CAST(:tenant_id AS uuid), :brand_name,
                70, 50
            )
            ON CONFLICT (tenant_id) DO NOTHING
        """),
        {
            "settings_id": settings_id,
            "tenant_id": DEV_TENANT_ID,
            "brand_name": "ContractRiskEdge",
        },
    )

    conn.execute(
        sa.text("""
            INSERT INTO admin_users (
                user_id, tenant_id, email, name, role,
                is_active, is_invited, preferences
            )
            VALUES (
                :user_id, CAST(:tenant_id AS uuid), :email, :name, 'admin',
                true, false, '{}'::jsonb
            )
            ON CONFLICT (user_id) DO NOTHING
        """),
        {
            "user_id": DEV_USER_ID,
            "tenant_id": DEV_TENANT_ID,
            "email": "dev@contractriskedge.local",
            "name": "Development Admin",
        },
    )

    # RLS after bootstrap seed (migration role has no app.tenant_id set).
    for table in ("admin_users", "tenant_settings"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
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
    for table in ("tenant_settings", "admin_users"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_index(op.f("ix_tenant_settings_tenant_id"), table_name="tenant_settings")
    op.drop_table("tenant_settings")
    op.drop_index(op.f("ix_admin_users_tenant_id"), table_name="admin_users")
    op.drop_table("admin_users")
    op.drop_table("admin_roles")
