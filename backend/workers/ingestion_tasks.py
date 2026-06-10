"""Celery ingestion entry tasks — imported by API without circular dependency on workers.ingestion."""

from __future__ import annotations

import logging

from celery.exceptions import MaxRetriesExceededError, Retry

from app.domains.ingestion.models import IngestionState, coerce_ingestion_state
from app.domains.ingestion.repository import IngestionRepository
from workers.celery_app import celery_app
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 8


async def _mark_upload_failed(upload_id: str, tenant_id: str, user_id: str, error: str) -> None:
    """Best-effort transition to FAILED so uploads do not stay stuck in UPLOADED."""
    session = await worker_loop.create_session(tenant_id, user_id, "admin")
    try:
        repo = IngestionRepository(session, tenant_id=tenant_id)
        upload = await repo.get_by_id(upload_id) or await repo.get_upload(upload_id, tenant_id)
        if not upload:
            return
        current = coerce_ingestion_state(upload.ingestion_state)
        if current in (IngestionState.REVIEW_READY, IngestionState.FAILED, IngestionState.CANCELLED):
            return
        resolved_tenant = str(upload.tenant_id)
        await repo.update_state(upload_id, resolved_tenant, IngestionState.FAILED, error=error)
        await session.commit()
    except Exception:
        logger.exception("Failed to mark upload %s as failed", upload_id)
    finally:
        await session.close()


async def _transition_to_validating(upload_id: str, tenant_id: str, user_id: str) -> bool:
    """Move upload to VALIDATING.

    Resolves tenant_id from the upload row when the caller-supplied tenant does
    not match (prevents silent no-ops from tenant mismatch).

    Returns True if transition was performed or upload is already past UPLOADED.
    Raises RuntimeError if upload row is not found (caller should retry).
    """
    session = await worker_loop.create_session(tenant_id, user_id, "admin")
    try:
        repo = IngestionRepository(session, tenant_id=tenant_id)
        upload = await repo.get_upload(upload_id, tenant_id)
        if not upload:
            upload = await repo.get_by_id(upload_id)
        if not upload:
            logger.warning(
                "Upload not found for ingest_document (will retry): %s tenant=%s",
                upload_id,
                tenant_id,
            )
            raise RuntimeError(f"Upload {upload_id} not found in DB after upload commit")

        resolved_tenant = str(upload.tenant_id)
        if resolved_tenant != tenant_id:
            await session.close()
            session = await worker_loop.create_session(resolved_tenant, user_id, "admin")
            repo = IngestionRepository(session, tenant_id=resolved_tenant)

        current = coerce_ingestion_state(upload.ingestion_state)
        if current == IngestionState.UPLOADED:
            await repo.update_state(upload_id, resolved_tenant, IngestionState.VALIDATING)
            await session.commit()
            logger.info("ingest_document: %s -> validating", upload_id)
            return True

        logger.info(
            "ingest_document: upload %s already in state %s, skipping transition",
            upload_id,
            current.value,
        )
        return True
    finally:
        await session.close()


@celery_app.task(
    bind=True,
    name="ingest_document",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
)
def ingest_document(self, upload_id: str, tenant_id: str, user_id: str = "system") -> None:
    """Queue post-upload validation and pipeline processing.

    user_id is provided by the API caller to avoid a race-condition DB lookup.
    """
    logger.info("ingest_document started upload_id=%s tenant_id=%s", upload_id, tenant_id)
    helper = WorkerAsyncHelper()
    try:
        helper.run(_transition_to_validating(upload_id, tenant_id, user_id))
    except Retry:
        raise
    except MaxRetriesExceededError:
        helper.run(_mark_upload_failed(
            upload_id,
            tenant_id,
            user_id,
            "Ingestion failed to start after multiple retries — use Retry to resume",
        ))
        raise
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            helper.run(_mark_upload_failed(
                upload_id,
                tenant_id,
                user_id,
                f"Ingestion failed to start: {exc}",
            ))
        raise

    from workers.ingestion import validate_upload_task

    validate_upload_task.delay(upload_id, tenant_id, user_id)
