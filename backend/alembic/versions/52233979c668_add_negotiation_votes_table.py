"""add negotiation_votes table

Revision ID: 52233979c668
Revises: 002_add_coverage_snapshots
Create Date: 2026-06-23 13:34:38.690176

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "52233979c668"
down_revision: Union[str, Sequence[str], None] = "002_add_coverage_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create negotiation_votes table if not yet present."""
    # ── Create table (idempotent — no-op if already exists) ──────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS negotiation_votes (
            vote_id      VARCHAR(36) PRIMARY KEY,
            session_id   VARCHAR(36) NOT NULL
                         REFERENCES negotiation_sessions(session_id)
                         ON DELETE CASCADE,
            clause_id    VARCHAR(255) NOT NULL,
            finding_id   VARCHAR(255),
            voter_name   VARCHAR(255) NOT NULL,
            voter_role   VARCHAR(100) NOT NULL,
            vote         VARCHAR(20) NOT NULL,
            comment      TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # ── Align indexes with the ORM model ────────────────────────────────
    # Drop legacy single-column indexes (may or may not exist)
    op.execute("DROP INDEX IF EXISTS ix_neg_votes_session")
    op.execute("DROP INDEX IF EXISTS ix_neg_votes_clause")

    # Create index for session_id FK lookups (from mapped_column(index=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_negotiation_votes_session_id "
        "ON negotiation_votes (session_id)"
    )

    # Composite index for clause lookups within a session
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_neg_votes_session_clause "
        "ON negotiation_votes (session_id, clause_id)"
    )

    # Composite index for voter lookups within a session
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_neg_votes_session_voter "
        "ON negotiation_votes (session_id, voter_name)"
    )


def downgrade() -> None:
    """Downgrade schema — drop negotiation_votes table."""
    op.drop_index("ix_neg_votes_session_voter", table_name="negotiation_votes")
    op.drop_index("ix_neg_votes_session_clause", table_name="negotiation_votes")
    op.drop_index("ix_negotiation_votes_session_id", table_name="negotiation_votes")
    op.drop_table("negotiation_votes")
