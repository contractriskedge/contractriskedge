"""add_assigned_at_and_workflow_stage

Revision ID: 246c2ccbd7ed
Revises: d4e5f6a7b8c9
Create Date: 2026-05-18 17:17:22.055779

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '246c2ccbd7ed'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('contract_reviews', sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('contract_reviews', sa.Column('workflow_stage', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('contract_reviews', 'workflow_stage')
    op.drop_column('contract_reviews', 'assigned_at')
