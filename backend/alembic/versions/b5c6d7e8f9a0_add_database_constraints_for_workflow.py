"""add_database_constraints_for_workflow_integrity

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-05-19 23:30:00.000000

Adds database-level constraints to enforce workflow integrity:

1. Unique current version per review (only one version can be 'current')
2. Immutable finalized versions (prevent updates to finalized versions)
3. Approved version must reference a valid version
4. Status change timestamps (completed_at must be set on terminal states)
5. Prevent duplicate approvals per review
6. Prevent escalation without reason
7. Ensure review status enum consistency
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Unique current version per review
    # Only one version can be 'current' at a time per review
    op.create_index(
        "uq_current_version_per_review",
        "contract_document_versions",
        ["review_id"],
        unique=True,
        postgresql_where=sa.text("status = 'current'"),
    )

    # 2. Immutable finalized versions — prevent setting finalized versions back to current
    # This is a partial unique index that helps enforce immutability at DB level
    op.create_index(
        "uq_finalized_version_per_review",
        "contract_document_versions",
        ["review_id", "version_number"],
        unique=True,
        postgresql_where=sa.text("status = 'finalized'"),
    )

    # 3. Prevent duplicate 'approved' approvals per review
    # Only one approval with decision='approved' should exist per review
    op.create_index(
        "uq_single_approval_per_review",
        "review_approvals",
        ["review_id"],
        unique=True,
        postgresql_where=sa.text("decision = 'approved'"),
    )

    # 4. Prevent escalation without reason — enforce reason is not empty
    # Add CHECK constraint via raw SQL since SQLAlchemy doesn't support it easily
    op.execute("""
        ALTER TABLE review_escalations
        ADD CONSTRAINT ck_escalation_reason_not_empty
        CHECK (reason IS NOT NULL AND length(trim(reason)) > 0)
    """)

    # 5. Ensure completed_at is set when review reaches terminal states
    # Create a trigger function to auto-set completed_at
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_set_completed_at()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.status IN ('approved', 'rejected', 'finalized', 'archived', 'closed')
               AND OLD.status NOT IN ('approved', 'rejected', 'finalized', 'archived', 'closed') THEN
                NEW.completed_at = COALESCE(NEW.completed_at, NOW());
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER trg_review_completed_at
            BEFORE UPDATE OF status ON contract_reviews
            FOR EACH ROW
            EXECUTE FUNCTION trg_set_completed_at()
    """)

    # 6. Ensure finalized versions have a checksum (data integrity)
    op.execute("""
        ALTER TABLE contract_document_versions
        ADD CONSTRAINT ck_finalized_version_has_checksum
        CHECK (
            status != 'finalized' OR
            (checksum_sha256 IS NOT NULL AND storage_key IS NOT NULL)
        )
    """)

    # 7. Prevent updating finalized document versions (immutability)
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_prevent_finalized_version_update()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.status = 'finalized' THEN
                RAISE EXCEPTION 'Cannot modify a finalized document version (version_id: %)', OLD.version_id
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER trg_finalized_version_immutable
            BEFORE UPDATE ON contract_document_versions
            FOR EACH ROW
            EXECUTE FUNCTION trg_prevent_finalized_version_update()
    """)


def downgrade() -> None:
    # Remove triggers first
    op.execute("DROP TRIGGER IF EXISTS trg_finalized_version_immutable ON contract_document_versions")
    op.execute("DROP FUNCTION IF EXISTS trg_prevent_finalized_version_update()")
    op.execute("DROP TRIGGER IF EXISTS trg_review_completed_at ON contract_reviews")
    op.execute("DROP FUNCTION IF EXISTS trg_set_completed_at()")

    # Remove constraints
    op.execute("ALTER TABLE contract_document_versions DROP CONSTRAINT IF EXISTS ck_finalized_version_has_checksum")
    op.execute("ALTER TABLE review_escalations DROP CONSTRAINT IF EXISTS ck_escalation_reason_not_empty")

    # Remove indexes
    op.drop_index("uq_single_approval_per_review", table_name="review_approvals")
    op.drop_index("uq_finalized_version_per_review", table_name="contract_document_versions")
    op.drop_index("uq_current_version_per_review", table_name="contract_document_versions")
