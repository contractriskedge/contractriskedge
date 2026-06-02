"""add_feature_flag_overrides_table

Revision ID: 64b88a831ccb
Revises: d7e8f9a0b1c2
Create Date: 2026-05-29 14:36:47.829542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '64b88a831ccb'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create feature_flag_overrides table for tenant-level feature flag configuration."""
    op.create_table(
        'feature_flag_overrides',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('flag_key', sa.Text(), nullable=False),
        sa.Column('target_type', sa.Text(), nullable=False),
        sa.Column('target_id', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flag_key', 'target_type', 'target_id', name='uq_feature_flag_override'),
    )
    op.create_index('ix_feature_flag_overrides_flag_key', 'feature_flag_overrides', ['flag_key'])
    op.create_index('ix_feature_flag_overrides_target', 'feature_flag_overrides', ['target_type', 'target_id'])


def downgrade() -> None:
    """Drop feature_flag_overrides table."""
    op.drop_table('feature_flag_overrides')
