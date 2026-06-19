"""add_playbook_version_id_to_review_findings

Revision ID: e8e2ad2f59ae
Revises: b0c1d2e3f4a5
Create Date: 2026-06-13 19:41:49.133520

Adds playbook_version_id column to review_findings so that findings are
pinned to the specific playbook version that was active when the policy
violation was generated. This ensures historical traceability.

See Sprint 25.2 — Version Pinning.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e8e2ad2f59ae'
down_revision: Union[str, Sequence[str], None] = 'b0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE review_findings
        ADD COLUMN IF NOT EXISTS playbook_version_id UUID
        REFERENCES playbook_versions(version_id) ON DELETE SET NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_review_findings_playbook_version_id
        ON review_findings (playbook_version_id);
    """)
    op.execute("""
        UPDATE review_findings rf
        SET playbook_version_id = lp.active_version_id
        FROM legal_playbooks lp
        WHERE rf.playbook_id = lp.playbook_id
          AND rf.playbook_version_id IS NULL
          AND lp.active_version_id IS NOT NULL;
    """)

    # Backfill playbook_version_id on policy_evaluations from the active version
    op.execute("""
        UPDATE policy_evaluations pe
        SET playbook_version_id = lp.active_version_id
        FROM legal_playbooks lp
        WHERE pe.playbook_id = lp.playbook_id
          AND pe.playbook_version_id IS NULL
          AND lp.active_version_id IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_review_findings_playbook_version_id;")
    op.execute("ALTER TABLE review_findings DROP COLUMN IF EXISTS playbook_version_id;")
