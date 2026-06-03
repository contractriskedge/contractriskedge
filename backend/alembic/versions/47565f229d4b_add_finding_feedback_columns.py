"""add_finding_feedback_columns

Revision ID: 47565f229d4b
Revises: f8a9b0c1d2e3
Create Date: 2026-06-02 19:20:55.007656

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '47565f229d4b'
down_revision: Union[str, Sequence[str], None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add feedback columns to review_findings."""
    op.add_column('review_findings', sa.Column('feedback_type', sa.Text(), nullable=True))
    op.add_column('review_findings', sa.Column('feedback_note', sa.Text(), nullable=True))
    op.add_column('review_findings', sa.Column('feedback_priority', sa.Text(), nullable=True))
    op.add_column('review_findings', sa.Column('feedback_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove feedback columns from review_findings."""
    op.drop_column('review_findings', 'feedback_at')
    op.drop_column('review_findings', 'feedback_priority')
    op.drop_column('review_findings', 'feedback_note')
    op.drop_column('review_findings', 'feedback_type')
