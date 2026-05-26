"""Production-grade document ingestion orchestration pipeline.

Orchestrates the full lifecycle: upload → store → extract → OCR fallback
→ chunk → embed → index → emit events. Enforces tenant isolation,
deduplication, retry logic, and comprehensive observability.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Callable, Awaitable

from app.config import settings
from app.domains.ingestion.models import IngestionState, UploadSession, coerce_ingestion_state
from app.domains.ingestion.repository import IngestionRepository
from app.domains.ingestion.exceptions import (
    UploadNotFoundError,
    IngestionStateTransitionError,
    FileTypeNotAllowedError,
    FileTooLargeError,
    ChecksumMismatchError,
    StorageUploadError,
    StorageDownloadError,
    IngestionRetryLimitExceededError,
)
from app.domains.ingestion.security import (
    validate_extension,
    validate_content_type,
    validate_file_size,
    validate_filename_safety,
    validate_magic_bytes,
    FileValidationError,
)
from app.domains.ingestion.events import (
    UploadInitiated,
    UploadCompleted,
    UploadFailed,
    IngestionStatusChanged,
)
from app.domains.extraction.repository import ExtractionRepository
from app.domains.extraction.service import ExtractionService
from app.domains.extraction.quality import quality_evaluator
from app.domains.extraction.parsers import parser_registry
from app.domains.extraction.normalizer import normalize_text
from app.domains.extraction.models import ExtractionMethod
from app.domains.vectors.chunking import chunking_service, ChunkData
from app.domains.vectors.repository import VectorRepository
from app.domains.vectors.models import EmbeddingStatus
from app.domains.vectors.services.embedding_service import EmbeddingService
from app.integrations.storage.s3 import storage_service, StorageServiceError
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_FILE_SIZE: int = 100_000_000  # 100 MB
MAX_RETRIES: int = 3
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt"}
DEFAULT_STORAGE_BUCKET: str = "contractrisk-documents"
CHUNK_STRATEGY: str = "semantic"


# ── Exceptions ────────────────────────────────────────────────────────────────


class IngestionOrchestrationError(Exception):
    """Base exception for ingestion orchestration failures."""


class DuplicateUploadError(IngestionOrchestrationError):
    """Raised when a duplicate upload is detected via checksum."""


class MimeTypeValidationError(IngestionOrchestrationError):
    """Raised when MIME type is not supported."""


class FileSizeValidationError(IngestionOrchestrationError):
    """Raised when file exceeds size limit."""


class ExtractionFailedError(IngestionOrchestrationError):
    """Raised when text extraction fails."""


class OcrFallbackFailedError(IngestionOrchestrationError):
    """Raised when OCR fallback also fails."""


class ChunkingFailedError(IngestionOrchestrationError):
    """Raised when document chunking fails."""


class EmbeddingFailedError(IngestionOrchestrationError):
    """Raised when embedding generation fails."""


# ── Event Hooks ───────────────────────────────────────────────────────────────

"""
Event hooks for future websocket progress updates.

Register callbacks via ``IngestionOrchestrator.on()``::

    async def on_progress(event: IngestionProgressEvent):
        await websocket.send_json(event.data)

    orchestrator.on("progress", on_progress)
