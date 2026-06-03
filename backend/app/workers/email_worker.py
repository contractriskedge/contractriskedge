"""Email notification worker — async email delivery via Resend.

Processes the email_queue table:
1. Picks up pending emails (with retry eligibility)
2. Renders HTML template from template_name + template_data
3. Sends via ResendEmailService
4. Marks as sent or schedules retry

Run with:
    celery -A app.workers.celery_app worker --loglevel=info -Q email
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.domains.notify.email_service import ResendEmailService, EmailMessage
from app.domains.notify.email_templates import TEMPLATE_MAP, TEMPLATE_ALIASES

logger = logging.getLogger(__name__)

TASK_NAME = "send_email"

# Try to register as Celery task; gracefully degrade if Celery unavailable
celery_app = None
try:
    from app.workers.celery_app import celery_app as _celery
    celery_app = _celery
except ImportError:
    logger.warning("Celery not available — email worker task not registered")


def _render_html(template_name: str, template_data: dict) -> tuple[str, str]:
    """Render email HTML from template. Returns (subject, html_body)."""
    # Filter out metadata keys that aren't template parameters
    render_kwargs = {k: v for k, v in template_data.items() if k not in ("subject", "body")}
    subject = template_data.get("subject", "Contract Risk Edge Notification")

    # Try template map first, then aliases
    render_fn = TEMPLATE_MAP.get(template_name) or TEMPLATE_ALIASES.get(template_name)
    if render_fn:
        html = render_fn(**render_kwargs)
        return subject, html

    # Fallback: generic template
    body = template_data.get("body", "")
    html = f"""<h2>Notification</h2><p>{body}</p>"""
    return subject, html


async def process_email_queue(
    batch_size: int = 10,
    session=None,
) -> int:
    """Process pending emails from the queue. Returns count of emails processed.

    When ``session`` is provided (e.g. from the API request), pending rows flushed
    in that session are visible without waiting for Celery beat.
    """
    from app.domains.notify.repository import NotificationRepository
    from app.config import settings

    email_svc = ResendEmailService()
    is_mock = not settings.resend_api_key
    if is_mock:
        logger.info("RESEND_API_KEY not configured — running in MOCK mode (emails logged to console)")
    processed = 0

    owns_session = session is None
    engine = None
    if owns_session:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker

        db_url = settings.database_url
        engine = create_async_engine(db_url)
        async_session_factory = sessionmaker(engine, class_=AsyncSession)
        session = async_session_factory()

    repo = NotificationRepository(session, tenant_id=settings.dev_tenant_id)

    try:
        pending = await repo.get_pending_emails(limit=batch_size)

        for entry in pending:
            try:
                subject, html = _render_html(entry.template_name, entry.template_data or {})
                msg = EmailMessage(
                    to=entry.recipient_email,
                    subject=subject,
                    html=html,
                )
                provider_id = await email_svc.send(msg)

                if provider_id:
                    await repo.mark_email_sent(entry.email_id, provider_id)
                    logger.info("Email sent: %s -> %s (%s)", entry.template_name, entry.recipient_email, provider_id)
                else:
                    # Mark as failed permanently if no provider_id returned
                    await repo.mark_email_failed(entry.email_id, "No provider message ID returned")
                    logger.warning("Email failed (no ID): %s -> %s", entry.template_name, entry.recipient_email)

            except Exception as exc:
                logger.error("Email send error for %s: %s", entry.email_id, exc)
                if entry.attempt_count + 1 >= entry.max_attempts:
                    await repo.mark_email_failed(entry.email_id, str(exc))
                    logger.warning("Email %s failed after %d attempts", entry.email_id, entry.max_attempts)
                else:
                    retry_at = datetime.now(timezone.utc) + timedelta(minutes=settings.email_retry_interval_minutes)
                    await repo.mark_email_failed(entry.email_id, str(exc), retry_at=retry_at)
                    logger.info("Email %s will retry at %s", entry.email_id, retry_at)

            processed += 1

        if owns_session:
            await session.commit()
        logger.info("Email queue processing complete: %d emails processed", processed)

    finally:
        if owns_session:
            await session.close()
            if engine is not None:
                await engine.dispose()

    return processed


if celery_app:
    @celery_app.task(name=TASK_NAME, queue="email", bind=True, max_retries=0)
    def send_email_task(self) -> int:
        """Celery task: process pending email queue."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(process_email_queue())
            return result
        finally:
            loop.close()
else:
    logger.warning("Celery not available — email worker task not registered")
