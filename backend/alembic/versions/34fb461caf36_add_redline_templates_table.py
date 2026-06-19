"""add_redline_templates_table

Revision ID: 34fb461caf36
Revises: a84aaa7071b9
Create Date: 2026-06-19 13:56:04.230556

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '34fb461caf36'
down_revision: Union[str, Sequence[str], None] = 'a84aaa7071b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create redline_templates table."""
    op.create_table('redline_templates',
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('clause_type', sa.Text(), nullable=False),
        sa.Column('category', sa.Text(), nullable=False),
        sa.Column('jurisdiction', sa.Text(), nullable=True),
        sa.Column('industry', sa.Text(), nullable=True),
        sa.Column('language', sa.Text(), nullable=False),
        sa.Column('risk_level', sa.Text(), nullable=True),
        sa.Column('template_text', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('playbook_id', sa.UUID(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('accept_rate', sa.Float(), nullable=False),
        sa.Column('created_by', sa.Text(), nullable=True),
        sa.Column('approved_by', sa.Text(), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retired_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['playbook_id'], ['clause_standards.clause_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('template_id')
    )
    op.create_index(op.f('ix_redline_templates_clause_type'), 'redline_templates', ['clause_type'], unique=False)
    op.create_index(op.f('ix_redline_templates_playbook_id'), 'redline_templates', ['playbook_id'], unique=False)
    op.create_index(op.f('ix_redline_templates_tenant_id'), 'redline_templates', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema — drop redline_templates table."""
    op.drop_index(op.f('ix_redline_templates_tenant_id'), table_name='redline_templates')
    op.drop_index(op.f('ix_redline_templates_playbook_id'), table_name='redline_templates')
    op.drop_index(op.f('ix_redline_templates_clause_type'), table_name='redline_templates')
    op.drop_table('redline_templates')
