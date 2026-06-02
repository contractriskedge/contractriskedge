"""add_clause_intelligence_tables

Revision ID: c1a2b3c4d5e6
Revises: 20e8e596fc8a
Create Date: 2026-05-28 12:00:00.000000

Creates clause intelligence domain tables:
- clauses — Core clause records with AI analysis
- clause_versions — Version history
- clause_embeddings — Vector embeddings for semantic search
- clause_benchmarks — Market benchmark data
- negotiation_history — Negotiation outcome tracking
- clause_usage — Usage analytics
- fallback_clauses — Preferred fallback language
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "20e8e596fc8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Clauses ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS clauses (
            clause_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            clause_type TEXT,
            text TEXT NOT NULL,
            jurisdiction TEXT,
            contract_types TEXT[] NOT NULL DEFAULT '{}',
            risk_score DOUBLE PRECISION,
            risk_level TEXT,
            ai_confidence DOUBLE PRECISION,
            ai_explanation TEXT,
            negotiation_strength DOUBLE PRECISION,
            negotiation_guidance TEXT,
            benchmark_percentile DOUBLE PRECISION,
            usage_frequency INTEGER NOT NULL DEFAULT 0,
            approval_status TEXT NOT NULL DEFAULT 'draft',
            owner TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            is_favorite BOOLEAN NOT NULL DEFAULT FALSE,
            tags TEXT[] NOT NULL DEFAULT '{}',
            governance_notes TEXT,
            deviation_frequency INTEGER NOT NULL DEFAULT 0,
            market_percentile DOUBLE PRECISION,
            playbook_linkage TEXT,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_clauses_tenant_id ON clauses (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clauses_category ON clauses (category);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clauses_approval_status ON clauses (approval_status);")

    # ── Clause Versions ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS clause_versions (
            version_id UUID PRIMARY KEY,
            clause_id UUID NOT NULL REFERENCES clauses(clause_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            risk_score DOUBLE PRECISION,
            change_description TEXT,
            created_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_clause_versions_clause_id ON clause_versions (clause_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clause_versions_tenant_id ON clause_versions (tenant_id);")

    # ── Clause Embeddings ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS clause_embeddings (
            embedding_id UUID PRIMARY KEY,
            clause_id UUID NOT NULL UNIQUE REFERENCES clauses(clause_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            embedding_model TEXT NOT NULL,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_clause_embeddings_clause_id ON clause_embeddings (clause_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clause_embeddings_tenant_id ON clause_embeddings (tenant_id);")

    # ── Clause Benchmarks ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS clause_benchmarks (
            benchmark_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            jurisdiction TEXT,
            market_median DOUBLE PRECISION NOT NULL,
            market_p25 DOUBLE PRECISION,
            market_p75 DOUBLE PRECISION,
            sample_size INTEGER NOT NULL DEFAULT 0,
            avg_risk_score DOUBLE PRECISION,
            acceptance_rate DOUBLE PRECISION,
            deviation_rate DOUBLE PRECISION,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_clause_benchmarks_tenant_id ON clause_benchmarks (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clause_benchmarks_category ON clause_benchmarks (category);")

    # ── Negotiation History ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS negotiation_history (
            history_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            clause_id UUID NOT NULL REFERENCES clauses(clause_id) ON DELETE CASCADE,
            counterparty TEXT,
            original_text TEXT NOT NULL,
            negotiated_text TEXT,
            outcome TEXT,
            risk_delta DOUBLE PRECISION,
            strategy_used TEXT,
            success BOOLEAN,
            created_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_negotiation_history_tenant_id ON negotiation_history (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_negotiation_history_clause_id ON negotiation_history (clause_id);")

    # ── Clause Usage ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS clause_usage (
            usage_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            clause_id UUID NOT NULL REFERENCES clauses(clause_id) ON DELETE CASCADE,
            contract_id TEXT,
            used_as TEXT,
            was_accepted BOOLEAN,
            was_deviated BOOLEAN NOT NULL DEFAULT FALSE,
            deviation_reason TEXT,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_clause_usage_tenant_id ON clause_usage (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clause_usage_clause_id ON clause_usage (clause_id);")

    # ── Fallback Clauses ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS fallback_clauses (
            fallback_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            label TEXT NOT NULL,
            text TEXT NOT NULL,
            risk_score DOUBLE PRECISION,
            negotiation_strength DOUBLE PRECISION,
            usage_rate DOUBLE PRECISION,
            is_preferred BOOLEAN NOT NULL DEFAULT FALSE,
            jurisdiction TEXT,
            created_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_fallback_clauses_tenant_id ON fallback_clauses (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fallback_clauses_category ON fallback_clauses (category);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fallback_clauses CASCADE;")
    op.execute("DROP TABLE IF EXISTS clause_usage CASCADE;")
    op.execute("DROP TABLE IF EXISTS negotiation_history CASCADE;")
    op.execute("DROP TABLE IF EXISTS clause_benchmarks CASCADE;")
    op.execute("DROP TABLE IF EXISTS clause_embeddings CASCADE;")
    op.execute("DROP TABLE IF EXISTS clause_versions CASCADE;")
    op.execute("DROP TABLE IF EXISTS clauses CASCADE;")
