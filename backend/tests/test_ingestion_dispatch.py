"""Tests for ingestion pipeline redispatch helpers."""

from unittest.mock import MagicMock, patch

from app.domains.ingestion.models import IngestionState
from workers.ingestion_dispatch import redispatch_ingestion


def test_redispatch_uploaded_calls_ingest_document():
    with patch("workers.ingestion_tasks.ingest_document") as ingest:
        ingest.delay = MagicMock()
        action = redispatch_ingestion("upload-1", "tenant-1", "user-1", IngestionState.UPLOADED)
        ingest.delay.assert_called_once_with("upload-1", "tenant-1", "user-1")
        assert action == "ingest_document"


def test_redispatch_validating_calls_validate_upload():
    with patch("workers.ingestion.validate_upload_task") as validate:
        validate.delay = MagicMock()
        action = redispatch_ingestion("upload-2", "tenant-1", "user-1", IngestionState.VALIDATING)
        validate.delay.assert_called_once_with("upload-2", "tenant-1", "user-1")
        assert action == "validate_upload"


def test_redispatch_uploaded_calls_ingest_document_not_validate():
    """UPLOADED must call ingest_document (validate_upload requires VALIDATING)."""
    with patch("workers.ingestion.validate_upload_task") as validate:
        with patch("workers.ingestion_tasks.ingest_document") as ingest:
            ingest.delay = MagicMock()
            validate.delay = MagicMock()
            action = redispatch_ingestion("upload-3", "tenant-1", "user-1", IngestionState.UPLOADED)
            ingest.delay.assert_called_once_with("upload-3", "tenant-1", "user-1")
            validate.delay.assert_not_called()
            assert action == "ingest_document"
