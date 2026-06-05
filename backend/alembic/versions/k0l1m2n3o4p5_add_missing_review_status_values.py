"""add_missing_review_status_values

Revision ID: k0l1m2n3o4p5
Revises: 2dfddf86fae7
Create Date: 2026-06-04 16:00:00.000000

Adds 4 missing values to the review_status PostgreSQL enum:
  - analyzing     (transient state during AI analysis)
  - legal_review  (legal team actively reviewing)
  - procurement_review (procurement team actively reviewing)
  - security_review    (security team actively reviewing)

These values exist in the Python ReviewStatus and WorkflowState enums
but were never added to the database enum via a migration.

Also adds a CHECK constraint migration note: 'ai_reviewed' is intentionally
NOT added — it is an alias for 'ai_analyzed' and is mapped through
LEGACY_STATUS_MAP. 'negotiation' is intentionally NOT added — it is
tracked via the separate negotiation_sessions table.

See sprint21_task4.2.1_audit.md for full root cause analysis.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "k0l1m2n3o4p5"
down_revision: Union[str, Sequence[str], None] = "2dfddf86fae7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 4 missing review_status enum values.
    # Order matters for enum display; we insert in logical workflow order.
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'analyzing'")
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'procurement_review'")
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'legal_review'")
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'security_review'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    # The new values will remain in the enum type but won't be used
    # by new code if this migration is rolled back.
    pass
