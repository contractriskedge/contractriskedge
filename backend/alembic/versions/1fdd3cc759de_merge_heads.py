"""Merge heads

Revision ID: 1fdd3cc759de
Revises: 3e41978fb1e2, f9e8d7c6b5a4
Create Date: 2026-06-12 09:57:14.480612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fdd3cc759de'
down_revision: Union[str, Sequence[str], None] = ('3e41978fb1e2', 'f9e8d7c6b5a4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
