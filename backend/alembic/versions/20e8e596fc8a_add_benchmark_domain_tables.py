"""add_benchmark_domain_tables

Revision ID: 20e8e596fc8a
Revises: bbd84d9c7ee9
Create Date: 2026-05-28 08:07:24.976505

Creates the full benchmark domain schema using raw SQL to avoid
enum type conflicts with pre-existing types in the database.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20e8e596fc8a'
down_revision: Union[str, Sequence[str], None] = 'bbd84d9c7ee9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create benchmark domain + worker_heartbeats tables."""

    # ── Worker Heartbeats ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS worker_heartbeats (
            worker_id TEXT PRIMARY KEY,
            queue TEXT NOT NULL,
            status TEXT NOT NULL,
            tasks_completed INTEGER NOT NULL DEFAULT 0,
            tasks_failed INTEGER NOT NULL DEFAULT 0,
            last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            started_at TIMESTAMPTZ NOT NULL
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_worker_heartbeats_last_heartbeat_at ON worker_heartbeats (last_heartbeat_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worker_heartbeats_queue ON worker_heartbeats (queue);")

    # ── Benchmark Corpora ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_corpora (
            corpus_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            source TEXT NOT NULL DEFAULT 'uploaded',
            industry TEXT,
            geography TEXT,
            contract_type TEXT,
            document_count INTEGER NOT NULL DEFAULT 0,
            clause_count INTEGER NOT NULL DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}',
            is_active TEXT NOT NULL DEFAULT 'true',
            created_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, name)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_corpora_tenant_id ON benchmark_corpora (tenant_id);")

    # ── Benchmark Clauses ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_clauses (
            clause_id UUID PRIMARY KEY,
            corpus_id UUID NOT NULL REFERENCES benchmark_corpora(corpus_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            clause_text TEXT NOT NULL,
            clause_text_snippet TEXT,
            source_document TEXT,
            risk_score DOUBLE PRECISION,
            is_favorable TEXT,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_clauses_category ON benchmark_clauses (category);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_clauses_corpus_category ON benchmark_clauses (corpus_id, category);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_clauses_corpus_id ON benchmark_clauses (corpus_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_clauses_tenant_id ON benchmark_clauses (tenant_id);")
    # pgvector embedding column
    op.execute("ALTER TABLE benchmark_clauses ADD COLUMN IF NOT EXISTS embedding vector(1536);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_clauses_embedding ON benchmark_clauses USING ivfflat (embedding);")

    # ── Benchmark Corpus Approvals ────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_corpus_approvals (
            approval_id UUID PRIMARY KEY,
            corpus_id UUID NOT NULL UNIQUE REFERENCES benchmark_corpora(corpus_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            state TEXT NOT NULL DEFAULT 'draft',
            submitted_by TEXT,
            submitted_at TIMESTAMPTZ,
            reviewed_by TEXT,
            reviewed_at TIMESTAMPTZ,
            review_notes TEXT,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_corpus_approvals_tenant_id ON benchmark_corpus_approvals (tenant_id);")

    # ── Benchmark Jobs ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_jobs (
            job_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            progress_pct INTEGER NOT NULL DEFAULT 0,
            progress_message TEXT,
            error_message TEXT,
            error_details JSONB,
            corpus_id UUID REFERENCES benchmark_corpora(corpus_id) ON DELETE SET NULL,
            upload_id UUID,
            items_processed INTEGER NOT NULL DEFAULT 0,
            items_failed INTEGER NOT NULL DEFAULT 0,
            items_total INTEGER NOT NULL DEFAULT 0,
            result_summary JSONB,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_jobs_created ON benchmark_jobs (created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_jobs_tenant_id ON benchmark_jobs (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_jobs_tenant_status ON benchmark_jobs (tenant_id, status);")

    # ── Benchmark Corpus Versions ─────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_corpus_versions (
            version_id UUID PRIMARY KEY,
            corpus_id UUID NOT NULL REFERENCES benchmark_corpora(corpus_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            version_label TEXT,
            snapshot JSONB NOT NULL,
            clause_count INTEGER NOT NULL DEFAULT 0,
            change_description TEXT,
            created_by TEXT,
            job_id UUID REFERENCES benchmark_jobs(job_id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (corpus_id, version_number)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_corpus_versions_corpus_id ON benchmark_corpus_versions (corpus_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_corpus_versions_tenant_id ON benchmark_corpus_versions (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_corpus_versions_corpus ON benchmark_corpus_versions (corpus_id, version_number);")

    # ── Benchmark Dedupe Reports ──────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_dedupe_reports (
            report_id UUID PRIMARY KEY,
            corpus_id UUID NOT NULL REFERENCES benchmark_corpora(corpus_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            severity TEXT NOT NULL,
            clause_id_a UUID NOT NULL REFERENCES benchmark_clauses(clause_id) ON DELETE CASCADE,
            clause_id_b UUID NOT NULL REFERENCES benchmark_clauses(clause_id) ON DELETE CASCADE,
            similarity_score DOUBLE PRECISION NOT NULL,
            clause_category TEXT,
            detected_by TEXT,
            resolved TEXT NOT NULL DEFAULT 'false',
            resolution_action TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_dedupe_reports_corpus_id ON benchmark_dedupe_reports (corpus_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_dedupe_reports_tenant_id ON benchmark_dedupe_reports (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dedupe_corpus_severity ON benchmark_dedupe_reports (corpus_id, severity);")

    # ── Benchmark Scores ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_scores (
            score_id UUID PRIMARY KEY,
            upload_id UUID NOT NULL REFERENCES upload_sessions(upload_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            corpus_id UUID NOT NULL REFERENCES benchmark_corpora(corpus_id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            your_score DOUBLE PRECISION NOT NULL,
            market_median DOUBLE PRECISION NOT NULL,
            market_p25 DOUBLE PRECISION,
            market_p75 DOUBLE PRECISION,
            market_mean DOUBLE PRECISION,
            market_stddev DOUBLE PRECISION,
            percentile DOUBLE PRECISION NOT NULL,
            deviation DOUBLE PRECISION,
            deviation_percent DOUBLE PRECISION,
            direction TEXT,
            sample_size INTEGER NOT NULL DEFAULT 0,
            confidence DOUBLE PRECISION,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (upload_id, corpus_id, category)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_scores_tenant_id ON benchmark_scores (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_scores_upload ON benchmark_scores (upload_id, tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_scores_upload_id ON benchmark_scores (upload_id);")

    # ── Benchmark Lineage ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_lineage (
            lineage_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            corpus_id UUID NOT NULL REFERENCES benchmark_corpora(corpus_id) ON DELETE CASCADE,
            corpus_version_id UUID REFERENCES benchmark_corpus_versions(version_id) ON DELETE SET NULL,
            job_id UUID REFERENCES benchmark_jobs(job_id) ON DELETE SET NULL,
            operation TEXT NOT NULL,
            score_count_affected INTEGER NOT NULL DEFAULT 0,
            corpus_clause_count INTEGER NOT NULL DEFAULT 0,
            previous_lineage_id UUID,
            delta_summary JSONB,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_lineage_corpus ON benchmark_lineage (corpus_id, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_lineage_corpus_id ON benchmark_lineage (corpus_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_benchmark_lineage_tenant_id ON benchmark_lineage (tenant_id);")


def downgrade() -> None:
    """Downgrade schema — drop all benchmark domain + worker_heartbeats tables."""
    op.execute("DROP TABLE IF EXISTS benchmark_lineage CASCADE;")
    op.execute("DROP TABLE IF EXISTS benchmark_scores CASCADE;")
    op.execute("DROP TABLE IF EXISTS benchmark_dedupe_reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS benchmark_corpus_versions CASCADE;")
    op.execute("DROP TABLE IF EXISTS benchmark_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS benchmark_corpus_approvals CASCADE;")
    op.execute("DROP TABLE IF EXISTS benchmark_clauses CASCADE;")
    op.execute("DROP TABLE IF EXISTS benchmark_corpora CASCADE;")
    op.execute("DROP TABLE IF EXISTS worker_heartbeats CASCADE;")
