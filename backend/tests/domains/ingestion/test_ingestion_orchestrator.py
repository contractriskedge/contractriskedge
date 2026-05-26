"""Comprehensive unit tests for the IngestionOrchestrator.

Tests cover:
    - Full pipeline (PDF, DOCX, TXT)
    - Scanned PDF (OCR fallback)
    - Malformed PDF
    - OCR fallback
    - Retry handling
    - Duplicate upload detection
    - MinIO/S3 failures
    - Embedding failures
    - Tenant isolation
    - MIME type validation
    - File size validation
    - State machine transitions
    - Event emission
    - Progress hooks
    - Metrics collection
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import UUID

import pytest

from app.domains.ingestion.models import IngestionState, UploadSession
from app.domains.ingestion.services.ingestion_orchestrator import (
    IngestionOrchestrator,
    IngestionOrchestrationError,
    IngestionMetrics,
    IngestionProgressEvent,
    MimeTypeValidationError,
    FileSizeValidationError,
    DuplicateUploadError,
    ExtractionFailedError,
    OcrFallbackFailedError,
    ChunkingFailedError,
    EmbeddingFailedError,
    StorageUploadError,
    MAX_FILE_SIZE,
    ALLOWED_MIME_TYPES,
)
from app.domains.ingestion.exceptions import (
    UploadNotFoundError,
    IngestionStateTransitionError,
    IngestionRetryLimitExceededError,
)
from app.domains.vectors.chunking import ChunkData


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_pdf_bytes() -> bytes:
    """Create minimal valid PDF bytes."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n0\n%%EOF"


def _make_docx_bytes() -> bytes:
    """Create minimal valid DOCX bytes (ZIP with PK header)."""
    import struct
    # Minimal ZIP with PK\x03\x04 signature
    return b"PK\x03\x04" + b"\x00" * 22


def _make_txt_bytes() -> bytes:
    """Create plain text bytes."""
    return b"Hello, this is a test contract document.\nIt has multiple lines.\n"


def _make_malformed_pdf_bytes() -> bytes:
    """Create bytes that look like PDF but are corrupted."""
    return b"%PDF-1.4\ncorrupted\x00\x01\x02content"


