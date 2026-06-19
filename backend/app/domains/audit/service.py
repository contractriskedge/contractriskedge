"""Audit service — unified query across governance and review audit tables."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.schemas import (
    AuditEventItem, AuditQueryParams, AuditQueryResponse,
    AuditEventTypeCount, AuditSummaryResponse,
)

logger = logging.getLogger(__name__)


def derive_event_status(event_type: str, metadata: Optional[dict[str, Any]]) -> str:
    """Resolve outcome status from metadata or event type naming."""
    if metadata and metadata.get("status"):
        return str(metadata["status"])
    et = (event_type or "").lower()
    if any(token in et for token in ("failure", "failed", "error", "rejected")):
        return "failure"
    if any(token in et for token in ("denied", "blocked", "forbidden")):
        return "blocked"
    return "success"


def derive_event_severity(event_type: str, metadata: Optional[dict[str, Any]], status: str) -> str:
    if metadata and metadata.get("severity"):
        return str(metadata["severity"])
    if status == "blocked":
        return "high"
    if status == "failure":
        return "medium"
    et = (event_type or "").lower()
    if any(token in et for token in ("escalated", "breach", "critical")):
        return "high"
    if any(token in et for token in ("auth.", "security.")):
        return "medium"
    return "info"


def _parse_metadata(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return {}


@dataclass
class AuditService:
    """Queries audit events from multiple audit tables."""

    session: AsyncSession
    tenant_id: str

    async def query_events(self, params: AuditQueryParams) -> AuditQueryResponse:
        """Query audit events with filtering and pagination via UNION ALL."""
        offset = (params.page - 1) * params.page_size
        conditions_gov: list[str] = ["g.tenant_id = :tenant_id"]
        conditions_rev: list[str] = ["r.tenant_id = :tenant_id"]
        bind: dict[str, Any] = {"tenant_id": self.tenant_id}

        if params.event_type:
            conditions_gov.append("g.event_type = :event_type")
            bind["event_type"] = params.event_type
            if params.event_type != "review_status_change":
                conditions_rev.append("1 = 0")
        if params.resource_type:
            conditions_gov.append("g.entity_type = :resource_type")
            bind["resource_type"] = params.resource_type
            if params.resource_type != "review":
                conditions_rev.append("1 = 0")
        if params.resource_id:
            conditions_gov.append("g.entity_id::text = :resource_id")
            conditions_rev.append("r.review_id::text = :resource_id")
            bind["resource_id"] = params.resource_id
        if params.actor_id:
            conditions_gov.append("g.actor_id = :actor_id")
            conditions_rev.append("r.changed_by = :actor_id")
            bind["actor_id"] = params.actor_id
        if params.action:
            conditions_gov.append("g.event_type = :action")
            bind["action"] = params.action
        if params.from_date:
            conditions_gov.append("g.created_at >= :from_date")
            conditions_rev.append("r.created_at >= :from_date")
            bind["from_date"] = params.from_date
        if params.to_date:
            conditions_gov.append("g.created_at <= :to_date")
            conditions_rev.append("r.created_at <= :to_date")
            bind["to_date"] = params.to_date
        if params.status:
            conditions_gov.append(
                "COALESCE(g.metadata->>'status', 'success') = :status"
            )
            if params.status != "success":
                conditions_rev.append("1 = 0")
            bind["status"] = params.status

        gov_where = " AND ".join(conditions_gov)
        rev_where = " AND ".join(conditions_rev)

        count_sql = sa_text(f"""
            SELECT COUNT(*)::int FROM (
                SELECT g.event_id FROM governance_audit_events g WHERE {gov_where}
                UNION ALL
                SELECT r.history_id FROM review_status_history r WHERE {rev_where}
            ) combined
        """)
        total = (await self.session.execute(count_sql, bind)).scalar() or 0
        total_pages = max(1, (total + params.page_size - 1) // params.page_size)

        query_sql = sa_text(f"""
            SELECT * FROM (
                SELECT
                    g.event_id::text AS event_id,
                    g.event_type,
                    g.event_type AS action,
                    g.entity_type AS resource_type,
                    g.entity_id::text AS resource_id,
                    g.actor_id,
                    g.previous_state AS before_state,
                    g.new_state AS after_state,
                    g.change_summary AS description,
                    g.correlation_id,
                    g.metadata,
                    g.source,
                    g.created_at
                FROM governance_audit_events g
                WHERE {gov_where}
                UNION ALL
                SELECT
                    ('review-' || r.history_id::text) AS event_id,
                    'review_status_change' AS event_type,
                    ('status_change: ' || r.from_status || ' -> ' || r.to_status) AS action,
                    'review' AS resource_type,
                    r.review_id::text AS resource_id,
                    r.changed_by AS actor_id,
                    jsonb_build_object('status', r.from_status) AS before_state,
                    jsonb_build_object('status', r.to_status) AS after_state,
                    r.reason AS description,
                    NULL AS correlation_id,
                    '{{}}'::jsonb AS metadata,
                    'review_service' AS source,
                    r.created_at
                FROM review_status_history r
                WHERE {rev_where}
            ) combined
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = (await self.session.execute(
            query_sql, {**bind, "limit": params.page_size, "offset": offset}
        )).fetchall()

        events = []
        for row in rows:
            meta = _parse_metadata(row.metadata)
            status = derive_event_status(row.event_type, meta)
            events.append(
                AuditEventItem(
                    event_id=row.event_id,
                    event_type=row.event_type,
                    action=row.action,
                    resource_type=row.resource_type,
                    resource_id=row.resource_id,
                    actor_id=row.actor_id,
                    before_state=row.before_state,
                    after_state=row.after_state,
                    description=row.description,
                    correlation_id=row.correlation_id,
                    status=status,
                    severity=derive_event_severity(row.event_type, meta, status),
                    source=row.source,
                    ip_address=meta.get("ip_address"),
                    error_message=meta.get("error_message"),
                    created_at=row.created_at,
                )
            )

        return AuditQueryResponse(
            events=events,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    async def get_summary(self, period_days: int = 7) -> AuditSummaryResponse:
        """Get summary of audit activity for the period."""
        period = f"{period_days} days"
        gov_count = (await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM governance_audit_events
                WHERE tenant_id = :tenant_id
                  AND created_at > NOW() - :period::interval
            """),
            {"tenant_id": self.tenant_id, "period": period},
        )).scalar() or 0

        review_count = (await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM review_status_history
                WHERE tenant_id = :tenant_id
                  AND created_at > NOW() - :period::interval
            """),
            {"tenant_id": self.tenant_id, "period": period},
        )).scalar() or 0

        total = gov_count + review_count

        by_type_rows = (await self.session.execute(
            sa_text("""
                SELECT event_type, COUNT(*)::int AS count
                FROM governance_audit_events
                WHERE tenant_id = :tenant_id
                  AND created_at > NOW() - :period::interval
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 20
            """),
            {"tenant_id": self.tenant_id, "period": period},
        )).fetchall()
        by_type = [
            AuditEventTypeCount(event_type=row.event_type, count=row.count)
            for row in by_type_rows
        ]
        if review_count > 0:
            by_type.append(AuditEventTypeCount(event_type="review_status_change", count=review_count))

        unique_actors = (await self.session.execute(
            sa_text("""
                SELECT COUNT(DISTINCT actor_id)::int FROM governance_audit_events
                WHERE tenant_id = :tenant_id
                  AND created_at > NOW() - :period::interval
            """),
            {"tenant_id": self.tenant_id, "period": period},
        )).scalar() or 0

        return AuditSummaryResponse(
            total_events=total,
            events_by_type=by_type,
            unique_actors=unique_actors,
            period_days=period_days,
        )
