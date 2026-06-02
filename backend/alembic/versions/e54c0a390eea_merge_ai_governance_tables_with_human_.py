"""Merge ai_governance_tables with human_oversight_tables

Revision ID: e54c0a390eea
Revises: f2g3h4i5j6k7, j0a1b2c3d4e5
Create Date: 2026-06-01 17:10:39.363528

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e54c0a390eea'
down_revision: Union[str, Sequence[str], None] = ('f2g3h4i5j6k7', 'j0a1b2c3d4e5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