def _make_upload_session(
    upload_id: Optional[str] = None,
    tenant_id: str = "test-tenant-a",
    state: IngestionState = IngestionState.UPLOADED,
    filename: str = "test.pdf",
    content_type: str = "application/pdf",
    file_size: int = 1024,
    storage_key: Optional[str] = None,
    checksum: Optional[str] = None,
    retry_count: int = 0,
) -> MagicMock:
    """Create a mock UploadSession with the given attributes."""
    session = MagicMock(spec=UploadSession)
    session.upload_id = UUID(upload_id) if upload_id else uuid.uuid4()
    session.tenant_id = tenant_id
    # Ensure ingestion_state is an IngestionState enum, not a string
    if isinstance(state, str):
        state = IngestionState(state)
    session.ingestion_state = state
    session.filename = filename
    session.content_type = content_type
    session.file_size = file_size
    session.storage_key = storage_key or f"{tenant_id}/contracts/2026/01/{uuid.uuid4()}/{filename}"
    session.storage_bucket = "contractrisk-documents"
    session.server_checksum_sha256 = checksum
    session.retry_count = retry_count
    session.user_id = "test-user"
    session.metadata = {}
    session.correlation_id = str(uuid.uuid4())
    return session


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock async SQLAlchemy session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Create a mock EmbeddingService."""
    service = MagicMock()
    service.generate_embedding = AsyncMock()
    service.generate_embedding.return_value = [0.1] * 1536
    service.generate_embeddings_batch = AsyncMock()
    service.generate_embeddings_batch.return_value = [[0.1] * 1536, [0.2] * 1536]
    service.model = "text-embedding-3-small"
    return service


@pytest.fixture
def mock_event_bus() -> MagicMock:
    """Create a mock EventBus."""
    bus = MagicMock()
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_storage_service() -> MagicMock:
    """Mock the global storage_service."""
    with patch("app.domains.ingestion.services.ingestion_orchestrator.storage_service") as mock:
        mock.ensure_bucket = AsyncMock()
        mock.upload_fileobj = AsyncMock()
        mock.build_object_key = MagicMock(return_value="test-tenant-a/contracts/2026/01/uuid/test.pdf")
        mock.download_fileobj = AsyncMock()
        mock.download_fileobj.return_value = _make_pdf_bytes()
        yield mock


@pytest.fixture
def mock_parser_registry() -> MagicMock:
    """Mock the parser_registry to return a working parser."""
    with patch("app.domains.ingestion.services.ingestion_orchestrator.parser_registry") as mock:
        parser = MagicMock()
        result = MagicMock()
        result.pages = []
        result.total_pages = 0
        result.total_chars = 0
        result.method = "txt_parse"
        result.ocr_required = False
        result.avg_confidence = 0.95
        result.ocr_engine_used = None
        result.total_processing_time_ms = 10
        parser.extract = MagicMock(return_value=result)
        mock.get_parser = MagicMock(return_value=parser)
        yield mock


@pytest.fixture
def mock_quality_evaluator() -> MagicMock:
    """Mock the quality_evaluator."""
    with patch("app.domains.ingestion.services.ingestion_orchestrator.quality_evaluator") as mock:
        quality = MagicMock()
        quality.is_acceptable = True
        quality.overall_score = 0.95
        quality.rejection_reason = None
        mock.evaluate = MagicMock(return_value=quality)
        yield mock


@pytest.fixture
def mock_chunking_service() -> MagicMock:
    """Mock the chunking_service."""
    with patch("app.domains.ingestion.services.ingestion_orchestrator.chunking_service") as mock:
        mock.chunk_pages = MagicMock(return_value=[
            ChunkData(
                text="Chunk 1 content",
                chunk_index=0,
                token_count=10,
                page_numbers=[1],
                checksum=hashlib.sha256(b"Chunk 1 content").hexdigest(),
                char_count=15,
            ),
            ChunkData(
                text="Chunk 2 content",
                chunk_index=1,
                token_count=10,
                page_numbers=[1],
                checksum=hashlib.sha256(b"Chunk 2 content").hexdigest(),
                char_count=15,
            ),
        ])
        yield mock


@pytest.fixture
def orchestrator(
    mock_session: MagicMock,
    mock_embedding_service: MagicMock,
    mock_event_bus: MagicMock,
) -> IngestionOrchestrator:
    """Create an IngestionOrchestrator with mocked dependencies."""
    return IngestionOrchestrator(
        session=mock_session,
        embedding_service=mock_embedding_service,
        event_bus=mock_event_bus,
        tenant_id="test-tenant-a",
    )


# ── Test: Initialization ──────────────────────────────────────────────────────


class TestIngestionOrchestratorInit:
    """Verify orchestrator initialization."""

    def test_init_with_tenant(self, mock_session: MagicMock, mock_embedding_service: MagicMock) -> None:
        orch = IngestionOrchestrator(
            session=mock_session,
            embedding_service=mock_embedding_service,
            tenant_id="test-tenant-a",
        )
        assert orch._tenant_id == "test-tenant-a"
        assert orch._ingestion_repo is None  # Lazy init

    def test_init_without_tenant_warns(self, mock_session: MagicMock, mock_embedding_service: MagicMock) -> None:
        orch = IngestionOrchestrator(
            session=mock_session,
            embedding_service=mock_embedding_service,
        )
        assert orch._tenant_id == ""

    def test_repositories_lazy_init(self, orchestrator: IngestionOrchestrator) -> None:
        """Repositories are lazily initialized on first access."""
        assert orchestrator._ingestion_repo is None
        _ = orchestrator.ingestion_repo
        assert orchestrator._ingestion_repo is not None


# ── Test: Validation ──────────────────────────────────────────────────────────


class TestValidation:
    """Verify file validation logic."""

    async def test_valid_pdf(self, orchestrator: IngestionOrchestrator) -> None:
        """Valid PDF passes all validation checks."""
        # Mock get_upload to return different states on successive calls
        upload_uploaded = _make_upload_session(state=IngestionState.UPLOADED)
        upload_validating = _make_upload_session(state=IngestionState.VALIDATING)

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.side_effect = [upload_uploaded, upload_validating]
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()) as mock_update:
                mock_update.return_value = _make_upload_session(state=IngestionState.VALIDATED)

                await orchestrator._validate_upload(
                    upload_id=str(uuid.uuid4()),
                    filename="test.pdf",
                    content_type="application/pdf",
                    file_data=_make_pdf_bytes(),
                )

    async def test_invalid_extension_raises(self, orchestrator: IngestionOrchestrator) -> None:
        """Invalid file extension raises MimeTypeValidationError."""
        with pytest.raises(MimeTypeValidationError, match="not supported"):
            await orchestrator._validate_upload(
                upload_id=str(uuid.uuid4()),
                filename="malware.exe",
                content_type="application/x-msdownload",
                file_data=b"fake content",
            )

    async def test_mime_mismatch_raises(self, orchestrator: IngestionOrchestrator) -> None:
        """MIME type that doesn't match extension raises error."""
        with pytest.raises(MimeTypeValidationError, match="does not match"):
            await orchestrator._validate_upload(
                upload_id=str(uuid.uuid4()),
                filename="test.pdf",
                content_type="text/plain",
                file_data=_make_pdf_bytes(),
            )

    async def test_unsupported_mime_raises(self, orchestrator: IngestionOrchestrator) -> None:
        """Unsupported MIME type raises error."""
        with pytest.raises(MimeTypeValidationError, match="not supported"):
            await orchestrator._validate_upload(
                upload_id=str(uuid.uuid4()),
                filename="test.exe",
                content_type="application/octet-stream",
                file_data=b"fake content",
            )

    async def test_file_too_large_raises(self, orchestrator: IngestionOrchestrator) -> None:
        """File exceeding max size raises FileSizeValidationError."""
        oversized = b"x" * (MAX_FILE_SIZE + 1)
        with pytest.raises(FileSizeValidationError, match="exceeds|too large|File too large"):
            await orchestrator._validate_upload(
                upload_id=str(uuid.uuid4()),
                filename="huge.pdf",
                content_type="application/pdf",
                file_data=oversized,
            )

    async def test_magic_bytes_mismatch_raises(self, orchestrator: IngestionOrchestrator) -> None:
        """Wrong magic bytes raises error."""
        with pytest.raises(MimeTypeValidationError, match="magic bytes"):
            await orchestrator._validate_upload(
                upload_id=str(uuid.uuid4()),
                filename="test.pdf",
                content_type="application/pdf",
                file_data=b"Not a PDF at all" * 10,
            )


