"""Document ingestion module for the AI Contract Risk Analyzer.

Provides async document processing pipeline with Redis-backed Celery task queue,
PDF/DOCX text extraction, OCR fallback, clause segmentation, and semantic chunking.
"""

from ingestion.models import JobStatus, JobRecord, IngestionRequest
from ingestion.queue import IngestionQueue
from ingestion.tasks import process_document, celery_app

__all__ = [
    "JobStatus",
    "JobRecord",
    "IngestionRequest",
    "IngestionQueue",
    "process_document",
    "celery_app",
]
