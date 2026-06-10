"""obligation_contract_hardening

Revision ID: 6cba5ff6e285
Revises: cc234500e3be
Create Date: 2026-06-09 16:30:00.000000

Hardens obligation-to-contract relationship:

1. Adds contract_uuid_id FK to obligation_audit_log for direct contract
   traceability on every audit event.

2. Backfills contract_uuid_id on existing obligations where possible
   by matching contract_id string to contract_reviews review_id.

3. Makes contract_uuid_id NOT NULL on obligations (after backfill).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "6cba5ff6e285"
down_revision: Union[str, Sequence[str], None] = "cc234500e3be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add contract_uuid_id to obligation_audit_log ───────────
    op.execute("""
        ALTER TABLE obligation_audit_log
        ADD COLUMN IF NOT EXISTS contract_uuid_id UUID REFERENCES contract_reviews(review_id) ON DELETE SET NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_obligation_audit_log_contract_uuid_id
        ON obligation_audit_log (contract_uuid_id);
    """)

    # Backfill contract_uuid_id on audit logs from linked obligations
    op.execute("""
        UPDATE obligation_audit_log al
        SET contract_uuid_id = o.contract_uuid_id
        FROM obligations o
        WHERE al.obligation_id = o.id
          AND al.contract_uuid_id IS NULL
          AND o.contract_uuid_id IS NOT NULL;
    """)

    # ── 2. Backfill contract_uuid_id on orphan obligations ────────
    # Try matching by contract_id string -> review_id UUID
    op.execute("""
        UPDATE obligations o
        SET contract_uuid_id = r.review_id,
            contract_name = COALESCE(o.contract_name, r.metadata->>'name'),
            vendor = COALESCE(o.vendor, r.metadata->>'vendor')
        FROM contract_reviews r
        WHERE o.contract_uuid_id IS NULL
          AND o.contract_id IS NOT NULL
          AND r.review_id::text = o.contract_id;
    """)

    # For remaining orphans, try matching by contract_name
    op.execute("""
        UPDATE obligations o
        SET contract_uuid_id = r.review_id,
            contract_name = COALESCE(o.contract_name, r.metadata->>'name'),
            vendor = COALESCE(o.vendor, r.metadata->>'vendor')
        FROM contract_reviews r
        WHERE o.contract_uuid_id IS NULL
          AND o.contract_name IS NOT NULL
          AND (r.metadata->>'name') ILIKE '%' || o.contract_name || '%';
    """)

    # ── 3. Make contract_uuid_id NOT NULL on obligations ──────────
    op.execute("""
        ALTER TABLE obligations ALTER COLUMN contract_uuid_id SET NOT NULL;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE obligations ALTER COLUMN contract_uuid_id DROP NOT NULL;")
    op.execute("DROP INDEX IF EXISTS ix_obligation_audit_log_contract_uuid_id;")
    op.execute("ALTER TABLE obligation_audit_log DROP COLUMN IF EXISTS contract_uuid_id;")
