"""Add current_round and max_rounds to negotiation_sessions

Revision ID: 0b1c2d3e4f5a
Revises: 00a60a2d2bd4
Create Date: 2026-06-08 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b1c2d3e4f5a'
down_revision: Union[str, Sequence[str], None] = '00a60a2d2bd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add current_round and max_rounds columns to negotiation_sessions."""
    op.add_column("negotiation_sessions", sa.Column("current_round", sa.Integer(), nullable=False, server_default=sa.text("1")))
    op.add_column("negotiation_sessions", sa.Column("max_rounds", sa.Integer(), nullable=False, server_default=sa.text("3")))


def downgrade() -> None:
    """Remove columns."""
    op.drop_column("negotiation_sessions", "max_rounds")
    op.drop_column("negotiation_sessions", "current_round")
