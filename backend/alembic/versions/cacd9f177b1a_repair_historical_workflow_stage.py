"""repair_historical_workflow_stage

Repair workflow_stage values for reviews created before the
derive_workflow_stage() helper was implemented.

Only updates rows where workflow_stage is NULL or does not match
the correct value for the review's current status.

Migration is idempotent — safe to run multiple times.

Revision ID: cacd9f177b1a
Revises: 47565f229d4b
Create Date: 2026-06-03 10:53:11.117245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cacd9f177b1a'
down_revision: Union[str, Sequence[str], None] = '47565f229d4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # ── 1. status='closed' → workflow_stage='archived' ──
    result = connection.execute(sa.text("""
        UPDATE contract_reviews
        SET workflow_stage = 'archived', updated_at = NOW()
        WHERE status = 'closed'
          AND is_deleted = FALSE
          AND (workflow_stage IS NULL OR workflow_stage != 'archived')
    """))
    print(f"  closed -> archived: {result.rowcount} rows")

    # ── 2. status='approved' → workflow_stage='completed' ──
    result = connection.execute(sa.text("""
        UPDATE contract_reviews
        SET workflow_stage = 'completed', updated_at = NOW()
        WHERE status = 'approved'
          AND is_deleted = FALSE
          AND (workflow_stage IS NULL OR workflow_stage != 'completed')
    """))
    print(f"  approved -> completed: {result.rowcount} rows")

    # ── 3. status='legal_approval' → workflow_stage='legal_ops' ──
    result = connection.execute(sa.text("""
        UPDATE contract_reviews
        SET workflow_stage = 'legal_ops', updated_at = NOW()
        WHERE status = 'legal_approval'
          AND is_deleted = FALSE
          AND (workflow_stage IS NULL OR workflow_stage != 'legal_ops')
    """))
    print(f"  legal_approval -> legal_ops: {result.rowcount} rows")

    # ── 4. status='exec_approval' → workflow_stage='executive' ──
    result = connection.execute(sa.text("""
        UPDATE contract_reviews
        SET workflow_stage = 'executive', updated_at = NOW()
        WHERE status = 'exec_approval'
          AND is_deleted = FALSE
          AND (workflow_stage IS NULL OR workflow_stage != 'executive')
    """))
    print(f"  exec_approval -> executive: {result.rowcount} rows")

    # ── 5. status='escalated' → workflow_stage='escalated' ──
    result = connection.execute(sa.text("""
        UPDATE contract_reviews
        SET workflow_stage = 'escalated', updated_at = NOW()
        WHERE status = 'escalated'
          AND is_deleted = FALSE
          AND (workflow_stage IS NULL OR workflow_stage != 'escalated')
    """))
    print(f"  escalated -> escalated: {result.rowcount} rows")

    # ── 6. status='in_review' → workflow_stage='reviewer' ──
    result = connection.execute(sa.text("""
        UPDATE contract_reviews
        SET workflow_stage = 'reviewer', updated_at = NOW()
        WHERE status = 'in_review'
          AND is_deleted = FALSE
          AND (workflow_stage IS NULL OR workflow_stage != 'reviewer')
    """))
    print(f"  in_review -> reviewer: {result.rowcount} rows")

    # ── 7. status='rejected' → workflow_stage='completed' ──
    result = connection.execute(sa.text("""
        UPDATE contract_reviews
        SET workflow_stage = 'completed', updated_at = NOW()
        WHERE status = 'rejected'
          AND is_deleted = FALSE
          AND (workflow_stage IS NULL OR workflow_stage != 'completed')
    """))
    print(f"  rejected -> completed: {result.rowcount} rows")

    print("")
    print("  -- Verification: check remaining NULL workflow_stage:")
    print("  SELECT status, COUNT(*) FROM contract_reviews")
    print("  WHERE is_deleted = FALSE AND workflow_stage IS NULL")
    print("  GROUP BY status ORDER BY status;")
    print("")
    print("  -- Verification: check all status/stage pairs:")
    print("  SELECT status, workflow_stage, COUNT(*)")
    print("  FROM contract_reviews WHERE is_deleted = FALSE")
    print("  GROUP BY status, workflow_stage ORDER BY status;")


def downgrade() -> None:
    """Data repair — no schema changes to revert."""
    pass
