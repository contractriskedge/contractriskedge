"""merge_all_heads

Revision ID: bbd84d9c7ee9
Revises: a1b2c3d4e5f6, g1h2i3j4k5l6, h1i2j3k4l5m6, i2j3k4l5m6n7
Create Date: 2026-05-28 08:07:00.620104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbd84d9c7ee9'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'g1h2i3j4k5l6', 'h1i2j3k4l5m6', 'i2j3k4l5m6n7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
