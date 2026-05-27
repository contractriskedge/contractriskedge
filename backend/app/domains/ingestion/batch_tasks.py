"""Celery tasks for batch upload orchestration.

The batch_upload_pipeline task receives a batch_id and fans out
to individual process_upload tasks for each file in the batch.
"""

from __future__ import annotations

import uuid
import logging

from sqlalchemy import select, update

from app.config import settings
from app.domains.ingestion.batch_models import BatchUpload, BatchStatus
from app.domains.ingestion.models import UploadSession, IngestionState
from app.kernel.database.celery_base import TenantSafeTask
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    base=TenantSafeTask,
    name="process_batch_uploads",
    queue="ingestion",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_batch_uploads(self, batch_id: str) -> dict:
    """Process all pending uploads in a batch.

    Iterates over all upload sessions linked to the batch that are in
    UPLOADED state and dispatches them to the individual ingestion pipeline.
    """
    session = self.get_session(
        tenant_id="system", user_id="system", user_role="admin",
    )
    batch_uuid = uuid.UUID(batch_id)

    try:
        # Mark batch as processing
        session.execute(
            update(BatchUpload).where(BatchUpload.batch_id == batch_uuid).values(
                status=BatchStatus.PROCESSING,
            )
        )
        session.commit()

        # Find all uploaded files in this batch
        result = session.execute(
            select(UploadSession).where(
                UploadSession.batch_id == batch_uuid,
                UploadSession.ingestion_state == IngestionState.UPLOADED,
            )
        )
        uploads = list(result.scalars().all())

        if not uploads:
            logger.warning("Batch %s has no pending uploads to process", batch_id)
            return {"batch_id": batch_id, "dispatched": 0}

        # Dispatch each upload to the ingestion pipeline
        from app.domains.ingestion.service import process_upload as process_single_upload

        dispatched = 0
        for upload in uploads:
            try:
                process_single_upload.delay(str(upload.upload_id))
                dispatched += 1
            except Exception as exc:
                logger.error("Failed to dispatch upload %s: %s", upload.upload_id, exc)
                # Mark individual file as failed
                session.execute(
                    update(UploadSession).where(
                        UploadSession.upload_id == upload.upload_id,
                    ).values(
                        ingestion_state=IngestionState.FAILED,
                        ingestion_error=f"Dispatch failed: {exc}",
                    )
                )
                session.commit()

        logger.info(
            "Batch %s: dispatched %d/%d uploads",
            batch_id, dispatched, len(uploads),
        )
        return {
            "batch_id": batch_id,
            "total": len(uploads),
            "dispatched": dispatched,
        }

    except Exception as exc:
        logger.error("Batch processing failed for %s: %s", batch_id, exc)
        session.rollback()
        # Mark batch as failed
        try:
            session.execute(
                update(BatchUpload).where(BatchUpload.batch_id == batch_uuid).values(
                    status=BatchStatus.FAILED,
                    error_message=str(exc),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
        raise self.retry(exc=exc)
