"""SLA overdue check — flags overdue contract reviews and emits SLA_BREACHED events.

Runs periodically via Celery Beat. Scans all active reviews where
sla_deadline < NOW() and sla_status != 'overdue', then:

1. Updates sla_status → 'overdue' / 'critical_overdue'
2. Sets sla_breached → True
3. Recalculates overdue_hours
4. Emits SLA_BREACHED domain event
5. Logs status change in review_status_history
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update, func as sa_func, text as sa_text

from app.domains.review.models import ContractReview, ReviewStatusHistory

logger = logging.getLogger(__name__)

TASK_NAME = "check_sla_overdue"


async def check_sla_overdue() -> dict:
    """Check all active reviews for SLA breaches and update them.

    Returns a summary dict with counts of affected reviews.
    """
    from app.kernel.database.sync_session import get_sync_factory

    now = datetime.now(timezone.utc)
    affected = 0
    critical = 0

    factory = get_sync_factory()
    session = factory.create_session(tenant_id="system", user_id="system", user_role="admin")
    try:
        # Get all active tenants
        tenants_sql = sa_text("SELECT tenant_id FROM tenants WHERE is_active = TRUE")
        tenants = session.execute(tenants_sql).fetchall()

        for (tenant_id,) in tenants:
            tenant_id_str = str(tenant_id)

            # Find all active reviews where SLA has passed
            stmt = select(ContractReview).where(
                ContractReview.tenant_id == tenant_id_str,
                ContractReview.sla_deadline.isnot(None),
                ContractReview.sla_deadline < now,
                ContractReview.sla_status.in_(["on_track", "warning"]),
                ContractReview.is_deleted.is_(False),
                ContractReview.status.notin_(["approved", "rejected", "closed"]),
            )
            result = session.execute(stmt)
            reviews = result.scalars().all()

            for review in reviews:
                diff_seconds = (now - review.sla_deadline).total_seconds()
                overdue_hours = max(0, diff_seconds / 3600)
                is_critical = overdue_hours >= 24
                new_sla_status = "critical_overdue" if is_critical else "overdue"

                # Update the review record
                session.execute(
                    update(ContractReview).where(
                        ContractReview.review_id == review.review_id,
                        ContractReview.tenant_id == tenant_id_str,
                    ).values(
                        sla_status=new_sla_status,
                        sla_breached=True,
                        overdue_hours=round(overdue_hours, 1),
                        updated_at=sa_func.now(),
                    )
                )

                # Log status change in history
                session.add(ReviewStatusHistory(
                    review_id=review.review_id,
                    tenant_id=tenant_id_str,
                    from_status=review.sla_status,
                    to_status=f"sla_{new_sla_status}",
                    changed_by="system",
                    reason=f"SLA breached — overdue by {round(overdue_hours, 1)} hours",
                ))

                affected += 1
                if is_critical:
                    critical += 1

                logger.info(
                    "SLA breached: review=%s tenant=%s overdue_hours=%.1f status=%s",
                    review.review_id, tenant_id_str, overdue_hours, new_sla_status,
                )

                # Send SLA breach notification to assignee
                if review.assigned_to:
                    from app.domains.notify.repository import NotificationRepository
                    from app.domains.notify.service import NotificationService
                    from app.kernel.events.bus import EventBus

                    notify_repo = NotificationRepository(session, tenant_id=tenant_id_str)
                    notify_svc = NotificationService(
                        repo=notify_repo,
                        event_bus=EventBus(),
                        tenant_id=tenant_id_str,
                    )
                    notify_svc.send_notification(
                        user_id=review.assigned_to,
                        notif_type="review.overdue",
                        title="Review SLA Breached",
                        body=f"SLA breached for review. Overdue by {round(overdue_hours, 1)} hours.",
                        severity="critical" if is_critical else "high",
                        entity_type="review",
                        entity_id=str(review.review_id),
                        action_url=f"/reviews/{review.review_id}",
                        dedup_key=f"sla_breach:{review.review_id}",
                    )

        session.commit()
    finally:
        session.close()

    return {
        "checked_at": now.isoformat(),
        "total_affected": affected,
        "critical_overdue": critical,
        "overdue": affected - critical,
    }


# ── Celery Task Registration ──────────────────────────────────────

try:
    from workers.celery_app import celery_app

    @celery_app.task(name=TASK_NAME, queue="default")
    def check_sla_overdue_task():
        """Celery task wrapper — runs the SLA check synchronously."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(check_sla_overdue())
            logger.info("SLA check complete: %s", result)
            return result
        finally:
            loop.close()

except ImportError:
    logger.warning("Celery not available — SLA check task not registered")
