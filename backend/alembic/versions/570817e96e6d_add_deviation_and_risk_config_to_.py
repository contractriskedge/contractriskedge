"""add_deviation_and_risk_config_to_playbooks

Revision ID: 570817e96e6d
Revises: fcd198fc38e3
Create Date: 2026-06-13 19:45:23.433083

Adds configurable deviation detection thresholds and risk scoring weights
to legal_playbooks, replacing the previously hardcoded values in the
PolicyEngine (engine.py).

Columns added:
  - deviation_thresholds  JSONB — per-playbook similarity cutoffs
      {"similarity": 0.5, "forbidden_similarity": 0.3}
  - risk_weights          JSONB — per-playbook severity weights
      {"critical": 5.0, "high": 3.0, "medium": 2.0, "low": 1.0, "info": 0.1}
  - risk_levels           JSONB — per-playbook risk level thresholds
      {"critical": 8.0, "high": 5.0, "medium": 3.0}

See Sprint 25.4 and 25.5.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '570817e96e6d'
down_revision: Union[str, Sequence[str], None] = 'fcd198fc38e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE legal_playbooks
        ADD COLUMN IF NOT EXISTS deviation_thresholds JSONB
        NOT NULL DEFAULT '{"similarity": 0.5, "forbidden_similarity": 0.3}'::jsonb;
    """)
    op.execute("""
        ALTER TABLE legal_playbooks
        ADD COLUMN IF NOT EXISTS risk_weights JSONB
        NOT NULL DEFAULT '{"critical": 5.0, "high": 3.0, "medium": 2.0, "low": 1.0, "info": 0.1}'::jsonb;
    """)
    op.execute("""
        ALTER TABLE legal_playbooks
        ADD COLUMN IF NOT EXISTS risk_levels JSONB
        NOT NULL DEFAULT '{"critical": 8.0, "high": 5.0, "medium": 3.0}'::jsonb;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE legal_playbooks DROP COLUMN IF EXISTS risk_levels;")
    op.execute("ALTER TABLE legal_playbooks DROP COLUMN IF EXISTS risk_weights;")
    op.execute("ALTER TABLE legal_playbooks DROP COLUMN IF EXISTS deviation_thresholds;")
