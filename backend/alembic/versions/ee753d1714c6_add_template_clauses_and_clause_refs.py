"""add template_clauses table and clause_refs column

Revision ID: ee753d1714c6
Revises: 63df7560be62
Create Date: 2026-06-26 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'ee753d1714c6'
down_revision: Union[str, Sequence[str], None] = '63df7560be62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create template_clauses table and add clause_refs column."""
    op.create_table('template_clauses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('template_id', sa.String(36),
                  sa.ForeignKey('contract_templates.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('clause_type', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('risk_level', sa.String(50), nullable=True),
        sa.Column('ai_rewrite_allowed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('fallback_clause_id', sa.String(36), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_conditional', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('condition_expression', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('updated_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_template_clauses_tenant_type', 'template_clauses',
                    ['tenant_id', 'clause_type'])
    op.create_index('ix_template_clauses_tenant_template', 'template_clauses',
                    ['tenant_id', 'template_id'])

    # Add clause_refs JSONB column to template_versions
    op.add_column('template_versions',
        sa.Column('clause_refs', postgresql.JSONB, nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    """Drop template_clauses table and clause_refs column."""
    op.drop_column('template_versions', 'clause_refs')
    op.drop_table('template_clauses')
