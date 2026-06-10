"""Redispatch ingestion pipeline Celery tasks for stuck or resumed uploads."""

from __future__ import annotations

import logging

from app.domains.ingestion.models import IngestionState

logger = logging.getLogger(__name__)

# States where a worker may have died mid-step; safe to re-queue the next task.
_REDISPATCH_EXTRACT = frozenset({
    IngestionState.STORAGE_CONFIRMED,
    IngestionState.OCR_PENDING,
    IngestionState.OCR_PROCESSING,
})
_REDISPATCH_CHUNK = frozenset({
    IngestionState.OCR_COMPLETE,
    IngestionState.CHUNKING_PENDING,
})
_REDISPATCH_EMBED = frozenset({
    IngestionState.EMBEDDING_PENDING,
})
_REDISPATCH_VALIDATE = frozenset({
    IngestionState.VALIDATING,
    IngestionState.VALIDATED,
    IngestionState.UPLOADED,
})


def redispatch_ingestion(upload_id: str, tenant_id: str, user_id: str, state: IngestionState) -> str | None:
    """Queue the appropriate Celery task for *state*. Returns a short action label."""
    if state in _REDISPATCH_EXTRACT:
        from workers.extraction import extract_document_task

        extract_document_task.delay(upload_id, tenant_id, user_id)
        logger.info("Redispatched extract_document for %s (state=%s)", upload_id, state.value)
        return "extract_document"

    if state in _REDISPATCH_CHUNK:
        from workers.vectors import chunk_document_task

        chunk_document_task.delay(upload_id, tenant_id, user_id)
        logger.info("Redispatched chunk_document for %s (state=%s)", upload_id, state.value)
        return "chunk_document"

    if state in _REDISPATCH_EMBED:
        from workers.vectors import generate_embeddings_task

        generate_embeddings_task.delay(upload_id, tenant_id, user_id)
        logger.info("Redispatched generate_embeddings for %s (state=%s)", upload_id, state.value)
        return "generate_embeddings"

    if state == IngestionState.VALIDATED:
        from workers.ingestion import confirm_storage_task

        confirm_storage_task.delay(upload_id, tenant_id, user_id)
        logger.info("Redispatched confirm_storage for %s", upload_id)
        return "confirm_storage"

    if state == IngestionState.UPLOADED:
        from workers.ingestion_tasks import ingest_document

        ingest_document.delay(upload_id, tenant_id, user_id)
        logger.info("Redispatched ingest_document for %s (state=%s)", upload_id, state.value)
        return "ingest_document"

    if state == IngestionState.VALIDATING:
        from workers.ingestion import validate_upload_task

        validate_upload_task.delay(upload_id, tenant_id, user_id)
        logger.info("Redispatched validate_upload for %s (state=%s)", upload_id, state.value)
        return "validate_upload"

    if state == IngestionState.ANALYSIS_PENDING:
        from workers.ai_worker import analyze_contract_task

        analyze_contract_task.delay(upload_id, tenant_id, user_id, "full")
        logger.info("Redispatched analyze_contract for %s", upload_id)
        return "analyze_contract"

    return None
