"""add default_workflow help_text updated_by

Revision ID: eaeac7742638
Revises: 7ed474143abc
Create Date: 2026-06-26 18:47:24.227198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eaeac7742638'
down_revision: Union[str, Sequence[str], None] = '7ed474143abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
