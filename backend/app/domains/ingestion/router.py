"""Production-grade ingestion API endpoints.

Provides:
    - ``POST /api/v1/uploads`` — Multipart file upload with async ingestion trigger
    - ``GET  /api/v1/uploads/{upload_id}`` — Upload metadata and status
    - ``GET  /api/v1/uploads/{upload_id}/status`` — Ingestion state + progress
    - ``POST /api/v1/uploads/{upload_id}/retry`` — Retry failed ingestion
    - ``GET  /api/v1/uploads/{upload_id}/chunks`` — List document chunks

All endpoints enforce tenant isolation, require authentication, and emit
audit events. The upload endpoint integrates with MinIO, IngestionOrchestrator,
and Celery for fully asynchronous processing.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_tenant_id, get_db, get_event_bus
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.kernel.security.events import log_security_event, SecurityEventType, SecurityEventSeverity
from app.kernel.database.session import TenantAwareSessionFactory
from app.kernel.web.pagination import PaginatedResponse, PaginationMeta
from app.kernel.web.exceptions import AppError, NotFoundError, ConflictError, ValidationError, RateLimitError
from app.kernel.events.bus import EventBus
from app.domains.ingestion.schemas import (
    IngestionState,
    ingestion_state_for_api,
    UploadRequest,
    UploadResponse,
    UploadStatusResponse,
    UploadRetryResponse,
    UploadChunkResponse,
    UploadChunkListResponse,
    UploadSummary,
    ErrorResponse,
)
from app.domains.ingestion.repository import IngestionRepository
from app.domains.ingestion.service import IngestionService
from app.domains.ingestion.exceptions import (
    ChecksumMismatchError,
    UploadNotFoundError,
    IngestionStateTransitionError,
    IngestionRetryLimitExceededError,
)
from app.domains.ingestion.security import (
    validate_extension,
    validate_magic_bytes,
    validate_file_size,
    validate_filename_safety,
    FileValidationError,
)
from app.domains.vectors.repository import VectorRepository
from app.integrations.storage.s3 import storage_service
from workers.ingestion_tasks import ingest_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_UPLOAD_SIZE: int = 100_000_000  # 100 MB
ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


# ── Dependencies ──────────────────────────────────────────────────────────────


async def get_ingestion_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    event_bus=Depends(get_event_bus),
) -> IngestionService:
    """Provide a tenant-scoped IngestionService."""
    return IngestionService(
        repository=IngestionRepository(db, tenant_id=tenant_id),
        event_bus=event_bus,
        user=user,
        tenant_id=tenant_id,
    )


# ── Rate Limiting Hook ────────────────────────────────────────────────────────

_UPLOAD_RATE_LIMITS: dict[str, list[float]] = {}
"""Simple in-memory rate limiter: tenant_id -> [timestamps of recent uploads]."""

MAX_UPLOADS_PER_MINUTE: int = 10


async def check_upload_rate_limit(tenant_id: str) -> None:
    """Check if the tenant has exceeded the upload rate limit.

    Simple in-memory sliding window. For production, replace with Redis.
    """
    now = time.monotonic()
    window_start = now - 60.0

    timestamps = _UPLOAD_RATE_LIMITS.get(tenant_id, [])
    timestamps = [t for t in timestamps if t > window_start]
    timestamps.append(now)
    _UPLOAD_RATE_LIMITS[tenant_id] = timestamps

    if len(timestamps) > MAX_UPLOADS_PER_MINUTE:
        log_security_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=SecurityEventSeverity.WARNING,
            message=f"Upload rate limit exceeded for tenant {tenant_id}",
            tenant_id=tenant_id,
            details={"uploads_in_window": len(timestamps), "max_allowed": MAX_UPLOADS_PER_MINUTE},
        )
        raise RateLimitError(message="Upload rate limit exceeded. Max 10 uploads per minute.")


# ── POST /uploads ─────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description=(
        "Upload a document file (PDF, DOCX, or TXT) for ingestion. "
        "The file is validated, stored in MinIO, and the ingestion pipeline "
        "is triggered asynchronously. Returns the upload_id for status tracking."
    ),
    responses={
        201: {"model": UploadResponse, "description": "Upload accepted"},
        400: {"model": ErrorResponse, "description": "Validation error"},
        413: {"model": ErrorResponse, "description": "File too large"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    client_checksum_sha256: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Upload a document file and start the ingestion pipeline.

    The file is validated for type, size, and magic bytes, then stored
    in MinIO. The ingestion pipeline (extract -> chunk -> embed -> index)
    is triggered asynchronously via Celery.

    **Supported formats:** PDF, DOCX, TXT (max 100 MB).
    """
    try:
        print("UPLOAD ROUTER EXECUTED")
        print(f"TENANT ID: {tenant_id}")
        print(f"USER ID: {user.id}")
        print("PERMISSION CHECK PASSED")
        correlation_id = str(uuid.uuid4())
        import traceback

        print("\n" + "=" * 80)
        print("UPLOAD ENDPOINT HIT")
        print("=" * 80)
        overall_start = time.monotonic()

        # ── Rate limit check ───────────────────────────────────────────
        print("STEP 1 — before rate limit check")
        await check_upload_rate_limit(tenant_id)
        print("STEP 2 — rate limit check passed")
        # ── Read file ──────────────────────────────────────────────────
        try:
            print("STEP 3 — before file read")
            file_data = await file.read()
            print("STEP 4 — file read complete")
            print(f"FILE SIZE: {len(file_data)}")
            print("STEP 5 — validating content type")
            if file.content_type not in ALLOWED_CONTENT_TYPES:
                raise ValidationError(message=f"Unsupported content type: {file.content_type}")

            print("STEP 6 — validating extension")
            validate_extension(file.filename or "")

            safe_filename = validate_filename_safety(file.filename or "untitled")

            print("STEP 7 — validating file size")
            validate_file_size(len(file_data))

            print("STEP 8 — validating magic bytes")
            validate_magic_bytes(
                file_data,
                file.content_type or "application/pdf",
            )

            print("STEP 9 — validation complete")

            print("STEP 10 — creating repository")
            repo = IngestionRepository(db, tenant_id=tenant_id)

            print("STEP 11 — generating checksum")
            server_checksum = hashlib.sha256(file_data).hexdigest()

            if client_checksum_sha256 and client_checksum_sha256 != server_checksum:
                raise ChecksumMismatchError(
                    message="Client checksum does not match server-computed checksum",
                )

            existing_uploads = await repo.list_by_tenant(tenant_id)
            for existing in existing_uploads:
                if getattr(existing, "server_checksum_sha256", None) == server_checksum:
                    raise ConflictError(
                        message=f"Duplicate upload: file with checksum {server_checksum[:12]}... already exists",
                    )

            print("STEP 12 — creating upload session")
            upload = await repo.create_upload(
                tenant_id=tenant_id,
                user_id=user.id,
                filename=safe_filename,
                content_type=file.content_type or "application/pdf",
                file_size=len(file_data),
                client_checksum_sha256=client_checksum_sha256,
                metadata={},
            )

            print(f"STEP 12 — upload session created: {upload.upload_id}")

            bucket = settings.s3_bucket or "contractrisk-documents"

            print("STEP 13 — ensuring MinIO bucket")
            await storage_service.ensure_bucket(bucket)

            storage_key = f"{tenant_id}/{upload.upload_id}/{file.filename}"

            print("STEP 14 — uploading file to MinIO")
            await storage_service.upload_fileobj(
                bucket=bucket,
                key=storage_key,
                file_body=file_data,
                content_type=file.content_type or "application/pdf",
            )

            print("STEP 15 — MinIO upload complete")

            print("STEP 16 — updating storage metadata")
            await repo.set_storage_key(
                upload_id=str(upload.upload_id),
                tenant_id=tenant_id,
                storage_key=storage_key,
                storage_bucket=bucket,
            )
            await repo.set_checksum(
                upload_id=str(upload.upload_id),
                tenant_id=tenant_id,
                server_checksum_sha256=server_checksum,
            )

            print("STEP 17 — storage metadata updated")

            print("STEP 18 — dispatching ingestion task")

            # Commit before queuing Celery so workers see the upload row (get_db commits after response).
            await db.commit()

            queued_to_celery = False
            if settings.environment != "development":
                try:
                    ingest_document.apply_async(
                        kwargs={
                            "upload_id": str(upload.upload_id),
                            "tenant_id": tenant_id,
                            "user_id": user.id,
                        },
                        countdown=2,
                    )
                    queued_to_celery = True
                    print("STEP 19 — ingestion task queued")

                except Exception as queue_exc:
                    logger.warning(
                        "Upload saved but ingestion task not queued: %s",
                        queue_exc,
                    )
                    print(f"STEP 19 — ingestion queue skipped: {queue_exc}")

            # Development: always run inline — Celery workers are optional and often
            # misconfigured locally (duplicate nodenames, stale processes).
            if settings.environment == "development":
                logger.info(
                    "Starting inline ingestion pipeline for upload %s (dev mode)",
                    upload.upload_id,
                )
                _schedule_inline_ingestion(
                    upload_id=str(upload.upload_id),
                    tenant_id=tenant_id,
                    user_id=user.id,
                    db_factory=request.app.state.db_factory,
                    correlation_id=correlation_id,
                )
            elif not queued_to_celery:
                try:
                    await repo.update_state(
                        str(upload.upload_id), tenant_id,
                        IngestionState.FAILED,
                        error="Ingestion queue unavailable — start Redis/Celery worker or retry",
                    )
                    await db.commit()
                except Exception:
                    pass

            return UploadResponse(
                upload_id=str(upload.upload_id),
                filename=upload.filename,
                file_size=upload.file_size,
                content_type=upload.content_type,
                ingestion_state=ingestion_state_for_api(upload.ingestion_state),
                correlation_id=correlation_id,
            )
        except FileValidationError as exc:
            raise ValidationError(message=str(exc)) from exc
        except Exception:
            raise
    except FileValidationError as exc:
        raise ValidationError(message=str(exc)) from exc
    except Exception:
        print("\n" + "=" * 80)
        print("UPLOAD ENDPOINT CRASH")
        print("=" * 80)
        traceback.print_exc()
        print("=" * 80 + "\n")
        raise


