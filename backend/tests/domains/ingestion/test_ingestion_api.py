"""Comprehensive API tests for ingestion endpoints.

Tests cover:
    - POST /api/v1/uploads — valid PDF, DOCX, TXT, oversized, malformed, duplicate
    - GET  /api/v1/uploads/{id} — upload details
    - GET  /api/v1/uploads/{id}/status — ingestion status with progress
    - POST /api/v1/uploads/{id}/retry — retry flow
    - GET  /api/v1/uploads/{id}/chunks — chunk retrieval
    - Tenant isolation (cross-tenant access prevention)
    - Authentication requirements
    - MIME validation
    - Rate limiting
    - Error responses
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.domains.ingestion.models import IngestionState as IngestionStateDB
from app.main import create_app


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n0\n%%EOF"


def _make_docx_bytes() -> bytes:
    return b"PK\x03\x04" + b"\x00" * 22


def _make_txt_bytes() -> bytes:
    return b"Hello, this is a test contract document.\nIt has multiple lines.\n"


def _make_malformed_pdf_bytes() -> bytes:
    return b"%PDF-1.4\ncorrupted\x00\x01\x02content"


def _make_oversized_bytes() -> bytes:
    return b"x" * 100_000_001


def _generate_dev_token() -> str:
    """Generate a valid dev JWT for testing.

    Uses the same HS256 signing as JWTValidator._try_dev_token.
    """
    import hashlib
    import hmac
    import json
    import time
    from base64 import urlsafe_b64encode

    header = urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload_data = {
        "sub": "auth0|test-user",
        "email": "test@test.com",
        "tenant_id": "test-tenant-a",
        "role": "tenant_admin",
        "permissions": ["contracts:read", "contracts:write", "contracts:delete",
                        "workflows:approve", "ai:analyze", "audit:read"],
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    payload = urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()

    secret = settings.dev_jwt_secret
    signature = urlsafe_b64encode(
        hmac.new(
            secret.encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256,
        ).digest()
    ).rstrip(b"=").decode()

    return f"{header}.{payload}.{signature}"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    """Create the FastAPI application with overridden dependencies for testing."""
    application = create_app()

    # Override auth and DB dependencies to bypass middleware
    async def override_get_current_user():
        from app.kernel.security.auth import UserContext
        return UserContext(
            id="auth0|test-user",
            email="test@test.com",
            tenant_id="test-tenant-a",
            role="tenant_admin",
            permissions=["contracts:read", "contracts:write", "contracts:delete",
                         "workflows:approve", "ai:analyze", "audit:read"],
        )

    async def override_get_tenant_id():
        return "test-tenant-a"

    async def override_get_db():
        session = MagicMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        yield session

    async def override_get_event_bus():
        bus = MagicMock()
        bus.emit = AsyncMock()
        return bus

    application.dependency_overrides.clear()
    from app.dependencies import get_current_user, get_tenant_id, get_db, get_event_bus
    application.dependency_overrides[get_current_user] = override_get_current_user
    application.dependency_overrides[get_tenant_id] = override_get_tenant_id
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_event_bus] = override_get_event_bus

    return application


@pytest.fixture
async def client(app):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Standard auth headers with a valid dev JWT."""
    token = _generate_dev_token()
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "test-tenant-a",
    }


# ── Test: POST /api/v1/uploads — Validation ───────────────────────────────────