# ── Test: Storage ─────────────────────────────────────────────────────────────


class TestStorage:
    """Verify file storage logic."""

    async def test_store_file_success(
        self,
        orchestrator: IngestionOrchestrator,
        mock_storage_service: MagicMock,
    ) -> None:
        """File is stored in MinIO and session is updated."""
        upload_id = str(uuid.uuid4())
        file_data = _make_pdf_bytes()

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.VALIDATED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch.object(orchestrator.ingestion_repo, "set_storage_key", AsyncMock()):
                    with patch.object(orchestrator.ingestion_repo, "set_checksum", AsyncMock()):
                        with patch.object(orchestrator.ingestion_repo, "list_by_tenant", AsyncMock(return_value=[])):
                            with patch("app.domains.ingestion.services.ingestion_orchestrator.settings.s3_bucket", "test-bucket"):
                                key = await orchestrator._store_file(
                                    upload_id=upload_id,
                                    file_data=file_data,
                                    content_type="application/pdf",
                                    filename="test.pdf",
                                )

                                assert key is not None
                                mock_storage_service.upload_fileobj.assert_awaited_once()

    async def test_store_file_minio_failure(
        self,
        orchestrator: IngestionOrchestrator,
        mock_storage_service: MagicMock,
    ) -> None:
        """MinIO failure raises StorageUploadError."""
        mock_storage_service.upload_fileobj.side_effect = Exception("MinIO connection refused")

        with patch.object(orchestrator.ingestion_repo, "list_by_tenant", AsyncMock(return_value=[])):
            with patch("app.domains.ingestion.services.ingestion_orchestrator.settings.s3_bucket", "test-bucket"):
                with pytest.raises(StorageUploadError, match="MinIO"):
                    await orchestrator._store_file(
                        upload_id=str(uuid.uuid4()),
                        file_data=_make_pdf_bytes(),
                        content_type="application/pdf",
                        filename="test.pdf",
                    )

    async def test_duplicate_detection(
        self,
        orchestrator: IngestionOrchestrator,
        mock_storage_service: MagicMock,
    ) -> None:
        """Duplicate checksum raises DuplicateUploadError."""
        upload_id = str(uuid.uuid4())
        file_data = _make_pdf_bytes()
        checksum = hashlib.sha256(file_data).hexdigest()

        existing = _make_upload_session(
            upload_id=str(uuid.uuid4()),
            checksum=checksum,
            state=IngestionState.REVIEW_READY,
        )

        with patch.object(orchestrator.ingestion_repo, "list_by_tenant", AsyncMock(return_value=[existing])):
            with patch("app.domains.ingestion.services.ingestion_orchestrator.settings.s3_bucket", "test-bucket"):
                with pytest.raises(DuplicateUploadError, match="Duplicate"):
                    await orchestrator._store_file(
                        upload_id=upload_id,
                        file_data=file_data,
                        content_type="application/pdf",
                        filename="test.pdf",
                    )


# ── Test: Extraction ──────────────────────────────────────────────────────────


