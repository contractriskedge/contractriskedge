"""add template_packages and template_package_items tables

Revision ID: b2c3d4e5f6a7
Revises: f1e2d3c4b5a6
Create Date: 2026-06-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create template_packages and template_package_items tables."""
    op.create_table('template_packages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('updated_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_template_packages_tenant_industry', 'template_packages',
                    ['tenant_id', 'industry'])

    op.create_table('template_package_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('package_id', sa.String(36),
                  sa.ForeignKey('template_packages.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('template_id', sa.String(36),
                  sa.ForeignKey('contract_templates.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_package_items_package_template', 'template_package_items',
                    ['package_id', 'template_id'], unique=True)


def downgrade() -> None:
    """Drop template_packages and template_package_items tables."""
    op.drop_table('template_package_items')
    op.drop_table('template_packages')
