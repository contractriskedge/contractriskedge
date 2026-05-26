"""Vector ingestion Celery tasks — chunking, embedding generation, and re-embedding."""

from __future__ import annotations

import logging

from app.config import settings
from app.domains.ingestion.models import IngestionState, coerce_ingestion_state
from app.domains.ingestion.repository import IngestionRepository
from app.domains.extraction.repository import ExtractionRepository
from app.domains.vectors.chunking import chunking_service
from app.domains.vectors.embeddings import OpenAIEmbeddingProvider, EmbeddingRequest, embedding_registry
from app.domains.vectors.repository import VectorRepository
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


from workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="chunk_document",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def chunk_document_task(self, upload_id: str, tenant_id: str, user_id: str):
    """Chunk extracted pages into semantic chunks.

    Triggered after OCR_COMPLETE state.
    Transitions: OCR_COMPLETE -> CHUNKING_PENDING -> EMBEDDING_PENDING.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_chunk_document(helper, upload_id, tenant_id, user_id))


async def _chunk_document(helper: WorkerAsyncHelper, upload_id: str, tenant_id: str, user_id: str):
    session = await worker_loop.create_session(tenant_id, user_id, "api")
    async with helper.session_scope(session):
        try:
            ingest_repo = IngestionRepository(session, tenant_id=tenant_id)
            extract_repo = ExtractionRepository(session, tenant_id=tenant_id)
            vector_repo = VectorRepository(session, tenant_id=tenant_id)

            upload = await ingest_repo.get_upload(upload_id, tenant_id)
            if not upload:
                logger.error("Upload not found for chunking: %s", upload_id)
                return

            state = coerce_ingestion_state(upload.ingestion_state)
            if state == IngestionState.OCR_COMPLETE:
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.CHUNKING_PENDING)
                await session.commit()
            elif state == IngestionState.CHUNKING_PENDING:
                pass
            elif state == IngestionState.EMBEDDING_PENDING:
                logger.info("Upload %s already chunked, dispatching embeddings", upload_id)
                generate_embeddings_task.delay(upload_id, tenant_id, user_id)
                return
            else:
                logger.warning(
                    "Upload %s not in chunking-ready state (%s)",
                    upload_id,
                    state.value,
                )
                return

            # Get extracted pages
            pages = await extract_repo.get_pages_by_upload(upload_id, tenant_id)
            if not pages:
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.FAILED,
                                               error="No extracted pages found for chunking")
                await session.commit()
                return

            page_dicts = [{"page_number": p.page_number, "text": p.text} for p in pages]

            # Chunk
            chunks = chunking_service.chunk_pages(page_dicts, strategy="semantic")
            logger.info("Chunked upload %s: %d chunks", upload_id, len(chunks))

            # Store chunks
            db_chunks = await vector_repo.store_chunks_bulk(upload_id, tenant_id, chunks)
            await session.commit()

            # Transition to embedding pending
            await ingest_repo.update_state(upload_id, tenant_id, IngestionState.EMBEDDING_PENDING)
            await session.commit()

            # Dispatch embedding
            generate_embeddings_task.delay(upload_id, tenant_id, user_id)
            logger.info("Chunking complete for %s. Dispatched embedding.", upload_id)

        except Exception as exc:
            await session.rollback()
            logger.error("Chunking failed for %s: %s", upload_id, exc)
            try:
                ingest_repo = IngestionRepository(session, tenant_id=tenant_id)
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.FAILED, error=str(exc))
                await session.commit()
            except Exception:
                pass
            raise


@celery_app.task(
    bind=True,
    name="generate_embeddings",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def generate_embeddings_task(self, upload_id: str, tenant_id: str, user_id: str):
    """Generate embeddings for all chunks and store in pgvector.

    Triggered after CHUNKING_PENDING → EMBEDDING_PENDING.
    Transitions to ANALYSIS_PENDING or FAILED.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_generate_embeddings(helper, upload_id, tenant_id, user_id))


async def _generate_embeddings(helper: WorkerAsyncHelper, upload_id: str, tenant_id: str, user_id: str):
    session = await worker_loop.create_session(tenant_id, user_id, "api")
    async with helper.session_scope(session):
        try:
            ingest_repo = IngestionRepository(session, tenant_id=tenant_id)
            vector_repo = VectorRepository(session, tenant_id=tenant_id)

            upload = await ingest_repo.get_upload(upload_id, tenant_id)
            if not upload:
                logger.error("Upload not found for embedding: %s", upload_id)
                return

            state = coerce_ingestion_state(upload.ingestion_state)
            if state not in (IngestionState.EMBEDDING_PENDING, IngestionState.ANALYSIS_PENDING):
                logger.warning(
                    "Upload %s not in EMBEDDING_PENDING state (%s)",
                    upload_id,
                    state.value,
                )
                return
            if state == IngestionState.ANALYSIS_PENDING:
                logger.info("Upload %s embeddings already done", upload_id)
                return

            # Get pending chunks
            chunks = await vector_repo.get_pending_chunks(upload_id, tenant_id)
            if not chunks:
                logger.warning("No pending chunks for upload %s", upload_id)
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.ANALYSIS_PENDING)
                await session.commit()
                return

            # Initialize provider
            provider = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
            embedding_registry.register(provider)

            # Create embedding run
            run = await vector_repo.create_run(upload_id, tenant_id, "text-embedding-3-large", 1536)

            # Generate embeddings in batches
            total_tokens = 0
            total_cost = 0.0
            total_latency = 0
            chunks_embedded = 0

            for i in range(0, len(chunks), provider.MAX_BATCH_SIZE):
                batch = chunks[i:i + provider.MAX_BATCH_SIZE]
                requests = [EmbeddingRequest(text=c.text) for c in batch]

                try:
                    responses = await provider.embed_batch(requests)
                except Exception as exc:
                    logger.error("Embedding batch failed: %s", exc)
                    await vector_repo.record_failure(upload_id, tenant_id, "batch_failed", str(exc))
                    continue

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
                        chunks_embedded += 1
                        total_tokens += response.token_count
                        total_cost += response.cost_usd
                        total_latency += response.latency_ms

            # Complete run
            avg_latency = total_latency // max(chunks_embedded, 1)
            await vector_repo.complete_run(
                run_id=run.run_id,
                total_chunks=len(chunks),
                chunks_embedded=chunks_embedded,
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
                avg_latency_ms=avg_latency,
            )
            await session.commit()

            # Transition to analysis pending and dispatch AI analysis
            await ingest_repo.update_state(upload_id, tenant_id, IngestionState.ANALYSIS_PENDING)
            await session.commit()

            # Dispatch AI analysis
            from workers.ai_worker import analyze_contract_task
            analyze_contract_task.delay(upload_id, tenant_id, user_id, "full")

            logger.info(
                "Embeddings generated for %s: %d/%d chunks, %d tokens, $%.6f. AI analysis dispatched.",
                upload_id, chunks_embedded, len(chunks), total_tokens, total_cost,
            )

        except Exception as exc:
            await session.rollback()
            logger.error("Embedding failed for %s: %s", upload_id, exc)
            try:
                ingest_repo = IngestionRepository(session, tenant_id=tenant_id)
                await ingest_repo.update_state(upload_id, tenant_id, IngestionState.FAILED, error=str(exc))
                await session.commit()
            except Exception:
                pass
            raise
