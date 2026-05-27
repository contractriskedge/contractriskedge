"""
Sync worker Celery tasks.

Handles external document synchronization and retry of failed sync jobs.
"""

import uuid
from typing import Any, Optional, Optional

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.database import get_async_session
from app.integration.connectors.base import ConnectorAuth
from app.integration.models.integration import Integration, IntegrationStatus
from app.integration.models.sync_job import IntegrationSyncJob, SyncJobStatus, SyncJobTrigger
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.connector_registry import get_connector_registry
from app.integration.services.crypto import CredentialVault
from app.integration.services.rate_limiter import RateLimiter
from app.integration.services.sync_service import SyncOrchestrator
from app.integration.services.telemetry import get_telemetry
from app.integration.workers.celery_app import celery_app

logger = get_logger(__name__)


class SyncTask(Task):
    """Base task for sync operations with retry configuration."""

    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=SyncTask,
    name="sync_external_documents_task",
    queue="sync",
)
def sync_external_documents_task(
    self,
    integration_id: str,
    tenant_id: str,
    correlation_id: str,
    sync_type: str = "full",
    cursor: Optional[str] = None,
    delta_token: Optional[str] = None,
) -> dict[str, Any]:
    """
    Synchronize documents from an external provider.

    Args:
        integration_id: Integration UUID
        tenant_id: Tenant UUID
        correlation_id: Correlation UUID for tracing
        sync_type: 'full' or 'delta'
        cursor: Pagination cursor for incremental sync
        delta_token: Delta token for change tracking

    Returns:
        Sync result dict
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _sync_external_documents_async(
                integration_id=uuid.UUID(integration_id),
                tenant_id=uuid.UUID(tenant_id),
                correlation_id=uuid.UUID(correlation_id),
                sync_type=sync_type,
                cursor=cursor,
                delta_token=delta_token,
                task=self,
            )
        )
        return result
    finally:
        loop.close()


async def _sync_external_documents_async(
    integration_id: uuid.UUID,
    tenant_id: uuid.UUID,
    correlation_id: uuid.UUID,
    sync_type: str = "full",
    cursor: Optional[str] = None,
    delta_token: Optional[str] = None,
    task: Optional[Task] = None,
) -> dict[str, Any]:
    """
    Async implementation of external document sync.

    Steps:
    1. Load integration and credentials
    2. Create connector adapter with auth
    3. Execute sync via orchestrator
    4. Record results and handle failures
    """
    telemetry = get_telemetry()
    registry = get_connector_registry()

    async with get_async_session() as db:
        audit = IntegrationAuditService(db, tenant_id)
        orchestrator = SyncOrchestrator(
            db=db,
            tenant_id=tenant_id,
            audit=audit,
            telemetry=telemetry,
        )

        # Load integration
        result = await db.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.tenant_id == tenant_id,
                Integration.is_deleted == False,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            logger.error("integration_not_found", integration_id=str(integration_id))
            return {"status": "not_found", "integration_id": str(integration_id)}

        if integration.status != IntegrationStatus.ACTIVE:
            logger.error(
                "integration_not_active",
                integration_id=str(integration_id),
                status=integration.status.value,
            )
            return {
                "status": "not_active",
                "integration_id": str(integration_id),
                "current_status": integration.status.value,
            }

        # Get connector adapter
        connector_cls = registry.get_adapter(integration.provider.value)
        if not connector_cls:
            logger.error("connector_not_found", provider=integration.provider.value)
            return {
                "status": "connector_not_found",
                "provider": integration.provider.value,
            }

        # Load credentials and build auth
        auth = await _build_connector_auth(
            db=db,
            integration_id=integration_id,
            tenant_id=tenant_id,
        )

        # Instantiate connector
        connector = connector_cls(
            auth=auth,
            config=integration.config or {},
            tenant_id=tenant_id,
            integration_id=integration_id,
        )

        try:
            # Create and execute sync job
            job = await orchestrator.start_sync(
                integration_id=integration_id,
                trigger=SyncJobTrigger.SCHEDULED,
                sync_type=sync_type,
                metadata={
                    "cursor": cursor,
                    "delta_token": delta_token,
                    "correlation_id": str(correlation_id),
                },
            )

            # Set delta sync parameters
            if cursor:
                job.cursor = cursor
            if delta_token:
                job.delta_token = delta_token

            # Execute
            job = await orchestrator.execute_sync(job, connector)

            # Audit
            await audit.log_sync_completed(
                integration_id=integration_id,
                sync_job_id=job.id,
                status=job.status.value,
                items_synced=job.synced_items or 0,
                correlation_id=correlation_id,
            )

            return {
                "status": job.status.value,
                "job_id": str(job.id),
                "synced_items": job.synced_items,
                "failed_items": job.failed_items,
                "duration_seconds": job.duration_seconds,
                "cursor": job.cursor,
                "delta_token": job.delta_token,
            }

        except Exception as exc:
            logger.error(
                "sync_execution_failed",
                integration_id=str(integration_id),
                error=str(exc),
            )
            telemetry.record_sync_completion(
                provider=integration.provider.value,
                status="failed",
                duration_ms=0,
            )
            if task:
                raise task.retry(exc=exc)
            return {"status": "failed", "error": str(exc)}

        finally:
            await connector.close()


@celery_app.task(
    bind=True,
    base=SyncTask,
    name="retry_sync_failure_task",
    queue="sync",
)
def retry_sync_failure_task(
    self,
    sync_job_id: str,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Retry a failed sync job.

    Args:
        sync_job_id: UUID of the failed sync job
        tenant_id: Tenant UUID
        correlation_id: Correlation UUID

    Returns:
        Retry result dict
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _retry_sync_failure_async(
                sync_job_id=uuid.UUID(sync_job_id),
                tenant_id=uuid.UUID(tenant_id),
                correlation_id=uuid.UUID(correlation_id),
            )
        )
        return result
    finally:
        loop.close()


async def _retry_sync_failure_async(
    sync_job_id: uuid.UUID,
    tenant_id: uuid.UUID,
    correlation_id: uuid.UUID,
) -> dict[str, Any]:
    """Async implementation of sync failure retry."""
    telemetry = get_telemetry()

    async with get_async_session() as db:
        audit = IntegrationAuditService(db, tenant_id)
        orchestrator = SyncOrchestrator(
            db=db,
            tenant_id=tenant_id,
            audit=audit,
            telemetry=telemetry,
        )

        try:
            retry_job = await orchestrator.retry_sync(
                job_id=sync_job_id,
                force=False,
            )

            telemetry.record_sync_retry(
                provider="unknown",
                attempt=retry_job.retry_count,
                max_retries=retry_job.max_retries,
            )

            logger.info(
                "sync_retry_scheduled",
                original_job_id=str(sync_job_id),
                retry_job_id=str(retry_job.id),
            )

            return {
                "status": "retry_scheduled",
                "original_job_id": str(sync_job_id),
                "retry_job_id": str(retry_job.id),
                "retry_count": retry_job.retry_count,
            }

        except ValueError as exc:
            logger.error("sync_retry_failed", error=str(exc))
            return {"status": "failed", "error": str(exc)}


async def _build_connector_auth(
    db: AsyncSession,
    integration_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Optional[ConnectorAuth]:
    """Build connector auth from stored credentials."""
    from app.integration.models.credential import IntegrationCredential

    result = await db.execute(
        select(IntegrationCredential).where(
            IntegrationCredential.integration_id == integration_id,
            IntegrationCredential.tenant_id == tenant_id,
            IntegrationCredential.is_revoked == False,
        ).order_by(IntegrationCredential.version.desc())
    )
    credential = result.scalar_one_or_none()
    if not credential:
        logger.warning("no_credentials_found", integration_id=str(integration_id))
        return None

    vault = CredentialVault()

    access_token = None
    if credential.encrypted_access_token:
        access_token = vault.retrieve_token(
            str(tenant_id),
            str(integration_id),
            credential.encrypted_access_token,
        )

    refresh_token = None
    if credential.encrypted_refresh_token:
        refresh_token = vault.retrieve_token(
            str(tenant_id),
            str(integration_id),
            credential.encrypted_refresh_token,
            token_type="refresh_token",
        )

    return ConnectorAuth(
        access_token=access_token or "",
        refresh_token=refresh_token,
        token_type=credential.oauth_token_type or "Bearer",
        expires_at=credential.oauth_access_token_expires_at,
        scopes=credential.oauth_scopes,
    )
