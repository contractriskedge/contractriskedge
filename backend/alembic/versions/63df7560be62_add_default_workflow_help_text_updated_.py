"""add default_workflow help_text updated_by

Revision ID: 63df7560be62
Revises: eaeac7742638
Create Date: 2026-06-26 18:47:26.599889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63df7560be62'
down_revision: Union[str, Sequence[str], None] = 'eaeac7742638'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add default_workflow, help_text, updated_by columns."""
    op.add_column("contract_templates", sa.Column("default_workflow", sa.String(200), nullable=True))
    op.add_column("template_variables", sa.Column("help_text", sa.Text(), nullable=True))
    op.add_column("template_versions", sa.Column("updated_by", sa.String(200), nullable=True))
    op.add_column("generated_contracts", sa.Column("updated_by", sa.String(200), nullable=True))


def downgrade() -> None:
    """Drop added columns."""
    op.drop_column("generated_contracts", "updated_by")
    op.drop_column("template_versions", "updated_by")
    op.drop_column("template_variables", "help_text")
    op.drop_column("contract_templates", "default_workflow")
