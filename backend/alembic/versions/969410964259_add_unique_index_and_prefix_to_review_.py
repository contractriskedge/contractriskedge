"""Add unique index and prefix to review_number

Revision ID: 969410964259
Revises: 570817e96e6d
Create Date: 2026-06-18 15:02:07.987141

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '969410964259'
down_revision: Union[str, Sequence[str], None] = '570817e96e6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique index on review_number and make it non-null."""
    # First, backfill empty review_number values with a generated one
    # so the unique constraint can be applied.
    op.execute("""
        UPDATE contract_reviews
        SET review_number = CONCAT('CREV-', TO_CHAR(created_at, 'YYYYMM'), '-', review_id::text)
        WHERE review_number IS NULL OR review_number = ''
    """)
    # Add unique index (not constraint — allows multiple tenants to have the same number)
    op.create_index('ix_contract_reviews_review_number', 'contract_reviews', ['review_number'], unique=False)
    # Make review_number non-null with a default
    op.alter_column('contract_reviews', 'review_number',
                    existing_type=sa.String(50),
                    nullable=False,
                    existing_server_default=sa.text("''::character varying"))


def downgrade() -> None:
    """Remove unique index and restore nullable."""
    op.drop_index('ix_contract_reviews_review_number', table_name='contract_reviews')
    op.alter_column('contract_reviews', 'review_number',
                    existing_type=sa.String(50),
                    nullable=True,
                    existing_server_default=sa.text("''::character varying"))