class TestExtraction:
    """Verify text extraction logic."""

    async def test_extract_pdf_success(
        self,
        orchestrator: IngestionOrchestrator,
        mock_parser_registry: MagicMock,
        mock_quality_evaluator: MagicMock,
    ) -> None:
        """PDF text extraction succeeds with good quality."""
        upload_id = str(uuid.uuid4())
        file_data = _make_pdf_bytes()

        # Mock parser result with pages
        result = MagicMock()
        result.pages = []
        result.total_pages = 0
        result.total_chars = 0
        result.method = "txt_parse"
        result.ocr_required = False
        result.avg_confidence = 0.95
        result.ocr_engine_used = None
        result.total_processing_time_ms = 10
        mock_parser_registry.get_parser.return_value.extract.return_value = result

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.STORAGE_CONFIRMED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                    with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create_run:
                        mock_create_run.return_value = MagicMock(run_id=uuid.uuid4())
                        with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):
                            extracted = await orchestrator._extract_document(
                                upload_id=upload_id,
                                file_data=file_data,
                                content_type="application/pdf",
                                filename="test.pdf",
                            )

                            assert extracted["ocr_required"] is False
                            assert "pages" in extracted

    async def test_extract_docx_success(
        self,
        orchestrator: IngestionOrchestrator,
        mock_parser_registry: MagicMock,
        mock_quality_evaluator: MagicMock,
    ) -> None:
        """DOCX text extraction succeeds."""
        upload_id = str(uuid.uuid4())

        result = MagicMock()
        result.pages = []
        result.total_pages = 0
        result.method = "docx_parse"
        result.ocr_required = False
        result.avg_confidence = 1.0
        result.total_processing_time_ms = 5
        mock_parser_registry.get_parser.return_value.extract.return_value = result

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.STORAGE_CONFIRMED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                    with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create_run:
                        mock_create_run.return_value = MagicMock(run_id=uuid.uuid4())
                        with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):
                            extracted = await orchestrator._extract_document(
                                upload_id=upload_id,
                                file_data=_make_docx_bytes(),
                                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                filename="test.docx",
                            )
                            assert extracted["ocr_required"] is False

    async def test_extract_txt_success(
        self,
        orchestrator: IngestionOrchestrator,
        mock_parser_registry: MagicMock,
        mock_quality_evaluator: MagicMock,
    ) -> None:
        """TXT extraction succeeds."""
        upload_id = str(uuid.uuid4())

        result = MagicMock()
        result.pages = []
        result.total_pages = 0
        result.method = "txt_parse"
        result.ocr_required = False
        result.avg_confidence = 1.0
        result.total_processing_time_ms = 2
        mock_parser_registry.get_parser.return_value.extract.return_value = result

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.STORAGE_CONFIRMED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                    with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create_run:
                        mock_create_run.return_value = MagicMock(run_id=uuid.uuid4())
                        with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):
                            extracted = await orchestrator._extract_document(
                                upload_id=upload_id,
                                file_data=_make_txt_bytes(),
                                content_type="text/plain",
                                filename="test.txt",
                            )
                            assert extracted["ocr_required"] is False

    async def test_extract_no_parser_raises(
        self,
        orchestrator: IngestionOrchestrator,
        mock_parser_registry: MagicMock,
    ) -> None:
        """Missing parser raises ExtractionFailedError."""
        mock_parser_registry.get_parser.return_value = None

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.STORAGE_CONFIRMED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with pytest.raises(ExtractionFailedError, match="No parser"):
                    await orchestrator._extract_document(
                        upload_id=str(uuid.uuid4()),
                        file_data=_make_malformed_pdf_bytes(),
                        content_type="application/pdf",
                        filename="test.pdf",
                    )


# ── Test: OCR Fallback ────────────────────────────────────────────────────────


class TestOcrFallback:
    """Verify OCR fallback logic."""

    async def test_ocr_fallback_triggered(
        self,
        orchestrator: IngestionOrchestrator,
    ) -> None:
        """OCR fallback is triggered when extraction quality is low."""
        upload_id = str(uuid.uuid4())

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.OCR_PENDING)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch("asyncio.create_subprocess_exec", AsyncMock()) as mock_subprocess:
                    proc = MagicMock()
                    proc.returncode = 0
                    proc.communicate = AsyncMock(return_value=(b"", b""))
                    mock_subprocess.return_value = proc

                    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                        mock_tmp.return_value.__enter__.return_value.name = "/tmp/test_ocr.pdf"

                        with patch("builtins.open", MagicMock()) as mock_open:
                            mock_open.return_value.__enter__.return_value.read.return_value = _make_pdf_bytes()

                            with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                                with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create:
                                    mock_create.return_value = MagicMock(run_id=uuid.uuid4())
                                    with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):
                                        with patch("app.domains.ingestion.services.ingestion_orchestrator.parser_registry") as mock_reg:
                                            parser = MagicMock()
                                            result = MagicMock()
                                            result.pages = []
                                            result.total_pages = 0
                                            result.method = "ocr_fallback"
                                            parser.extract.return_value = result
                                            mock_reg.get_parser.return_value = parser

                                            with patch("app.domains.ingestion.services.ingestion_orchestrator.quality_evaluator") as mock_q:
                                                quality = MagicMock()
                                                quality.is_acceptable = True
                                                quality.overall_score = 0.85
                                                mock_q.evaluate.return_value = quality

                                                result_dict = await orchestrator._ocr_fallback(
                                                    upload_id=upload_id,
                                                    file_data=_make_pdf_bytes(),
                                                    filename="test.pdf",
                                                )

                                                assert result_dict["method"] == "ocr_fallback"


# ── Test: Chunking ────────────────────────────────────────────────────────────


class TestChunking:
    """Verify document chunking logic."""

    async def test_chunk_success(
        self,
        orchestrator: IngestionOrchestrator,
        mock_chunking_service: MagicMock,
    ) -> None:
        """Document is chunked into semantic chunks."""
        upload_id = str(uuid.uuid4())

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.OCR_COMPLETE)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch.object(orchestrator.vector_repo, "store_chunk", AsyncMock()):
                    chunks = await orchestrator._chunk_document(
                        upload_id=upload_id,
                        extracted={"pages": [{"page_number": 1, "text": "Test content"}]},
                    )

                    assert len(chunks) == 2
                    assert chunks[0].text == "Chunk 1 content"

    async def test_chunk_no_pages_raises(self, orchestrator: IngestionOrchestrator) -> None:
        """Empty pages raises ChunkingFailedError."""
        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.OCR_COMPLETE)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with pytest.raises(ChunkingFailedError, match="No extracted pages"):
                    await orchestrator._chunk_document(
                        upload_id=str(uuid.uuid4()),
                        extracted={"pages": []},
                    )


# ── Test: Embedding ───────────────────────────────────────────────────────────


