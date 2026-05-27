"""
Webhook event processing Celery task.

Processes webhook events asynchronously with retry and dead-letter support.
"""

import uuid
from typing import Any, Optional, Optional

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.database import get_async_session
from app.integration.models.webhook import WebhookEvent, WebhookEventStatus
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.telemetry import get_telemetry
from app.integration.workers.celery_app import celery_app

logger = get_logger(__name__)


class WebhookProcessingTask(Task):
    """Base task with failure tracking for webhook processing."""

    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=WebhookProcessingTask,
    name="process_webhook_event_task",
    queue="webhooks",
)
def process_webhook_event_task(
    self,
    event_id: str,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Process a webhook event asynchronously.

    Args:
        event_id: UUID of the webhook event to process
        tenant_id: Tenant UUID
        correlation_id: Correlation UUID for tracing

    Returns:
        Processing result dict
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _process_webhook_event_async(
                event_id=uuid.UUID(event_id),
                tenant_id=uuid.UUID(tenant_id),
                correlation_id=uuid.UUID(correlation_id),
                task=self,
            )
        )
        return result
    finally:
        loop.close()


async def _process_webhook_event_async(
    event_id: uuid.UUID,
    tenant_id: uuid.UUID,
    correlation_id: uuid.UUID,
    task: Optional[Task] = None,
) -> dict[str, Any]:
    """
    Async implementation of webhook event processing.

    Steps:
    1. Load the event
    2. Mark as processing
    3. Parse and validate payload
    4. Route to appropriate handler
    5. Mark as completed or failed
    """
    telemetry = get_telemetry()

    async with get_async_session() as db:
        audit = IntegrationAuditService(db, tenant_id)

        # Load event
        result = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.id == event_id,
                WebhookEvent.tenant_id == tenant_id,
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            logger.error("webhook_event_not_found", event_id=str(event_id))
            return {"status": "not_found", "event_id": str(event_id)}

        try:
            # Mark as processing
            event.status = WebhookEventStatus.PROCESSING
            event.processing_attempts += 1
            await db.flush()

            # Parse payload
            payload = event.raw_payload or {}
            event_type = event.event_type

            # Route to handler based on event type
            handler_result = await _route_webhook_event(
                event_type=event_type,
                payload=payload,
                integration_id=event.integration_id,
                tenant_id=tenant_id,
                db=db,
            )

            # Mark as completed
            event.status = WebhookEventStatus.COMPLETED
            event.parsed_payload = handler_result
            event.processed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            await db.flush()

            await audit.log_webhook_event(
                integration_id=event.integration_id,
                webhook_event_id=event.id,
                event_type=event_type,
                status="completed",
            )

            telemetry.record_webhook_event(
                provider=event.webhook.provider if event.webhook else "unknown",
                event_type=event_type,
                status="completed",
            )

            logger.info(
                "webhook_event_processed",
                event_id=str(event_id),
                event_type=event_type,
            )

            return {
                "status": "completed",
                "event_id": str(event_id),
                "event_type": event_type,
            }

        except Exception as exc:
            logger.error(
                "webhook_event_processing_failed",
                event_id=str(event_id),
                error=str(exc),
            )

            should_retry = event.processing_attempts < event.max_retries

            if should_retry:
                event.status = WebhookEventStatus.RETRYING
                backoff = min(60 * (2 ** event.processing_attempts), 3600)
                event.next_retry_at = (
                    __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                    + __import__("datetime").timedelta(seconds=backoff)
                )
                # Retry the Celery task
                if task:
                    raise task.retry(exc=exc)
            else:
                event.status = WebhookEventStatus.DEAD_LETTER
                telemetry.record_dead_letter(
                    provider=event.webhook.provider if event.webhook else "unknown",
                    resource_type="webhook_event",
                )

            event.last_error = str(exc)
            await db.flush()

            await audit.log_webhook_event(
                integration_id=event.integration_id,
                webhook_event_id=event.id,
                event_type=event.event_type,
                status="failed",
            )

            telemetry.record_webhook_event(
                provider=event.webhook.provider if event.webhook else "unknown",
                event_type=event.event_type,
                status="failed",
            )

            return {
                "status": "failed",
                "event_id": str(event_id),
                "error": str(exc),
            }


async def _route_webhook_event(
    event_type: str,
    payload: dict[str, Any],
    integration_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Optional[dict[str, Any]]:
    """
    Route a webhook event to the appropriate handler.

    Override this with domain-specific routing logic.
    """
    # Default: return parsed payload as-is
    # In production, route to specific handlers:
    # - document.updated -> trigger document re-sync
    # - contract.signed -> update contract status
    # - file.created -> ingest new file

    logger.info(
        "webhook_event_routed",
        event_type=event_type,
        integration_id=str(integration_id),
    )

    return {
        "routed": True,
        "event_type": event_type,
        "integration_id": str(integration_id),
    }
