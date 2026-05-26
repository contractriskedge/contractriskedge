"""Add llm_cost_records table for LLM cost tracking.

Revision ID: 002
Revises: 001
Create Date: 2026-05-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add llm_cost_records table with supporting indexes."""
    
    op.create_table(
        "llm_cost_records",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("cached", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_llm_cost_created", "llm_cost_records", ["created_at"])
    op.create_index("idx_llm_cost_tenant", "llm_cost_records", ["tenant_id"])
    op.create_index("idx_llm_cost_provider", "llm_cost_records", ["provider"])
    op.create_index(
        "idx_llm_cost_daily",
        "llm_cost_records",
        [sa.text("date(created_at)"), sa.text("tenant_id")],
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )
    op.execute("ALTER TABLE llm_cost_records ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Remove llm_cost_records table."""
    op.drop_table("llm_cost_records")
