"""Notifications and workflow Celery workers — delivery, SLA evaluation, escalation processing."""

from __future__ import annotations

import logging

from app.config import settings
from app.domains.notify.repository import NotificationRepository, WorkflowRepository
from app.domains.notify.service import NotificationService
from app.domains.notify.workflows import WorkflowAutomationService
from app.kernel.events.bus import EventBus
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


from workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="deliver_notification",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def deliver_notification_task(self, notification_id: str, tenant_id: str, user_id: str, channel: str):
    """Deliver a notification via the specified channel.

    For in_app: marks delivery as delivered immediately.
    For email: prepares email payload (actual sending is future).
    Retries up to 5 times with exponential backoff.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_deliver_notification(helper, notification_id, tenant_id, user_id, channel))


async def _deliver_notification(helper: WorkerAsyncHelper, notification_id: str, tenant_id: str, user_id: str, channel: str):
    session = await worker_loop.create_session(tenant_id, user_id, "api")
    async with helper.session_scope(session):
        try:
            repo = NotificationRepository(session, tenant_id=tenant_id)
            notif = await repo.get(notification_id, tenant_id)
            if not notif:
                logger.warning("Notification not found: %s", notification_id)
                return

            from sqlalchemy import func, update
            from app.domains.notify.models import NotificationDelivery

            if channel == "in_app":
                stmt = update(NotificationDelivery).where(
                    NotificationDelivery.notification_id == notification_id,
                ).values(status="delivered", delivered_at=func.now())
                await session.execute(stmt)
                await session.commit()
                logger.info("In-app notification delivered: %s", notification_id)

            elif channel == "email":
                logger.info("Email notification prepared: %s", notification_id)
                # Attempt to send real email
                try:
                    from app.domains.notify.email import send_email
                    notif = await session.execute(
                        select(Notification).where(Notification.notification_id == notification_id)
                    )
                    notif_row = notif.scalar_one_or_none()
                    if notif_row:
                        success = await send_email(
                            recipient_email=user_id if "@" in user_id else f"{user_id}@localhost",
                            subject=notif_row.title,
                            html_body=f"<p>{notif_row.body or ''}</p>",
                        )
                        if success:
                            stmt = update(NotificationDelivery).where(
                                NotificationDelivery.notification_id == notification_id,
                            ).values(status="delivered", delivered_at=func.now())
                            await session.execute(stmt)
                        else:
                            logger.warning("Email send returned False for %s", notification_id)
                            stmt = update(NotificationDelivery).where(
                                NotificationDelivery.notification_id == notification_id,
                            ).values(status="failed")
                            await session.execute(stmt)
                except Exception as email_err:
                    logger.error("Email delivery failed for %s: %s", notification_id, email_err)
                    stmt = update(NotificationDelivery).where(
                        NotificationDelivery.notification_id == notification_id,
                    ).values(status="failed", last_error=str(email_err))
                    await session.execute(stmt)
                else:
                    # Fallback: mark as delivered if email not configured
                    stmt = update(NotificationDelivery).where(
                        NotificationDelivery.notification_id == notification_id,
                    ).values(status="delivered", delivered_at=func.now())
                    await session.execute(stmt)
                await session.commit()

        except Exception as exc:
            await session.rollback()
            logger.error("Notification delivery failed: %s", exc)
            raise


@celery_app.task(
    bind=True,
    name="process_workflow_timers",
    max_retries=3,
    acks_late=True,
)
def process_workflow_timers_task(self, tenant_id: str):
    """Process all due workflow timers for a tenant.

    Triggers SLA warnings, overdue markings, and auto-escalations.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_process_timers(helper, tenant_id))


async def _process_timers(helper: WorkerAsyncHelper, tenant_id: str):
    session = await worker_loop.create_session(tenant_id, "system", "api")
    async with helper.session_scope(session):
        try:
            notif_service = NotificationService(
                repo=NotificationRepository(session, tenant_id=tenant_id),
                event_bus=EventBus(), tenant_id=tenant_id,
            )
            workflow_service = WorkflowAutomationService(
                repo=WorkflowRepository(session, tenant_id=tenant_id),
                notif_service=notif_service,
                event_bus=EventBus(), tenant_id=tenant_id,
            )
            count = await workflow_service.process_due_timers()
            await session.commit()
            if count > 0:
                logger.info("Processed %d workflow timers for tenant %s", count, tenant_id)
        except Exception as exc:
            await session.rollback()
            logger.error("Timer processing failed: %s", exc)
