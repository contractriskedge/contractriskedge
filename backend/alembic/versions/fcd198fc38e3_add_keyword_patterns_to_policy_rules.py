"""add_keyword_patterns_to_policy_rules

Revision ID: fcd198fc38e3
Revises: e8e2ad2f59ae
Create Date: 2026-06-13 19:43:41.608315

Adds keyword_patterns JSONB column to policy_rules so that clause-type
keyword matching is data-driven rather than hardcoded in Python.

The KEYWORD_RULE_MAP dict in policy_linkage.py is replaced by this column.
Each rule can store keyword patterns that should trigger a match, e.g.:

    {"patterns": ["ip_ownership", "intellectual_property"]}

See Sprint 25.3 — DB-Driven Keyword Mapping.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'fcd198fc38e3'
down_revision: Union[str, Sequence[str], None] = 'e8e2ad2f59ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE policy_rules
        ADD COLUMN IF NOT EXISTS keyword_patterns JSONB NOT NULL DEFAULT '[]'::jsonb;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE policy_rules DROP COLUMN IF EXISTS keyword_patterns;
    """)
