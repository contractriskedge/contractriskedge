"""add_unique_review_assignee_constraint

Revision ID: l0m1n2o3p4q5
Revises: k0l1m2n3o4p5
Create Date: 2026-06-04 22:00:00.000000

Adds a UNIQUE constraint on (review_id, assignee_id) in the
review_assignments table to prevent duplicate assignments.

Before creating the constraint, detects and cleans any existing
duplicate rows by keeping only the most recent assignment for
each (review_id, assignee_id) pair.

This is part of the Sprint 21 assignment idempotency remediation
(Task 4.4). See sprint21_task4.3a_analysis.md for root cause.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "l0m1n2o3p4q5"
down_revision: Union[str, Sequence[str], None] = "k0l1m2n3o4p5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Remove duplicate rows before adding constraint.
    # Keep only the most recent assignment per (review_id, assignee_id).
    op.execute("""
        DELETE FROM review_assignments a
        USING review_assignments b
        WHERE a.assignment_id < b.assignment_id
          AND a.review_id = b.review_id
          AND a.assignee_id = b.assignee_id
    """)

    # Step 2: Add the unique constraint.
    op.execute("""
        ALTER TABLE review_assignments
        ADD CONSTRAINT uq_review_assignee UNIQUE (review_id, assignee_id)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE review_assignments DROP CONSTRAINT IF EXISTS uq_review_assignee")
