"""
Cleanup Celery task for stale integrations and expired data.

Periodically runs to:
- Disable stale/unused integrations
- Clean up expired webhook events
- Archive old sync jobs
- Purge dead-letter records after retention period
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, select, update
from structlog import get_logger

from app.database import get_async_session
from app.integration.models.integration import Integration, IntegrationStatus
from app.integration.models.sync_failure import SyncFailure
from app.integration.models.sync_job import IntegrationSyncJob, SyncJobStatus
from app.integration.models.webhook import WebhookEvent, WebhookEventStatus
from app.integration.services.telemetry import get_telemetry
from app.integration.workers.celery_app import celery_app

logger = get_logger(__name__)

# Retention periods
STALE_INTEGRATION_DAYS = 90  # Disable integrations with no activity
EXPIRED_EVENT_RETENTION_HOURS = 72  # Delete expired events after
SYNC_JOB_RETENTION_DAYS = 30  # Archive sync jobs after
DEAD_LETTER_RETENTION_DAYS = 14  # Purge dead-letter records after


@celery_app.task(
    bind=True,
    name="cleanup_stale_integrations_task",
    queue="maintenance",
)
def cleanup_stale_integrations_task(
    self,
    tenant_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Clean up stale integrations and expired data.

    Args:
        tenant_id: Optional tenant UUID. If None, processes all tenants.

    Returns:
        Cleanup summary
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _cleanup_stale_integrations_async(
                tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            )
        )
        return result
    finally:
        loop.close()


async def _cleanup_stale_integrations_async(
    tenant_id: Optional[uuid.UUID] = None,
) -> dict[str, Any]:
    """Async implementation of cleanup operations."""
    telemetry = get_telemetry()
    now = datetime.now(timezone.utc)

    stats = {
        "integrations_disabled": 0,
        "expired_events_deleted": 0,
        "old_sync_jobs_archived": 0,
        "dead_letter_purged": 0,
    }

    async with get_async_session() as db:
        # 1. Disable stale integrations
        stale_cutoff = now - timedelta(days=STALE_INTEGRATION_DAYS)
        conditions = [
            Integration.status == IntegrationStatus.ACTIVE,
            Integration.last_sync_at <= stale_cutoff,
        ]
        if tenant_id:
            conditions.append(Integration.tenant_id == tenant_id)

        stale_result = await db.execute(
            select(Integration).where(*conditions)
        )
        stale_integrations = list(stale_result.scalars().all())

        for integration in stale_integrations:
            integration.status = IntegrationStatus.DISABLED
            integration.disabled_at = now
            integration.disabled_reason = (
                f"Auto-disabled after {STALE_INTEGRATION_DAYS} days of inactivity"
            )
            stats["integrations_disabled"] += 1
            logger.info(
                "integration_disabled_stale",
                integration_id=str(integration.id),
                tenant_id=str(integration.tenant_id),
                last_sync=str(integration.last_sync_at),
            )

        # 2. Delete expired webhook events
        expired_cutoff = now - timedelta(hours=EXPIRED_EVENT_RETENTION_HOURS)
        event_conditions = [
            WebhookEvent.expires_at <= expired_cutoff,
            WebhookEvent.status.in_([
                WebhookEventStatus.COMPLETED,
                WebhookEventStatus.FAILED,
                WebhookEventStatus.DEAD_LETTER,
                WebhookEventStatus.IGNORED,
            ]),
        ]
        if tenant_id:
            event_conditions.append(WebhookEvent.tenant_id == tenant_id)

        event_delete = await db.execute(
            delete(WebhookEvent).where(*event_conditions)
        )
        stats["expired_events_deleted"] = event_delete.rowcount

        # 3. Archive old sync jobs
        sync_cutoff = now - timedelta(days=SYNC_JOB_RETENTION_DAYS)
        sync_conditions = [
            IntegrationSyncJob.created_at <= sync_cutoff,
            IntegrationSyncJob.status.in_([
                SyncJobStatus.SUCCESS,
                SyncJobStatus.FAILED,
                SyncJobStatus.CANCELLED,
                SyncJobStatus.DEAD_LETTER,
            ]),
        ]
        if tenant_id:
            sync_conditions.append(IntegrationSyncJob.tenant_id == tenant_id)

        # Mark as archived (soft-delete by clearing sensitive data)
        sync_archive = await db.execute(
            update(IntegrationSyncJob)
            .where(*sync_conditions)
            .values(
                metadata_=None,
                error_details=None,
                result_summary=None,
            )
        )
        stats["old_sync_jobs_archived"] = sync_archive.rowcount

        # 4. Purge old dead-letter records
        dl_cutoff = now - timedelta(days=DEAD_LETTER_RETENTION_DAYS)
        dl_conditions = [
            SyncFailure.is_dead_letter == True,
            SyncFailure.dead_lettered_at <= dl_cutoff,
        ]
        if tenant_id:
            dl_conditions.append(SyncFailure.tenant_id == tenant_id)

        dl_delete = await db.execute(
            delete(SyncFailure).where(*dl_conditions)
        )
        stats["dead_letter_purged"] = dl_delete.rowcount

        await db.flush()

    logger.info(
        "cleanup_completed",
        **stats,
    )

    return stats