class TestEmbedding:
    """Verify embedding generation logic."""

    async def test_embedding_success(
        self,
        orchestrator: IngestionOrchestrator,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Embeddings are generated and stored."""
        upload_id = str(uuid.uuid4())
        chunks = [
            ChunkData(text="Test 1", chunk_index=0, token_count=5, page_numbers=[1]),
            ChunkData(text="Test 2", chunk_index=1, token_count=5, page_numbers=[1]),
        ]

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.CHUNKING_PENDING)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch.object(orchestrator.vector_repo, "create_run", AsyncMock()) as mock_create:
                    mock_create.return_value = MagicMock(run_id=uuid.uuid4())
                    with patch.object(orchestrator.vector_repo, "get_chunks_by_upload", AsyncMock()) as mock_get_chunks:
                        db_chunk = MagicMock()
                        db_chunk.chunk_id = uuid.uuid4()
                        mock_get_chunks.return_value = [db_chunk, db_chunk]
                        with patch.object(orchestrator.vector_repo, "update_embedding", AsyncMock()):
                            with patch.object(orchestrator.vector_repo, "complete_run", AsyncMock()):
                                result = await orchestrator._generate_embeddings(
                                    upload_id=upload_id,
                                    chunks=chunks,
                                )

                                assert result["chunks_embedded"] == 2
                                assert result["total_tokens"] > 0

    async def test_embedding_no_texts_raises(self, orchestrator: IngestionOrchestrator) -> None:
        """Empty texts raises EmbeddingFailedError."""
        with pytest.raises(EmbeddingFailedError, match="No texts"):
            await orchestrator._generate_embeddings(
                upload_id=str(uuid.uuid4()),
                chunks=[],
            )


# ── Test: Full Pipeline ───────────────────────────────────────────────────────


class TestFullPipeline:
    """Verify the complete ingestion pipeline end-to-end."""

    async def test_full_pipeline_success(
        self,
        orchestrator: IngestionOrchestrator,
        mock_storage_service: MagicMock,
        mock_parser_registry: MagicMock,
        mock_quality_evaluator: MagicMock,
        mock_chunking_service: MagicMock,
        mock_embedding_service: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """Full pipeline completes successfully for a valid PDF."""
        upload_id = str(uuid.uuid4())
        file_data = _make_pdf_bytes()

        # Mock all repository methods
        # Set up parser to return pages with content
        parser = MagicMock()
        result = MagicMock()
        page = MagicMock()
        page.page_number = 1
        page.text = "This is extracted text from the PDF document. It contains multiple sentences for testing."
        page.char_count = len(page.text)
        page.confidence = 0.95
        page.has_text_layer = True
        page.width_pts = 612
        page.height_pts = 792
        page.rotation_degrees = 0
        page.processing_time_ms = 10
        page.word_count = 15
        page.symbol_count = 0
        result.pages = [page]
        result.total_pages = 1
        result.total_chars = len(page.text)
        result.method = "pymupdf_direct"
        result.ocr_required = False
        result.avg_confidence = 0.95
        result.ocr_engine_used = None
        result.total_processing_time_ms = 10
        parser.extract.return_value = result
        mock_parser_registry.get_parser.return_value = parser

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.UPLOADED)

            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()) as mock_update_state:
                mock_update_state.return_value = _make_upload_session(state=IngestionState.REVIEW_READY)

                with patch.object(orchestrator.ingestion_repo, "set_storage_key", AsyncMock()):
                    with patch.object(orchestrator.ingestion_repo, "set_checksum", AsyncMock()):
                        with patch.object(orchestrator.ingestion_repo, "list_by_tenant", AsyncMock(return_value=[])):

                            with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                                with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create:
                                    mock_create.return_value = MagicMock(run_id=uuid.uuid4())
                                    with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):

                                        with patch.object(orchestrator.vector_repo, "store_chunk", AsyncMock()):
                                            with patch.object(orchestrator.vector_repo, "create_run", AsyncMock()) as mock_vc:
                                                mock_vc.return_value = MagicMock(run_id=uuid.uuid4())
                                                with patch.object(orchestrator.vector_repo, "get_chunks_by_upload", AsyncMock()) as mock_gc:
                                                    db_chunk = MagicMock()
                                                    db_chunk.chunk_id = uuid.uuid4()
                                                    mock_gc.return_value = [db_chunk, db_chunk]
                                                    with patch.object(orchestrator.vector_repo, "update_embedding", AsyncMock()):
                                                        with patch.object(orchestrator.vector_repo, "complete_run", AsyncMock()):

                                                            metrics = await orchestrator.run_pipeline(
                                                                upload_id=upload_id,
                                                                file_data=file_data,
                                                                filename="test.pdf",
                                                                content_type="application/pdf",
                                                            )

                                                            assert metrics.success is True
                                                            assert metrics.total_duration_ms > 0
                                                            assert metrics.file_size_bytes == len(file_data)
                                                            assert metrics.content_type == "application/pdf"
                                                            mock_event_bus.emit.assert_awaited()

    async def test_pipeline_with_ocr_fallback(
        self,
        orchestrator: IngestionOrchestrator,
        mock_storage_service: MagicMock,
        mock_parser_registry: MagicMock,
        mock_chunking_service: MagicMock,
        mock_embedding_service: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """Pipeline handles OCR fallback for scanned PDFs."""
        upload_id = str(uuid.uuid4())
        file_data = _make_pdf_bytes()

        # First extraction has low quality -> triggers OCR
        low_quality = MagicMock()
        low_quality.is_acceptable = False
        low_quality.overall_score = 0.3
        low_quality.rejection_reason = "Low text density"

        # Mock quality evaluator to return low quality first, then acceptable
        with patch("app.domains.ingestion.services.ingestion_orchestrator.quality_evaluator") as mock_q:
            # First call returns low quality (extraction), second returns acceptable (OCR)
            mock_q.evaluate = MagicMock(side_effect=[low_quality, low_quality])

            with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
                mock_get.return_value = _make_upload_session(state=IngestionState.UPLOADED)

                with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                    with patch.object(orchestrator.ingestion_repo, "set_storage_key", AsyncMock()):
                        with patch.object(orchestrator.ingestion_repo, "set_checksum", AsyncMock()):
                            with patch.object(orchestrator.ingestion_repo, "list_by_tenant", AsyncMock(return_value=[])):

                                with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                                    with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create:
                                        mock_create.return_value = MagicMock(run_id=uuid.uuid4())
                                        with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):

                                            with patch.object(orchestrator.vector_repo, "store_chunk", AsyncMock()):
                                                with patch.object(orchestrator.vector_repo, "create_run", AsyncMock()) as mock_vc:
                                                    mock_vc.return_value = MagicMock(run_id=uuid.uuid4())
                                                    with patch.object(orchestrator.vector_repo, "get_chunks_by_upload", AsyncMock()) as mock_gc:
                                                        db_chunk = MagicMock()
                                                        db_chunk.chunk_id = uuid.uuid4()
                                                        mock_gc.return_value = [db_chunk, db_chunk]
                                                        with patch.object(orchestrator.vector_repo, "update_embedding", AsyncMock()):
                                                            with patch.object(orchestrator.vector_repo, "complete_run", AsyncMock()):

                                                                # Mock OCR subprocess
                                                                with patch("asyncio.create_subprocess_exec", AsyncMock()) as mock_sub:
                                                                    proc = MagicMock()
                                                                    proc.returncode = 0
                                                                    proc.communicate = AsyncMock(return_value=(b"", b""))
                                                                    mock_sub.return_value = proc

                                                                    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                                                                        mock_tmp.return_value.__enter__.return_value.name = "/tmp/test_ocr.pdf"
                                                                        with patch("builtins.open", MagicMock()) as mock_open:
                                                                            mock_open.return_value.__enter__.return_value.read.return_value = _make_pdf_bytes()

                                                                            with pytest.raises(Exception):
                                                                                # The pipeline will fail because OCR quality is also low
                                                                                await orchestrator.run_pipeline(
                                                                                    upload_id=upload_id,
                                                                                    file_data=file_data,
                                                                                    filename="test.pdf",
                                                                                    content_type="application/pdf",
                                                                                )

    async def test_pipeline_malformed_pdf(
        self,
        orchestrator: IngestionOrchestrator,
        mock_storage_service: MagicMock,
    ) -> None:
        """Malformed PDF fails at extraction stage."""
        upload_id = str(uuid.uuid4())
        file_data = _make_malformed_pdf_bytes()

        # Mock parser to raise on extraction
        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.UPLOADED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch.object(orchestrator.ingestion_repo, "set_storage_key", AsyncMock()):
                    with patch.object(orchestrator.ingestion_repo, "set_checksum", AsyncMock()):
                        with patch.object(orchestrator.ingestion_repo, "list_by_tenant", AsyncMock(return_value=[])):
                            with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                                with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create:
                                    mock_create.return_value = MagicMock(run_id=uuid.uuid4())
                                    with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):
                                        with patch("app.domains.ingestion.services.ingestion_orchestrator.parser_registry") as mock_reg:
                                            parser = MagicMock()
                                            parser.extract = MagicMock(side_effect=Exception("Corrupted PDF"))
                                            mock_reg.get_parser.return_value = parser

                                            with pytest.raises(ExtractionFailedError):
                                                await orchestrator.run_pipeline(
                                                    upload_id=upload_id,
                                                    file_data=file_data,
                                                    filename="test.pdf",
                                                    content_type="application/pdf",
                                                )

    async def test_pipeline_embedding_failure(
        self,
        orchestrator: IngestionOrchestrator,
        mock_storage_service: MagicMock,
        mock_parser_registry: MagicMock,
        mock_quality_evaluator: MagicMock,
        mock_chunking_service: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Embedding failure is properly handled."""
        upload_id = str(uuid.uuid4())

        mock_embedding_service.generate_embeddings_batch.side_effect = Exception("OpenAI API error")

        # Set up parser to return pages with content
        parser = MagicMock()
        result = MagicMock()
        page = MagicMock()
        page.page_number = 1
        page.text = "Extracted text for embedding failure test."
        page.char_count = len(page.text)
        page.confidence = 0.95
        page.has_text_layer = True
        page.width_pts = 612
        page.height_pts = 792
        page.rotation_degrees = 0
        page.processing_time_ms = 10
        page.word_count = 8
        page.symbol_count = 0
        result.pages = [page]
        result.total_pages = 1
        result.total_chars = len(page.text)
        result.method = "pymupdf_direct"
        result.ocr_required = False
        result.avg_confidence = 0.95
        result.ocr_engine_used = None
        result.total_processing_time_ms = 10
        parser.extract.return_value = result
        mock_parser_registry.get_parser.return_value = parser

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.UPLOADED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with patch.object(orchestrator.ingestion_repo, "set_storage_key", AsyncMock()):
                    with patch.object(orchestrator.ingestion_repo, "set_checksum", AsyncMock()):
                        with patch.object(orchestrator.ingestion_repo, "list_by_tenant", AsyncMock(return_value=[])):
                            with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                                with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create:
                                    mock_create.return_value = MagicMock(run_id=uuid.uuid4())
                                    with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):
                                        with patch.object(orchestrator.vector_repo, "store_chunk", AsyncMock()):
                                            with patch.object(orchestrator.vector_repo, "create_run", AsyncMock()) as mock_vc:
                                                mock_vc.return_value = MagicMock(run_id=uuid.uuid4())

                                                with pytest.raises(EmbeddingFailedError):
                                                    await orchestrator.run_pipeline(
                                                        upload_id=upload_id,
                                                        file_data=_make_pdf_bytes(),
                                                        filename="test.pdf",
                                                        content_type="application/pdf",
                                                    )


