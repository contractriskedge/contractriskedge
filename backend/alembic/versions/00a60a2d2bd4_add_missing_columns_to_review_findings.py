"""Add missing columns to review_findings table

Revision ID: 00a60a2d2bd4
Revises: m0n1o2p3q4r5
Create Date: 2026-06-08 13:14:56.361728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '00a60a2d2bd4'
down_revision: Union[str, Sequence[str], None] = 'm0n1o2p3q4r5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing columns that exist in the ReviewFinding model but were never
    # created in the database. These columns support enriched finding metadata
    # for page-level navigation, source text highlighting, and confidence scoring.
    op.add_column("review_findings", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("review_findings", sa.Column("section_heading", sa.Text(), nullable=True))
    op.add_column("review_findings", sa.Column("paragraph_index", sa.Integer(), nullable=True))
    op.add_column("review_findings", sa.Column("source_text", sa.Text(), nullable=True))
    op.add_column("review_findings", sa.Column("source_start_offset", sa.Integer(), nullable=True))
    op.add_column("review_findings", sa.Column("source_end_offset", sa.Integer(), nullable=True))
    op.add_column("review_findings", sa.Column("confidence_score", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("review_findings", "confidence_score")
    op.drop_column("review_findings", "source_end_offset")
    op.drop_column("review_findings", "source_start_offset")
    op.drop_column("review_findings", "source_text")
    op.drop_column("review_findings", "paragraph_index")
    op.drop_column("review_findings", "section_heading")
    op.drop_column("review_findings", "page_number")
