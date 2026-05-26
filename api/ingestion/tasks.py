"""Celery background tasks for document ingestion processing.

Defines the distributed task workers that handle document extraction,
clause segmentation, and chunking with automatic retry logic
(3 retries with exponential backoff).
"""

from __future__ import annotations

import logging
import os
import time
import traceback
from typing import Any, Dict, Optional

from celery import Celery, Task
from celery.exceptions import MaxRetriesExceededError
from celery.signals import task_failure, task_success
from kombu import Queue as KombuQueue

from ingestion.models import (
    DocumentChunk,
    ExtractionMethod,
    JobRecord,
    JobStatus,
    PageExtraction,
)

logger = logging.getLogger(__name__)

# ── Celery Application Setup ────────────────────────────────────────────────

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "contract_risk_ingestion",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_queues=[
        KombuQueue("ingestion", routing_key="ingestion.#"),
        KombuQueue("extraction", routing_key="extraction.#"),
        KombuQueue("ocr", routing_key="ocr.#"),
    ],
    task_routes={
        "ingestion.tasks.process_document": {"queue": "ingestion"},
        "ingestion.tasks.extract_text": {"queue": "extraction"},
        "ingestion.tasks.run_ocr": {"queue": "ocr"},
    },
    task_default_queue="ingestion",
    task_default_exchange="ingestion",
    task_default_routing_key="ingestion.default",
)

# ── Retry Configuration ─────────────────────────────────────────────────────

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 60  # seconds
COUNTDOWN_POLICY = [RETRY_BACKOFF_BASE * (2**i) for i in range(MAX_RETRIES)]
# Results in: 60s, 120s, 240s


class DocumentProcessingError(Exception):
    """Base exception for document processing failures."""


class ExtractionError(DocumentProcessingError):
    """Raised when text extraction fails."""


class OCRError(DocumentProcessingError):
    """Raised when OCR processing fails."""


def get_ingestion_queue() -> Any:
    """Get the IngestionQueue instance (lazy import to avoid circular deps).

    Returns:
        An IngestionQueue instance connected via Redis URL.
    """
    from ingestion.queue import IngestionQueue

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return IngestionQueue(redis_url=redis_url)


