"""Document ingestion API endpoints.

Provides endpoints for uploading contract documents, checking
ingestion status, and managing the ingestion queue.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel

from ingestion.models import (
    IngestionRequest,
    JobRecord,
    JobStatus,
    JobStatusResponse,
)
from ingestion.queue import IngestionQueue, JobNotFoundError
from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions
from middleware.file_security import validate_file_magic, UPLOAD_RATE_LIMIT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


def _get_queue() -> IngestionQueue:
    """Get the ingestion queue instance.

    Returns:
        An IngestionQueue connected via Redis URL.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return IngestionQueue(redis_url=redis_url)


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    user: TokenPayload = Depends(get_current_user),
    webhook_url: Optional[str] = None,
    webhook_secret: Optional[str] = None,
    enable_ocr: bool = False,
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Upload a contract document for ingestion.

    Accepts PDF, DOCX, DOC, and TXT files up to 100 MB. Returns
    immediately with a job ID for tracking.

    Args:
        file: The uploaded document file.
        user: Authenticated user (from Auth0 JWT).
        webhook_url: Optional webhook URL for completion notification.
        webhook_secret: Optional secret for HMAC signing.
        enable_ocr: Whether to force OCR processing.

    Returns:
        Dict with job_id, status, and status_url for tracking.

    Raises:
        HTTPException: If file type is invalid or file is too large.
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES.keys())}",
        )

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    expected_ext = ALLOWED_CONTENT_TYPES.get(file.content_type or "", "")
    if ext and ext != expected_ext:
        logger.warning(
            "Content-type/extension mismatch: %s vs %s",
            file.content_type,
            ext,
        )

    # Read file contents with size check
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Create upload directory if needed
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Generate document ID and save file
    document_id = str(uuid.uuid4())
    safe_filename = f"{document_id}{expected_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except OSError as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )

    # Validate file magic bytes
    is_valid, error_msg = validate_file_magic(file_path, expected_ext)
    if not is_valid:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Create job record
    job = JobRecord(
        document_id=document_id,
        tenant_id=user.tenant_id or "default",
        user_id=user.sub,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        status=JobStatus.PENDING,
    )

    # Enqueue the job
    queue = _get_queue()
    try:
        job_id = await queue.enqueue(job)
    except Exception as exc:
        logger.error("Failed to enqueue job: %s", exc)
        # Clean up saved file
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue document for processing",
        )

    # Submit to Celery for async processing
    try:
        from ingestion.tasks import process_document

        options: Dict[str, Any] = {"enable_ocr": enable_ocr}
        process_document.delay(
            job_id=job_id,
            document_path=file_path,
            options=options,
        )
    except Exception as exc:
        logger.warning(
            "Failed to submit Celery task for job %s: %s",
            job_id,
            exc,
        )
        # Job is still enqueued; will be picked up by worker

    logger.info(
        "Document uploaded: job=%s, file=%s, user=%s, size=%d",
        job_id,
        file.filename,
        user.sub,
        len(contents),
    )

    return {
        "job_id": job_id,
        "document_id": document_id,
        "status": JobStatus.PENDING.value,
        "status_url": f"/api/v1/ingest/status/{job_id}",
        "filename": file.filename,
    }


