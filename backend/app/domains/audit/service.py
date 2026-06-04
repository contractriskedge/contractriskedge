"""Audit service — query audit events from governance_audit_events and review_status_history."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, text as sa_text, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.schemas import (
    AuditEventItem, AuditQueryParams, AuditQueryResponse,
    AuditEventTypeCount, AuditSummaryResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class AuditService:
    """Queries audit events from multiple audit tables."""

    session: AsyncSession
    tenant_id: str

    async def query_events(self, params: AuditQueryParams) -> AuditQueryResponse:
        """Query audit events with filtering and pagination.

        Searches across governance_audit_events and review_status_history
        tables. Pagination is performed at the DB level for performance.
        """
        # Get total count across both tables
        gov_count = await self._count_governance_events(params)
        review_count = await self._count_review_events(params)
        total = gov_count + review_count
        total_pages = max(1, (total + params.page_size - 1) // params.page_size)

        # Query governance events with DB pagination
        gov_events = await self._query_governance_events_paginated(params)

        # Query review events with DB pagination
        review_events = await self._query_review_events_paginated(params)

        # Merge and sort (both queries return time-descending data)
        all_events: list[AuditEventItem] = []
        gi, ri = 0, 0
        while gi < len(gov_events) and ri < len(review_events):
            if gov_events[gi].created_at >= review_events[ri].created_at:
                all_events.append(gov_events[gi])
                gi += 1
            else:
                all_events.append(review_events[ri])
                ri += 1
        all_events.extend(gov_events[gi:])
        all_events.extend(review_events[ri:])

        # Apply pagination on merged results
        start = (params.page - 1) * params.page_size
        page_events = all_events[start:start + params.page_size]

        return AuditQueryResponse(
            events=page_events,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    async def get_summary(self, period_days: int = 7) -> AuditSummaryResponse:
        """Get summary of audit activity for the period."""
        # Count governance events
        gov_count_sql = sa_text("""
            SELECT COUNT(*)::int FROM governance_audit_events
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - :period::interval
        """)
        result = await self.session.execute(
            gov_count_sql, {"tenant_id": self.tenant_id, "period": f"{period_days} days"},
        )
        gov_count = result.scalar() or 0

        # Count review history events
        review_count_sql = sa_text("""
            SELECT COUNT(*)::int FROM review_status_history
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - :period::interval
        """)
        result = await self.session.execute(
            review_count_sql, {"tenant_id": self.tenant_id, "period": f"{period_days} days"},
        )
        review_count = result.scalar() or 0

        total = gov_count + review_count

        # Events by type
        by_type_sql = sa_text("""
            SELECT event_type, COUNT(*)::int AS count
            FROM governance_audit_events
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - :period::interval
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 20
        """)
        result = await self.session.execute(
            by_type_sql, {"tenant_id": self.tenant_id, "period": f"{period_days} days"},
        )
        by_type = [
            AuditEventTypeCount(event_type=row.event_type, count=row.count)
            for row in result.fetchall()
        ]

        # Add review status changes as a type
        if review_count > 0:
            by_type.append(AuditEventTypeCount(
                event_type="review_status_change",
                count=review_count,
            ))

        # Unique actors
        actors_sql = sa_text("""
            SELECT COUNT(DISTINCT actor_id)::int FROM governance_audit_events
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - :period::interval
        """)
        result = await self.session.execute(
            actors_sql, {"tenant_id": self.tenant_id, "period": f"{period_days} days"},
        )
        unique_actors = result.scalar() or 0

        return AuditSummaryResponse(
            total_events=total,
            events_by_type=by_type,
            unique_actors=unique_actors,
            period_days=period_days,
        )

    async def _count_governance_events(self, params: AuditQueryParams) -> int:
        """Count governance_audit_events matching filters."""
        conditions, bind = self._build_governance_conditions(params)
        sql = sa_text(f"SELECT COUNT(*)::int FROM governance_audit_events WHERE {' AND '.join(conditions)}")
        result = await self.session.execute(sql, bind)
        return result.scalar() or 0

    async def _count_review_events(self, params: AuditQueryParams) -> int:
        """Count review_status_history matching filters."""
        conditions, bind = self._build_review_conditions(params)
        sql = sa_text(f"SELECT COUNT(*)::int FROM review_status_history WHERE {' AND '.join(conditions)}")
        result = await self.session.execute(sql, bind)
        return result.scalar() or 0

    async def _query_governance_events_paginated(self, params: AuditQueryParams) -> list[AuditEventItem]:
        """Query governance_audit_events with DB-level pagination."""
        conditions, bind = self._build_governance_conditions(params)
        offset = (params.page - 1) * params.page_size
        sql = sa_text(f"""
            SELECT event_id, event_type, previous_state, new_state, change_summary,
                   entity_type, entity_id,
                   actor_id, correlation_id, created_at
            FROM governance_audit_events
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = await self.session.execute(sql, {**bind, "limit": params.page_size, "offset": offset})
        return [
            AuditEventItem(
                event_id=str(row.event_id),
                event_type=row.event_type,
                action=row.event_type,
                resource_type=row.entity_type,
                resource_id=str(row.entity_id) if row.entity_id else "",
                actor_id=row.actor_id,
                before_state=row.previous_state,
                after_state=row.new_state,
                description=row.change_summary,
                correlation_id=row.correlation_id,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]

    async def _query_review_events_paginated(self, params: AuditQueryParams) -> list[AuditEventItem]:
        """Query review_status_history with DB-level pagination."""
        conditions, bind = self._build_review_conditions(params)
        offset = (params.page - 1) * params.page_size
        sql = sa_text(f"""
            SELECT history_id, review_id, from_status, to_status,
                   changed_by, reason, created_at
            FROM review_status_history
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = await self.session.execute(sql, {**bind, "limit": params.page_size, "offset": offset})
        return [
            AuditEventItem(
                event_id=f"review-{row.history_id}",
                event_type="review_status_change",
                action=f"status_change: {row.from_status} -> {row.to_status}",
                resource_type="review",
                resource_id=str(row.review_id),
                actor_id=row.changed_by,
                before_state={"status": row.from_status},
                after_state={"status": row.to_status},
                description=row.reason,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]

    def _build_governance_conditions(self, params: AuditQueryParams) -> tuple[list[str], dict]:
        """Build WHERE conditions and bind params for governance_audit_events."""
        conditions = ["tenant_id = :tenant_id"]
        bind: dict = {"tenant_id": self.tenant_id}
        if params.event_type:
            conditions.append("event_type = :event_type")
            bind["event_type"] = params.event_type
        if params.resource_type:
            conditions.append("entity_type = :resource_type")
            bind["resource_type"] = params.resource_type
        if params.resource_id:
            conditions.append("entity_id = :resource_id")
            bind["resource_id"] = params.resource_id
        if params.actor_id:
            conditions.append("actor_id = :actor_id")
            bind["actor_id"] = params.actor_id
        if params.action:
            conditions.append("event_type = :action")
            bind["action"] = params.action
        if params.from_date:
            conditions.append("created_at >= :from_date")
            bind["from_date"] = params.from_date
        if params.to_date:
            conditions.append("created_at <= :to_date")
            bind["to_date"] = params.to_date
        return conditions, bind

    def _build_review_conditions(self, params: AuditQueryParams) -> tuple[list[str], dict]:
        """Build WHERE conditions and bind params for review_status_history."""
        conditions = ["tenant_id = :tenant_id"]
        bind: dict = {"tenant_id": self.tenant_id}
        if params.resource_id:
            conditions.append("review_id = :resource_id")
            bind["resource_id"] = params.resource_id
        if params.actor_id:
            conditions.append("changed_by = :actor_id")
            bind["actor_id"] = params.actor_id
        if params.from_date:
            conditions.append("created_at >= :from_date")
            bind["from_date"] = params.from_date
        if params.to_date:
            conditions.append("created_at <= :to_date")
            bind["to_date"] = params.to_date
        return conditions, bind
