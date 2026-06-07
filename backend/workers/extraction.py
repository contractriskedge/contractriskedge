"""OCR and extraction Celery tasks — document type detection, text extraction, OCR fallback."""

from __future__ import annotations

import logging
import time

from app.config import settings
from app.domains.extraction.parsers import parser_registry, EncryptedPDFError, CorruptedDocumentError
from app.domains.extraction.quality import quality_evaluator
from app.domains.extraction.service import ExtractionService
from app.domains.extraction.repository import ExtractionRepository
from app.domains.ingestion.models import IngestionState, coerce_ingestion_state
from app.domains.ingestion.repository import IngestionRepository
from app.integrations.storage.s3 import storage_service
from app.kernel.events.bus import EventBus
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop


logger = logging.getLogger(__name__)

MAX_RETRIES = 3


from workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="extract_document",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def extract_document_task(self, upload_id: str, tenant_id: str, user_id: str):
    """Main extraction task: detect document type, extract text, evaluate quality.

    Triggered after STORAGE_CONFIRMED state.
    Transitions to OCR_COMPLETE, OCR_PENDING (needs OCR fallback), or FAILED.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_extract_document(helper, self, upload_id, tenant_id, user_id))


async def _extract_document(helper: WorkerAsyncHelper, task, upload_id: str, tenant_id: str, user_id: str):
    session = await worker_loop.create_session(tenant_id, user_id, "api")
    async with helper.session_scope(session):
        lock_key = f"extraction:{upload_id}"
        redis = None
        try:
            # ── Redis extraction lock ─────────────────────────────
            # Prevent concurrent extraction workers for the same upload.
            import redis.asyncio as aioredis
            redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            locked = await redis.setnx(lock_key, "1")
            if not locked:
                logger.info("Extraction already in progress for %s, skipping", upload_id)
                return
            await redis.expire(lock_key, 600)  # 10 min TTL safety

            extract_repo = ExtractionRepository(session, tenant_id=tenant_id)
            ingest_repo = IngestionRepository(session, tenant_id=tenant_id)
            service = ExtractionService(
                extraction_repo=extract_repo,
                ingestion_repo=ingest_repo,
                event_bus=EventBus(),
                user=None,
                tenant_id=tenant_id,
            )

            upload = await ingest_repo.get_upload(upload_id, tenant_id)
            if not upload:
                logger.error("Upload not found for extraction: %s", upload_id)
                return

            state = coerce_ingestion_state(upload.ingestion_state)
            if state not in (
                IngestionState.OCR_PENDING,
                IngestionState.STORAGE_CONFIRMED,
                IngestionState.OCR_PROCESSING,
            ):
                logger.warning(
                    "Upload %s not in OCR-ready state (%s), skipping",
                    upload_id,
                    state.value,
                )
                return

            # ── Idempotency check: skip if pages already exist ───
            existing_pages = await extract_repo.count_pages(upload_id, tenant_id)
            if existing_pages > 0:
                logger.info(
                    "Extraction already completed for %s (%d pages exist). "
                    "Skipping extraction, advancing through state chain.",
                    upload_id, existing_pages,
                )
                # Advance through proper state chain:
                # STORAGE_CONFIRMED → OCR_PENDING → OCR_PROCESSING → OCR_COMPLETE
                if state == IngestionState.STORAGE_CONFIRMED:
                    await ingest_repo.update_state(upload_id, tenant_id, IngestionState.OCR_PENDING)
                    await session.commit()
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.OCR_PROCESSING)
                await session.commit()
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.OCR_COMPLETE)
                await session.commit()
                from workers.vectors import chunk_document_task
                chunk_document_task.delay(upload_id, tenant_id, user_id)
                return

            if state == IngestionState.STORAGE_CONFIRMED:
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.OCR_PENDING)
                await session.commit()
                state = IngestionState.OCR_PENDING
            if state == IngestionState.OCR_PENDING:
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.OCR_PROCESSING)
                await session.commit()

            # Run extraction
            result = await service.run_extraction(upload_id)

            # Evaluate quality
            quality = quality_evaluator.evaluate(result)
            logger.info("Extraction quality for %s: score=%.4f, acceptable=%s",
                         upload_id, quality.overall_score, quality.is_acceptable)

            # Handle quality result
            next_state = await service.handle_quality_result(upload_id, result, quality)
            await session.commit()

            if next_state == IngestionState.OCR_COMPLETE:
                logger.info("Extraction complete for %s (%d pages, %d chars)",
                             upload_id, result.total_pages, result.total_chars)
                # Dispatch chunking pipeline
                from workers.vectors import chunk_document_task
                chunk_document_task.delay(upload_id, tenant_id, user_id)
            elif next_state == IngestionState.OCR_PENDING:
                logger.info("Extraction needs OCR fallback for %s: %s",
                             upload_id, quality.rejection_reason)
            elif next_state == IngestionState.QUARANTINED:
                logger.warning("Extraction quarantined for %s: %s",
                                upload_id, quality.rejection_reason)

        except (EncryptedPDFError, CorruptedDocumentError) as exc:
            await session.rollback()
            logger.error("Extraction failed for %s: %s", upload_id, exc)
            try:
                ingest_repo = IngestionRepository(session, tenant_id=tenant_id)
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.FAILED, error=str(exc))
                await session.commit()
            except Exception:
                pass
        except Exception as exc:
            await session.rollback()
            error_msg = str(exc)
            # Handle unique constraint violation gracefully — pages exist from
            # a previous extraction attempt. Advance the workflow instead of
            # marking as failed.
            if "uq_page_per_upload" in error_msg or "unique constraint" in error_msg.lower():
                logger.warning(
                    "Duplicate page detected for %s (workflow race). "
                    "Pages already exist — advancing to OCR_COMPLETE.",
                    upload_id,
                )
                try:
                    ingest_repo = IngestionRepository(session, tenant_id=tenant_id)
                    await ingest_repo.update_state(
                        upload_id, tenant_id, IngestionState.OCR_COMPLETE
                    )
                    await session.commit()
                    from workers.vectors import chunk_document_task
                    chunk_document_task.delay(upload_id, tenant_id, user_id)
                except Exception:
                    pass
                return

            logger.error("Extraction error for %s: %s", upload_id, exc)
            retries = getattr(task.request, "retries", 0)
            if retries >= MAX_RETRIES:
                try:
                    ingest_repo = IngestionRepository(session, tenant_id=tenant_id)
                    await ingest_repo.update_state(
                        upload_id,
                        tenant_id,
                        IngestionState.FAILED,
                        error=str(exc),
                    )
                    await session.commit()
                    logger.error(
                        "Extraction failed permanently for %s after %d retries",
                        upload_id,
                        retries,
                    )
                    return
                except Exception:
                    pass
            raise
        finally:
            # ── Release extraction lock ───────────────────────────
            if redis:
                try:
                    await redis.delete(lock_key)
                    await redis.close()
                except Exception:
                    pass
