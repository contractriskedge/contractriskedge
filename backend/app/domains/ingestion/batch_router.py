"""Batch upload API router — endpoints for multi-file batch upload operations.

Endpoints:
- POST /api/v1/uploads/batch — Create a new batch upload container
- POST /api/v1/uploads/batch/{batch_id}/files — Upload a file to an existing batch
- GET  /api/v1/uploads/batch/{batch_id} — Get batch details with per-file status
- GET  /api/v1/uploads/batches — List batches with pagination
- POST /api/v1/uploads/batch/{batch_id}/process — Trigger processing of all uploaded files
- POST /api/v1/uploads/batch/{batch_id}/cancel — Cancel a batch
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.domains.ingestion.batch_models import BatchStatus
from app.domains.ingestion.batch_schemas import (
    BatchUploadCreate,
    BatchUploadResponse,
    BatchUploadDetailResponse,
    BatchUploadFileItem,
    BatchUploadListResponse,
)
from app.domains.ingestion.batch_service import BatchUploadService
from app.domains.ingestion.models import UploadSession, IngestionState
from app.domains.ingestion.security import (
    validate_extension,
    validate_content_type,
    validate_file_size,
    validate_filename_safety,
)
from app.kernel.security.auth import UserContext

router = APIRouter(prefix="/uploads", tags=["Batch Uploads"])


def _batch_to_response(batch) -> BatchUploadResponse:
    return BatchUploadResponse(
        batch_id=batch.batch_id,
        name=batch.name,
        status=batch.status.value if hasattr(batch.status, 'value') else str(batch.status),
        total_files=batch.total_files,
        completed_files=batch.completed_files,
        failed_files=batch.failed_files,
        total_bytes=batch.total_bytes,
        error_message=batch.error_message,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        completed_at=batch.completed_at,
    )


@router.post(
    "/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new batch upload container",
)
async def create_batch(
    body: BatchUploadCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Create a new batch upload container. Files can be added to it later."""
    service = BatchUploadService(db, user.tenant_id, user.id)
    batch = await service.create_batch(name=body.name)
    await db.commit()
    await db.refresh(batch)
    return _batch_to_response(batch)


@router.post(
    "/batch/{batch_id}/files",
    response_model=BatchUploadFileItem,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to an existing batch",
)
async def upload_batch_file(
    batch_id: uuid.UUID,
    file: UploadFile = File(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Upload a single file to a batch. Validates the file before associating."""
    # Validate batch exists and is accepting files
    service = BatchUploadService(db, user.tenant_id, user.id)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status in (BatchStatus.COMPLETED, BatchStatus.CANCELLED, BatchStatus.FAILED):
        raise HTTPException(status_code=400, detail=f"Batch is in '{batch.status.value}' state and cannot accept more files")

    # Validate file
    filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    try:
        validate_filename_safety(filename)
        validate_extension(filename)
        validate_content_type(content_type)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Read file content for size validation
    file_body = await file.read()
    try:
        validate_file_size(len(file_body))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Create upload session linked to batch
    upload = UploadSession(
        upload_id=uuid.uuid4(),
        tenant_id=uuid.UUID(user.tenant_id),
        user_id=user.id,
        filename=filename,
        content_type=content_type,
        file_size=len(file_body),
        ingestion_state=IngestionState.UPLOADED,
        batch_id=batch_id,
    )
    db.add(upload)
    await db.flush()

    # Update batch counters
    await service.link_upload_to_batch(upload.upload_id, batch_id, len(file_body))
    await db.commit()
    await db.refresh(upload)

    return BatchUploadFileItem(
        upload_id=upload.upload_id,
        filename=upload.filename,
        file_size=upload.file_size,
        status=upload.ingestion_state.value if hasattr(upload.ingestion_state, 'value') else str(upload.ingestion_state),
        error_message=upload.ingestion_error,
        created_at=upload.created_at,
    )


@router.get(
    "/batch/{batch_id}",
    response_model=BatchUploadDetailResponse,
    summary="Get batch details with per-file status",
)
async def get_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Get full batch details including the status of every file in the batch."""
    service = BatchUploadService(db, user.tenant_id, user.id)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    files = await service.get_batch_files(batch_id)
    file_items = [
        BatchUploadFileItem(
            upload_id=f.upload_id,
            filename=f.filename,
            file_size=f.file_size,
            status=f.ingestion_state.value if hasattr(f.ingestion_state, 'value') else str(f.ingestion_state),
            error_message=f.ingestion_error,
            created_at=f.created_at,
        )
        for f in files
    ]

    response = _batch_to_response(batch)
    return BatchUploadDetailResponse(
        **response.model_dump(),
        files=file_items,
    )


@router.get(
    "/batches",
    response_model=BatchUploadListResponse,
    summary="List batch uploads with pagination",
)
async def list_batches(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by batch status"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """List batch uploads for the current tenant."""
    service = BatchUploadService(db, user.tenant_id, user.id)
    status_filter = None
    if status:
        try:
            status_filter = BatchStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid batch status: {status}")

    batches, total = await service.list_batches(
        page=page, page_size=page_size, status_filter=status_filter,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)

    return BatchUploadListResponse(
        items=[_batch_to_response(b) for b in batches],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/batch/{batch_id}/process",
    response_model=dict,
    summary="Trigger processing of all uploaded files in a batch",
)
async def process_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Start the ingestion pipeline for all uploaded files in the batch."""
    service = BatchUploadService(db, user.tenant_id, user.id)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status != BatchStatus.UPLOADING:
        raise HTTPException(
            status_code=400,
            detail=f"Batch is in '{batch.status.value}' state. Must be 'uploading' to process.",
        )

    # Dispatch Celery task (lazy import to avoid circular dependency)
    from app.domains.ingestion.batch_tasks import process_batch_uploads
    process_batch_uploads.delay(str(batch_id))

    return {
        "message": "Batch processing started",
        "batch_id": str(batch_id),
        "total_files": batch.total_files,
    }


@router.post(
    "/batch/{batch_id}/cancel",
    response_model=dict,
    summary="Cancel a batch upload",
)
async def cancel_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Cancel a batch and mark all pending uploads as cancelled."""
    service = BatchUploadService(db, user.tenant_id, user.id)
    cancelled = await service.cancel_batch(batch_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Batch cannot be cancelled or not found")
    await db.commit()
    return {"message": "Batch cancelled", "batch_id": str(batch_id)}