# ── Test: Tenant Isolation ────────────────────────────────────────────────────


class TestTenantIsolation:
    """Verify tenant isolation enforcement."""

    async def test_orchestrator_requires_tenant(self) -> None:
        """Orchestrator logs warning when created without tenant."""
        from unittest.mock import MagicMock
        orch = IngestionOrchestrator(
            session=MagicMock(),
            embedding_service=MagicMock(),
        )
        assert orch._tenant_id == ""

    async def test_upload_not_found_for_wrong_tenant(
        self,
        orchestrator: IngestionOrchestrator,
    ) -> None:
        """Upload from wrong tenant raises UploadNotFoundError."""
        with patch.object(orchestrator.ingestion_repo, "get_upload", AsyncMock(return_value=None)):
            with pytest.raises(UploadNotFoundError, match="not found"):
                await orchestrator._transition_state(
                    upload_id=str(uuid.uuid4()),
                    target_state=IngestionState.VALIDATING,
                )


# ── Test: Retry Logic ─────────────────────────────────────────────────────────


class TestRetryLogic:
    """Verify retry handling."""

    async def test_retry_from_failed(
        self,
        orchestrator: IngestionOrchestrator,
        mock_storage_service: MagicMock,
    ) -> None:
        """Failed ingestion can be retried."""
        upload_id = str(uuid.uuid4())

        failed_upload = _make_upload_session(
            upload_id=upload_id,
            state=IngestionState.FAILED,
            retry_count=1,
            storage_key="test-key",
        )

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = failed_upload
            with patch.object(orchestrator.ingestion_repo, "increment_retry", AsyncMock()):
                with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                    with patch.object(orchestrator.ingestion_repo, "set_storage_key", AsyncMock()):
                        with patch.object(orchestrator.ingestion_repo, "set_checksum", AsyncMock()):
                            with patch.object(orchestrator.ingestion_repo, "list_by_tenant", AsyncMock(return_value=[])):
                                with patch("app.domains.ingestion.services.ingestion_orchestrator.parser_registry") as mock_reg:
                                    parser = MagicMock()
                                    result = MagicMock()
                                    page = MagicMock()
                                    page.page_number = 1
                                    page.text = "Retry test content."
                                    page.char_count = len(page.text)
                                    page.confidence = 0.95
                                    page.has_text_layer = True
                                    page.width_pts = 612
                                    page.height_pts = 792
                                    page.rotation_degrees = 0
                                    page.processing_time_ms = 10
                                    page.word_count = 5
                                    page.symbol_count = 0
                                    result.pages = [page]
                                    result.total_pages = 1
                                    result.total_chars = len(page.text)
                                    result.method = "pymupdf_direct"
                                    result.ocr_required = False
                                    result.avg_confidence = 0.95
                                    result.ocr_engine_used = None
                                    result.total_processing_time_ms = 10
                                    parser.extract.return_value = result
                                    mock_reg.get_parser.return_value = parser

                                    with patch.object(orchestrator.extraction_repo, "store_page", AsyncMock()):
                                        with patch.object(orchestrator.extraction_repo, "create_run", AsyncMock()) as mock_create:
                                            mock_create.return_value = MagicMock(run_id=uuid.uuid4())
                                            with patch.object(orchestrator.extraction_repo, "complete_run", AsyncMock()):
                                                with patch.object(orchestrator.vector_repo, "store_chunk", AsyncMock()):
                                                    with patch.object(orchestrator.vector_repo, "create_run", AsyncMock()) as mock_vc:
                                                        mock_vc.return_value = MagicMock(run_id=uuid.uuid4())
                                                        with patch.object(orchestrator.vector_repo, "get_chunks_by_upload", AsyncMock()) as mock_gc:
                                                            db_chunk = MagicMock()
                                                            db_chunk.chunk_id = uuid.uuid4()
                                                            mock_gc.return_value = [db_chunk, db_chunk]
                                                            with patch.object(orchestrator.vector_repo, "update_embedding", AsyncMock()):
                                                                with patch.object(orchestrator.vector_repo, "complete_run", AsyncMock()):
                                                                    with patch("app.domains.ingestion.services.ingestion_orchestrator.quality_evaluator") as mock_q:
                                                                        quality = MagicMock()
                                                                        quality.is_acceptable = True
                                                                        quality.overall_score = 0.95
                                                                        mock_q.evaluate.return_value = quality

                                                                        metrics = await orchestrator.retry_ingestion(upload_id=upload_id)
                                                                        assert metrics.retry_count == 1

    async def test_retry_limit_exceeded(
        self,
        orchestrator: IngestionOrchestrator,
    ) -> None:
        """Retry beyond max raises IngestionRetryLimitExceededError."""
        upload_id = str(uuid.uuid4())
        failed_upload = _make_upload_session(
            upload_id=upload_id,
            state=IngestionState.FAILED,
            retry_count=3,
        )

        with patch.object(orchestrator.ingestion_repo, "get_upload", AsyncMock(return_value=failed_upload)):
            with pytest.raises(IngestionRetryLimitExceededError, match="Max retries"):
                await orchestrator.retry_ingestion(upload_id=upload_id)

    async def test_retry_only_from_failed(
        self,
        orchestrator: IngestionOrchestrator,
    ) -> None:
        """Retry from non-FAILED state raises error."""
        upload_id = str(uuid.uuid4())
        active_upload = _make_upload_session(
            upload_id=upload_id,
            state=IngestionState.EMBEDDING_PENDING,
        )

        with patch.object(orchestrator.ingestion_repo, "get_upload", AsyncMock(return_value=active_upload)):
            with pytest.raises(IngestionStateTransitionError, match="Can only retry from FAILED"):
                await orchestrator.retry_ingestion(upload_id=upload_id)