@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> JobStatusResponse:
    """Get the status of an ingestion job.

    Args:
        job_id: The ingestion job identifier.
        user: Authenticated user.

    Returns:
        JobStatusResponse with current status and progress.

    Raises:
        HTTPException: If job not found or access denied.
    """
    queue = _get_queue()
    try:
        job = await queue.get_job(job_id)
    except Exception as exc:
        logger.error("Failed to query job %s: %s", job_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query job status",
        )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job {job_id} not found",
        )

    # Tenant isolation check
    if job.tenant_id != (user.tenant_id or "default"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs")
async def list_ingestion_jobs(
    status_filter: Optional[JobStatus] = None,
    limit: int = 50,
    offset: int = 0,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """List ingestion jobs for the current tenant.

    Args:
        status_filter: Optional status to filter by.
        limit: Maximum results (default 50, max 200).
        offset: Result offset for pagination.
        user: Authenticated user.

    Returns:
        Dict with jobs list and total count.
    """
    if limit > 200:
        limit = 200

    queue = _get_queue()
    try:
        jobs = await queue.list_jobs(
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error("Failed to list jobs: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list ingestion jobs",
        )

    # Filter by tenant
    tenant_id = user.tenant_id or "default"
    tenant_jobs = [j for j in jobs if j.tenant_id == tenant_id]

    return {
        "jobs": [
            JobStatusResponse(
                job_id=j.job_id,
                status=j.status,
                progress=j.progress,
                error_message=j.error_message,
                created_at=j.created_at,
                updated_at=j.updated_at,
                completed_at=j.completed_at,
            )
            for j in tenant_jobs
        ],
        "total": len(tenant_jobs),
        "limit": limit,
        "offset": offset,
    }


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_ingestion_job(
    job_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.DELETE_CONTRACTS)),
) -> None:
    """Cancel and remove an ingestion job.

    Args:
        job_id: The job to cancel.
        user: Authenticated user.

    Raises:
        HTTPException: If job not found or access denied.
    """
    queue = _get_queue()
    job = await queue.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job {job_id} not found",
        )

    if job.tenant_id != (user.tenant_id or "default"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    await queue.remove_job(job_id)


@router.get("/queue/stats")
async def get_queue_statistics(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, int]:
    """Get ingestion queue statistics.

    Args:
        user: Authenticated user.

    Returns:
        Dict with counts per status.
    """
    queue = _get_queue()
    try:
        stats = await queue.get_queue_stats()
        return {
            "pending": stats.pending,
            "processing": stats.processing,
            "done": stats.done,
            "failed": stats.failed,
            "total": stats.total,
        }
    except Exception as exc:
        logger.error("Failed to get queue stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get queue statistics",
        )


# ── Batch Upload ─────────────────────────────────────────────────────────


class BatchUploadResult(BaseModel):
    """Result of a single file in a batch upload."""

    filename: str
    job_id: str
    document_id: str
    status: str
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Response for a batch upload request."""

    batch_id: str
    total: int
    accepted: int
    failed: int
    results: List[BatchUploadResult]


@router.post("/batch-upload", status_code=status.HTTP_202_ACCEPTED)
async def batch_upload_documents(
    files: List[UploadFile] = File(..., description="Multiple files (max 20, up to 100 MB each)"),
    user: TokenPayload = Depends(get_current_user),
    webhook_url: Optional[str] = Query(None, description="Optional webhook for batch completion"),
    webhook_secret: Optional[str] = Query(None, description="Secret for HMAC signing"),
    enable_ocr: bool = Query(False, description="Force OCR processing"),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> BatchUploadResponse:
    """Upload multiple contract documents in a single batch.

    Accepts up to 20 files (PDF, DOCX, DOC, TXT) in one request.
    Each file is validated and enqueued independently. Returns a
    batch summary with individual job IDs for tracking.

    Args:
        files: List of uploaded files (max 20).
        user: Authenticated user.
        webhook_url: Optional webhook for batch completion notification.
        webhook_secret: Optional HMAC secret.
        enable_ocr: Whether to force OCR processing.

    Returns:
        BatchUploadResponse with batch_id and per-file results.

    Raises:
        HTTPException: If batch is empty or exceeds size limits.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided in batch upload",
        )

    if len(files) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch upload limited to 20 files, got {len(files)}",
        )

    batch_id = str(uuid.uuid4())
    results: List[BatchUploadResult] = []
    queue = _get_queue()

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    for file in files:
        # Validate content type
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            results.append(BatchUploadResult(
                filename=file.filename or "unknown",
                job_id="",
                document_id="",
                status="failed",
                error=f"Unsupported type '{file.content_type}'. Allowed: {', '.join(ALLOWED_CONTENT_TYPES.keys())}",
            ))
            continue

        # Validate extension
        ext = os.path.splitext(file.filename or "")[1].lower()
        expected_ext = ALLOWED_CONTENT_TYPES.get(file.content_type or "", "")
        if ext and ext != expected_ext:
            logger.warning("Content-type/extension mismatch: %s vs %s", file.content_type, ext)

        # Read contents with size check
        try:
            contents = await file.read()
        except Exception as exc:
            results.append(BatchUploadResult(
                filename=file.filename or "unknown",
                job_id="",
                document_id="",
                status="failed",
                error=f"Failed to read file: {exc}",
            ))
            continue

        if len(contents) > MAX_FILE_SIZE:
            results.append(BatchUploadResult(
                filename=file.filename or "unknown",
                job_id="",
                document_id="",
                status="failed",
                error=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB",
            ))
            continue

        if len(contents) == 0:
            results.append(BatchUploadResult(
                filename=file.filename or "unknown",
                job_id="",
                document_id="",
                status="failed",
                error="Uploaded file is empty",
            ))
            continue

        # Save file
        document_id = str(uuid.uuid4())
        safe_filename = f"{document_id}{expected_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        try:
            with open(file_path, "wb") as f:
                f.write(contents)
        except OSError as exc:
            results.append(BatchUploadResult(
                filename=file.filename or "unknown",
                job_id="",
                document_id="",
                status="failed",
                error=f"Failed to save file: {exc}",
            ))
            continue

        # Validate magic bytes
        is_valid, error_msg = validate_file_magic(file_path, expected_ext)
        if not is_valid:
            try:
                os.remove(file_path)
            except OSError:
                pass
            results.append(BatchUploadResult(
                filename=file.filename or "unknown",
                job_id="",
                document_id="",
                status="failed",
                error=error_msg,
            ))
            continue

        # Create and enqueue job
        job = JobRecord(
            document_id=document_id,
            tenant_id=user.tenant_id or "default",
            user_id=user.sub,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            status=JobStatus.PENDING,
        )

        try:
            job_id = await queue.enqueue(job)
        except Exception as exc:
            logger.error("Failed to enqueue job for %s: %s", file.filename, exc)
            try:
                os.remove(file_path)
            except OSError:
                pass
            results.append(BatchUploadResult(
                filename=file.filename or "unknown",
                job_id="",
                document_id="",
                status="failed",
                error="Failed to queue document for processing",
            ))
            continue

        # Submit Celery task
        try:
            from ingestion.tasks import process_document
            options: Dict[str, Any] = {"enable_ocr": enable_ocr}
            process_document.delay(
                job_id=job_id,
                document_path=file_path,
                options=options,
            )
        except Exception as exc:
            logger.warning("Failed to submit Celery task for %s: %s", file.filename, exc)

        results.append(BatchUploadResult(
            filename=file.filename or "unknown",
            job_id=job_id,
            document_id=document_id,
            status=JobStatus.PENDING.value,
        ))

        logger.info(
            "Batch upload: job=%s, file=%s, user=%s, batch=%s",
            job_id,
            file.filename,
            user.sub,
            batch_id,
        )

    accepted = sum(1 for r in results if r.status != "failed")
    failed = len(results) - accepted

    return BatchUploadResponse(
        batch_id=batch_id,
        total=len(results),
        accepted=accepted,
        failed=failed,
        results=results,
    )
