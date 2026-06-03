"""Add benchmark_job_type and benchmark_job_status enum types

Revision ID: f8a9b0c1d2e3
Revises: e54c0a390eea
Create Date: 2026-06-02 20:18:00.000000

Creates the PostgreSQL enum types benchmark_job_type and
benchmark_job_status that the SQLAlchemy model expects, then
alters the benchmark_jobs table columns from TEXT to the new
enum types.

The original migration (20e8e596fc8a) used TEXT columns to avoid
dependency issues, but the model uses SAEnum with create_type=False,
meaning the types must exist in the database at runtime.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e54c0a390eea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create enum types and alter benchmark_jobs columns."""

    # ── Create enum types ─────────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'benchmark_job_type') THEN
                CREATE TYPE benchmark_job_type AS ENUM (
                    'recompute_scores',
                    'refresh_embeddings',
                    'stale_detection',
                    'export_csv',
                    'corpus_refresh'
                );
            END IF;
        END
        $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'benchmark_job_status') THEN
                CREATE TYPE benchmark_job_status AS ENUM (
                    'pending',
                    'running',
                    'completed',
                    'failed',
                    'cancelled'
                );
            END IF;
        END
        $$;
    """)

    # ── Alter columns from TEXT to enum types ─────────────────────
    op.execute("""
        ALTER TABLE benchmark_jobs
            ALTER COLUMN job_type TYPE benchmark_job_type
            USING job_type::benchmark_job_type;
    """)

    op.execute("""
        ALTER TABLE benchmark_jobs
            ALTER COLUMN status TYPE benchmark_job_status
            USING status::benchmark_job_status;
    """)

    op.execute("""
        ALTER TABLE benchmark_jobs
            ALTER COLUMN status SET DEFAULT 'pending'::benchmark_job_status;
    """)


def downgrade() -> None:
    """Revert columns back to TEXT and drop enum types."""

    # ── Revert columns to TEXT ────────────────────────────────────
    op.execute("""
        ALTER TABLE benchmark_jobs
            ALTER COLUMN job_type TYPE TEXT;
    """)

    op.execute("""
        ALTER TABLE benchmark_jobs
            ALTER COLUMN status TYPE TEXT;
    """)

    op.execute("""
        ALTER TABLE benchmark_jobs
            ALTER COLUMN status SET DEFAULT 'pending';
    """)

    # ── Drop enum types ───────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS benchmark_job_type;")
    op.execute("DROP TYPE IF EXISTS benchmark_job_status;")
