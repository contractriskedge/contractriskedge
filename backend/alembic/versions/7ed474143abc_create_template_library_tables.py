"""create template library tables

Revision ID: 7ed474143abc
Revises: 945eb119ab75
Create Date: 2026-06-26 18:04:06.372535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7ed474143abc'
down_revision: Union[str, Sequence[str], None] = '945eb119ab75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create template library tables."""
    # ── Template Categories ───────────────────────────────────────
    op.create_table('template_categories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_template_categories_tenant_slug', 'template_categories',
                    ['tenant_id', 'slug'], unique=True)

    # ── Contract Templates ────────────────────────────────────────
    op.create_table('contract_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('category_id', sa.String(36),
                  sa.ForeignKey('template_categories.id'), nullable=True),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('owner', sa.String(200), nullable=True),
        sa.Column('department', sa.String(200), nullable=True),
        sa.Column('business_unit', sa.String(200), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('current_version_id', sa.String(36), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_by', sa.String(200), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_contract_templates_tenant_status', 'contract_templates',
                    ['tenant_id', 'status'])
    op.create_index('ix_contract_templates_tenant_category', 'contract_templates',
                    ['tenant_id', 'category_id'])

    # ── Template Versions ─────────────────────────────────────────
    op.create_table('template_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('template_id', sa.String(36),
                  sa.ForeignKey('contract_templates.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(200), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('storage_key', sa.String(500), nullable=True),
        sa.Column('storage_bucket', sa.String(200), nullable=True),
        sa.Column('file_name', sa.String(300), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=False,
                  server_default='application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        sa.Column('variables', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('placeholder_content', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_template_versions_template_number', 'template_versions',
                    ['template_id', 'version_number'], unique=True)

    # ── Template Variables ────────────────────────────────────────
    op.create_table('template_variables',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('key', sa.String(200), nullable=False),
        sa.Column('label', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('field_type', sa.String(50), nullable=False, server_default='text'),
        sa.Column('default_value', sa.Text(), nullable=True),
        sa.Column('options', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('validation_rules', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_template_variables_tenant_key', 'template_variables',
                    ['tenant_id', 'key'])

    # ── Template Favorites ────────────────────────────────────────
    op.create_table('template_favorites',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('template_id', sa.String(36),
                  sa.ForeignKey('contract_templates.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('user_id', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_template_favorites_tenant_user_template', 'template_favorites',
                    ['tenant_id', 'user_id', 'template_id'], unique=True)

    # ── Generated Contracts ───────────────────────────────────────
    op.create_table('generated_contracts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('template_id', sa.String(36),
                  sa.ForeignKey('contract_templates.id'), nullable=False),
        sa.Column('template_version_id', sa.String(36),
                  sa.ForeignKey('template_versions.id'), nullable=False),
        sa.Column('review_id', sa.String(36), nullable=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('variable_values', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('generated_docx_key', sa.String(500), nullable=True),
        sa.Column('generated_pdf_key', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_generated_contracts_tenant_template', 'generated_contracts',
                    ['tenant_id', 'template_id'])

    # ── Template Usage History ────────────────────────────────────
    op.create_table('template_usage_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('template_id', sa.String(36),
                  sa.ForeignKey('contract_templates.id'), nullable=False),
        sa.Column('template_version_id', sa.String(36),
                  sa.ForeignKey('template_versions.id'), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.String(200), nullable=False),
        sa.Column('details', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_template_usage_tenant_template', 'template_usage_history',
                    ['tenant_id', 'template_id'])
    op.create_index('ix_template_usage_tenant_action', 'template_usage_history',
                    ['tenant_id', 'action'])


def downgrade() -> None:
    """Drop template library tables."""
    op.drop_table('template_usage_history')
    op.drop_table('generated_contracts')
    op.drop_table('template_favorites')
    op.drop_table('template_variables')
    op.drop_table('template_versions')
    op.drop_table('contract_templates')
    op.drop_table('template_categories')