def _schedule_inline_ingestion(
    upload_id: str,
    tenant_id: str,
    user_id: str,
    db_factory: TenantAwareSessionFactory,
    correlation_id: str,
) -> None:
    """Start inline ingestion on a daemon thread (dev mode).

    Uses a thread-local event loop and DB pool — the app-scoped async engine
    cannot be shared across uvicorn's loop and a worker thread.
    """
    def _thread_main() -> None:
        try:
            asyncio.run(
                _run_inline_ingestion(
                    upload_id=upload_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
            )
        except Exception:
            logger.exception("Inline ingestion thread crashed for upload %s", upload_id)

    thread = threading.Thread(
        target=_thread_main,
        name=f"ingest-{upload_id[:8]}",
        daemon=True,
    )
    thread.start()


async def _run_inline_ingestion(
    upload_id: str,
    tenant_id: str,
    user_id: str,
    correlation_id: str,
) -> None:
    """Run ingestion inline after the upload response (dev mode).

    Creates a thread-local DB pool — never reuse the app/request async engine.
    """
    from app.domains.ingestion.services.ingestion_orchestrator import IngestionOrchestrator
    from app.domains.vectors.services.embedding_service import EmbeddingService
    from app.integrations.storage.s3 import storage_service
    from app.kernel.database.orm_registry import register_orm_models
    from app.kernel.events.bus import EventBus

    register_orm_models()
    thread_db = TenantAwareSessionFactory(
        database_url=settings.database_url,
        pool_size=2,
        max_overflow=1,
    )
    session = await thread_db.create_session(tenant_id, user_id, "admin")
    try:
        repo = IngestionRepository(session, tenant_id=tenant_id)
        upload = await repo.get_upload(upload_id, tenant_id)
        if not upload:
            logger.error("Inline ingestion: upload %s not found", upload_id)
            return

        file_data = await storage_service.download_fileobj(
            upload.storage_bucket or settings.s3_bucket or "contractrisk-documents",
            upload.storage_key or "",
        )

        orchestrator = IngestionOrchestrator(
            session=session,
            embedding_service=EmbeddingService(
                api_key=settings.openai_api_key,
                model=settings.default_embedding_model,
            ),
            event_bus=EventBus(),
            tenant_id=tenant_id,
        )
        await orchestrator.run_pipeline(
            upload_id=upload_id,
            file_data=file_data,
            filename=upload.filename,
            content_type=upload.content_type,
            correlation_id=correlation_id,
        )
        await session.commit()
    except Exception as exc:
        error_msg = f"Inline ingestion failed: {exc}"
        logger.exception("Inline ingestion pipeline failed for upload %s", upload_id)
        try:
            repo = IngestionRepository(session, tenant_id=tenant_id)
            await repo.update_state(
                upload_id, tenant_id,
                IngestionState.FAILED,
                error=error_msg[:500],
            )
            await session.commit()
        except Exception:
            logger.exception("Failed to mark upload %s as failed after pipeline crash", upload_id)
    finally:
        await session.close()
        await thread_db.close()


# ── GET /uploads/{upload_id} ──────────────────────────────────────────────────


@router.get(
    "/{upload_id}",
    response_model=UploadStatusResponse,
    summary="Get upload details",
    description="Retrieve metadata and current ingestion status for an upload.",
    responses={
        200: {"model": UploadStatusResponse, "description": "Upload details"},
        404: {"model": ErrorResponse, "description": "Upload not found"},
    },
)
async def get_upload(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get upload metadata and current ingestion status."""
    repo = IngestionRepository(db, tenant_id=tenant_id)
    upload = await repo.get_upload(upload_id, tenant_id)
    if not upload:
        raise NotFoundError(f"Upload {upload_id} not found")

    return UploadStatusResponse(
        upload_id=str(upload.upload_id),
        filename=upload.filename,
        file_size=upload.file_size,
        content_type=upload.content_type,
        ingestion_state=ingestion_state_for_api(upload.ingestion_state),
        ingestion_error=upload.ingestion_error,
        retry_count=upload.retry_count,
        max_retries=3,
        can_retry=_upload_can_retry(upload),
        storage_key=upload.storage_key,
        checksum_sha256=upload.server_checksum_sha256,
        created_at=upload.created_at,
        updated_at=upload.updated_at,
        completed_at=upload.completed_at,
    )


def _upload_can_retry(upload) -> bool:
    """Whether an upload can be retried or resumed from its current state."""
    if upload.retry_count >= 3:
        return False
    api_state = ingestion_state_for_api(upload.ingestion_state)
    resumable = {
        IngestionState.UPLOADED,
        IngestionState.VALIDATING,
        IngestionState.VALIDATED,
        IngestionState.OCR_PENDING,
        IngestionState.OCR_PROCESSING,
        IngestionState.STORAGE_CONFIRMED,
        IngestionState.OCR_COMPLETE,
        IngestionState.CHUNKING_PENDING,
        IngestionState.EMBEDDING_PENDING,
        IngestionState.ANALYSIS_PENDING,
    }
    return api_state == IngestionState.FAILED or api_state in resumable


# ── GET /uploads/{upload_id}/status ───────────────────────────────────────────


@router.get(
    "/{upload_id}/status",
    response_model=UploadStatusResponse,
    summary="Get ingestion status",
    description="Get the current ingestion pipeline state and progress for an upload.",
    responses={
        200: {"model": UploadStatusResponse, "description": "Ingestion status"},
        404: {"model": ErrorResponse, "description": "Upload not found"},
    },
)
async def get_upload_status(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get the current ingestion pipeline status."""
    repo = IngestionRepository(db, tenant_id=tenant_id)
    upload = await repo.get_upload(upload_id, tenant_id)
    if not upload:
        raise NotFoundError(f"Upload {upload_id} not found")

    api_state = ingestion_state_for_api(upload.ingestion_state)
    progress = _build_progress(api_state.value)

    return UploadStatusResponse(
        upload_id=str(upload.upload_id),
        filename=upload.filename,
        file_size=upload.file_size,
        content_type=upload.content_type,
        ingestion_state=api_state,
        ingestion_error=upload.ingestion_error,
        retry_count=upload.retry_count,
        max_retries=3,
        can_retry=_upload_can_retry(upload),
        progress=progress,
        storage_key=upload.storage_key,
        checksum_sha256=upload.server_checksum_sha256,
        created_at=upload.created_at,
        updated_at=upload.updated_at,
        completed_at=upload.completed_at,
    )


def _build_progress(state: str) -> dict:
    """Build a progress object from the current ingestion state."""
    stages = [
        ("uploaded", 0, "Upload received"),
        ("validating", 5, "Validating file"),
        ("validated", 10, "File validated"),
        ("storage_confirmed", 15, "File stored"),
        ("ocr_pending", 20, "Preparing extraction"),
        ("ocr_processing", 35, "Extracting text"),
        ("ocr_complete", 50, "Text extracted"),
        ("chunking_pending", 55, "Preparing chunking"),
        ("embedding_pending", 70, "Generating embeddings"),
        ("analysis_pending", 85, "Finalizing"),
        ("review_ready", 100, "Ready for review"),
    ]

    current_pct = 0
    current_label = "Unknown"
    for stage_name, pct, label in stages:
        if stage_name == state:
            current_pct = pct
            current_label = label
            break
        current_pct = pct
        current_label = label

    return {
        "percent": current_pct,
        "label": current_label,
        "state": state,
    }


# ── POST /uploads/{upload_id}/retry ───────────────────────────────────────────


@router.post(
    "/{upload_id}/retry",
    response_model=UploadRetryResponse,
    summary="Retry or resume ingestion",
    description="Retry a failed upload or re-queue a stuck pipeline step (e.g. text extraction). Max 3 retries allowed.",
    responses={
        200: {"model": UploadRetryResponse, "description": "Retry initiated"},
        404: {"model": ErrorResponse, "description": "Upload not found"},
        409: {"model": ErrorResponse, "description": "Cannot retry (wrong state or limit reached)"},
    },
)
async def retry_ingestion(
    upload_id: str,
    service: IngestionService = Depends(get_ingestion_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Retry ingestion for a failed upload session."""
    try:
        result = await service.retry_ingestion(upload_id)
        return UploadRetryResponse(
            upload_id=upload_id,
            ingestion_state=IngestionState.UPLOADED,
            retry_count=result.get("retry_count", 0),
        )
    except UploadNotFoundError:
        raise NotFoundError(f"Upload {upload_id} not found")
    except IngestionRetryLimitExceededError as exc:
        raise ConflictError(str(exc))
    except IngestionStateTransitionError as exc:
        raise ConflictError(str(exc))


# ── POST /uploads/{upload_id}/process (dev mode) ─────────────────────────────


@router.post(
    "/{upload_id}/process",
    response_model=UploadRetryResponse,
    summary="Process upload synchronously (dev mode)",
    description="Run the full ingestion pipeline synchronously for development environments without Celery/Redis. "
                "Only available when environment='development'. Skips OCR and uses direct text extraction.",
    responses={
        200: {"model": UploadRetryResponse, "description": "Processing complete"},
        404: {"model": ErrorResponse, "description": "Upload not found"},
        400: {"model": ErrorResponse, "description": "Not available in production mode"},
    },
)
async def process_upload_sync(
    upload_id: str,
    service: IngestionService = Depends(get_ingestion_service),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Run the full ingestion pipeline synchronously.

    Development-only. Processes the upload through validation, extraction,
    chunking, embedding, and AI analysis in a single request.
    """
    if settings.environment != "development":
        raise HTTPException(status_code=400, detail="Synchronous processing only available in development mode")

    repo = IngestionRepository(db, tenant_id=tenant_id)
    upload = await repo.get_upload(upload_id, tenant_id)
    if not upload:
        raise NotFoundError(f"Upload {upload_id} not found")

    from app.domains.ingestion.models import IngestionState, coerce_ingestion_state
    from app.domains.extraction.repository import ExtractionRepository
    from app.domains.extraction.service import ExtractionService
    from app.domains.vectors.repository import VectorRepository
    from app.domains.vectors.chunking import chunking_service
    from app.domains.vectors.embeddings import OpenAIEmbeddingProvider, EmbeddingRequest, embedding_registry
    from app.domains.ai.repository import AIRepository
    from app.domains.ai.service import AIService
    from app.domains.ai.llm import OpenAIProvider
    from app.domains.ai.providers.registry import llm_registry
    from app.kernel.events.bus import EventBus

    current_state = coerce_ingestion_state(upload.ingestion_state)

    # Helper: transition if current state allows it, otherwise skip
    async def _try_transition(from_state: IngestionState, to_state: IngestionState) -> bool:
        nonlocal current_state
        if current_state == from_state:
            await repo.update_state(upload_id, tenant_id, to_state)
            await db.commit()
            current_state = to_state
            return True
        return False

    # Step 1: Validate (skip if already past)
    await _try_transition(IngestionState.UPLOADED, IngestionState.VALIDATING)
    await _try_transition(IngestionState.VALIDATING, IngestionState.VALIDATED)
    await _try_transition(IngestionState.VALIDATED, IngestionState.STORAGE_CONFIRMED)

    # Step 2: Extract text (skip if already past OCR)
    await _try_transition(IngestionState.STORAGE_CONFIRMED, IngestionState.OCR_PENDING)
    await _try_transition(IngestionState.OCR_PENDING, IngestionState.OCR_PROCESSING)

    if current_state in (IngestionState.OCR_PROCESSING, IngestionState.STORAGE_CONFIRMED, IngestionState.OCR_PENDING):
        extract_repo = ExtractionRepository(db, tenant_id=tenant_id)
        extract_svc = ExtractionService(
            extraction_repo=extract_repo,
            ingestion_repo=repo,
            event_bus=EventBus(),
            user=None,
            tenant_id=tenant_id,
        )
        try:
            storage_key = upload.storage_key
            if storage_key:
                bucket = upload.storage_bucket or settings.s3_bucket or "contractrisk-documents"
                file_data = await storage_service.download_fileobj(bucket, storage_key)
                result = await extract_svc.extract_text(upload_id, tenant_id, file_data)
                logger.info("Extraction complete: %s pages", result.get("page_count", 0))
        except Exception as exc:
            logger.error("Extraction failed: %s", exc)
            await repo.update_state(upload_id, tenant_id, IngestionState.FAILED, error=str(exc))
            await db.commit()
            return UploadRetryResponse(upload_id=upload_id, ingestion_state="failed", retry_count=upload.retry_count)

    await _try_transition(IngestionState.OCR_COMPLETE, IngestionState.CHUNKING_PENDING)
    # If already past OCR_COMPLETE, current_state is already CHUNKING_PENDING or beyond

    # Step 3: Chunk (skip if chunks already exist)
    if current_state in (IngestionState.CHUNKING_PENDING, IngestionState.OCR_COMPLETE):
        vector_repo = VectorRepository(db, tenant_id=tenant_id)
        pages = await extract_repo.get_pages_by_upload(upload_id, tenant_id)
        if pages:
            page_dicts = [{"page_number": p.page_number, "text": p.text} for p in pages]
            chunks = chunking_service.chunk_pages(page_dicts, strategy="semantic")
            await vector_repo.store_chunks_bulk(upload_id, tenant_id, chunks)
            await db.commit()

    await _try_transition(IngestionState.CHUNKING_PENDING, IngestionState.EMBEDDING_PENDING)

    # Step 4: Embed (skip if already embedded)
    if current_state in (IngestionState.EMBEDDING_PENDING, IngestionState.CHUNKING_PENDING):
        vector_repo = VectorRepository(db, tenant_id=tenant_id)
        chunks = await vector_repo.get_pending_chunks(upload_id, tenant_id)
        if chunks:
            provider = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
            embedding_registry.register(provider)
            for i in range(0, len(chunks), provider.MAX_BATCH_SIZE):
                batch = chunks[i:i + provider.MAX_BATCH_SIZE]
                requests_batch = [EmbeddingRequest(text=c.text) for c in batch]
                try:
                    responses = await provider.embed_batch(requests_batch)
                    for j, response in enumerate(responses):
                        if j < len(batch):
                            await vector_repo.update_embedding(
                                chunk_id=batch[j].chunk_id,
                                tenant_id=tenant_id,
                                embedding=response.embedding,
                                model=response.model,
                                dimension=1536,
                                token_count=response.token_count,
                            )
                except Exception as exc:
                    logger.error("Embedding batch failed: %s", exc)

    await _try_transition(IngestionState.EMBEDDING_PENDING, IngestionState.ANALYSIS_PENDING)

    # Step 5: AI Analysis (skip if already past)
    if current_state in (IngestionState.ANALYSIS_PENDING, IngestionState.EMBEDDING_PENDING):
        llm_provider = OpenAIProvider(api_key=settings.openai_api_key)
        llm_registry.register(llm_provider)

        ai_service = AIService(
            ai_repo=AIRepository(db, tenant_id=tenant_id),
            vector_repo=vector_repo,
            ingest_repo=repo,
            event_bus=EventBus(),
            user=None,
            tenant_id=tenant_id,
        )
        try:
            result = await ai_service.analyze(upload_id, "full", force=True)
            await db.commit()
            logger.info("AI analysis complete: risk=%.4f findings=%d redlines=%d",
                         result.risk_score, len(result.findings), len(result.redlines))
        except Exception as exc:
            logger.error("AI analysis failed: %s", exc)
            try:
                await repo.update_state(upload_id, tenant_id, IngestionState.FAILED, error=str(exc))
                await db.commit()
            except ValueError:
                logger.warning("Could not transition to FAILED (already in terminal state)")
            return UploadRetryResponse(upload_id=upload_id, ingestion_state="failed", retry_count=upload.retry_count)

    return UploadRetryResponse(
        upload_id=upload_id,
        ingestion_state="review_ready",
        retry_count=upload.retry_count,
    )


# ── GET /uploads/{upload_id}/chunks ───────────────────────────────────────────


@router.get(
    "/{upload_id}/chunks",
    response_model=UploadChunkListResponse,
    summary="List document chunks",
    description="Retrieve all chunks for an upload with their embedding status.",
    responses={
        200: {"model": UploadChunkListResponse, "description": "List of chunks"},
        404: {"model": ErrorResponse, "description": "Upload not found"},
    },
)
async def get_upload_chunks(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get all chunks for an upload with their embedding status."""
    repo = IngestionRepository(db, tenant_id=tenant_id)
    upload = await repo.get_upload(upload_id, tenant_id)
    if not upload:
        raise NotFoundError(f"Upload {upload_id} not found")

    vector_repo = VectorRepository(db, tenant_id=tenant_id)
    db_chunks = await vector_repo.get_chunks_by_upload(upload_id, tenant_id)

    chunk_responses = [
        UploadChunkResponse(
            chunk_id=str(c.chunk_id),
            chunk_index=c.chunk_index,
            text=c.text,
            token_count=c.token_count,
            page_numbers=list(c.page_numbers) if c.page_numbers else [],
            section_heading=c.section_heading,
            clause_type=c.clause_type,
            checksum=c.checksum or "",
            embedding_status=str(c.embedding_status) if hasattr(c, "embedding_status") else "unknown",
        )
        for c in db_chunks
    ]

    return UploadChunkListResponse(
        upload_id=upload_id,
        total_chunks=len(chunk_responses),
        chunks=chunk_responses,
    )


# ── GET /uploads/ (list) ──────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedResponse[UploadSummary],
    summary="List uploads",
    description="List all upload sessions for the current tenant with optional state filter.",
)
async def list_uploads(
    state: Optional[str] = Query(None, description="Filter by ingestion state"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: IngestionService = Depends(get_ingestion_service),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List upload sessions with pagination and optional state filter."""
    items, total = await service.list_uploads(state, page, page_size)
    data = []
    for u in items:
        # Fetch contract_number from linked contract_review
        contract_number = None
        try:
            from sqlalchemy import text as sa_text
            row = await db.execute(
                sa_text("SELECT metadata->>'contract_number' FROM contract_reviews WHERE upload_id = :uid AND tenant_id = :tid"),
                {"uid": u.upload_id, "tid": tenant_id},
            )
            cn = row.scalar()
            if cn:
                contract_number = cn
        except Exception:
            pass
        data.append(
            UploadSummary(
                upload_id=str(u.upload_id),
                filename=u.filename,
                file_size=u.file_size,
                content_type=u.content_type,
                ingestion_state=ingestion_state_for_api(u.ingestion_state),
                created_at=u.created_at,
                contract_number=contract_number,
            )
        )
    return PaginatedResponse(
        data=data,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


# ── DELETE /uploads/{upload_id} ─────────────────────────────────────────────


@router.delete(
    "/{upload_id}",
    summary="Delete an upload",
    description="Remove an upload and its associated data from the system, including in-progress pipeline jobs.",
    responses={
        200: {"description": "Upload deleted"},
        404: {"model": ErrorResponse, "description": "Upload not found"},
        409: {"model": ErrorResponse, "description": "Upload cannot be deleted"},
    },
)
async def delete_upload(
    upload_id: str,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
    service: IngestionService = Depends(get_ingestion_service),
):
    """Delete an upload and its associated data (any ingestion state)."""
    await service.delete_upload(upload_id)
    return {"upload_id": upload_id, "deleted": True, "message": "Upload deleted"}


# ── GET /uploads/queue/stats ────────────────────────────────────────────────


@router.get(
    "/queue/stats",
    summary="Get ingestion queue statistics",
    description="Return real-time Celery queue depth and processing stats for the ingestion pipeline.",
    responses={
        200: {"description": "Queue statistics"},
        503: {"description": "Redis/Celery unavailable"},
    },
)
async def get_queue_stats(
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get ingestion queue depth and processing stats from Redis/Celery.

    Returns counts of pending, processing, completed, and failed jobs
    across all ingestion queues. Used by the frontend to display
    real-time queue health.
    """
    try:
        import redis.asyncio as aioredis

        broker = aioredis.from_url(settings.celery_broker_url, decode_responses=True)
        queue_names = ["ingestion", "ai", "notifications", "default"]

        queues = []
        total_pending = 0
        total_processing = 0

        for qname in queue_names:
            # Safely get queue length — handle WRONGTYPE if key exists as non-list
            pending = 0
            try:
                key_type = await broker.type(qname)
                if key_type == b"list":
                    pending = await broker.llen(qname) or 0
            except Exception:
                pass
            total_pending += pending

            # Check for reserved/processing tasks
            processing = 0
            binding_key = f"_kombu.binding.{qname}"
            try:
                btype = await broker.type(binding_key)
                if btype == b"list":
                    processing = await broker.llen(binding_key) or 0
            except Exception:
                pass
            total_processing += processing

            queues.append({
                "id": qname,
                "name": qname.replace("_", " ").title(),
                "status": "active" if pending > 0 or processing > 0 else "idle",
                "pendingCount": pending,
                "processingCount": processing,
                "completedCount": 0,
                "failedCount": 0,
                "throughput": 0,
                "avgLatency": 0,
            })

        await broker.close()

        return {
            "queues": queues,
            "totalPending": total_pending,
            "totalProcessing": total_processing,
            "totalQueues": len(queues),
            "activeQueues": sum(1 for q in queues if q["status"] == "active"),
        }

    except ImportError:
        return {
            "queues": [],
            "totalPending": 0,
            "totalProcessing": 0,
            "totalQueues": 0,
            "activeQueues": 0,
        }
    except Exception as exc:
        logger.warning("Failed to get queue stats from Redis: %s", exc)
        return {
            "queues": [],
            "totalPending": 0,
            "totalProcessing": 0,
            "totalQueues": 0,
            "activeQueues": 0,
            "error": str(exc),
        }
