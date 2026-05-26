"""Celery ingestion entry tasks — imported by API without circular dependency on workers.ingestion."""

from __future__ import annotations

import logging
from typing import Optional

from app.domains.ingestion.models import IngestionState, coerce_ingestion_state
from app.domains.ingestion.repository import IngestionRepository
from workers.celery_app import celery_app
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


async def _transition_to_validating(upload_id: str, tenant_id: str) -> Optional[str]:
    """Move upload to VALIDATING and return the owning user_id for downstream tasks.

    Returns None when the upload row is not visible yet (e.g. API transaction uncommitted).
    """
    session = await worker_loop.create_session(tenant_id, "system", "admin")
    try:
        repo = IngestionRepository(session, tenant_id=tenant_id)
        upload = await repo.get_upload(upload_id, tenant_id)
        if not upload:
            logger.error("Upload not found for ingest_document: %s", upload_id)
            return None
        if coerce_ingestion_state(upload.ingestion_state) == IngestionState.UPLOADED:
            await repo.update_state(upload_id, tenant_id, IngestionState.VALIDATING)
            await session.commit()
        return upload.user_id
    finally:
        await session.close()


@celery_app.task(
    name="ingest_document",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def ingest_document(upload_id: str, tenant_id: str) -> None:
    """Queue post-upload validation and pipeline processing."""
    logger.info("ingest_document started upload_id=%s tenant_id=%s", upload_id, tenant_id)
    helper = WorkerAsyncHelper()
    user_id = helper.run(_transition_to_validating(upload_id, tenant_id))

    if user_id is None:
        raise RuntimeError(f"Upload not found: {upload_id}")

    # Import here so workers.ingestion is only loaded in the Celery worker process.
    from workers.ingestion import validate_upload_task

    validate_upload_task.delay(upload_id, tenant_id, user_id)
