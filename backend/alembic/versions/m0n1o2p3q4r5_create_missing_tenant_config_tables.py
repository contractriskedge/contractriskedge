"""create_missing_tenant_config_tables

Revision ID: m0n1o2p3q4r5
Revises: l0m1n2o3p4q5
Create Date: 2026-06-05 09:15:00.000000

Creates 3 missing database tables required by the tenant_config service:
  - policy_packs       — bundled policy/threshold/clause overrides
  - scoring_overrides  — tenant-specific risk scoring overrides
  - compliance_packs   — compliance pack definitions per region/regulation

These tables were designed in the service layer (raw SQL) but never had
Alembic migrations created. This migration fixes that gap.

See sprint23_task2.2_settings_foundation_fix.md for full audit.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "m0n1o2p3q4r5"
down_revision: Union[str, Sequence[str], None] = "l0m1n2o3p4q5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── policy_packs ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS policy_packs (
            pack_id VARCHAR(12) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            scope VARCHAR(50),
            region VARCHAR(100),
            industry VARCHAR(100),
            jurisdiction VARCHAR(100),
            playbook_id VARCHAR(36),
            rule_overrides JSONB DEFAULT '[]'::jsonb,
            threshold_overrides JSONB DEFAULT '[]'::jsonb,
            clause_overrides JSONB DEFAULT '[]'::jsonb,
            is_active BOOLEAN DEFAULT TRUE,
            version INTEGER DEFAULT 1,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_policy_packs_tenant_id ON policy_packs (tenant_id)")

    # ── scoring_overrides ────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS scoring_overrides (
            override_id VARCHAR(12) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            clause_type VARCHAR(255) NOT NULL,
            override_severity VARCHAR(50),
            override_risk_weight FLOAT,
            override_risk_score FLOAT,
            is_active BOOLEAN DEFAULT TRUE,
            reason TEXT,
            applies_to_business_units JSONB DEFAULT '[]'::jsonb,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_scoring_overrides_tenant_id ON scoring_overrides (tenant_id)")

    # ── compliance_packs ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS compliance_packs (
            pack_id VARCHAR(12) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            region VARCHAR(100) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            regulations JSONB DEFAULT '[]'::jsonb,
            required_clause_categories JSONB DEFAULT '[]'::jsonb,
            forbidden_clause_categories JSONB DEFAULT '[]'::jsonb,
            jurisdiction_rules JSONB DEFAULT '[]'::jsonb,
            is_active BOOLEAN DEFAULT TRUE,
            version INTEGER DEFAULT 1,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_compliance_packs_tenant_id ON compliance_packs (tenant_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS compliance_packs CASCADE")
    op.execute("DROP TABLE IF EXISTS scoring_overrides CASCADE")
    op.execute("DROP TABLE IF EXISTS policy_packs CASCADE")
