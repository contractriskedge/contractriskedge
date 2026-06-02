"""
Sync management API router.

Endpoints for triggering syncs, viewing sync status, and retrying failures.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

from app.integration.connectors.base import ConnectorAuth
from app.integration.models.integration import Integration
from app.integration.models.sync_job import (
    IntegrationSyncJob,
    SyncConflict,
    SyncJobStatus,
    SyncJobTrigger,
)
from app.integration.routers.dependencies import (
    get_audit_service,
    get_db,
    get_sync_orchestrator,
    get_tenant_id,
)
from app.integration.schemas.sync import (
    SyncConflictResponse,
    SyncJobCreate,
    SyncJobListResponse,
    SyncJobResponse,
    SyncRetryRequest,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.connector_registry import get_connector_registry
from app.integration.services.crypto import CredentialVault
from app.integration.services.sync_service import SyncOrchestrator

router = APIRouter(prefix="/sync", tags=["Sync"], dependencies=[Depends(require_permission(Permissions.CONTRACTS_READ))])


@router.post(
    "/trigger/{integration_id}",
    response_model=SyncJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a sync",
)
async def trigger_sync(
    integration_id: uuid.UUID,
    body: SyncJobCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator),
    audit: IntegrationAuditService = Depends(get_audit_service),
):
    """Trigger a sync operation for an integration."""
    try:
        job = await orchestrator.start_sync(
            integration_id=integration_id,
            trigger=SyncJobTrigger(body.trigger),
            sync_type=body.sync_type,
            metadata=body.metadata,
        )

        # Queue async execution
        from app.integration.workers.sync_worker import sync_external_documents_task

        sync_external_documents_task.delay(
            integration_id=str(integration_id),
            tenant_id=str(tenant_id),
            correlation_id=str(job.correlation_id),
            sync_type=body.sync_type,
        )

        await audit.log_event(
            integration_id=integration_id,
            action="sync_triggered",
            resource_type="sync_job",
            resource_id=str(job.id),
            new_state={"trigger": body.trigger, "sync_type": body.sync_type},
            change_summary=f"Sync triggered ({body.trigger}: {body.sync_type})",
            success=True,
        )

        return job

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/jobs",
    response_model=SyncJobListResponse,
    summary="List sync jobs",
)
async def list_sync_jobs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    integration_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List sync jobs with pagination and filtering."""
    query = select(IntegrationSyncJob).where(
        IntegrationSyncJob.tenant_id == tenant_id,
    )

    if integration_id:
        query = query.where(IntegrationSyncJob.integration_id == integration_id)
    if status_filter:
        query = query.where(IntegrationSyncJob.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(IntegrationSyncJob.created_at.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return SyncJobListResponse(
        items=[SyncJobResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get(
    "/jobs/{job_id}",
    response_model=SyncJobResponse,
    summary="Get sync job status",
)
async def get_sync_job(
    job_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Get the status of a specific sync job."""
    result = await db.execute(
        select(IntegrationSyncJob).where(
            IntegrationSyncJob.id == job_id,
            IntegrationSyncJob.tenant_id == tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync job not found",
        )
    return job


@router.post(
    "/retry/{job_id}",
    response_model=SyncJobResponse,
    summary="Retry a failed sync job",
)
async def retry_sync_job(
    job_id: uuid.UUID,
    body: SyncRetryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator),
):
    """Retry a failed sync job."""
    try:
        retry_job = await orchestrator.retry_sync(
            job_id=job_id,
            force=body.force,
            max_retries=body.max_retries,
        )

        # Queue retry execution
        from app.integration.workers.sync_worker import sync_external_documents_task

        sync_external_documents_task.delay(
            integration_id=str(retry_job.integration_id),
            tenant_id=str(tenant_id),
            correlation_id=str(retry_job.correlation_id),
            sync_type=retry_job.sync_type,
            cursor=retry_job.cursor,
            delta_token=retry_job.delta_token,
        )

        return retry_job

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/conflicts",
    response_model=list[SyncConflictResponse],
    summary="List sync conflicts",
)
async def list_sync_conflicts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    job_id: Optional[uuid.UUID] = Query(None),
    resolved: Optional[bool] = Query(None),
):
    """List sync conflicts, optionally filtered by job or resolution status."""
    query = select(SyncConflict).where(
        SyncConflict.tenant_id == tenant_id,
    )

    if job_id:
        query = query.where(SyncConflict.sync_job_id == job_id)
    if resolved is not None:
        if resolved:
            query = query.where(SyncConflict.resolution.isnot(None))
        else:
            query = query.where(SyncConflict.resolution.is_(None))

    query = query.order_by(SyncConflict.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())
