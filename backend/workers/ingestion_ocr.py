"""OCR pipeline Celery tasks — text extraction from uploaded documents."""

from __future__ import annotations

import logging

from app.domains.ingestion.models import IngestionState, coerce_ingestion_state
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


from workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="start_ocr_pipeline",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def start_ocr_pipeline_task(self, upload_id: str, tenant_id: str, user_id: str):
    """Start OCR pipeline: download from storage, extract text, store pages.

    This is a placeholder that will be expanded with PyMuPDF/Tesseract integration.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_run_ocr_pipeline(helper, upload_id, tenant_id, user_id))


async def _run_ocr_pipeline(helper: WorkerAsyncHelper, upload_id: str, tenant_id: str, user_id: str):
    session = await worker_loop.create_session(tenant_id, user_id, "api")
    async with helper.session_scope(session):
        try:
            from app.domains.ingestion.repository import IngestionRepository
            repo = IngestionRepository(session, tenant_id=tenant_id)

            upload = await repo.get_upload(upload_id, tenant_id)
            if not upload:
                logger.error("Upload not found for OCR: %s", upload_id)
                return

            state = coerce_ingestion_state(upload.ingestion_state)
            if state == IngestionState.STORAGE_CONFIRMED:
                await repo.update_state(upload_id, tenant_id, IngestionState.OCR_PENDING)
                await session.commit()
            elif state == IngestionState.OCR_PENDING:
                logger.info("Upload %s already in OCR_PENDING, continuing pipeline", upload_id)
            else:
                logger.warning(
                    "Upload %s not ready for OCR pipeline (state=%s), skipping",
                    upload_id,
                    state.value,
                )
                return

            # Hand off to extraction (legacy path; confirm_storage now queues extract directly)
            from workers.ingestion_dispatch import redispatch_ingestion

            redispatch_ingestion(upload_id, tenant_id, user_id, IngestionState.OCR_PENDING)

            logger.info("OCR pipeline dispatched for upload: %s", upload_id)

        except Exception as exc:
            await session.rollback()
            logger.error("OCR pipeline failed for upload %s: %s", upload_id, exc)
            try:
                await repo.update_state(upload_id, tenant_id, IngestionState.FAILED, error=str(exc))
                await session.commit()
            except Exception:
                pass
            raise