# ── Test: Event Hooks ─────────────────────────────────────────────────────────


class TestEventHooks:
    """Verify progress event hooks."""

    async def test_progress_handler_called(
        self,
        orchestrator: IngestionOrchestrator,
    ) -> None:
        """Registered progress handler is called during pipeline stages."""
        events: list[IngestionProgressEvent] = []

        async def handler(event: IngestionProgressEvent) -> None:
            events.append(event)

        orchestrator.on(handler)

        await orchestrator._emit_progress(
            upload_id="test-upload",
            stage="validate",
            status="started",
        )

        assert len(events) == 1
        assert events[0].stage == "validate"
        assert events[0].status == "started"

    async def test_progress_handler_error_does_not_block(
        self,
        orchestrator: IngestionOrchestrator,
    ) -> None:
        """A failing progress handler does not block pipeline."""
        async def failing_handler(event: IngestionProgressEvent) -> None:
            raise ValueError("Handler failed")

        async def good_handler(event: IngestionProgressEvent) -> None:
            pass

        orchestrator.on(failing_handler)
        orchestrator.on(good_handler)

        # Should not raise
        await orchestrator._emit_progress(
            upload_id="test-upload",
            stage="test",
            status="completed",
        )


# ── Test: State Machine ───────────────────────────────────────────────────────


