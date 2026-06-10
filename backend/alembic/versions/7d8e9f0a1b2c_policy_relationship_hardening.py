"""policy_relationship_hardening

Revision ID: 7d8e9f0a1b2c
Revises: 6cba5ff6e285
Create Date: 2026-06-09 17:00:00.000000

Hardens policy entity relationships:

1. Adds contract_uuid_id FK to policy_evaluations, policy_overrides,
   and clause_recommendations for direct contract traceability.

2. Makes review_id NOT NULL on policy_evaluations, policy_overrides,
   and clause_recommendations (after backfill).

3. Backfills contract_uuid_id from contract_reviews via upload_id join.

Navigation path for all policy entities:
  entity → upload_id → contract_reviews.upload_id → contract_reviews
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "7d8e9f0a1b2c"
down_revision: Union[str, Sequence[str], None] = "6cba5ff6e285"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. policy_evaluations ──────────────────────────────────────
    op.execute("""
        ALTER TABLE policy_evaluations
        ADD COLUMN IF NOT EXISTS contract_uuid_id UUID REFERENCES contract_reviews(review_id) ON DELETE SET NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_policy_evaluations_contract_uuid_id
        ON policy_evaluations (contract_uuid_id);
    """)
    # Backfill contract_uuid_id from contract_reviews via upload_id
    op.execute("""
        UPDATE policy_evaluations pe
        SET contract_uuid_id = cr.review_id
        FROM contract_reviews cr
        WHERE pe.upload_id = cr.upload_id
          AND pe.contract_uuid_id IS NULL;
    """)
    # Make review_id NOT NULL (all existing records have it)
    op.execute("""
        ALTER TABLE policy_evaluations ALTER COLUMN review_id SET NOT NULL;
    """)

    # ── 2. policy_overrides ────────────────────────────────────────
    op.execute("""
        ALTER TABLE policy_overrides
        ADD COLUMN IF NOT EXISTS contract_uuid_id UUID REFERENCES contract_reviews(review_id) ON DELETE SET NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_policy_overrides_contract_uuid_id
        ON policy_overrides (contract_uuid_id);
    """)
    # Backfill contract_uuid_id from contract_reviews via upload_id
    op.execute("""
        UPDATE policy_overrides po
        SET contract_uuid_id = cr.review_id
        FROM contract_reviews cr
        WHERE po.upload_id = cr.upload_id
          AND po.contract_uuid_id IS NULL;
    """)
    # Make review_id NOT NULL
    op.execute("""
        ALTER TABLE policy_overrides ALTER COLUMN review_id SET NOT NULL;
    """)

    # ── 3. clause_recommendations ──────────────────────────────────
    op.execute("""
        ALTER TABLE clause_recommendations
        ADD COLUMN IF NOT EXISTS contract_uuid_id UUID REFERENCES contract_reviews(review_id) ON DELETE SET NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_clause_recommendations_contract_uuid_id
        ON clause_recommendations (contract_uuid_id);
    """)
    # Backfill contract_uuid_id from contract_reviews via upload_id
    op.execute("""
        UPDATE clause_recommendations cr_rec
        SET contract_uuid_id = cr.review_id
        FROM contract_reviews cr
        WHERE cr_rec.upload_id = cr.upload_id
          AND cr_rec.contract_uuid_id IS NULL;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE policy_evaluations ALTER COLUMN review_id DROP NOT NULL;")
    op.execute("ALTER TABLE policy_overrides ALTER COLUMN review_id DROP NOT NULL;")
    for table in ["policy_evaluations", "policy_overrides", "clause_recommendations"]:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_contract_uuid_id;")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS contract_uuid_id;")
