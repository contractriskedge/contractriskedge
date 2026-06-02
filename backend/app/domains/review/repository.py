"""Review repository — data access for reviews, findings, redlines, comments, assignments, escalations."""

from __future__ import annotations

import logging
import uuid as uuid_mod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func, or_
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.repository.base import BaseRepository

logger = logging.getLogger(__name__)
from app.domains.review.models import (
    ContractReview, ReviewFinding, ReviewRedline, ReviewComment,
    ReviewAssignment, ReviewEscalation, ReviewApproval, ReviewStatusHistory,
    ReviewStatus, FindingResolution, RedlineStatus,
)


@dataclass
class ReviewRepository(BaseRepository):

    async def _paginate_with_join(self, query, page: int = 1, page_size: int = 20):
        """Paginate a joined query that returns (model, filename, content_type) tuples.

        Returns (list[model_with_attrs], total_count).
        """
        # Count from a subquery (strip the join columns)
        from sqlalchemy import func as sa_func
        count_subq = query.subquery()
        total = await self.scalar(
            select(sa_func.count()).select_from(count_subq)
        )
        # Fetch page
        result = await self.session.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        rows = result.all()
        items = []
        for row in rows:
            review, filename, content_type = row
            review._document_filename = filename
            review._document_content_type = content_type
            items.append(review)
        return items, total or 0

    async def create_review(self, upload_id: str, tenant_id: str, created_by: str) -> ContractReview:
        review = ContractReview(upload_id=upload_id, tenant_id=tenant_id, created_by=created_by)
        self.session.add(review)
        await self.session.flush()
        return review

    async def get_review(self, review_id: str, tenant_id: str) -> Optional[ContractReview]:
        from app.domains.ingestion.models import UploadSession

        try:
            review_uuid = uuid_mod.UUID(str(review_id))
        except (ValueError, TypeError):
            return None

        stmt = (
            select(ContractReview, UploadSession.filename, UploadSession.content_type)
            .outerjoin(UploadSession, ContractReview.upload_id == UploadSession.upload_id)
            .where(
                ContractReview.review_id == review_uuid,
                ContractReview.tenant_id == tenant_id,
            )
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        review, filename, content_type = row
        # Attach transient attributes for the service layer
        review._document_filename = filename
        review._document_content_type = content_type
        return review

    async def get_review_by_upload(self, upload_id: str, tenant_id: str) -> Optional[ContractReview]:
        from app.domains.ingestion.models import UploadSession

        stmt = (
            select(ContractReview, UploadSession.filename, UploadSession.content_type)
            .outerjoin(UploadSession, ContractReview.upload_id == UploadSession.upload_id)
            .where(
                ContractReview.upload_id == upload_id,
                ContractReview.tenant_id == tenant_id,
            )
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        review, filename, content_type = row
        review._document_filename = filename
        review._document_content_type = content_type
        return review

    async def list_reviews(self, tenant_id: str, filters, pagination):
        from app.domains.ingestion.models import UploadSession

        query = (
            select(ContractReview, UploadSession.filename, UploadSession.content_type)
            .outerjoin(UploadSession, ContractReview.upload_id == UploadSession.upload_id)
            .where(ContractReview.tenant_id == tenant_id)
            .where(ContractReview.is_deleted == False)
        )
        if filters.status:
            query = query.where(ContractReview.status == filters.status)
        if filters.assigned_to:
            query = query.where(ContractReview.assigned_to == filters.assigned_to)
        if filters.priority:
            query = query.where(ContractReview.priority == filters.priority)
        sort_col = getattr(ContractReview, pagination.sort_by, ContractReview.created_at)
        order = sort_col.desc() if pagination.sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)
        return await self._paginate_with_join(query, pagination.page, pagination.page_size)

    async def get_my_work(self, tenant_id: str, user_id: str) -> list[ContractReview]:
        """Get reviews assigned to the current user that are not deleted."""
        from app.domains.ingestion.models import UploadSession

        query = (
            select(ContractReview, UploadSession.filename, UploadSession.content_type)
            .outerjoin(UploadSession, ContractReview.upload_id == UploadSession.upload_id)
            .where(ContractReview.tenant_id == tenant_id)
            .where(ContractReview.is_deleted == False)
            .where(ContractReview.assigned_to == user_id)
            .order_by(ContractReview.created_at.desc())
        )
        result = await self.session.execute(query)
        rows = result.all()
        items = []
        for row in rows:
            review, filename, content_type = row
            review._document_filename = filename
            review._document_content_type = content_type
            items.append(review)
        return items

    async def get_queue(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        risk_min: Optional[float] = None,
        risk_max: Optional[float] = None,
        age_min_hours: Optional[float] = None,
        age_max_hours: Optional[float] = None,
        escalated_only: bool = False,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ContractReview], int]:
        """Get the operational review queue with filters. Excludes deleted reviews."""
        from app.domains.ingestion.models import UploadSession

        query = (
            select(ContractReview, UploadSession.filename, UploadSession.content_type)
            .outerjoin(UploadSession, ContractReview.upload_id == UploadSession.upload_id)
            .where(ContractReview.tenant_id == tenant_id)
            .where(ContractReview.is_deleted == False)
        )
        if status:
            query = query.where(ContractReview.status == status)
        if assigned_to:
            query = query.where(ContractReview.assigned_to == assigned_to)
        if escalated_only:
            query = query.where(ContractReview.status == "escalated")
        if risk_min is not None or risk_max is not None:
            from sqlalchemy import cast, Float, text
            # risk_score is inside document_metadata JSONB
            risk_expr = text("(r.document_metadata->>'risk_score')::float")
            if risk_min is not None:
                query = query.where(risk_expr >= risk_min)
            if risk_max is not None:
                query = query.where(risk_expr <= risk_max)

        # Age filters via created_at
        if age_min_hours is not None or age_max_hours is not None:
            from sqlalchemy import text as sa_text
            now = sa_text("NOW()")
            if age_min_hours is not None:
                query = query.where(ContractReview.created_at <= func.now() - func.make_interval(hours=int(age_min_hours)))
            if age_max_hours is not None:
                query = query.where(ContractReview.created_at >= func.now() - func.make_interval(hours=int(age_max_hours)))

        sort_col = getattr(ContractReview, sort_by, ContractReview.created_at)
        order = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)

        return await self._paginate_with_join(query, page, page_size)

    async def update_status(self, review_id: str, tenant_id: str, new_status: ReviewStatus,
                             changed_by: str, reason: Optional[str] = None) -> Optional[ContractReview]:
        review = await self.get_review(review_id, tenant_id)
        if not review:
            return None

        current_status = review.status
        if isinstance(current_status, str):
            current_status = ReviewStatus(current_status)
        if not current_status.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {current_status} to {new_status}")

        old_status = current_status.value
        status_value = new_status.value if isinstance(new_status, ReviewStatus) else str(new_status)
        review_values: dict = {
            "status": status_value,
            "updated_at": func.now(),
        }
        if new_status in (ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.CLOSED):
            review_values["completed_at"] = func.now()
        await self.session.execute(
            update(ContractReview)
            .where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == tenant_id,
            )
            .values(**review_values)
        )

        # Log status change
        self.session.add(ReviewStatusHistory(
            review_id=review_id, tenant_id=tenant_id,
            from_status=old_status, to_status=status_value,
            changed_by=changed_by, reason=reason,
        ))
        await self.session.flush()
        review.status = new_status
        return review

    async def get_findings(self, review_id: str, tenant_id: str, severity: Optional[str] = None,
                            resolution: Optional[str] = None, page: int = 1, page_size: int = 50):
        query = select(ReviewFinding).where(
            ReviewFinding.review_id == review_id, ReviewFinding.tenant_id == tenant_id,
        )
        if severity:
            query = query.where(ReviewFinding.severity == severity)
        if resolution:
            query = query.where(ReviewFinding.resolution == resolution)
        # No default resolution filter — show ALL findings (resolved + unresolved)
        query = query.order_by(
            func.array_position(array(['critical', 'high', 'medium', 'low', 'info']), ReviewFinding.severity)
        )
        return await self.paginate(query, page, page_size)

    async def resolve_finding(self, finding_id: str, tenant_id: str,
                               resolution: FindingResolution, note: Optional[str] = None,
                               resolved_by: Optional[str] = None) -> Optional[ReviewFinding]:
        stmt = update(ReviewFinding).where(
            ReviewFinding.finding_id == finding_id, ReviewFinding.tenant_id == tenant_id,
        ).values(
            resolution=resolution.value,
            resolution_note=note,
            resolved_by=resolved_by,
            resolved_at=func.now(),
        )
        await self.session.execute(stmt)
        await self.session.flush()
        result = await self.session.execute(
            select(ReviewFinding)
            .where(
                ReviewFinding.finding_id == finding_id,
                ReviewFinding.tenant_id == tenant_id,
            )
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_redlines(self, review_id: str, tenant_id: str, status: Optional[str] = None):
        query = select(ReviewRedline).where(
            ReviewRedline.review_id == review_id, ReviewRedline.tenant_id == tenant_id,
        )
        if status:
            query = query.where(ReviewRedline.status == status)
        query = query.order_by(ReviewRedline.created_at)
        result = await self.session.execute(query)
        redlines = list(result.scalars().all())
        logger.debug(
            "Fetched %d redlines for review %s (status=%s)",
            len(redlines), review_id, status or "all",
        )
        for r in redlines:
            meta = dict(r.redline_metadata) if r.redline_metadata else {}
            trace = meta.get("traceability", {})
            if isinstance(trace, dict) and trace.get("generated_from") == "mitigation_recommendation":
                logger.debug(
                    "  Mitigation redline: id=%s type=%s",
                    r.redline_id, trace.get("mitigation_type", "unknown"),
                )
        return redlines

    async def update_redline(self, redline_id: str, tenant_id: str,
                              status: RedlineStatus, modified_text: Optional[str] = None,
                              reviewed_by: Optional[str] = None,
                              review_notes: Optional[str] = None) -> Optional[ReviewRedline]:
        stmt = update(ReviewRedline).where(
            ReviewRedline.redline_id == redline_id, ReviewRedline.tenant_id == tenant_id,
        ).values(
            status=status.value,
            reviewer_modified_text=modified_text,
            review_notes=review_notes,
            reviewed_by=reviewed_by,
            reviewed_at=func.now(),
        )
        await self.session.execute(stmt)
        await self.session.flush()
        result = await self.session.execute(
            select(ReviewRedline)
            .where(
                ReviewRedline.redline_id == redline_id,
                ReviewRedline.tenant_id == tenant_id,
            )
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def add_comment(self, review_id: str, tenant_id: str, author_id: str,
                           body: str, entity_type: Optional[str] = None,
                           entity_id: Optional[str] = None,
                           parent_comment_id: Optional[str] = None,
                           mentions: Optional[list[str]] = None) -> ReviewComment:
        comment = ReviewComment(
            review_id=review_id, tenant_id=tenant_id, author_id=author_id, body=body,
            entity_type=entity_type, entity_id=entity_id,
            parent_comment_id=parent_comment_id, mentions=mentions or [],
        )
        self.session.add(comment)
        await self.session.flush()

        # Update comment count
        await self.session.execute(
            update(ContractReview).where(ContractReview.review_id == review_id)
            .values(comment_count=ContractReview.comment_count + 1)
        )
        return comment

    async def create_redline(
        self,
        review_id: str,
        tenant_id: str,
        upload_id: str,
        clause_type: Optional[str],
        original_text: str,
        proposed_text: str,
        operation: Optional[str],
        anchor_text: Optional[str],
        rationale: Optional[str],
        risk_level: Optional[str],
        finding_id: Optional[str] = None,
        redline_metadata: Optional[dict] = None,
    ) -> ReviewRedline:
        """Create a new redline (e.g. from a mitigation recommendation)."""
        from app.domains.review.models import ReviewRedline as RRModel

        redline = RRModel(
            review_id=review_id,
            tenant_id=tenant_id,
            upload_id=upload_id,
            clause_type=clause_type,
            original_text=original_text,
            proposed_text=proposed_text,
            operation=operation or "insert",
            anchor_text=anchor_text,
            rationale=rationale,
            risk_level=risk_level,
            finding_id=finding_id,
            redline_metadata=redline_metadata or {},
            status=RedlineStatus.PROPOSED,
        )
        self.session.add(redline)
        await self.session.flush()

        # Update redline count
        await self.session.execute(
            update(ContractReview).where(ContractReview.review_id == review_id)
            .values(redline_count=ContractReview.redline_count + 1)
        )
        await self.session.flush()

        return redline

    async def get_comments(self, review_id: str, tenant_id: str):
        stmt = select(ReviewComment).where(
            ReviewComment.review_id == review_id, ReviewComment.tenant_id == tenant_id,
            ReviewComment.deleted_at.is_(None),
        ).order_by(ReviewComment.created_at)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def assign_reviewer(self, review_id: str, tenant_id: str,
                               assignee_id: str, assigned_by: str, role: str = "reviewer",
                               due_date: Optional[datetime] = None) -> ReviewAssignment:
        assignment = ReviewAssignment(
            review_id=review_id, tenant_id=tenant_id, assignee_id=assignee_id,
            assigned_by=assigned_by, role=role, due_date=due_date,
        )
        self.session.add(assignment)
        await self.session.execute(
            update(ContractReview).where(ContractReview.review_id == review_id)
            .values(assigned_to=assignee_id, assigned_by=assigned_by)
        )
        await self.session.flush()
        return assignment

    async def get_assignments(self, review_id: str, tenant_id: str):
        stmt = select(ReviewAssignment).where(
            ReviewAssignment.review_id == review_id, ReviewAssignment.tenant_id == tenant_id,
        ).order_by(ReviewAssignment.created_at)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def escalate(self, review_id: str, tenant_id: str, escalated_by: str,
                        reason: str, escalated_to: Optional[str] = None) -> ReviewEscalation:
        # Get current escalation count
        stmt = select(func.count()).select_from(ReviewEscalation).where(
            ReviewEscalation.review_id == review_id, ReviewEscalation.tenant_id == tenant_id,
        )
        count = await self.scalar(stmt) or 0

        escalation = ReviewEscalation(
            review_id=review_id, tenant_id=tenant_id, level=count + 1,
            escalated_by=escalated_by, escalated_to=escalated_to, reason=reason,
        )
        self.session.add(escalation)
        await self.session.execute(
            update(ContractReview).where(ContractReview.review_id == review_id)
            .values(escalation_count=ContractReview.escalation_count + 1)
        )
        await self.session.flush()
        return escalation

    async def approve(self, review_id: str, tenant_id: str, approver_id: str,
                       decision: str, comments: Optional[str] = None,
                       conditions: Optional[dict] = None) -> ReviewApproval:
        approval = ReviewApproval(
            review_id=review_id, tenant_id=tenant_id, approver_id=approver_id,
            decision=decision, comments=comments, conditions=conditions,
        )
        self.session.add(approval)
        await self.session.flush()
        return approval

    async def get_approvals(self, review_id: str, tenant_id: str):
        stmt = select(ReviewApproval).where(
            ReviewApproval.review_id == review_id, ReviewApproval.tenant_id == tenant_id,
        ).order_by(ReviewApproval.created_at)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_status_history(self, review_id: str, tenant_id: str):
        stmt = select(ReviewStatusHistory).where(
            ReviewStatusHistory.review_id == review_id, ReviewStatusHistory.tenant_id == tenant_id,
        ).order_by(ReviewStatusHistory.created_at)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def archive_old_reviews(self, tenant_id: str, older_than_days: int = 90,
                                   status_filter: Optional[str] = None,
                                   dry_run: bool = False) -> dict:
        """Archive (soft-delete) reviews older than specified days."""
        from sqlalchemy import text as sa_text

        # Build the archive query
        conditions = [
            "r.tenant_id = :tenant_id",
            "r.created_at < NOW() - :older_than_days::interval",
            "r.is_deleted = FALSE",
        ]
        if status_filter:
            conditions.append("r.status = :status_filter")

        where_clause = " AND ".join(conditions)
        count_sql = sa_text(f"SELECT COUNT(*)::int FROM contract_reviews r WHERE {where_clause}")

        count_params = {"tenant_id": tenant_id, "older_than_days": f"{older_than_days} days"}
        if status_filter:
            count_params["status_filter"] = status_filter

        result = await self.session.execute(count_sql, count_params)
        count = result.scalar() or 0

        if dry_run:
            return {"archived_count": count}

        # Perform the soft delete
        update_sql = sa_text(f"""
            UPDATE contract_reviews r
            SET is_deleted = TRUE, deleted_at = NOW(), updated_at = NOW(),
                delete_reason = 'Auto-archived: older than {older_than_days} days'
            WHERE {where_clause}
        """)
        await self.session.execute(update_sql, count_params)
        await self.session.flush()

        return {"archived_count": count}

    # ── Dashboard Aggregation ─────────────────────────────────────

    async def get_dashboard_stats(self, tenant_id: str) -> dict:
        """Get aggregated dashboard statistics."""
        from sqlalchemy import text as sa_text

        sql = sa_text("""
            SELECT
                COUNT(DISTINCT r.review_id)::int AS total_reviews,
                COALESCE(SUM(r.finding_count)::int, 0) AS total_findings,
                COALESCE(SUM(r.redline_count)::int, 0) AS total_redlines,
                AVG(f.confidence)::float AS average_confidence,
                COUNT(DISTINCT r.review_id) FILTER (WHERE r.sla_breached = TRUE)::int AS sla_breach_count,
                COUNT(DISTINCT r.review_id) FILTER (WHERE r.status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval'))::int AS pending_reviews,
                COUNT(DISTINCT r.review_id) FILTER (WHERE r.status IN ('approved', 'rejected', 'closed'))::int AS completed_reviews,
                COUNT(DISTINCT r.review_id) FILTER (WHERE r.status = 'escalated')::int AS escalated_count,
                COUNT(DISTINCT r.review_id) FILTER (WHERE r.sla_deadline IS NOT NULL AND r.sla_deadline < NOW() AND r.status NOT IN ('approved', 'rejected', 'closed'))::int AS sla_at_risk,
                (SELECT COUNT(*)::int FROM review_escalations e WHERE e.tenant_id = :tenant_id) AS total_escalation_events,
                (
                    SELECT COUNT(*)::int
                    FROM review_escalations e
                    JOIN contract_reviews cr ON cr.review_id = e.review_id AND cr.tenant_id = e.tenant_id
                    WHERE e.tenant_id = :tenant_id2 AND cr.status != 'escalated'
                ) AS resolved_escalations,
                COUNT(DISTINCT r.review_id) FILTER (WHERE r.assigned_to IS NULL AND r.status NOT IN ('approved', 'rejected', 'closed'))::int AS unassigned_count,
                COUNT(DISTINCT r.review_id) FILTER (WHERE r.sla_status = 'overdue')::int AS overdue_count,
                COUNT(DISTINCT r.review_id) FILTER (WHERE r.completed_at IS NOT NULL AND r.completed_at >= NOW() - INTERVAL '7 days')::int AS completed_7d,
                COALESCE(ROUND(AVG(CASE WHEN r.status NOT IN ('approved', 'rejected', 'closed') THEN EXTRACT(EPOCH FROM (NOW() - r.created_at))/3600 ELSE NULL END)::numeric, 1), 0)::float AS avg_review_age_hours
            FROM contract_reviews r
            LEFT JOIN review_findings f ON f.review_id = r.review_id AND f.tenant_id = r.tenant_id
            WHERE r.tenant_id = :tenant_id3 AND r.is_deleted = FALSE
        """)
        result = await self.session.execute(sql, {"tenant_id": tenant_id, "tenant_id2": tenant_id, "tenant_id3": tenant_id})
        row = result.fetchone()
        data = dict(row._mapping) if row else {}

        # Compute resolution rate
        total = data.get("total_escalation_events", 0)
        resolved = data.get("resolved_escalations", 0)
        data["escalation_resolution_rate"] = round((resolved / total) * 100, 1) if total > 0 else 0.0

        return data

    async def get_findings_by_severity(self, tenant_id: str) -> dict[str, int]:
        """Get finding counts grouped by severity."""
        from sqlalchemy import text as sa_text

        sql = sa_text("""
            SELECT f.severity, COUNT(*)::int AS count
            FROM review_findings f
            JOIN contract_reviews r ON r.review_id = f.review_id AND r.tenant_id = f.tenant_id
            WHERE f.tenant_id = :tenant_id AND r.is_deleted = FALSE
            GROUP BY f.severity
        """)
        result = await self.session.execute(sql, {"tenant_id": tenant_id})
        return {row.severity: row.count for row in result.fetchall()}

    async def get_findings_by_clause_type(self, tenant_id: str) -> dict[str, int]:
        """Get finding counts grouped by clause type."""
        from sqlalchemy import text as sa_text

        sql = sa_text("""
            SELECT f.clause_type, COUNT(*)::int AS count
            FROM review_findings f
            JOIN contract_reviews r ON r.review_id = f.review_id AND r.tenant_id = f.tenant_id
            WHERE f.tenant_id = :tenant_id AND r.is_deleted = FALSE
            GROUP BY f.clause_type
        """)
        result = await self.session.execute(sql, {"tenant_id": tenant_id})
        return {row.clause_type: row.count for row in result.fetchall()}

    async def get_reviews_by_status(self, tenant_id: str) -> dict[str, int]:
        """Get review counts grouped by status."""
        from sqlalchemy import text as sa_text

        sql = sa_text("""
            SELECT r.status, COUNT(*)::int AS count
            FROM contract_reviews r
            WHERE r.tenant_id = :tenant_id AND r.is_deleted = FALSE
            GROUP BY r.status
        """)
        result = await self.session.execute(sql, {"tenant_id": tenant_id})
        return {row.status: row.count for row in result.fetchall()}

    async def get_recent_activity(self, tenant_id: str, limit: int = 10) -> list[dict]:
        """Get recent activity entries across reviews."""
        from sqlalchemy import text as sa_text

        sql = sa_text("""
            (SELECT 'review_created' AS activity_type,
                    r.review_id::text, r.upload_id::text,
                    'Review created' AS description,
                    r.created_by AS actor, r.created_at AS timestamp
             FROM contract_reviews r WHERE r.tenant_id = :tenant_id AND r.is_deleted = FALSE)
            UNION ALL
            (SELECT 'finding_resolved' AS activity_type,
                    f.review_id::text, NULL::text,
                    'Finding resolved: ' || f.title AS description,
                    f.resolved_by AS actor, f.resolved_at AS timestamp
             FROM review_findings f
             JOIN contract_reviews r ON r.review_id = f.review_id AND r.tenant_id = f.tenant_id
             WHERE f.tenant_id = :tenant_id AND f.resolved_at IS NOT NULL AND r.is_deleted = FALSE)
            UNION ALL
            (SELECT 'review_escalated' AS activity_type,
                    e.review_id::text, NULL::text,
                    'Review escalated' AS description,
                    e.escalated_by AS actor, e.created_at AS timestamp
             FROM review_escalations e
             JOIN contract_reviews r ON r.review_id = e.review_id AND r.tenant_id = e.tenant_id
             WHERE e.tenant_id = :tenant_id AND r.is_deleted = FALSE)
            ORDER BY timestamp DESC
            LIMIT :limit
        """)
        result = await self.session.execute(sql, {"tenant_id": tenant_id, "limit": limit})
        return [dict(row._mapping) for row in result.fetchall()]

    # ── Governance Analytics ─────────────────────────────────────

    async def get_governance_analytics(self, tenant_id: str) -> dict:
        """Get governance-specific analytics for executive reporting.

        Returns:
            - avg_review_time_hours: average time from assigned to completed
            - approval_rate: percentage of decisions that were approved
            - rejection_rate: percentage of decisions that were rejected
            - total_approvals: count of approved reviews
            - total_rejections: count of rejected reviews
            - sla_breach_count: total SLA breaches
            - avg_overdue_hours: average overdue hours among breached reviews
            - escalation_frequency: count of escalations
            - reviewer_workload: list of {reviewer, active_count, completed_count}
            - top_failing_clauses: list of {clause_type, count} from rejected review findings
        """
        from sqlalchemy import text as sa_text

        # Core metrics
        core = sa_text("""
            SELECT
                -- Avg review time (hours) from assigned_at to completed_at
                COALESCE(
                    AVG(EXTRACT(EPOCH FROM (r.completed_at - r.assigned_at)) / 3600)
                    FILTER (WHERE r.assigned_at IS NOT NULL AND r.completed_at IS NOT NULL),
                    0
                )::float AS avg_review_time_hours,

                -- Approval / rejection counts
                COUNT(*) FILTER (WHERE r.status = 'approved')::int AS total_approvals,
                COUNT(*) FILTER (WHERE r.status = 'rejected')::int AS total_rejections,
                COUNT(*) FILTER (WHERE r.status IN ('approved', 'rejected'))::int AS total_decided,

                -- SLA breaches
                COUNT(*) FILTER (WHERE r.sla_breached = TRUE)::int AS sla_breach_count,
                COALESCE(AVG(r.overdue_hours) FILTER (WHERE r.sla_breached = TRUE), 0)::float AS avg_overdue_hours,

                -- Escalations
                COUNT(*) FILTER (WHERE r.status = 'escalated')::int AS escalation_frequency

            FROM contract_reviews r
            WHERE r.tenant_id = :tenant_id AND r.is_deleted = FALSE
        """)
        result = await self.session.execute(core, {"tenant_id": tenant_id})
        metrics = dict(result.fetchone()._mapping)

        # Compute rates
        total_decided = metrics.get("total_decided", 0) or 1
        metrics["approval_rate"] = round((metrics.get("total_approvals", 0) / total_decided) * 100, 1)
        metrics["rejection_rate"] = round((metrics.get("total_rejections", 0) / total_decided) * 100, 1)

        # Reviewer workload
        workload = sa_text("""
            SELECT
                r.assigned_to AS reviewer,
                COUNT(*) FILTER (WHERE r.status IN ('draft', 'ai_analyzed', 'review_ready', 'in_review', 'changes_requested', 'escalated'))::int AS active_count,
                COUNT(*) FILTER (WHERE r.status IN ('approved', 'rejected', 'closed'))::int AS completed_count
            FROM contract_reviews r
            WHERE r.tenant_id = :tenant_id AND r.assigned_to IS NOT NULL AND r.is_deleted = FALSE
            GROUP BY r.assigned_to
            ORDER BY active_count DESC
            LIMIT 20
        """)
        result = await self.session.execute(workload, {"tenant_id": tenant_id})
        metrics["reviewer_workload"] = [
            {"reviewer": row.reviewer, "active_count": row.active_count, "completed_count": row.completed_count}
            for row in result.fetchall()
        ]

        # Top failing clauses (from rejected review findings)
        clauses = sa_text("""
            SELECT f.clause_type, COUNT(*)::int AS count
            FROM review_findings f
            JOIN contract_reviews r ON r.review_id = f.review_id AND r.tenant_id = f.tenant_id
            WHERE r.tenant_id = :tenant_id AND r.status = 'rejected' AND f.clause_type IS NOT NULL
            GROUP BY f.clause_type
            ORDER BY count DESC
            LIMIT 10
        """)
        result = await self.session.execute(clauses, {"tenant_id": tenant_id})
        metrics["top_failing_clauses"] = [
            {"clause_type": row.clause_type, "count": row.count}
            for row in result.fetchall()
        ]

        return metrics