@celery_app.task(
    bind=True,
    name="process_document",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(DocumentProcessingError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def process_document(
    self: Task,
    job_id: str,
    document_path: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Main Celery task for processing a document through the full pipeline.

    Orchestrates the extraction, clause segmentation, and chunking
    stages. Automatically retries on failure with exponential backoff.

    Args:
        self: Celery task instance (injected by bind=True).
        job_id: The ingestion job identifier.
        document_path: Absolute path to the uploaded document file.
        options: Optional extraction options dict.

    Returns:
        A dict with processing results including pages, clauses, and chunks.

    Raises:
        ExtractionError: If document extraction fails after all retries.
    """
    options = options or {}
    queue = get_ingestion_queue()
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Mark as processing
        loop.run_until_complete(
            queue.update_status(
                job_id,
                JobStatus.PROCESSING,
                progress=5.0,
            )
        )

        # Step 1: Determine file type and extract text
        loop.run_until_complete(
            queue.update_status(job_id, JobStatus.PROCESSING, progress=10.0)
        )

        file_ext = os.path.splitext(document_path)[1].lower()
        logger.info(
            "Processing document %s (job %s, type: %s)",
            document_path,
            job_id,
            file_ext,
        )

        # Step 2: Extract text based on file type
        if file_ext == ".pdf":
            pages = _extract_pdf(document_path, options)
        elif file_ext in (".docx", ".doc"):
            pages = _extract_docx(document_path, options)
        else:
            raise ExtractionError(f"Unsupported file type: {file_ext}")

        if not pages:
            raise ExtractionError(f"No text extracted from {document_path}")

        loop.run_until_complete(
            queue.update_status(
                job_id,
                JobStatus.PROCESSING,
                progress=40.0,
                extraction_results=pages,
            )
        )

        # Step 3: Segment into clauses
        clauses = _segment_clauses(pages)
        loop.run_until_complete(
            queue.update_status(
                job_id,
                JobStatus.PROCESSING,
                progress=65.0,
                clauses=clauses,
            )
        )

        # Step 4: Create semantic chunks
        chunks = _create_chunks(job_id, pages, clauses)
        loop.run_until_complete(
            queue.update_status(
                job_id,
                JobStatus.PROCESSING,
                progress=85.0,
                chunks=chunks,
            )
        )

        # Step 5: Index chunks in Pinecone vector store
        pinecone_indexed = 0
        pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if pinecone_api_key and openai_api_key and chunks:
            try:
                from rag.vector_store import PineconeVectorStore
                from rag.embedding import EmbeddingPipeline

                vector_store = PineconeVectorStore(
                    api_key=pinecone_api_key,
                    environment=os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws"),
                    index_name=os.getenv("PINECONE_INDEX", "contract-chunks"),
                )
                embedding = EmbeddingPipeline(api_key=openai_api_key)

                # Extract texts and prepare vectors
                chunk_texts = [c.text for c in chunks if c.text.strip()]
                if chunk_texts:
                    embeddings = loop.run_until_complete(
                        embedding.embed_texts(chunk_texts)
                    )
                    vectors = []
                    for chunk, emb in zip(chunks, embeddings):
                        if emb:
                            vectors.append((
                                chunk.chunk_id,
                                emb,
                                {
                                    "text": chunk.text[:2000],
                                    "document_id": chunk.document_id,
                                    "page_number": chunk.page_number,
                                    "clause_type": chunk.clause_type or "unknown",
                                    "tenant_id": getattr(chunk, "tenant_id", "default"),
                                },
                            ))

                    if vectors:
                        pinecone_indexed = loop.run_until_complete(
                            vector_store.upsert_vectors(
                                vectors=vectors,
                                tenant_id="default",
                            )
                        )
                        logger.info(
                            "Indexed %d chunks in Pinecone for job %s",
                            pinecone_indexed,
                            job_id,
                        )
            except Exception as exc:
                logger.warning(
                    "Pinecone indexing skipped for job %s: %s",
                    job_id,
                    exc,
                )

        # Step 6: Mark as complete
        full_text = " ".join(p.text for p in pages)
        result = {
            "job_id": job_id,
            "status": JobStatus.DONE.value,
            "total_pages": len(pages),
            "total_clauses": len(clauses),
            "total_chunks": len(chunks),
            "total_characters": len(full_text),
            "extraction_methods": list(set(p.method.value for p in pages)),
        }

        loop.run_until_complete(
            queue.update_status(
                job_id,
                JobStatus.DONE,
                progress=100.0,
            )
        )

        logger.info(
            "Document processing complete for job %s: %d pages, %d clauses, %d chunks",
            job_id,
            len(pages),
            len(clauses),
            len(chunks),
        )
        return result

    except DocumentProcessingError as exc:
        logger.error(
            "Document processing failed for job %s: %s",
            job_id,
            str(exc),
            exc_info=True,
        )
        try:
            self.retry(
                exc=exc,
                countdown=COUNTDOWN_POLICY[self.request.retries],
            )
        except MaxRetriesExceededError:
            loop.run_until_complete(
                queue.update_status(
                    job_id,
                    JobStatus.FAILED,
                    error_message=str(exc),
                    progress=0.0,
                )
            )
            raise
        except Exception:
            # If retry itself fails, mark as failed
            loop.run_until_complete(
                queue.update_status(
                    job_id,
                    JobStatus.FAILED,
                    error_message=str(exc),
                    progress=0.0,
                )
            )
            raise
    except Exception as exc:
        logger.error(
            "Unexpected error processing job %s: %s",
            job_id,
            str(exc),
            exc_info=True,
        )
        loop.run_until_complete(
            queue.update_status(
                job_id,
                JobStatus.FAILED,
                error_message=f"Unexpected error: {exc}",
            )
        )
        raise ExtractionError(str(exc)) from exc
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="extract_text",
    max_retries=MAX_RETRIES,
    acks_late=True,
)
def extract_text(
    self: Task,
    document_path: str,
    options: Optional[Dict[str, Any]] = None,
) -> list[Dict[str, Any]]:
    """Standalone extraction task for PDF/DOCX files.

    Can be called independently or composed as part of the larger
    processing pipeline.

    Args:
        self: Celery task instance.
        document_path: Path to the document file.
        options: Optional extraction options.

    Returns:
        List of page extraction dicts.

    Raises:
        ExtractionError: If extraction fails.
    """
    options = options or {}
    file_ext = os.path.splitext(document_path)[1].lower()

    try:
        if file_ext == ".pdf":
            pages = _extract_pdf(document_path, options)
        elif file_ext in (".docx", ".doc"):
            pages = _extract_docx(document_path, options)
        else:
            raise ExtractionError(f"Unsupported file type: {file_ext}")

        return [p.model_dump() for p in pages]
    except Exception as exc:
        logger.error("Extraction failed for %s: %s", document_path, exc)
        self.retry(exc=exc, countdown=COUNTDOWN_POLICY[self.request.retries])
        raise


@celery_app.task(
    bind=True,
    name="run_ocr",
    max_retries=MAX_RETRIES,
    acks_late=True,
)
def run_ocr(
    self: Task,
    document_path: str,
    options: Optional[Dict[str, Any]] = None,
) -> list[Dict[str, Any]]:
    """OCR processing task using AWS Textract.

    Args:
        self: Celery task instance.
        document_path: Path to the document image/PDF.
        options: Optional OCR options.

    Returns:
        List of page extraction dicts with OCR results.
    """
    options = options or {}
    try:
        from ingestion.extractors.ocr_pipeline import OcrPipeline

        pipeline = OcrPipeline()
        pages = pipeline.process_document(document_path, options)
        return [p.model_dump() for p in pages]
    except Exception as exc:
        logger.error("OCR failed for %s: %s", document_path, exc)
        self.retry(exc=exc, countdown=COUNTDOWN_POLICY[self.request.retries])
        raise


def _extract_pdf(
    document_path: str,
    options: Dict[str, Any],
) -> list[PageExtraction]:
    """Extract text from a PDF document.

    Uses PyMuPDF as the primary extractor with Apache Tika as fallback.

    Args:
        document_path: Path to the PDF file.
        options: Extraction options.

    Returns:
        List of PageExtraction objects.

    Raises:
        ExtractionError: If all extraction methods fail.
    """
    from ingestion.extractors.pdf_extractor import PdfExtractor

    extractor = PdfExtractor()
    pages = extractor.extract(document_path, options)

    if not pages:
        raise ExtractionError(
            f"PDF extraction returned no results for {document_path}"
        )

    return pages


def _extract_docx(
    document_path: str,
    options: Dict[str, Any],
) -> list[PageExtraction]:
    """Extract text from a DOCX document.

    Args:
        document_path: Path to the DOCX file.
        options: Extraction options.

    Returns:
        List of PageExtraction objects.

    Raises:
        ExtractionError: If extraction fails.
    """
    from ingestion.extractors.docx_extractor import DocxExtractor

    extractor = DocxExtractor()
    pages = extractor.extract(document_path, options)

    if not pages:
        raise ExtractionError(
            f"DOCX extraction returned no results for {document_path}"
        )

    return pages


def _segment_clauses(pages: list[PageExtraction]) -> list[Any]:
    """Segment extracted text into clauses using ML-based detection.

    Args:
        pages: List of extracted page content.

    Returns:
        List of ClauseSegment objects.
    """
    from ingestion.extractors.clause_segmenter import ClauseSegmenter

    segmenter = ClauseSegmenter()
    return segmenter.segment(pages)


def _create_chunks(
    document_id: str,
    pages: list[PageExtraction],
    clauses: list[Any],
) -> list[DocumentChunk]:
    """Create semantic chunks from extracted text and clauses.

    Args:
        document_id: The document identifier.
        pages: Extracted page content.
        clauses: Identified clause segments.

    Returns:
        List of DocumentChunk objects.
    """
    from ingestion.chunker import SemanticChunker

    chunker = SemanticChunker()
    return chunker.chunk(document_id, pages, clauses)


# ── Signal Handlers ─────────────────────────────────────────────────────────


@task_success.connect(sender=process_document)
def on_process_document_success(sender: Any, result: Dict[str, Any], **kwargs: Any) -> None:
    """Handle successful document processing."""
    job_id = result.get("job_id", "unknown")
    logger.info("Process document task succeeded for job %s", job_id)


@task_failure.connect(sender=process_document)
def on_process_document_failure(
    sender: Any,
    task_id: str,
    exception: Exception,
    **kwargs: Any,
) -> None:
    """Handle failed document processing."""
    logger.error(
        "Process document task %s failed: %s",
        task_id,
        exception,
    )