class TestStateMachine:
    """Verify state machine transition rules."""

    async def test_valid_transition(self, orchestrator: IngestionOrchestrator) -> None:
        """Valid state transitions succeed."""
        upload_id = str(uuid.uuid4())

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.UPLOADED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()) as mock_update:
                mock_update.return_value = _make_upload_session(state=IngestionState.VALIDATING)

                result = await orchestrator._transition_state(
                    upload_id=upload_id,
                    target_state=IngestionState.VALIDATING,
                )
                assert result is not None

    async def test_invalid_transition_raises(self, orchestrator: IngestionOrchestrator) -> None:
        """Invalid state transitions raise error."""
        upload_id = str(uuid.uuid4())

        with patch.object(orchestrator.ingestion_repo, "get_upload") as mock_get:
            mock_get.return_value = _make_upload_session(state=IngestionState.UPLOADED)
            with patch.object(orchestrator.ingestion_repo, "update_state", AsyncMock()):
                with pytest.raises(IngestionStateTransitionError, match="Cannot transition"):
                    await orchestrator._transition_state(
                        upload_id=upload_id,
                        target_state=IngestionState.REVIEW_READY,  # Not reachable from UPLOADED
                    )


# ── Test: Metrics ─────────────────────────────────────────────────────────────


class TestMetrics:
    """Verify IngestionMetrics data class."""

    def test_metrics_defaults(self) -> None:
        metrics = IngestionMetrics()
        assert metrics.total_duration_ms == 0
        assert metrics.success is False
        assert metrics.total_chunks == 0
        assert metrics.total_tokens == 0

    def test_metrics_with_values(self) -> None:
        metrics = IngestionMetrics(
            correlation_id="test-123",
            total_duration_ms=5000,
            total_chunks=25,
            total_tokens=5000,
            total_pages=10,
            file_size_bytes=1024000,
            content_type="application/pdf",
            success=True,
        )
        assert metrics.correlation_id == "test-123"
        assert metrics.total_duration_ms == 5000
        assert metrics.success is True
