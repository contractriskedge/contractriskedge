"""Tests for upload and ingestion subsystem."""

from __future__ import annotations

import hashlib

import pytest
from app.domains.ingestion.security import (
    validate_extension,
    validate_content_type,
    validate_magic_bytes,
    validate_file_size,
    validate_filename_safety,
    FileValidationError,
    ALLOWED_TYPES,
)


class TestFileValidation:
    """Verify file type and content validation."""

    def test_valid_pdf_extension(self):
        assert validate_extension("contract.pdf") == "application/pdf"

    def test_valid_docx_extension(self):
        assert validate_extension("contract.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_valid_txt_extension(self):
        assert validate_extension("notes.txt") == "text/plain"

    def test_invalid_extension(self):
        with pytest.raises(FileValidationError, match="not supported"):
            validate_extension("malware.exe")

    def test_double_extension_rejected(self):
        with pytest.raises(FileValidationError):
            validate_extension("contract.pdf.exe")

    def test_valid_content_type(self):
        validate_content_type("application/pdf")  # Should not raise

    def test_invalid_content_type(self):
        with pytest.raises(FileValidationError, match="not supported"):
            validate_content_type("application/x-msdownload")

    def test_pdf_magic_bytes(self):
        """Verify PDF magic bytes (%PDF)."""
        data = b"%PDF-1.4\n...content..."
        validate_magic_bytes(data, "application/pdf")  # Should not raise

    def test_invalid_magic_bytes(self):
        """Verify rejection of mismatched magic bytes."""
        data = b"PK\x03\x04...zip content..."
        with pytest.raises(FileValidationError, match="magic bytes"):
            validate_magic_bytes(data, "application/pdf")

    def test_file_size_within_limit(self):
        validate_file_size(50_000_000)  # 50MB — should not raise

    def test_file_size_exceeds_limit(self):
        with pytest.raises(FileValidationError, match="exceeds maximum"):
            validate_file_size(200_000_000)  # 200MB

    def test_zero_file_size(self):
        with pytest.raises(FileValidationError, match="greater than 0"):
            validate_file_size(0)

    def test_filename_sanitization(self):
        assert validate_filename_safety("/etc/passwd") == "passwd"
        assert validate_filename_safety("../../contract.pdf") == "contract.pdf"

    def test_filename_path_traversal_rejected(self):
        with pytest.raises(FileValidationError, match="path traversal"):
            validate_filename_safety("../../../etc/passwd")


class TestChecksumValidation:
    """Verify checksum computation and matching."""

    def test_sha256_computation(self):
        from app.integrations.storage.s3 import storage_service
        data = b"test file content"
        checksum = storage_service.compute_sha256(data)
        expected = hashlib.sha256(data).hexdigest()
        assert checksum == expected

    def test_checksum_changes_with_content(self):
        from app.integrations.storage.s3 import storage_service
        c1 = storage_service.compute_sha256(b"content a")
        c2 = storage_service.compute_sha256(b"content b")
        assert c1 != c2


class TestTenantIsolation:
    """Verify tenant isolation in upload paths and storage keys."""

    def test_storage_key_contains_tenant(self):
        from app.integrations.storage.s3 import storage_service
        key = storage_service.build_object_key("tenant-abc", "contract.pdf")
        assert "tenant-abc" in key
        assert key.endswith("contract.pdf")

    def test_storage_keys_differ_by_tenant(self):
        from app.integrations.storage.s3 import storage_service
        key_a = storage_service.build_object_key("tenant-a", "doc.pdf")
        key_b = storage_service.build_object_key("tenant-b", "doc.pdf")
        assert key_a != key_b
        assert "tenant-a" in key_a
        assert "tenant-b" in key_b


class TestIngestionStateMachine:
    """Verify ingestion state transitions."""

    def test_valid_transition(self):
        from app.domains.ingestion.models import IngestionState
        assert IngestionState.UPLOADED.can_transition_to(IngestionState.VALIDATING)
        assert IngestionState.VALIDATING.can_transition_to(IngestionState.VALIDATED)
        assert IngestionState.REVIEW_READY.can_transition_to(IngestionState.REVIEW_READY) is False

    def test_invalid_transition(self):
        from app.domains.ingestion.models import IngestionState
        assert IngestionState.UPLOADED.can_transition_to(IngestionState.REVIEW_READY) is False
        assert IngestionState.REVIEW_READY.can_transition_to(IngestionState.UPLOADED) is False

    def test_fail_from_any_state(self):
        from app.domains.ingestion.models import IngestionState
        for state in IngestionState:
            if state not in (IngestionState.FAILED, IngestionState.CANCELLED, IngestionState.QUARANTINED, IngestionState.REVIEW_READY):
                assert state.can_transition_to(IngestionState.FAILED), f"{state.value} should allow FAILED"

    def test_retry_from_failed(self):
        from app.domains.ingestion.models import IngestionState
        assert IngestionState.FAILED.can_transition_to(IngestionState.UPLOADED)


class TestUploadSchemas:
    """Verify Pydantic schema validation."""

    def test_valid_upload_request(self):
        from app.domains.ingestion.schemas import UploadInitiateRequest
        req = UploadInitiateRequest(
            filename="contract.pdf",
            content_type="application/pdf",
            file_size=50_000,
        )
        assert req.filename == "contract.pdf"

    def test_invalid_content_type_rejected(self):
        from app.domains.ingestion.schemas import UploadInitiateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="not supported"):
            UploadInitiateRequest(
                filename="virus.exe",
                content_type="application/x-msdownload",
                file_size=1000,
            )

    def test_file_size_too_large_rejected(self):
        from app.domains.ingestion.schemas import UploadInitiateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UploadInitiateRequest(
                filename="huge.pdf",
                content_type="application/pdf",
                file_size=500_000_000,
            )

    def test_filename_path_traversal_rejected(self):
        from app.domains.ingestion.schemas import UploadInitiateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UploadInitiateRequest(
                filename="../../etc/passwd",
                content_type="text/plain",
                file_size=100,
            )
