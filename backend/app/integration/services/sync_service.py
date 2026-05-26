"""
Sync Orchestration Service — enterprise sync pipeline management.

Handles:
- Full and delta sync orchestration
- Conflict detection and resolution
- Retry-safe pipelines with dead-letter handling
- Partial sync recovery
- Idempotent sync operations
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.integration.connectors.base import BaseConnector, ConnectorAuth, SyncResult
from app.integration.models.integration import Integration, IntegrationStatus
from app.integration.models.sync_failure import SyncFailure
from app.integration.models.sync_job import (
    IntegrationSyncJob,
    SyncConflict,
    SyncJobStatus,
    SyncJobTrigger,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.connector_registry import get_connector_registry
from app.integration.services.rate_limiter import RateLimiter
from app.integration.services.telemetry import IntegrationTelemetry

logger = get_logger(__name__)


class SyncConflictResolver:
    """
    Detects and resolves conflicts between local and external data during sync.
    """

    RESOLUTION_STRATEGIES = {
        "local_wins": "local_wins",
        "external_wins": "external_wins",
        "manual": "manual",
        "skip": "skip",
    }

    @staticmethod
    def detect_conflict(
        external_entity: dict[str, Any],
        local_entity: Optional[dict[str, Any]],
        tracked_fields: Optional[list[str]] = None,
    ) -> Optional[SyncConflict]:
        """
        Detect if there's a conflict between external and local data.

        Returns a SyncConflict if a conflict is detected, None otherwise.
        """
        if not local_entity:
            return None

        tracked = tracked_fields or ["name", "content", "metadata"]
        conflicts = []

        for field in tracked:
            ext_val = external_entity.get(field)
            loc_val = local_entity.get(field)
            if ext_val is not None and loc_val is not None and ext_val != loc_val:
                conflicts.append(
                    {
                        "field": field,
                        "external_value": ext_val,
                        "local_value": loc_val,
                    }
                )

        if not conflicts:
            return None

        return {
            "external_id": external_entity.get("id", ""),
            "conflict_type": "field_mismatch",
            "fields": conflicts,
        }

    @staticmethod
    def resolve(
        conflict: dict[str, Any],
        strategy: str = "external_wins",
    ) -> dict[str, Any]:
        """Resolve a conflict using the specified strategy."""
        if strategy == "external_wins":
            return {"resolution": "external_wins", "value": conflict.get("external_value")}
        elif strategy == "local_wins":
            return {"resolution": "local_wins", "value": conflict.get("local_value")}
        elif strategy == "skip":
            return {"resolution": "skip"}
        else:
            return {"resolution": "manual"}


class SyncOrchestrator:
    """
    Enterprise sync orchestration service.

    Manages the full lifecycle of sync operations including scheduling,
    execution, conflict handling, retry, and observability.
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        rate_limiter: Optional[RateLimiter] = None,
        audit: Optional[IntegrationAuditService] = None,
        telemetry: Optional[IntegrationTelemetry] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.rate_limiter = rate_limiter or RateLimiter()
        self.audit = audit
        self.telemetry = telemetry
        self.registry = get_connector_registry()

    async def start_sync(
        self,
        integration_id: uuid.UUID,
        trigger: SyncJobTrigger = SyncJobTrigger.MANUAL,
        sync_type: str = "full",
        metadata: Optional[dict[str, Any]] = None,
    ) -> IntegrationSyncJob:
        """
        Start a new sync job for an integration.

        Creates the job record, checks rate limits, and initiates sync.
        """
        integration = await self._get_integration(integration_id)
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")

        if integration.status != IntegrationStatus.ACTIVE:
            raise ValueError(
                f"Integration {integration_id} is not active (status: {integration.status.value})"
            )

        # Check rate limit
        if self.rate_limiter:
            allowed = await self.rate_limiter.check_sync_rate_limit(
                integration_id, integration.rate_limit_max
            )
            if not allowed:
                raise ValueError("Rate limit exceeded for this integration")

        correlation_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        job = IntegrationSyncJob(
            integration_id=integration_id,
            tenant_id=self.tenant_id,
            correlation_id=correlation_id,
            status=SyncJobStatus.RUNNING,
            trigger=trigger,
            sync_type=sync_type,
            started_at=now,
            max_retries=3,
            metadata_=metadata or {},
        )

        self.db.add(job)
        await self.db.flush()

        logger.info(
            "sync_job_started",
            job_id=str(job.id),
            integration_id=str(integration_id),
            trigger=trigger.value,
            sync_type=sync_type,
            correlation_id=str(correlation_id),
        )

        return job

    async def execute_sync(
        self,
        job: IntegrationSyncJob,
        connector: BaseConnector,
    ) -> IntegrationSyncJob:
        """
        Execute a sync job using the provided connector.

        Handles full and delta syncs, records results, and tracks failures.
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Determine sync parameters
            cursor = job.cursor if job.sync_type == "delta" else None
            delta_token = job.delta_token if job.sync_type == "delta" else None

            # Execute the sync via connector
            result = await connector.sync_documents(
                cursor=cursor,
                delta_token=delta_token,
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            if result.success:
                job.status = SyncJobStatus.SUCCESS
                job.synced_items = result.synced_count
                job.failed_items = result.failed_count
                job.skipped_items = result.skipped_count
                job.cursor = result.cursor
                job.delta_token = result.delta_token
                job.duration_seconds = duration
                job.completed_at = datetime.now(timezone.utc)
                job.result_summary = result.metadata

                # Update integration
                await self._update_integration_sync_status(
                    job.integration_id, "success"
                )

                logger.info(
                    "sync_job_completed",
                    job_id=str(job.id),
                    synced=result.synced_count,
                    failed=result.failed_count,
                    duration_seconds=duration,
                )
            else:
                job.status = SyncJobStatus.FAILED
                job.failed_items = result.failed_count
                job.duration_seconds = duration
                job.error_message = str(result.errors)
                job.completed_at = datetime.now(timezone.utc)

                await self._record_failure(
                    job=job,
                    failure_type="sync_error",
                    error_message=str(result.errors),
                    error_details={"errors": result.errors},
                    should_retry=True,
                )

                await self._update_integration_sync_status(
                    job.integration_id, "failed"
                )

                logger.error(
                    "sync_job_failed",
                    job_id=str(job.id),
                    errors=result.errors,
                )

        except Exception as exc:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            job.status = SyncJobStatus.FAILED
            job.error_message = str(exc)
            job.duration_seconds = duration
            job.completed_at = datetime.now(timezone.utc)

            await self._record_failure(
                job=job,
                failure_type="exception",
                error_message=str(exc),
                should_retry=True,
            )

            await self._update_integration_sync_status(
                job.integration_id, "error"
            )

            logger.error(
                "sync_job_exception",
                job_id=str(job.id),
                error=str(exc),
            )

        # Telemetry
        if self.telemetry:
            self.telemetry.record_sync_completion(
                provider=connector.provider_name,
                status=job.status.value,
                duration_ms=duration * 1000,
                items_synced=job.synced_items or 0,
            )

        await self.db.flush()
        return job

    async def retry_sync(
        self,
        job_id: uuid.UUID,
        force: bool = False,
        max_retries: Optional[int] = None,
    ) -> IntegrationSyncJob:
        """
        Retry a failed sync job.

        Creates a new retry job linked to the original failure.
        """
        original = await self._get_sync_job(job_id)
        if not original:
            raise ValueError(f"Sync job not found: {job_id}")

        if original.status not in (SyncJobStatus.FAILED, SyncJobStatus.DEAD_LETTER):
            if not force:
                raise ValueError(f"Cannot retry job in status: {original.status.value}")

        if original.retry_count >= original.max_retries and not force:
            raise ValueError(
                f"Job {job_id} has exceeded max retries ({original.max_retries})"
            )

        # Create retry job
        retry_job = IntegrationSyncJob(
            integration_id=original.integration_id,
            tenant_id=self.tenant_id,
            correlation_id=original.correlation_id,
            status=SyncJobStatus.PENDING,
            trigger=SyncJobTrigger.RETRY,
            sync_type=original.sync_type,
            cursor=original.cursor,
            delta_token=original.delta_token,
            retry_count=original.retry_count + 1,
            max_retries=max_retries or original.max_retries,
            metadata_={"original_job_id": str(original.id)},
        )

        self.db.add(retry_job)
        await self.db.flush()

        logger.info(
            "sync_retry_created",
            original_job_id=str(job_id),
            retry_job_id=str(retry_job.id),
            retry_count=retry_job.retry_count,
        )

        return retry_job

    async def record_conflict(
        self,
        job_id: uuid.UUID,
        external_id: str,
        conflict_type: str,
        local_value: Optional[dict] = None,
        external_value: Optional[dict] = None,
        field: Optional[str] = None,
    ) -> SyncConflict:
        """Record a sync conflict for manual or automated resolution."""
        job = await self._get_sync_job(job_id)
        if not job:
            raise ValueError(f"Sync job not found: {job_id}")

        conflict = SyncConflict(
            sync_job_id=job_id,
            tenant_id=self.tenant_id,
            external_id=external_id,
            conflict_type=conflict_type,
            field=field,
            local_value=local_value,
            external_value=external_value,
        )

        self.db.add(conflict)
        await self.db.flush()

        logger.info(
            "sync_conflict_recorded",
            job_id=str(job_id),
            external_id=external_id,
            conflict_type=conflict_type,
        )

        return conflict

    async def resolve_conflict(
        self,
        conflict_id: uuid.UUID,
        resolution: str,
        resolved_by: Optional[uuid.UUID] = None,
    ) -> SyncConflict:
        """Resolve a sync conflict."""
        result = await self.db.execute(
            select(SyncConflict).where(
                SyncConflict.id == conflict_id,
                SyncConflict.tenant_id == self.tenant_id,
            )
        )
        conflict = result.scalar_one_or_none()
        if not conflict:
            raise ValueError(f"Conflict not found: {conflict_id}")

        conflict.resolution = resolution
        conflict.resolved_at = datetime.now(timezone.utc)
        conflict.resolved_by = resolved_by

        await self.db.flush()

        logger.info(
            "sync_conflict_resolved",
            conflict_id=str(conflict_id),
            resolution=resolution,
        )

        return conflict

    async def _record_failure(
        self,
        job: IntegrationSyncJob,
        failure_type: str,
        error_message: str,
        error_details: Optional[dict] = None,
        should_retry: bool = True,
    ) -> SyncFailure:
        """Record a sync failure for dead-letter tracking."""
        now = datetime.now(timezone.utc)
        is_dead_letter = job.retry_count >= job.max_retries

        failure = SyncFailure(
            sync_job_id=job.id,
            integration_id=job.integration_id,
            tenant_id=self.tenant_id,
            correlation_id=job.correlation_id,
            failure_type=failure_type,
            error_message=error_message,
            error_details=error_details or {},
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            is_dead_letter=is_dead_letter,
            occurred_at=now,
        )

        if should_retry and not is_dead_letter:
            backoff = min(60 * (2 ** job.retry_count), 3600)
            failure.next_retry_at = now + timedelta(seconds=backoff)
            job.next_retry_at = failure.next_retry_at
        else:
            failure.dead_lettered_at = now if is_dead_letter else None
            job.status = SyncJobStatus.DEAD_LETTER if is_dead_letter else SyncJobStatus.FAILED

        self.db.add(failure)
        await self.db.flush()

        return failure

    async def _get_integration(
        self, integration_id: uuid.UUID
    ) -> Optional[Integration]:
        result = await self.db.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.tenant_id == self.tenant_id,
                Integration.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def _get_sync_job(
        self, job_id: uuid.UUID
    ) -> Optional[IntegrationSyncJob]:
        result = await self.db.execute(
            select(IntegrationSyncJob).where(
                IntegrationSyncJob.id == job_id,
                IntegrationSyncJob.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _update_integration_sync_status(
        self, integration_id: uuid.UUID, status: str
    ) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(Integration)
            .where(Integration.id == integration_id)
            .values(
                last_sync_at=now,
                last_sync_status=status,
            )
        )
