"""add template_clause_refs table, clause approval/versioning fields

Revision ID: f1e2d3c4b5a6
Revises: ee753d1714c6
Create Date: 2026-06-26 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, Sequence[str], None] = 'ee753d1714c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create template_clause_refs table and add new columns to template_clauses."""
    # ── template_clause_refs table ────────────────────────────────
    op.create_table('template_clause_refs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('template_id', sa.String(36),
                  sa.ForeignKey('contract_templates.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('template_version_id', sa.String(36),
                  sa.ForeignKey('template_versions.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('clause_id', sa.String(36),
                  sa.ForeignKey('template_clauses.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('clause_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('condition_expression', sa.Text(), nullable=True),
        sa.Column('fallback_clause_id', sa.String(36), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_clause_refs_version_clause', 'template_clause_refs',
                    ['template_version_id', 'clause_id'], unique=True)
    op.create_index('ix_clause_refs_tenant_template', 'template_clause_refs',
                    ['tenant_id', 'template_id'])

    # ── New columns for template_clauses ──────────────────────────
    op.add_column('template_clauses',
        sa.Column('change_summary', sa.Text(), nullable=True),
    )
    op.add_column('template_clauses',
        sa.Column('approved_by', sa.String(200), nullable=True),
    )
    op.add_column('template_clauses',
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column('template_clauses',
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('template_clauses',
        sa.Column('contract_usage_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('template_clauses',
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
    )

    # Update existing clauses to have status='published' (they were 'active')
    op.execute(
        "UPDATE template_clauses SET status = 'published' WHERE status = 'active'"
    )


def downgrade() -> None:
    """Drop template_clause_refs table and remove new columns."""
    op.drop_column('template_clauses', 'tags')
    op.drop_column('template_clauses', 'contract_usage_count')
    op.drop_column('template_clauses', 'usage_count')
    op.drop_column('template_clauses', 'approved_at')
    op.drop_column('template_clauses', 'approved_by')
    op.drop_column('template_clauses', 'change_summary')
    op.drop_table('template_clause_refs')
