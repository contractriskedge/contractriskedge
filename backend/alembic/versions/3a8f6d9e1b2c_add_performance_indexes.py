"""Add performance indexes for query optimization and multi-tenant isolation.

This migration adds:
  - Composite indexes for tenant-scoped queries
  - GIN indexes for full-text search
  - Trigram indexes for ILIKE/fuzzy text search
  - Partial indexes for active/soft-delete filtering
  - Covering indexes for dashboard aggregation queries
  - Indexes for recovery daemon queries

Revision ID: 3a8f6d9e1b2c
Revises: 4b9c7e8f2d1a
Create Date: 2026-05-17
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3a8f6d9e1b2c"
down_revision: Union[str, None] = "e7b21230c345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes."""

    # ── Enable extensions ─────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")

    # ═══════════════════════════════════════════════════════════════
    # contract_reviews — review domain
    # ═══════════════════════════════════════════════════════════════

    # Composite indexes for tenant-scoped queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_tenant_status ON contract_reviews (tenant_id, status) WHERE is_deleted = FALSE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_tenant_created ON contract_reviews (tenant_id, created_at DESC) WHERE is_deleted = FALSE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_tenant_priority ON contract_reviews (tenant_id, priority) WHERE is_deleted = FALSE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_tenant_assigned ON contract_reviews (tenant_id, assigned_to) WHERE is_deleted = FALSE AND assigned_to IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_tenant_sla ON contract_reviews (tenant_id, sla_deadline) WHERE is_deleted = FALSE AND sla_deadline IS NOT NULL AND status NOT IN ('approved', 'rejected', 'closed')")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_active ON contract_reviews (tenant_id, review_id) WHERE is_deleted = FALSE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_stuck_recovery ON contract_reviews (tenant_id, updated_at) WHERE is_deleted = FALSE AND status IN ('draft', 'ai_analyzed')")

    # ═══════════════════════════════════════════════════════════════
    # review_findings — findings table (high-traffic)
    # ═══════════════════════════════════════════════════════════════

    op.execute("CREATE INDEX IF NOT EXISTS ix_findings_tenant_review ON review_findings (tenant_id, review_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_findings_tenant_severity ON review_findings (tenant_id, severity)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_findings_tenant_clause ON review_findings (tenant_id, clause_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_findings_tenant_resolution ON review_findings (tenant_id, resolution) WHERE resolution IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_findings_tenant_created ON review_findings (tenant_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_findings_text_search ON review_findings USING gin (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || coalesce(recommendation, '')))")
    op.execute("CREATE INDEX IF NOT EXISTS ix_findings_title_trgm ON review_findings USING gin (title gin_trgm_ops)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_redlines_tenant_review ON review_redlines (tenant_id, review_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_redlines_tenant_status ON review_redlines (tenant_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comments_tenant_review ON review_comments (tenant_id, review_id) WHERE deleted_at IS NULL")

    op.execute("CREATE INDEX IF NOT EXISTS ix_uploads_tenant_state ON upload_sessions (tenant_id, ingestion_state)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_uploads_tenant_created ON upload_sessions (tenant_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_uploads_tenant_checksum ON upload_sessions (tenant_id, client_checksum_sha256) WHERE client_checksum_sha256 IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_uploads_stuck_recovery ON upload_sessions (tenant_id, updated_at) WHERE ingestion_state NOT IN ('review_ready', 'failed', 'cancelled', 'quarantined')")

    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_tenant_upload ON ai_execution_runs (tenant_id, upload_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_tenant_status ON ai_execution_runs (tenant_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_tenant_created ON ai_execution_runs (tenant_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_stuck_recovery ON ai_execution_runs (tenant_id, started_at) WHERE status IN ('processing', 'pending') AND started_at IS NOT NULL")

    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_steps_tenant_run ON ai_execution_steps (tenant_id, run_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_findings_tenant_run ON ai_findings (tenant_id, run_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_redlines_tenant_run ON ai_redlines (tenant_id, run_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_failures_tenant_type ON ai_failures (tenant_id, failure_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_failures_tenant_created ON ai_failures (tenant_id, created_at DESC)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_tenant_type ON governance_audit_events (tenant_id, event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_tenant_entity ON governance_audit_events (tenant_id, entity_type, entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_tenant_actor ON governance_audit_events (tenant_id, actor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_tenant_created ON governance_audit_events (tenant_id, created_at DESC)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_review_history_tenant_review ON review_status_history (tenant_id, review_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_review_history_tenant_created ON review_status_history (tenant_id, created_at DESC)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_tenant_upload ON chunks (tenant_id, upload_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_tenant_clause ON chunks (tenant_id, clause_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_text_trgm ON chunks USING gin (text gin_trgm_ops)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_search_queries_tenant_created ON search_queries (tenant_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_queries_tenant_popular ON search_queries (tenant_id, query_text, created_at DESC) WHERE result_count > 0")

    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_tenant_user ON notifications (tenant_id, user_id, created_at DESC) WHERE is_read = FALSE")

    op.execute("CREATE INDEX IF NOT EXISTS ix_idempotency_tenant_operation ON idempotency_records (tenant_id, operation, idempotency_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_idempotency_expires ON idempotency_records (expires_at) WHERE expires_at IS NOT NULL")

    op.execute("CREATE INDEX IF NOT EXISTS ix_assignments_tenant_review ON review_assignments (tenant_id, review_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_assignments_tenant_assignee ON review_assignments (tenant_id, assignee_id) WHERE completed_at IS NULL")

    op.execute("CREATE INDEX IF NOT EXISTS ix_escalations_tenant_review ON review_escalations (tenant_id, review_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_escalations_tenant_status ON review_escalations (tenant_id, status)")


def downgrade() -> None:
    """Remove all added indexes."""
    indexes = [
        "ix_reviews_tenant_status",
        "ix_reviews_tenant_created",
        "ix_reviews_tenant_priority",
        "ix_reviews_tenant_assigned",
        "ix_reviews_tenant_sla",
        "ix_reviews_active",
        "ix_reviews_stuck_recovery",
        "ix_findings_tenant_review",
        "ix_findings_tenant_severity",
        "ix_findings_tenant_clause",
        "ix_findings_tenant_resolution",
        "ix_findings_tenant_created",
        "ix_findings_text_search",
        "ix_findings_title_trgm",
        "ix_redlines_tenant_review",
        "ix_redlines_tenant_status",
        "ix_comments_tenant_review",
        "ix_uploads_tenant_state",
        "ix_uploads_tenant_created",
        "ix_uploads_tenant_checksum",
        "ix_uploads_stuck_recovery",
        "ix_ai_runs_tenant_upload",
        "ix_ai_runs_tenant_status",
        "ix_ai_runs_tenant_created",
        "ix_ai_runs_stuck_recovery",
        "ix_ai_steps_tenant_run",
        "ix_ai_findings_tenant_run",
        "ix_ai_redlines_tenant_run",
        "ix_ai_failures_tenant_type",
        "ix_ai_failures_tenant_created",
        "ix_audit_tenant_type",
        "ix_audit_tenant_entity",
        "ix_audit_tenant_actor",
        "ix_audit_tenant_created",
        "ix_review_history_tenant_review",
        "ix_review_history_tenant_created",
        "ix_chunks_tenant_upload",
        "ix_chunks_tenant_clause",
        "ix_chunks_text_trgm",
        "ix_search_queries_tenant_created",
        "ix_search_queries_tenant_popular",
        "ix_notifications_tenant_user",
        "ix_idempotency_tenant_operation",
        "ix_idempotency_expires",
        "ix_assignments_tenant_review",
        "ix_assignments_tenant_assignee",
        "ix_escalations_tenant_review",
        "ix_escalations_tenant_status",
    ]
    for idx in indexes:
        op.drop_index(idx, table_name="dummy", if_exists=True)
