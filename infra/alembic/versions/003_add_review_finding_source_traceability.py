"""Add source traceability fields to review findings.

Revision ID: 003
Revises: 002
Create Date: 2026-06-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("review_findings", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("review_findings", sa.Column("section_heading", sa.Text(), nullable=True))
    op.add_column("review_findings", sa.Column("paragraph_index", sa.Integer(), nullable=True))
    op.add_column("review_findings", sa.Column("source_text", sa.Text(), nullable=True))
    op.add_column("review_findings", sa.Column("source_start_offset", sa.Integer(), nullable=True))
    op.add_column("review_findings", sa.Column("source_end_offset", sa.Integer(), nullable=True))
    op.add_column("review_findings", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.create_index("idx_review_findings_source_page", "review_findings", ["review_id", "page_number"])


def downgrade() -> None:
    op.drop_index("idx_review_findings_source_page", table_name="review_findings")
    op.drop_column("review_findings", "confidence_score")
    op.drop_column("review_findings", "source_end_offset")
    op.drop_column("review_findings", "source_start_offset")
    op.drop_column("review_findings", "source_text")
    op.drop_column("review_findings", "paragraph_index")
    op.drop_column("review_findings", "section_heading")
    op.drop_column("review_findings", "page_number")