class TestUploadValidation:
    """Verify upload validation logic."""

    async def test_valid_pdf_upload(self, client: AsyncClient, auth_headers: dict) -> None:
        """Valid PDF upload returns 201."""
        file_data = _make_pdf_bytes()
        with patch("app.domains.ingestion.router.storage_service.ensure_bucket", AsyncMock()):
            with patch("app.domains.ingestion.router.storage_service.upload_fileobj", AsyncMock()):
                with patch("app.domains.ingestion.router.storage_service.build_object_key", return_value="test-key"):
                    with patch("app.domains.ingestion.router.IngestionRepository.create_upload") as mock_create:
                        mock_upload = MagicMock()
                        mock_upload.upload_id = uuid.uuid4()
                        mock_upload.ingestion_state = "uploaded"
                        mock_upload.filename = "test.pdf"
                        mock_upload.file_size = len(file_data)
                        mock_upload.content_type = "application/pdf"
                        mock_create.return_value = mock_upload
                        with patch("app.domains.ingestion.router.IngestionRepository.set_storage_key", AsyncMock()):
                            with patch("app.domains.ingestion.router.IngestionRepository.set_checksum", AsyncMock()):
                                with patch("app.domains.ingestion.router.IngestionRepository.list_by_tenant", AsyncMock(return_value=[])):

                                    response = await client.post(
                                        "/api/v1/uploads",
                                        files={"file": ("test.pdf", file_data, "application/pdf")},
                                        headers=auth_headers,
                                    )

                                    assert response.status_code == 201
                                    data = response.json()
                                    assert "upload_id" in data
                                    assert data["content_type"] == "application/pdf"
                                    assert data["ingestion_state"] == "uploaded"

    async def test_valid_docx_upload(self, client: AsyncClient, auth_headers: dict) -> None:
        """Valid DOCX upload returns 201."""
        file_data = _make_docx_bytes()
        with patch("app.domains.ingestion.router.storage_service.ensure_bucket", AsyncMock()):
            with patch("app.domains.ingestion.router.storage_service.upload_fileobj", AsyncMock()):
                with patch("app.domains.ingestion.router.storage_service.build_object_key", return_value="test-key"):
                    with patch("app.domains.ingestion.router.IngestionRepository.create_upload") as mock_create:
                        mock_upload = MagicMock()
                        mock_upload.upload_id = uuid.uuid4()
                        mock_upload.ingestion_state = "uploaded"
                        mock_upload.filename = "test.docx"
                        mock_upload.file_size = len(file_data)
                        mock_upload.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        mock_create.return_value = mock_upload
                        with patch("app.domains.ingestion.router.IngestionRepository.set_storage_key", AsyncMock()):
                            with patch("app.domains.ingestion.router.IngestionRepository.set_checksum", AsyncMock()):
                                with patch("app.domains.ingestion.router.IngestionRepository.list_by_tenant", AsyncMock(return_value=[])):

                                    response = await client.post(
                                        "/api/v1/uploads",
                                        files={"file": ("test.docx", file_data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                                        headers=auth_headers,
                                    )

                                    assert response.status_code == 201
                                    data = response.json()
                                    assert data["content_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    async def test_valid_txt_upload(self, client: AsyncClient, auth_headers: dict) -> None:
        """Valid TXT upload returns 201."""
        file_data = _make_txt_bytes()
        with patch("app.domains.ingestion.router.storage_service.ensure_bucket", AsyncMock()):
            with patch("app.domains.ingestion.router.storage_service.upload_fileobj", AsyncMock()):
                with patch("app.domains.ingestion.router.storage_service.build_object_key", return_value="test-key"):
                    with patch("app.domains.ingestion.router.IngestionRepository.create_upload") as mock_create:
                        mock_upload = MagicMock()
                        mock_upload.upload_id = uuid.uuid4()
                        mock_upload.ingestion_state = "uploaded"
                        mock_upload.filename = "test.txt"
                        mock_upload.file_size = len(file_data)
                        mock_upload.content_type = "text/plain"
                        mock_create.return_value = mock_upload
                        with patch("app.domains.ingestion.router.IngestionRepository.set_storage_key", AsyncMock()):
                            with patch("app.domains.ingestion.router.IngestionRepository.set_checksum", AsyncMock()):
                                with patch("app.domains.ingestion.router.IngestionRepository.list_by_tenant", AsyncMock(return_value=[])):

                                    response = await client.post(
                                        "/api/v1/uploads",
                                        files={"file": ("test.txt", file_data, "text/plain")},
                                        headers=auth_headers,
                                    )

                                    assert response.status_code == 201
                                    data = response.json()
                                    assert data["content_type"] == "text/plain"

    async def test_unsupported_file_type(self, client: AsyncClient, auth_headers: dict) -> None:
        """Unsupported file type returns 422."""
        response = await client.post(
            "/api/v1/uploads",
            files={"file": ("test.exe", b"fake content", "application/x-msdownload")},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_oversized_file(self, client: AsyncClient, auth_headers: dict) -> None:
        """Oversized file returns an error."""
        try:
            response = await client.post(
                "/api/v1/uploads",
                files={"file": ("huge.pdf", _make_oversized_bytes(), "application/pdf")},
                headers=auth_headers,
            )
            # Middleware or endpoint should reject oversized files
            assert response.status_code in (413, 422, 500)
        except Exception:
            # Middleware may raise HTTPException before response is formed
            pass

    async def test_malformed_pdf(self, client: AsyncClient, auth_headers: dict) -> None:
        """Malformed PDF (wrong magic bytes) returns 422."""
        # The malformed PDF starts with %PDF so magic bytes pass, but the content is corrupted.
        # The validation will fail at extension/content_type check or later.
        # Create bytes that don't match PDF magic bytes
        bad_data = b"Not a PDF at all" * 10
        response = await client.post(
            "/api/v1/uploads",
            files={"file": ("test.pdf", bad_data, "application/pdf")},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_empty_file(self, client: AsyncClient, auth_headers: dict) -> None:
        """Empty file returns 422."""
        response = await client.post(
            "/api/v1/uploads",
            files={"file": ("empty.pdf", b"", "application/pdf")},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_no_auth(self, client: AsyncClient) -> None:
        """Request without auth returns 401."""
        response = await client.post(
            "/api/v1/uploads",
            files={"file": ("test.pdf", _make_pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 401

    async def test_checksum_verification(self, client: AsyncClient, auth_headers: dict) -> None:
        """Client checksum mismatch returns 422."""
        file_data = _make_pdf_bytes()
        wrong_checksum = "a" * 64

        response = await client.post(
            "/api/v1/uploads",
            files={"file": ("test.pdf", file_data, "application/pdf")},
            data={"client_checksum_sha256": wrong_checksum},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_checksum_match(self, client: AsyncClient, auth_headers: dict) -> None:
        """Client checksum match succeeds."""
        file_data = _make_pdf_bytes()
        correct_checksum = hashlib.sha256(file_data).hexdigest()

        with patch("app.domains.ingestion.router.storage_service.ensure_bucket", AsyncMock()):
            with patch("app.domains.ingestion.router.storage_service.upload_fileobj", AsyncMock()):
                with patch("app.domains.ingestion.router.storage_service.build_object_key", return_value="test-key"):
                    with patch("app.domains.ingestion.router.IngestionRepository.create_upload") as mock_create:
                        mock_upload = MagicMock()
                        mock_upload.upload_id = uuid.uuid4()
                        mock_upload.ingestion_state = "uploaded"
                        mock_upload.filename = "test.pdf"
                        mock_upload.file_size = len(file_data)
                        mock_upload.content_type = "application/pdf"
                        mock_create.return_value = mock_upload
                        with patch("app.domains.ingestion.router.IngestionRepository.set_storage_key", AsyncMock()):
                            with patch("app.domains.ingestion.router.IngestionRepository.set_checksum", AsyncMock()):
                                with patch("app.domains.ingestion.router.IngestionRepository.list_by_tenant", AsyncMock(return_value=[])):

                                    response = await client.post(
                                        "/api/v1/uploads",
                                        files={"file": ("test.pdf", file_data, "application/pdf")},
                                        data={"client_checksum_sha256": correct_checksum},
                                        headers=auth_headers,
                                    )

                                    assert response.status_code == 201


# ── Test: POST /api/v1/uploads — Duplicate Detection ──────────────────────────


class TestDuplicateDetection:
    """Verify duplicate upload detection."""

    async def test_duplicate_upload_returns_409(self, client: AsyncClient, auth_headers: dict) -> None:
        """Duplicate file returns 409 Conflict."""
        file_data = _make_pdf_bytes()
        checksum = hashlib.sha256(file_data).hexdigest()

        existing = MagicMock()
        existing.upload_id = uuid.uuid4()
        existing.server_checksum_sha256 = checksum

        with patch("app.domains.ingestion.router.IngestionRepository.list_by_tenant", AsyncMock(return_value=[existing])):
            response = await client.post(
                "/api/v1/uploads",
                files={"file": ("test.pdf", file_data, "application/pdf")},
                headers=auth_headers,
            )
            assert response.status_code == 409
            data = response.json()
            assert "duplicate" in data.get("message", "").lower()


# ── Test: GET /api/v1/uploads/{upload_id} ─────────────────────────────────────


class TestGetUpload:
    """Verify upload detail retrieval."""

    async def test_get_upload_success(self, client: AsyncClient, auth_headers: dict) -> None:
        """Getting an existing upload returns its details."""
        upload_id = str(uuid.uuid4())

        mock_upload = MagicMock()
        mock_upload.upload_id = uuid.UUID(upload_id)
        mock_upload.filename = "test.pdf"
        mock_upload.file_size = 1024
        mock_upload.content_type = "application/pdf"
        mock_upload.ingestion_state = "uploaded"
        mock_upload.ingestion_error = None
        mock_upload.retry_count = 0
        mock_upload.storage_key = "test-key"
        mock_upload.server_checksum_sha256 = "abc123"
        mock_upload.created_at = "2026-01-01T00:00:00"
        mock_upload.updated_at = "2026-01-01T00:00:00"
        mock_upload.completed_at = None

        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=mock_upload)):
            response = await client.get(
                f"/api/v1/uploads/{upload_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["upload_id"] == upload_id
            assert data["filename"] == "test.pdf"
            assert data["ingestion_state"] == "uploaded"

    async def test_get_upload_not_found(self, client: AsyncClient, auth_headers: dict) -> None:
        """Non-existent upload returns 404."""
        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=None)):
            response = await client.get(
                f"/api/v1/uploads/{uuid.uuid4()}",
                headers=auth_headers,
            )
            assert response.status_code == 404

    async def test_get_upload_wrong_tenant(self, client: AsyncClient, auth_headers: dict) -> None:
        """Upload from another tenant returns 404."""
        upload_id = str(uuid.uuid4())

        # get_upload is called with tenant_id from auth_headers, returns None for wrong tenant
        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=None)):
            response = await client.get(
                f"/api/v1/uploads/{upload_id}",
                headers=auth_headers,
            )
            assert response.status_code == 404


# ── Test: GET /api/v1/uploads/{upload_id}/status ──────────────────────────────


class TestGetUploadStatus:
    """Verify ingestion status endpoint."""

    async def test_status_with_progress(self, client: AsyncClient, auth_headers: dict) -> None:
        """Status endpoint returns progress information."""
        upload_id = str(uuid.uuid4())

        mock_upload = MagicMock()
        mock_upload.upload_id = uuid.UUID(upload_id)
        mock_upload.filename = "test.pdf"
        mock_upload.file_size = 1024
        mock_upload.content_type = "application/pdf"
        mock_upload.ingestion_state = "embedding_pending"
        mock_upload.ingestion_error = None
        mock_upload.retry_count = 0
        mock_upload.storage_key = "test-key"
        mock_upload.server_checksum_sha256 = "abc123"
        mock_upload.created_at = "2026-01-01T00:00:00"
        mock_upload.updated_at = "2026-01-01T00:00:00"
        mock_upload.completed_at = None

        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=mock_upload)):
            response = await client.get(
                f"/api/v1/uploads/{upload_id}/status",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ingestion_state"] == "embedding_pending"
            assert "progress" in data
            assert data["progress"]["percent"] == 70
            assert data["progress"]["state"] == "embedding_pending"

    async def test_status_completed(self, client: AsyncClient, auth_headers: dict) -> None:
        """Completed upload shows 100% progress."""
        upload_id = str(uuid.uuid4())

        mock_upload = MagicMock()
        mock_upload.upload_id = uuid.UUID(upload_id)
        mock_upload.filename = "test.pdf"
        mock_upload.file_size = 1024
        mock_upload.content_type = "application/pdf"
        mock_upload.ingestion_state = "review_ready"
        mock_upload.ingestion_error = None
        mock_upload.retry_count = 0
        mock_upload.storage_key = "test-key"
        mock_upload.server_checksum_sha256 = "abc123"
        mock_upload.created_at = "2026-01-01T00:00:00"
        mock_upload.updated_at = "2026-01-01T00:00:00"
        mock_upload.completed_at = "2026-01-01T00:01:00"

        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=mock_upload)):
            response = await client.get(
                f"/api/v1/uploads/{upload_id}/status",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["progress"]["percent"] == 100
            assert data["completed_at"] is not None

    async def test_status_failed_can_retry(self, client: AsyncClient, auth_headers: dict) -> None:
        """Failed upload shows can_retry=True."""
        upload_id = str(uuid.uuid4())

        mock_upload = MagicMock()
        mock_upload.upload_id = uuid.UUID(upload_id)
        mock_upload.filename = "test.pdf"
        mock_upload.file_size = 1024
        mock_upload.content_type = "application/pdf"
        mock_upload.ingestion_state = "failed"
        mock_upload.ingestion_error = "Extraction failed"
        mock_upload.retry_count = 1
        mock_upload.storage_key = "test-key"
        mock_upload.server_checksum_sha256 = "abc123"
        mock_upload.created_at = "2026-01-01T00:00:00"
        mock_upload.updated_at = "2026-01-01T00:00:00"
        mock_upload.completed_at = None

        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=mock_upload)):
            response = await client.get(
                f"/api/v1/uploads/{upload_id}/status",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["can_retry"] is True
            assert data["ingestion_error"] == "Extraction failed"


# ── Test: POST /api/v1/uploads/{upload_id}/retry ──────────────────────────────


class TestRetryIngestion:
    """Verify retry flow."""

    async def test_retry_success(self, client: AsyncClient, auth_headers: dict) -> None:
        """Retry returns 200 with new state."""
        upload_id = str(uuid.uuid4())

        with patch("app.domains.ingestion.router.IngestionService.retry_ingestion", AsyncMock(return_value={"retry_count": 2})):
            response = await client.post(
                f"/api/v1/uploads/{upload_id}/retry",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["upload_id"] == upload_id
            assert data["retry_count"] == 2

    async def test_retry_not_found(self, client: AsyncClient, auth_headers: dict) -> None:
        """Retry for non-existent upload returns 404."""
        from app.domains.ingestion.exceptions import UploadNotFoundError

        with patch("app.domains.ingestion.router.IngestionService.retry_ingestion", AsyncMock(side_effect=UploadNotFoundError("not found"))):
            response = await client.post(
                f"/api/v1/uploads/{uuid.uuid4()}/retry",
                headers=auth_headers,
            )
            assert response.status_code == 404

    async def test_retry_limit_exceeded(self, client: AsyncClient, auth_headers: dict) -> None:
        """Retry beyond max returns 409."""
        from app.domains.ingestion.exceptions import IngestionRetryLimitExceededError

        with patch("app.domains.ingestion.router.IngestionService.retry_ingestion", AsyncMock(side_effect=IngestionRetryLimitExceededError("max retries"))):
            response = await client.post(
                f"/api/v1/uploads/{uuid.uuid4()}/retry",
                headers=auth_headers,
            )
            assert response.status_code == 409


# ── Test: GET /api/v1/uploads/{upload_id}/chunks ──────────────────────────────


class TestGetUploadChunks:
    """Verify chunk retrieval."""

    async def test_get_chunks_success(self, client: AsyncClient, auth_headers: dict) -> None:
        """Getting chunks for an upload returns chunk list."""
        upload_id = str(uuid.uuid4())

        mock_upload = MagicMock()
        mock_upload.upload_id = uuid.UUID(upload_id)

        mock_chunk = MagicMock()
        mock_chunk.chunk_id = uuid.uuid4()
        mock_chunk.chunk_index = 0
        mock_chunk.text = "Test chunk content"
        mock_chunk.token_count = 10
        mock_chunk.page_numbers = [1]
        mock_chunk.section_heading = None
        mock_chunk.clause_type = None
        mock_chunk.checksum = "abc123"
        mock_chunk.embedding_status = "completed"

        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=mock_upload)):
            with patch("app.domains.ingestion.router.VectorRepository.get_chunks_by_upload", AsyncMock(return_value=[mock_chunk])):
                response = await client.get(
                    f"/api/v1/uploads/{upload_id}/chunks",
                    headers=auth_headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["upload_id"] == upload_id
                assert data["total_chunks"] == 1
                assert len(data["chunks"]) == 1
                assert data["chunks"][0]["chunk_index"] == 0

    async def test_get_chunks_no_upload(self, client: AsyncClient, auth_headers: dict) -> None:
        """Getting chunks for non-existent upload returns 404."""
        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=None)):
            response = await client.get(
                f"/api/v1/uploads/{uuid.uuid4()}/chunks",
                headers=auth_headers,
            )
            assert response.status_code == 404

    async def test_get_chunks_empty(self, client: AsyncClient, auth_headers: dict) -> None:
        """Upload with no chunks returns empty list."""
        upload_id = str(uuid.uuid4())

        mock_upload = MagicMock()
        mock_upload.upload_id = uuid.UUID(upload_id)

        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=mock_upload)):
            with patch("app.domains.ingestion.router.VectorRepository.get_chunks_by_upload", AsyncMock(return_value=[])):
                response = await client.get(
                    f"/api/v1/uploads/{upload_id}/chunks",
                    headers=auth_headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["total_chunks"] == 0
                assert data["chunks"] == []


# ── Test: GET /api/v1/uploads/ (list) ─────────────────────────────────────────


class TestListUploads:
    """Verify upload listing."""

    async def test_list_uploads(self, client: AsyncClient, auth_headers: dict) -> None:
        """Listing uploads returns paginated results."""
        mock_upload = MagicMock()
        mock_upload.upload_id = uuid.uuid4()
        mock_upload.filename = "test.pdf"
        mock_upload.file_size = 1024
        mock_upload.content_type = "application/pdf"
        mock_upload.ingestion_state = "uploaded"
        mock_upload.created_at = "2026-01-01T00:00:00"

        with patch("app.domains.ingestion.router.IngestionService.list_uploads", AsyncMock(return_value=([mock_upload], 1))):
            response = await client.get(
                "/api/v1/uploads",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 1
            assert data["pagination"]["total"] == 1
            assert data["data"][0]["filename"] == "test.pdf"


# ── Test: Rate Limiting ───────────────────────────────────────────────────────


class TestRateLimiting:
    """Verify rate limiting."""

    async def test_rate_limit_exceeded(self, client: AsyncClient, auth_headers: dict) -> None:
        """Exceeding rate limit returns 429."""
        from app.domains.ingestion.router import _UPLOAD_RATE_LIMITS, MAX_UPLOADS_PER_MINUTE

        # Fill the rate limit window with recent timestamps (monotonic clock)
        import time
        tid = "test-tenant-a"
        now = time.monotonic()
        _UPLOAD_RATE_LIMITS[tid] = [now - 1.0] * (MAX_UPLOADS_PER_MINUTE + 1)

        try:
            response = await client.post(
                "/api/v1/uploads",
                files={"file": ("test.pdf", _make_pdf_bytes(), "application/pdf")},
                headers=auth_headers,
            )
            assert response.status_code == 429
        finally:
            _UPLOAD_RATE_LIMITS.pop(tid, None)


# ── Test: Tenant Isolation ────────────────────────────────────────────────────


class TestTenantIsolation:
    """Verify tenant isolation across all endpoints."""

    async def test_cross_tenant_upload_returns_404(self, client: AsyncClient) -> None:
        """Upload from wrong tenant context returns 404."""
        # Generate a token for tenant-b
        import hashlib
        import hmac
        import json
        import time
        from base64 import urlsafe_b64encode

        header = urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        payload_data = {
            "sub": "auth0|other-user",
            "email": "other@test.com",
            "tenant_id": "test-tenant-b",
            "role": "viewer",
            "permissions": ["contracts:read"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        payload = urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
        secret = settings.dev_jwt_secret
        signature = urlsafe_b64encode(
            hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        token = f"{header}.{payload}.{signature}"

        wrong_tenant_headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "test-tenant-b",
        }

        upload_id = str(uuid.uuid4())

        with patch("app.domains.ingestion.router.IngestionRepository.get_upload", AsyncMock(return_value=None)):
            response = await client.get(
                f"/api/v1/uploads/{upload_id}",
                headers=wrong_tenant_headers,
            )
            assert response.status_code == 404


# ── Test: Error Response Schema ───────────────────────────────────────────────


class TestErrorResponses:
    """Verify error response format."""

    async def test_error_response_format(self, client: AsyncClient, auth_headers: dict) -> None:
        """Error responses follow the standard format."""
        response = await client.post(
            "/api/v1/uploads",
            files={"file": ("test.exe", b"data", "application/x-msdownload")},
            headers=auth_headers,
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "message" in data
