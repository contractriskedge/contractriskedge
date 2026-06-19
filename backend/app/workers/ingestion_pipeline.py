"""Ingestion pipeline Celery tasks — document extraction, chunking, embedding, and finalization.

Each task handles one stage of the ingestion pipeline with retry logic,
tenant isolation, and structured logging.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.domains.ingestion.models import IngestionState
from app.domains.ingestion.repository import IngestionRepository
from app.domains.vectors.services.embedding_service import EmbeddingService
from app.integrations.storage.s3 import storage_service
from app.kernel.events.bus import EventBus

from workers.celery_app import celery_app
from workers.ingestion import TenantAwareTask
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


# ── Helper: Build Orchestrator ────────────────────────────────────────────────


async def _build_orchestrator(
    tenant_id: str,
    user_id: str,
) -> tuple[Any, Any, Any]:
    """Create a DB session and orchestrator using the shared worker loop engine."""
    from app.domains.ingestion.services.ingestion_orchestrator import (
        IngestionOrchestrator,
    )

    session = await worker_loop.create_session(tenant_id, user_id, "api")
    embedding_service = EmbeddingService(
        api_key=settings.openai_api_key,
        model=settings.default_embedding_model,
        tenant_id=tenant_id,
    )
    orchestrator = IngestionOrchestrator(
        session=session,
        embedding_service=embedding_service,
        event_bus=EventBus(),
        tenant_id=tenant_id,
    )
    return session, orchestrator


# ── Task 1: Extract Document ──────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    base=TenantAwareTask,
    name="ingestion.extract_document",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def extract_document_task(
    self,
    upload_id: str,
    tenant_id: str,
    user_id: str = "system",
    correlation_id: str = "",
):
    """Extract text from an uploaded document.

    Triggered after STORAGE_CONFIRMED state.
    Downloads file from MinIO, runs parser, evaluates quality.
    Transitions to OCR_COMPLETE, triggers OCR_PENDING, or FAILED.
    """
    return worker_loop.run(_extract_document_async(
        self, upload_id, tenant_id, user_id, correlation_id,
    ))


async def _extract_document_async(
    task,
    upload_id: str,
    tenant_id: str,
    user_id: str,
    correlation_id: str,
):
    session = None
    try:
        session, orchestrator = await _build_orchestrator(tenant_id, user_id)

        upload = await orchestrator.ingestion_repo.get_upload(upload_id, tenant_id)
        if not upload:
            logger.error("Upload not found for extraction: %s", upload_id)
            return

        if upload.ingestion_state not in (
            IngestionState.STORAGE_CONFIRMED,
            IngestionState.OCR_PENDING,
        ):
            logger.warning(
                "Upload %s not in extractable state (%s), skipping",
                upload_id, upload.ingestion_state.value,
            )
            return

        # Download file from storage
        file_data = await storage_service.download_fileobj(
            upload.storage_bucket or settings.s3_bucket or "contractrisk-documents",
            upload.storage_key or "",
        )

        # Run extraction via orchestrator (stages 3-4)
        await orchestrator._extract_document(
            upload_id=upload_id,
            file_data=file_data,
            content_type=upload.content_type,
            filename=upload.filename,
        )

        logger.info(
            "Extraction task completed",
            extra={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
            },
        )

    except Exception as exc:
        logger.error(
            "Extraction task failed",
            extra={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        raise
    finally:
        if session:
            await session.close()


# ── Task 2: Chunk Document ────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    base=TenantAwareTask,
    name="ingestion.chunk_document",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def chunk_document_task(
    self,
    upload_id: str,
    tenant_id: str,
    user_id: str = "system",
    correlation_id: str = "",
):
    """Split extracted pages into semantic chunks.

    Triggered after OCR_COMPLETE state.
    Transitions to EMBEDDING_PENDING or FAILED.
    """
    return worker_loop.run(_chunk_document_async(
        self, upload_id, tenant_id, user_id, correlation_id,
    ))


async def _chunk_document_async(
    task,
    upload_id: str,
    tenant_id: str,
    user_id: str,
    correlation_id: str,
):
    session = None
    try:
        session, orchestrator = await _build_orchestrator(tenant_id, user_id)

        upload = await orchestrator.ingestion_repo.get_upload(upload_id, tenant_id)
        if not upload:
            logger.error("Upload not found for chunking: %s", upload_id)
            return

        if upload.ingestion_state not in (
            IngestionState.OCR_COMPLETE,
            IngestionState.CHUNKING_PENDING,
        ):
            logger.warning(
                "Upload %s not in chunkable state (%s), skipping",
                upload_id, upload.ingestion_state.value,
            )
            return

        # Get extracted pages
        pages = await orchestrator.extraction_repo.get_pages_by_upload(upload_id, tenant_id)
        page_dicts = [
            {"page_number": p.page_number, "text": p.text}
            for p in pages
        ]

        # Chunk via orchestrator (stage 5)
        from app.domains.vectors.chunking import chunking_service, CHUNK_STRATEGY
        chunks = chunking_service.chunk_pages(page_dicts, strategy="semantic")

        # Store chunks
        for chunk in chunks:
            await orchestrator.vector_repo.store_chunk(
                upload_id=upload_id,
                tenant_id=tenant_id,
                chunk=chunk,
            )

        await orchestrator._transition_state(upload_id, IngestionState.EMBEDDING_PENDING)

        logger.info(
            "Chunking task completed",
            extra={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "chunks": len(chunks),
            },
        )

    except Exception as exc:
        logger.error(
            "Chunking task failed",
            extra={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        raise
    finally:
        if session:
            await session.close()


# ── Task 3: Generate Embeddings ───────────────────────────────────────────────


@celery_app.task(
    bind=True,
    base=TenantAwareTask,
    name="ingestion.generate_embeddings",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def generate_embeddings_task(
    self,
    upload_id: str,
    tenant_id: str,
    user_id: str = "system",
    correlation_id: str = "",
):
    """Generate vector embeddings for all chunks of a document.

    Triggered after EMBEDDING_PENDING state.
    Transitions to REVIEW_READY or FAILED.
    """
    return worker_loop.run(_generate_embeddings_async(
        self, upload_id, tenant_id, user_id, correlation_id,
    ))


async def _generate_embeddings_async(
    task,
    upload_id: str,
    tenant_id: str,
    user_id: str,
    correlation_id: str,
):
    session = None
    try:
        session, orchestrator = await _build_orchestrator(tenant_id, user_id)

        upload = await orchestrator.ingestion_repo.get_upload(upload_id, tenant_id)
        if not upload:
            logger.error("Upload not found for embedding: %s", upload_id)
            return

        if upload.ingestion_state not in (
            IngestionState.EMBEDDING_PENDING,
        ):
            logger.warning(
                "Upload %s not in embeddable state (%s), skipping",
                upload_id, upload.ingestion_state.value,
            )
            return

        # Get stored chunks
        db_chunks = await orchestrator.vector_repo.get_chunks_by_upload(upload_id, tenant_id)
        if not db_chunks:
            logger.error("No chunks found for embedding: %s", upload_id)
            return

        # Extract texts
        texts = [c.text for c in db_chunks]

        # Generate embeddings
        vectors = await orchestrator._embedding_service.generate_embeddings_batch(texts)

        # Store vectors
        chunks_embedded = 0
        total_tokens = 0
        for i, (chunk, vector) in enumerate(zip(db_chunks, vectors)):
            await orchestrator.vector_repo.update_embedding(
                chunk_id=str(chunk.chunk_id),
                tenant_id=tenant_id,
                embedding=vector,
                model=orchestrator._embedding_service.model,
                dimension=1536,
                token_count=chunk.token_count,
            )
            chunks_embedded += 1
            total_tokens += chunk.token_count

        # Hand off to AI analysis — review is created when analysis completes
        user_id = user_id or "system"
        upload = await orchestrator.ingestion_repo.get_upload(upload_id, tenant_id)
        if upload and upload.ingestion_state != IngestionState.ANALYSIS_PENDING:
            await orchestrator._transition_state(
                upload_id, IngestionState.ANALYSIS_PENDING, upload=upload,
            )
        await session.commit()

        from workers.ai_worker import analyze_contract_task
        analyze_contract_task.delay(upload_id, tenant_id, user_id, "full")

        logger.info(
            "Embedding task completed — AI analysis dispatched",
            extra={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "chunks_embedded": chunks_embedded,
                "total_tokens": total_tokens,
            },
        )

    except Exception as exc:
        logger.error(
            "Embedding task failed",
            extra={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        raise
    finally:
        if session:
            await session.close()


# ── Task 4: Finalize Ingestion ────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    base=TenantAwareTask,
    name="ingestion.finalize",
    queue="ingestion",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def finalize_ingestion_task(
    self,
    upload_id: str,
    tenant_id: str,
    user_id: str = "system",
    correlation_id: str = "",
):
    """Ensure AI analysis runs and review handoff completes.

    Legacy task name retained for compatibility — no longer marks REVIEW_READY
    before a review record exists.
    """
    return worker_loop.run(_finalize_ingestion_async(
        self, upload_id, tenant_id, user_id, correlation_id,
    ))


async def _finalize_ingestion_async(
    task,
    upload_id: str,
    tenant_id: str,
    user_id: str,
    correlation_id: str,
):
    session = None
    try:
        session, orchestrator = await _build_orchestrator(tenant_id, user_id)

        await orchestrator._dispatch_ai_analysis(upload_id)
        await session.commit()

        logger.info(
            "Finalize task dispatched AI analysis",
            extra={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
            },
        )

    except Exception as exc:
        logger.error(
            "Finalize task failed",
            extra={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        raise
    finally:
        if session:
            await session.close()
