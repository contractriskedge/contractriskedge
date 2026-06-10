"""merge_obligation_fk_head

Revision ID: cc234500e3be
Revises: e5f6a7b8c9d0, i4j5k6l7m8n9
Create Date: 2026-06-09 10:11:26.233639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc234500e3be'
down_revision: Union[str, Sequence[str], None] = ('e5f6a7b8c9d0', 'i4j5k6l7m8n9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