"""


@dataclass
class IngestionProgressEvent:
    """Payload emitted at each pipeline stage for progress tracking."""
    upload_id: str
    tenant_id: str
    correlation_id: str
    stage: str  # "upload", "extract", "ocr", "chunk", "embed", "index", "complete", "fail"
    status: str  # "started", "in_progress", "completed", "failed"
    message: str = ""
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


ProgressHandler = Callable[[IngestionProgressEvent], Awaitable[None]]


# ── Ingestion Metrics ─────────────────────────────────────────────────────────


@dataclass
class IngestionMetrics:
    """Observability metrics for a full ingestion pipeline run."""
    correlation_id: str = ""
    total_duration_ms: int = 0
    storage_upload_ms: int = 0
    extraction_ms: int = 0
    ocr_ms: int = 0
    chunking_ms: int = 0
    embedding_ms: int = 0
    indexing_ms: int = 0
    total_chunks: int = 0
    total_tokens: int = 0
    total_pages: int = 0
    file_size_bytes: int = 0
    content_type: str = ""
    ocr_required: bool = False
    retry_count: int = 0
    success: bool = False


# ── Ingestion Orchestrator ────────────────────────────────────────────────────


class IngestionOrchestrator:
    """Orchestrates the full document ingestion pipeline.

    Pipeline stages:
        1. ``validate`` — MIME type, file size, extension, magic bytes
        2. ``store`` — Upload to MinIO/S3, compute checksum, detect duplicates
        3. ``extract`` — Extract text via PyMuPDF (direct) or python-docx
        4. ``ocr_fallback`` — If extraction quality is low, run OCRmyPDF + Tesseract
        5. ``chunk`` — Split extracted text into semantic chunks
        6. ``embed`` — Generate vector embeddings via EmbeddingService
        7. ``index`` — Store vectors in pgvector, update ingestion state
        8. ``complete`` — Emit events and metrics

    Tenant isolation is enforced at every stage. All DB writes are transactional
    via the injected SQLAlchemy session.

    Usage::

        orchestrator = IngestionOrchestrator(
            session=session,
            embedding_service=embedding_service,
            event_bus=event_bus,
            user=user,
            tenant_id=tenant_id,
        )
        result = await orchestrator.run_pipeline(
            upload_id=upload_id,
            file_data=file_bytes,
            filename="contract.pdf",
            content_type="application/pdf",
        )
    """

    def __init__(
        self,
        session: Any,  # AsyncSession
        embedding_service: EmbeddingService,
        event_bus: Optional[EventBus] = None,
        user: Optional[UserContext] = None,
        tenant_id: str = "",
    ) -> None:
        """Initialize the ingestion orchestrator.

        Args:
            session: Async SQLAlchemy session (tenant-scoped).
            embedding_service: Service for generating vector embeddings.
            event_bus: Optional domain event bus for emitting lifecycle events.
            user: Authenticated user context.
            tenant_id: Tenant UUID string. **REQUIRED** for tenant isolation.
        """
        self._session = session
        self._embedding_service = embedding_service
        self._event_bus = event_bus or EventBus()
        self._user = user
        self._tenant_id = tenant_id
        self._progress_handlers: list[ProgressHandler] = []

        # Repositories (lazy-init)
        self._ingestion_repo: Optional[IngestionRepository] = None
        self._extraction_repo: Optional[ExtractionRepository] = None
        self._vector_repo: Optional[VectorRepository] = None

        # Extraction service (lazy-init)
        self._extraction_service: Optional[ExtractionService] = None

        if not tenant_id:
            logger.warning("IngestionOrchestrator initialized without tenant_id")

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def ingestion_repo(self) -> IngestionRepository:
        if self._ingestion_repo is None:
            self._ingestion_repo = IngestionRepository(self._session, tenant_id=self._tenant_id)
        return self._ingestion_repo

    @property
    def extraction_repo(self) -> ExtractionRepository:
        if self._extraction_repo is None:
            self._extraction_repo = ExtractionRepository(self._session, tenant_id=self._tenant_id)
        return self._extraction_repo

    @property
    def vector_repo(self) -> VectorRepository:
        if self._vector_repo is None:
            self._vector_repo = VectorRepository(self._session, tenant_id=self._tenant_id)
        return self._vector_repo

    @property
    def extraction_service(self) -> ExtractionService:
        if self._extraction_service is None:
            self._extraction_service = ExtractionService(
                extraction_repo=self.extraction_repo,
                ingestion_repo=self.ingestion_repo,
                event_bus=self._event_bus,
                user=self._user,
                tenant_id=self._tenant_id,
            )
        return self._extraction_service

    # ── Event Hooks ───────────────────────────────────────────────────────

    def on(self, handler: ProgressHandler) -> None:
        """Register a progress event handler (e.g., for websocket updates)."""
        self._progress_handlers.append(handler)

    async def _emit_progress(
        self,
        upload_id: str,
        stage: str,
        status: str,
        message: str = "",
        data: Optional[dict] = None,
    ) -> None:
        """Emit a progress event to all registered handlers (non-blocking)."""
        event = IngestionProgressEvent(
            upload_id=upload_id,
            tenant_id=self._tenant_id,
            correlation_id=str(uuid.uuid4()),
            stage=stage,
            status=status,
            message=message,
            data=data or {},
        )
        for handler in self._progress_handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.warning("Progress handler failed: %s", exc)

    # ── Main Pipeline ─────────────────────────────────────────────────────

    async def run_pipeline(
        self,
        upload_id: str,
        file_data: bytes,
        filename: str,
        content_type: str,
        correlation_id: Optional[str] = None,
    ) -> IngestionMetrics:
        """Run the full ingestion pipeline for a single uploaded document.

        Args:
            upload_id: The upload session UUID.
            file_data: Raw file bytes from storage.
            filename: Original filename (for extension detection).
            content_type: Declared MIME type.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            ``IngestionMetrics`` with timing and result data.

        Raises:
            UploadNotFoundError: If the upload session does not exist.
            MimeTypeValidationError: If the file type is unsupported.
            FileSizeValidationError: If the file exceeds size limits.
            ExtractionFailedError: If text extraction fails.
            EmbeddingFailedError: If embedding generation fails.
            IngestionOrchestrationError: For other pipeline failures.
        """
        metrics = IngestionMetrics(
            correlation_id=correlation_id or str(uuid.uuid4()),
            file_size_bytes=len(file_data),
            content_type=content_type,
        )
        overall_start = time.monotonic()

        logger.info(
            "Ingestion pipeline started",
            extra={
                "upload_id": upload_id,
                "tenant_id": self._tenant_id,
                "correlation_id": metrics.correlation_id,
                "filename": filename,
                "content_type": content_type,
                "file_size": len(file_data),
            },
        )

        try:
            # ── Stage 1: Validate ─────────────────────────────────
            await self._emit_progress(upload_id, "validate", "started")
            await self._validate_upload(upload_id, filename, content_type, file_data)
            await self._emit_progress(upload_id, "validate", "completed")

            # ── Stage 2: Store ────────────────────────────────────
            await self._emit_progress(upload_id, "store", "started")
            store_start = time.monotonic()
            await self._store_file(upload_id, file_data, content_type, filename)
            metrics.storage_upload_ms = int((time.monotonic() - store_start) * 1000)
            await self._emit_progress(upload_id, "store", "completed")

            # ── Stage 3: Extract text ─────────────────────────────
            await self._emit_progress(upload_id, "extract", "started")
            extract_start = time.monotonic()
            extracted = await self._extract_document(upload_id, file_data, content_type, filename)
            metrics.extraction_ms = int((time.monotonic() - extract_start) * 1000)
            metrics.total_pages = len(extracted.get("pages", []))
            await self._emit_progress(upload_id, "extract", "completed", data={"pages": metrics.total_pages})

            # ── Stage 4: OCR fallback if needed ───────────────────
            if extracted.get("ocr_required", False):
                await self._emit_progress(upload_id, "ocr", "started")
                ocr_start = time.monotonic()
                extracted = await self._ocr_fallback(upload_id, file_data, filename)
                metrics.ocr_ms = int((time.monotonic() - ocr_start) * 1000)
                metrics.ocr_required = True
                await self._emit_progress(upload_id, "ocr", "completed", data={"pages": len(extracted.get("pages", []))})

            # ── Stage 5: Chunk ────────────────────────────────────
            await self._emit_progress(upload_id, "chunk", "started")
            chunk_start = time.monotonic()
            chunks = await self._chunk_document(upload_id, extracted)
            metrics.chunking_ms = int((time.monotonic() - chunk_start) * 1000)
            metrics.total_chunks = len(chunks)
            await self._emit_progress(upload_id, "chunk", "completed", data={"chunks": len(chunks)})

            # ── Stage 6: Generate embeddings ──────────────────────
            await self._emit_progress(upload_id, "embed", "started")
            embed_start = time.monotonic()
            embed_result = await self._generate_embeddings(upload_id, chunks)
            metrics.embedding_ms = int((time.monotonic() - embed_start) * 1000)
            metrics.total_tokens = embed_result.get("total_tokens", 0)
            await self._emit_progress(upload_id, "embed", "completed", data=embed_result)

            # ── Stage 7: Dispatch AI analysis ─────────────────────
            await self._emit_progress(upload_id, "analyze", "started")
            analyze_start = time.monotonic()
            await self._dispatch_ai_analysis(upload_id)
            metrics.indexing_ms = int((time.monotonic() - analyze_start) * 1000)
            await self._emit_progress(upload_id, "analyze", "dispatched")

            # ── Stage 8: Ingestion handoff complete ───────────────
            metrics.total_duration_ms = int((time.monotonic() - overall_start) * 1000)
            metrics.success = True

            await self._emit_progress(upload_id, "complete", "completed", data={
                "total_duration_ms": metrics.total_duration_ms,
                "total_chunks": metrics.total_chunks,
                "total_tokens": metrics.total_tokens,
                "next_stage": "ai_analysis",
            })

            await self._event_bus.emit(IngestionStatusChanged(
                tenant_id=self._tenant_id,
                actor_id=self._user.id if self._user else "system",
                data={
                    "upload_id": upload_id,
                    "state": str(IngestionState.ANALYSIS_PENDING),
                    "correlation_id": metrics.correlation_id,
                    "metrics": {
                        "total_duration_ms": metrics.total_duration_ms,
                        "total_chunks": metrics.total_chunks,
                        "total_tokens": metrics.total_tokens,
                        "total_pages": metrics.total_pages,
                        "ocr_required": metrics.ocr_required,
                    },
                },
            ))

            logger.info(
                "Ingestion pipeline handed off to AI analysis",
                extra={
                    "upload_id": upload_id,
                    "tenant_id": self._tenant_id,
                    "correlation_id": metrics.correlation_id,
                    "total_duration_ms": metrics.total_duration_ms,
                    "total_chunks": metrics.total_chunks,
                    "total_tokens": metrics.total_tokens,
                    "total_pages": metrics.total_pages,
                    "ocr_required": metrics.ocr_required,
                    "file_size_bytes": metrics.file_size_bytes,
                },
            )

        except Exception as exc:
            metrics.total_duration_ms = int((time.monotonic() - overall_start) * 1000)
            metrics.success = False
            await self._handle_pipeline_failure(upload_id, exc, metrics)
            raise

        return metrics

    # ── Stage 1: Validation ───────────────────────────────────────────────

    async def _validate_upload(
        self,
        upload_id: str,
        filename: str,
        content_type: str,
        file_data: bytes,
    ) -> None:
        """Validate file type, size, extension, and magic bytes.

        Raises:
            MimeTypeValidationError: If type/extension is unsupported.
            FileSizeValidationError: If file exceeds max size.
        """
        # Validate extension
        try:
            detected_type = validate_extension(filename)
        except FileValidationError as exc:
            raise MimeTypeValidationError(str(exc)) from exc

        # Validate declared content type matches detected type
        if detected_type != content_type:
            raise MimeTypeValidationError(
                f"Declared content type '{content_type}' does not match "
                f"detected type '{detected_type}' for extension"
            )

        # Validate MIME type
        try:
            validate_content_type(content_type)
        except FileValidationError as exc:
            raise MimeTypeValidationError(str(exc)) from exc

        # Validate file size
        try:
            validate_file_size(len(file_data))
        except FileValidationError as exc:
            raise FileSizeValidationError(str(exc)) from exc

        # Validate magic bytes
        try:
            validate_magic_bytes(file_data, content_type)
        except FileValidationError as exc:
            raise MimeTypeValidationError(str(exc)) from exc

        # Update state to VALIDATING -> VALIDATED
        upload = await self.ingestion_repo.get_upload(upload_id, self._tenant_id)
        await self._transition_state(upload_id, IngestionState.VALIDATING, upload=upload)
        await self._transition_state(upload_id, IngestionState.VALIDATED, upload=upload)

        logger.info(
            "Upload validated",
            extra={
                "upload_id": upload_id,
                "tenant_id": self._tenant_id,
                "content_type": content_type,
                "file_size": len(file_data),
            },
        )

    # ── Stage 2: Storage ─────────────────────────────────────────────────

    async def _store_file(
        self,
        upload_id: str,
        file_data: bytes,
        content_type: str,
        filename: str,
    ) -> str:
        """Store file in MinIO/S3 and compute checksum.

        Detects duplicate uploads via SHA-256 checksum.

        Returns:
            The storage object key.

        Raises:
            DuplicateUploadError: If a file with identical checksum exists.
            StorageUploadError: If the storage operation fails.
        """
        # Compute server-side checksum
        server_checksum = hashlib.sha256(file_data).hexdigest()

        # Check for duplicates within the same tenant
        duplicate = await self._find_duplicate(upload_id, server_checksum)
        if duplicate:
            raise DuplicateUploadError(
                f"Duplicate upload detected: file with checksum "
                f"{server_checksum[:12]}... already exists as upload {duplicate}"
            )

        # Build storage key and upload
        bucket = settings.s3_bucket or DEFAULT_STORAGE_BUCKET
        storage_key = storage_service.build_object_key(self._tenant_id, filename)

        try:
            await storage_service.ensure_bucket(bucket)
            await storage_service.upload_fileobj(
                bucket=bucket,
                key=storage_key,
                file_body=file_data,
                content_type=content_type,
                metadata={
                    "upload_id": upload_id,
                    "tenant_id": self._tenant_id,
                    "checksum_sha256": server_checksum,
                },
            )
        except Exception as exc:
            raise StorageUploadError(f"Failed to store file in MinIO: {exc}") from exc

        # Update upload session with storage info and checksum
        await self.ingestion_repo.set_storage_key(upload_id, self._tenant_id, storage_key, bucket)
        await self.ingestion_repo.set_checksum(upload_id, self._tenant_id, server_checksum)

        # Transition state
        await self._transition_state(upload_id, IngestionState.STORAGE_CONFIRMED)

        logger.info(
            "File stored in MinIO",
            extra={
                "upload_id": upload_id,
                "tenant_id": self._tenant_id,
                "storage_key": storage_key,
                "bucket": bucket,
                "checksum": server_checksum[:16],
                "file_size": len(file_data),
            },
        )

        return storage_key

    async def _find_duplicate(self, upload_id: str, checksum: str) -> Optional[str]:
        """Check if a file with the same checksum already exists for this tenant.

        Returns the existing upload_id if a duplicate is found, else None.
        """
        uploads = await self.ingestion_repo.list_by_tenant(
            self._tenant_id, limit=100,
        )
        for u in uploads:
            if u.server_checksum_sha256 == checksum and str(u.upload_id) != upload_id:
                return str(u.upload_id)
        return None

    # ── Stage 3: Text Extraction ─────────────────────────────────────────

    async def _extract_document(
        self,
        upload_id: str,
        file_data: bytes,
        content_type: str,
        filename: str,
    ) -> dict[str, Any]:
        """Extract text from the document using the appropriate parser.

        Supports PDF (PyMuPDF), DOCX (python-docx), and TXT (direct read).

        Returns:
            Dict with keys: ``pages`` (list of dicts), ``ocr_required`` (bool),
            ``method`` (str), ``quality_score`` (float).

        Raises:
            ExtractionFailedError: If extraction fails entirely.
        """
        await self._transition_state(upload_id, IngestionState.OCR_PENDING)

        try:
            # Select parser from registry
            parser = parser_registry.get_parser(content_type, file_data)
            if not parser:
                raise ExtractionFailedError(f"No parser found for content type: {content_type}")

            result = parser.extract(file_data, filename)

            # Normalize text
            for page in result.pages:
                page.text = normalize_text(page.text)

            # Evaluate quality
            quality = quality_evaluator.evaluate(result)

            # Store pages
            for page in result.pages:
                await self.extraction_repo.store_page(
                    upload_id=upload_id,
                    tenant_id=self._tenant_id,
                    page=page,
                    method=result.method,
                )

            # Create and complete extraction run
            run = await self.extraction_repo.create_run(
                upload_id=upload_id,
                tenant_id=self._tenant_id,
                method=ExtractionMethod(result.method),
            )
            await self.extraction_repo.complete_run(
                run_id=run.run_id,
                result=result,
                quality=quality,
            )

            ocr_required = (
                not quality.is_acceptable
                and result.method in ("pymupdf_direct",)
            )

            if not quality.is_acceptable and not ocr_required:
                raise ExtractionFailedError(
                    f"Extraction quality unacceptable: {quality.rejection_reason}"
                )

            # Transition to OCR_COMPLETE if no OCR needed
            if not ocr_required:
                upload = await self.ingestion_repo.get_upload(upload_id, self._tenant_id)
                await self._transition_state(upload_id, IngestionState.OCR_PROCESSING, upload=upload)
                upload.ingestion_state = IngestionState.OCR_PROCESSING
                await self._transition_state(upload_id, IngestionState.OCR_COMPLETE, upload=upload)

            logger.info(
                "Text extraction completed",
                extra={
                    "upload_id": upload_id,
                    "tenant_id": self._tenant_id,
                    "method": result.method,
                    "pages": len(result.pages),
                    "total_chars": result.total_chars,
                    "quality_score": quality.overall_score,
                    "ocr_required": ocr_required,
                },
            )

            return {
                "pages": [
                    {
                        "page_number": p.page_number,
                        "text": p.text,
                    }
                    for p in result.pages
                ],
                "ocr_required": ocr_required,
                "method": result.method,
                "quality_score": quality.overall_score,
            }

        except ExtractionFailedError:
            raise
        except Exception as exc:
            raise ExtractionFailedError(f"Text extraction failed: {exc}") from exc

    # ── Stage 4: OCR Fallback ────────────────────────────────────────────

    async def _ocr_fallback(
        self,
        upload_id: str,
        file_data: bytes,
        filename: str,
    ) -> dict[str, Any]:
        """Run OCR fallback for scanned PDFs or low-quality extractions.

        Uses OCRmyPDF to process the PDF, then re-extracts text via PyMuPDF.

        Returns:
            Dict with extracted pages (same shape as ``_extract_document``).

        Raises:
            OcrFallbackFailedError: If OCR processing fails.
        """
        await self._transition_state(upload_id, IngestionState.OCR_PROCESSING)

        try:
            # Run OCRmyPDF in a thread pool to avoid blocking
            import asyncio
            import tempfile
            import os

            loop = asyncio.get_running_loop()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_in:
                tmp_in.write(file_data)
                tmp_in_path = tmp_in.name

            tmp_out_path = tmp_in_path.replace(".pdf", "_ocr.pdf")

            try:
                # Call OCRmyPDF via subprocess (non-blocking)
                import subprocess

                proc = await asyncio.create_subprocess_exec(
                    "ocrmypdf",
                    "--force-ocr",
                    "--output-type", "pdf",
                    "--skip-text",
                    tmp_in_path,
                    tmp_out_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=120.0,
                )

                if proc.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown OCR error"
                    raise OcrFallbackFailedError(
                        f"OCRmyPDF failed (exit {proc.returncode}): {error_msg}"
                    )

                # Read OCR'd file
                with open(tmp_out_path, "rb") as f:
                    ocr_data = f.read()

            finally:
                # Cleanup temp files
                for p in (tmp_in_path, tmp_out_path):
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

            # Re-extract text from OCR'd PDF
            parser = parser_registry.get_parser("application/pdf", ocr_data)
            if not parser:
                raise OcrFallbackFailedError("No parser available for OCR'd PDF")

            result = parser.extract(ocr_data, filename)

            # Normalize text
            for page in result.pages:
                page.text = normalize_text(page.text)

            # Evaluate quality
            quality = quality_evaluator.evaluate(result)

            if not quality.is_acceptable:
                raise OcrFallbackFailedError(
                    f"OCR extraction quality still below threshold: "
                    f"{quality.rejection_reason}"
                )

            # Store OCR pages
            for page in result.pages:
                await self.extraction_repo.store_page(
                    upload_id=upload_id,
                    tenant_id=self._tenant_id,
                    page=page,
                    method="ocr_fallback",
                )

            # Create OCR extraction run
            ocr_run = await self.extraction_repo.create_run(
                upload_id=upload_id,
                tenant_id=self._tenant_id,
                method=ExtractionMethod.OCR_FALLBACK,
            )
            await self.extraction_repo.complete_run(
                run_id=ocr_run.run_id,
                result=result,
                quality=quality,
            )

            # Transition to OCR_COMPLETE
            upload = await self.ingestion_repo.get_upload(upload_id, self._tenant_id)
            await self._transition_state(upload_id, IngestionState.OCR_COMPLETE, upload=upload)

            logger.info(
                "OCR fallback completed",
                extra={
                    "upload_id": upload_id,
                    "tenant_id": self._tenant_id,
                    "pages": len(result.pages),
                    "quality_score": quality.overall_score,
                },
            )

            return {
                "pages": [
                    {
                        "page_number": p.page_number,
                        "text": p.text,
                    }
                    for p in result.pages
                ],
                "ocr_required": False,
                "method": "ocr_fallback",
                "quality_score": quality.overall_score,
            }

        except OcrFallbackFailedError:
            raise
        except asyncio.TimeoutError as exc:
            raise OcrFallbackFailedError("OCR processing timed out after 120s") from exc
        except Exception as exc:
            raise OcrFallbackFailedError(f"OCR fallback failed: {exc}") from exc

    # ── Stage 5: Chunking ────────────────────────────────────────────────

    async def _chunk_document(
        self,
        upload_id: str,
        extracted: dict[str, Any],
    ) -> list[ChunkData]:
        """Split extracted pages into semantic chunks.

        Returns:
            List of ``ChunkData`` objects.

        Raises:
            ChunkingFailedError: If chunking fails.
        """
        await self._transition_state(upload_id, IngestionState.CHUNKING_PENDING)

        pages = extracted.get("pages", [])
        if not pages:
            raise ChunkingFailedError("No extracted pages to chunk")

        try:
            page_dicts = [
                {"page_number": p["page_number"], "text": p["text"]}
                for p in pages
            ]

            chunks = chunking_service.chunk_pages(page_dicts, strategy=CHUNK_STRATEGY)

            if not chunks:
                raise ChunkingFailedError("Chunking produced zero chunks")

            # Store chunks
            for chunk in chunks:
                await self.vector_repo.store_chunk(
                    upload_id=upload_id,
                    tenant_id=self._tenant_id,
                    chunk=chunk,
                )

            logger.info(
                "Document chunked",
                extra={
                    "upload_id": upload_id,
                    "tenant_id": self._tenant_id,
                    "chunks": len(chunks),
                    "strategy": CHUNK_STRATEGY,
                },
            )

            return chunks

        except ChunkingFailedError:
            raise
        except Exception as exc:
            raise ChunkingFailedError(f"Chunking failed: {exc}") from exc

    # ── Stage 6: Embedding Generation ────────────────────────────────────

    async def _generate_embeddings(
        self,
        upload_id: str,
        chunks: list[ChunkData],
    ) -> dict[str, Any]:
        """Generate vector embeddings for all chunks.

        Returns:
            Dict with keys: ``total_tokens``, ``total_cost``, ``total_latency``,
            ``chunks_embedded``, ``chunks_failed``.

        Raises:
            EmbeddingFailedError: If all embeddings fail.
        """
        texts = [c.text for c in chunks]
        if not texts:
            raise EmbeddingFailedError("No texts to embed")

        await self._transition_state(upload_id, IngestionState.EMBEDDING_PENDING)

        try:
            # Create embedding run record
            run = await self.vector_repo.create_run(
                upload_id=upload_id,
                tenant_id=self._tenant_id,
                model=self._embedding_service.model,
                dimension=1536,
            )

            # Generate embeddings in batch
            vectors = await self._embedding_service.generate_embeddings_batch(texts)

            # Store vectors
            chunks_embedded = 0
            total_tokens = 0
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                # Get chunk ID from the stored chunk
                db_chunks = await self.vector_repo.get_chunks_by_upload(upload_id, self._tenant_id)
                if i < len(db_chunks):
                    await self.vector_repo.update_embedding(
                        chunk_id=str(db_chunks[i].chunk_id),
                        tenant_id=self._tenant_id,
                        embedding=vector,
                        model=self._embedding_service.model,
                        dimension=1536,
                        token_count=chunk.token_count,
                    )
                    chunks_embedded += 1
                    total_tokens += chunk.token_count

            # Complete the embedding run
            await self.vector_repo.complete_run(
                run_id=str(run.run_id),
                total_chunks=len(chunks),
                chunks_embedded=chunks_embedded,
                total_tokens=total_tokens,
                total_cost_usd=0.0,  # Cost tracking handled by EmbeddingService
                avg_latency_ms=0,
            )

            result = {
                "total_tokens": total_tokens,
                "chunks_embedded": chunks_embedded,
                "chunks_failed": len(chunks) - chunks_embedded,
            }

            # Transition to ANALYSIS_PENDING
            upload = await self.ingestion_repo.get_upload(upload_id, self._tenant_id)
            await self._transition_state(upload_id, IngestionState.ANALYSIS_PENDING, upload=upload)

            logger.info(
                "Embeddings generated",
                extra={
                    "upload_id": upload_id,
                    "tenant_id": self._tenant_id,
                    "model": self._embedding_service.model,
                    "chunks_embedded": chunks_embedded,
                    "total_tokens": total_tokens,
                },
            )

            return result

        except Exception as exc:
            raise EmbeddingFailedError(f"Embedding generation failed: {exc}") from exc

    # ── Stage 7: AI Analysis Dispatch ────────────────────────────────────

    async def _dispatch_ai_analysis(self, upload_id: str) -> None:
        """Hand off to AI analysis worker — review is created when analysis completes."""
        upload = await self.ingestion_repo.get_upload(upload_id, self._tenant_id)
        if not upload:
            raise ValueError(f"Upload not found: {upload_id}")

        current = coerce_ingestion_state(upload.ingestion_state)
        if current != IngestionState.ANALYSIS_PENDING:
            await self._transition_state(
                upload_id, IngestionState.ANALYSIS_PENDING, upload=upload,
            )

        user_id = self._user.id if self._user else "system"
        try:
            from workers.ai_worker import analyze_contract_task

            analyze_contract_task.delay(
                upload_id, self._tenant_id, user_id, "full",
            )
        except Exception as exc:
            logger.error(
                "Failed to dispatch AI analysis for %s: %s", upload_id, exc,
            )
            raise

        logger.info(
            "AI analysis dispatched",
            extra={
                "upload_id": upload_id,
                "tenant_id": self._tenant_id,
                "state": str(IngestionState.ANALYSIS_PENDING),
            },
        )

    # ── Stage 8: Finalize (called after AI + review creation) ────────────

    async def _finalize_ingestion(self, upload_id: str) -> None:
        """Mark upload review-ready after AI analysis and review record exist."""
        await self._transition_state(upload_id, IngestionState.REVIEW_READY)

        await self._event_bus.emit(UploadCompleted(
            tenant_id=self._tenant_id,
            actor_id=self._user.id if self._user else "system",
            data={
                "upload_id": upload_id,
                "state": str(IngestionState.REVIEW_READY),
            },
        ))

        logger.info(
            "Ingestion finalized",
            extra={
                "upload_id": upload_id,
                "tenant_id": self._tenant_id,
                "state": str(IngestionState.REVIEW_READY),
            },
        )

    # ── Failure Handling ─────────────────────────────────────────────────

    async def _handle_pipeline_failure(
        self,
        upload_id: str,
        error: Exception,
        metrics: IngestionMetrics,
    ) -> None:
        """Handle pipeline failure with state transition, logging, and cleanup."""
        error_message = f"{type(error).__name__}: {error}"

        logger.error(
            "Ingestion pipeline failed",
            extra={
                "upload_id": upload_id,
                "tenant_id": self._tenant_id,
                "correlation_id": metrics.correlation_id,
                "error": error_message,
                "total_duration_ms": metrics.total_duration_ms,
            },
            exc_info=True,
        )

        try:
            await self._transition_state(upload_id, IngestionState.FAILED, error=error_message)
        except Exception as state_exc:
            logger.warning("Failed to update ingestion state to FAILED: %s", state_exc)

        await self._event_bus.emit(UploadFailed(
            tenant_id=self._tenant_id,
            actor_id=self._user.id if self._user else "system",
            data={
                "upload_id": upload_id,
                "error": error_message,
                "correlation_id": metrics.correlation_id,
            },
        ))

        await self._emit_progress(
            upload_id, "fail", "failed",
            message=error_message,
            data={"error": error_message},
        )

    # ── State Machine Helper ─────────────────────────────────────────────

    async def _transition_state(
        self,
        upload_id: str,
        target_state: IngestionState,
        error: Optional[str] = None,
        upload: Optional[UploadSession] = None,
    ) -> UploadSession:
        """Transition the upload session to a new state with validation.

        Args:
            upload_id: The upload session UUID.
            target_state: The target ingestion state.
            error: Optional error message for FAILED state.
            upload: Optional pre-fetched upload. If not provided, fetches it.

        Raises:
            UploadNotFoundError: If the upload session does not exist.
            IngestionStateTransitionError: If the transition is invalid.
        """
        if upload is None:
            upload = await self.ingestion_repo.get_upload(upload_id, self._tenant_id)
        if not upload:
            raise UploadNotFoundError(f"Upload {upload_id} not found for tenant {self._tenant_id}")

        current_state = upload.ingestion_state
        # Handle case where ingestion_state is a plain string (e.g., from mock or serialization)
        if isinstance(current_state, str):
            current_state = IngestionState(current_state)

        if not current_state.can_transition_to(target_state):
            raise IngestionStateTransitionError(
                f"Cannot transition from {current_state} "
                f"to {target_state} for upload {upload_id}"
            )

        updated = await self.ingestion_repo.update_state(
            upload_id, self._tenant_id, target_state, error=error,
        )
        if updated is None:
            raise IngestionStateTransitionError(
                f"State transition failed: {upload.ingestion_state} -> {target_state}"
            )

        # Update the local upload state to reflect the transition
        upload.ingestion_state = target_state

        return updated

    # ── Retry Logic ──────────────────────────────────────────────────────

    async def retry_ingestion(self, upload_id: str) -> IngestionMetrics:
        """Retry a failed ingestion from scratch.

        Resets the upload to UPLOADED state and re-runs the full pipeline.

        Raises:
            UploadNotFoundError: If the upload does not exist.
            IngestionRetryLimitExceededError: If max retries reached.
        """
        upload = await self.ingestion_repo.get_upload(upload_id, self._tenant_id)
        if not upload:
            raise UploadNotFoundError(f"Upload {upload_id} not found")

        if upload.ingestion_state != IngestionState.FAILED:
            raise IngestionStateTransitionError(
                f"Can only retry from FAILED state, current: {upload.ingestion_state}"
            )

        if upload.retry_count >= MAX_RETRIES:
            raise IngestionRetryLimitExceededError(
                f"Max retries ({MAX_RETRIES}) reached for upload {upload_id}"
            )

        await self.ingestion_repo.increment_retry(upload_id, self._tenant_id)
        await self._transition_state(upload_id, IngestionState.UPLOADED, error=None)

        # Download file from storage
        file_data = await storage_service.download_fileobj(
            upload.storage_bucket or DEFAULT_STORAGE_BUCKET,
            upload.storage_key or "",
        )

        # Re-run pipeline
        metrics = await self.run_pipeline(
            upload_id=upload_id,
            file_data=file_data,
            filename=upload.filename,
            content_type=upload.content_type,
            correlation_id=f"retry-{upload.retry_count}-{upload_id}",
        )
        metrics.retry_count = upload.retry_count

        return metrics
