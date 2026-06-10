"""Ingestion Celery tasks — validation, storage confirmation, and pipeline orchestration."""

from __future__ import annotations

import hashlib
import logging

from celery import Task
from celery.exceptions import Retry

from app.config import settings
from app.domains.ingestion.models import IngestionState, coerce_ingestion_state
from app.domains.ingestion.security import validate_magic_bytes, FileValidationError
from app.integrations.storage.s3 import storage_service
from app.kernel.security.events import (
    log_security_event,
    SecurityEventType,
    SecurityEventSeverity,
)
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class TenantAwareTask(Task):
    """Base task that establishes tenant context for worker execution.

    Uses the shared ``WorkerLoop`` engine instead of creating a per-task
    ``TenantAwareSessionFactory``.  This ensures all tasks in the same
    worker process reuse the same connection pool and event loop.
    """

    abstract = True

    async def create_session(self, tenant_id: str, user_id: str, user_role: str = "api"):
        return await worker_loop.create_session(tenant_id, user_id, user_role)


from workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    base=TenantAwareTask,
    name="validate_upload",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def validate_upload_task(self, upload_id: str, tenant_id: str, user_id: str):
    """Validate uploaded file: checksum, magic bytes, malware scan hook.

    Runs inside the ingestion pipeline after upload completion.
    Transitions to VALIDATED or FAILED/QUARANTINED.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_validate_upload(helper, self, upload_id, tenant_id, user_id))


async def _validate_upload(helper: WorkerAsyncHelper, task, upload_id: str, tenant_id: str, user_id: str):
    session = await task.create_session(tenant_id, user_id, "api")
    async with helper.session_scope(session):
        try:
            from app.domains.ingestion.repository import IngestionRepository
            repo = IngestionRepository(session, tenant_id=tenant_id)

            upload = await repo.get_upload(upload_id, tenant_id)
            if not upload:
                logger.warning(
                    "Upload not found for validate_upload (will retry): %s",
                    upload_id,
                )
                raise task.retry(
                    exc=RuntimeError(f"Upload not found: {upload_id}"),
                    countdown=2,
                    max_retries=MAX_RETRIES,
                )

            if coerce_ingestion_state(upload.ingestion_state) != IngestionState.VALIDATING:
                logger.warning("Upload %s not in VALIDATING state, skipping", upload_id)
                return

            # 1. Download file from storage
            file_data = await storage_service.download_fileobj(
                upload.storage_bucket or settings.s3_bucket or "contractrisk-documents",
                upload.storage_key or "",
            )

            # 2. Compute server-side checksum
            server_checksum = hashlib.sha256(file_data).hexdigest()
            await repo.set_checksum(upload_id, tenant_id, server_checksum)

            # 3. Validate client checksum if provided
            if upload.client_checksum_sha256 and upload.client_checksum_sha256 != server_checksum:
                await repo.update_state(upload_id, tenant_id, IngestionState.FAILED,
                                        error="Client checksum mismatch")
                log_security_event(
                    SecurityEventType.SUSPICIOUS_REQUEST,
                    severity=SecurityEventSeverity.WARNING,
                    message=f"Checksum mismatch for upload {upload_id}",
                    actor_id=user_id,
                    tenant_id=tenant_id,
                    details={
                        "client_checksum": upload.client_checksum_sha256,
                        "server_checksum": server_checksum,
                    },
                )
                return

            # 4. Validate magic bytes
            try:
                validate_magic_bytes(file_data, upload.content_type)
            except FileValidationError as exc:
                await repo.update_state(upload_id, tenant_id, IngestionState.FAILED, error=str(exc))
                return

            # 5. Malware scan hook (placeholder)
            # scan_result = await malware_scanner.scan(file_data)
            # if scan_result.infected:
            #     await repo.update_state(upload_id, tenant_id, IngestionState.QUARANTINED, error=scan_result.threat)
            #     return

            # 6. Transition to VALIDATED
            await repo.update_state(upload_id, tenant_id, IngestionState.VALIDATED)

            # 7. Dispatch next pipeline stage
            confirm_storage_task.delay(upload_id, tenant_id, user_id)

            await session.commit()
            logger.info("Upload validated: %s", upload_id)

        except Retry:
            await session.rollback()
            raise
        except Exception as exc:
            await session.rollback()
            logger.error("Validation failed for upload %s: %s", upload_id, exc)
            try:
                await repo.update_state(upload_id, tenant_id, IngestionState.FAILED, error=str(exc))
                await session.commit()
            except Exception:
                pass
            raise


@celery_app.task(
    bind=True,
    base=TenantAwareTask,
    name="confirm_storage",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def confirm_storage_task(self, upload_id: str, tenant_id: str, user_id: str):
    """Confirm file is durably stored and transition to OCR pipeline."""
    helper = WorkerAsyncHelper()
    return helper.run(_confirm_storage(helper, self, upload_id, tenant_id, user_id))


async def _confirm_storage(helper: WorkerAsyncHelper, task, upload_id: str, tenant_id: str, user_id: str):
    session = await task.create_session(tenant_id, user_id, "api")
    from app.domains.ingestion.repository import IngestionRepository
    repo = IngestionRepository(session, tenant_id=tenant_id)
    async with helper.session_scope(session):
        try:
            upload = await repo.get_upload(upload_id, tenant_id)
            if not upload:
                return

            if coerce_ingestion_state(upload.ingestion_state) != IngestionState.VALIDATED:
                return

            # Verify object still exists
            exists = await storage_service.object_exists(
                upload.storage_bucket or settings.s3_bucket or "contractrisk-documents",
                upload.storage_key or "",
            )
            if not exists:
                await repo.update_state(upload_id, tenant_id, IngestionState.FAILED,
                                        error="File not found in storage after validation")
                await session.commit()
                return

            await repo.update_state(upload_id, tenant_id, IngestionState.STORAGE_CONFIRMED)
            await session.commit()

            # Text extraction (DOCX/PDF/TXT) — skip redundant start_ocr hop + extra S3 download
            from workers.extraction import extract_document_task
            extract_document_task.delay(upload_id, tenant_id, user_id)

            logger.info("Storage confirmed, extraction queued for upload: %s", upload_id)

        except Exception as exc:
            await session.rollback()
            logger.error("Storage confirmation failed for upload %s: %s", upload_id, exc)
            # Transition to FAILED so the upload doesn't stay stuck at VALIDATED
            # after Celery exhausts its retries.
            try:
                await repo.update_state(upload_id, tenant_id, IngestionState.FAILED,
                                        error=f"Storage confirmation failed: {exc}")
                await session.commit()
            except Exception:
                pass
            raise
