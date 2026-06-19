"""Add business_id_sequences table and finding_number

Revision ID: a84aaa7071b9
Revises: 969410964259
Create Date: 2026-06-18 15:09:50.508524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a84aaa7071b9'
down_revision: Union[str, Sequence[str], None] = '969410964259'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add business_id_sequences table and finding_number column."""
    # Table for atomic sequential ID generation
    op.create_table(
        'business_id_sequences',
        sa.Column('sequence_key', sa.String(100), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('current_value', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_business_id_sequences_tenant', 'business_id_sequences', ['tenant_id'])

    # Add finding_number to review_findings
    op.add_column('review_findings',
        sa.Column('finding_number', sa.String(50), nullable=True)
    )
    op.create_index('ix_review_findings_finding_number', 'review_findings', ['finding_number'])


def downgrade() -> None:
    """Remove business_id_sequences table and finding_number column."""
    op.drop_index('ix_review_findings_finding_number', table_name='review_findings')
    op.drop_column('review_findings', 'finding_number')
    op.drop_index('ix_business_id_sequences_tenant', table_name='business_id_sequences')
    op.drop_table('business_id_sequences')
