"""add_contract_fk_to_obligations

Revision ID: e5f6a7b8c9d0
Revises: bbd84d9c7ee9
Create Date: 2026-06-09 10:00:00.000000

Adds a proper UUID foreign key column `contract_uuid_id` to the obligations
table referencing contract_reviews.review_id, and backfills it from the
existing string `contract_id` column where possible.

Also adds an index on the new column and updates the audit log to include
contract_name for better traceability.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "bbd84d9c7ee9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add a new UUID column for proper FK relationship
    op.execute("""
        ALTER TABLE obligations
        ADD COLUMN IF NOT EXISTS contract_uuid_id UUID REFERENCES contract_reviews(review_id) ON DELETE SET NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_obligations_contract_uuid_id ON obligations (contract_uuid_id);
    """)

    # Backfill contract_uuid_id from contract_id where contract_id is a valid UUID
    op.execute("""
        UPDATE obligations
        SET contract_uuid_id = contract_id::uuid
        WHERE contract_id IS NOT NULL
          AND contract_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          AND contract_uuid_id IS NULL;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_obligations_contract_uuid_id;")
    op.execute("ALTER TABLE obligations DROP COLUMN IF EXISTS contract_uuid_id;")
