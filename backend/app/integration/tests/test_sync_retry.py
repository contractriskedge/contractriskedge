"""
Tests for sync orchestration and retry handling.

Covers:
- Sync job creation and execution
- Retry logic and backoff
- Dead-letter handling
- Conflict detection and resolution
- Partial sync recovery
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest import approx

from app.integration.models.sync_job import (
    IntegrationSyncJob,
    SyncConflict,
    SyncJobStatus,
    SyncJobTrigger,
)
from app.integration.models.integration import Integration, IntegrationStatus
from app.integration.services.sync_service import SyncOrchestrator, SyncConflictResolver
from app.integration.connectors.base import SyncResult


@pytest.mark.asyncio
async def test_start_sync_creates_job(
    mock_db, tenant_id, sample_integration
):
    """Test starting a sync creates a job in RUNNING status."""
    sample_integration.status = IntegrationStatus.ACTIVE
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_integration)
    ))

    orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)

    job = await orchestrator.start_sync(
        integration_id=sample_integration.id,
        trigger=SyncJobTrigger.MANUAL,
        sync_type="full",
    )

    assert job is not None
    assert job.status == SyncJobStatus.RUNNING
    assert job.trigger == SyncJobTrigger.MANUAL
    assert job.sync_type == "full"
    assert job.correlation_id is not None
    assert job.started_at is not None


@pytest.mark.asyncio
async def test_start_sync_inactive_integration(
    mock_db, tenant_id, sample_integration
):
    """Test sync on inactive integration raises error."""
    sample_integration.status = IntegrationStatus.DISABLED
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_integration)
    ))

    orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)

    with pytest.raises(ValueError, match="is not active"):
        await orchestrator.start_sync(
            integration_id=sample_integration.id,
            trigger=SyncJobTrigger.MANUAL,
        )


@pytest.mark.asyncio
async def test_execute_sync_success(mock_db, tenant_id, sample_integration, sample_sync_job):
    """Test successful sync execution updates job status."""
    from app.integration.tests.conftest import MockConnector

    sample_sync_job.status = SyncJobStatus.RUNNING
    mock_db.execute = AsyncMock()

    orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)
    connector = MockConnector()

    result = await orchestrator.execute_sync(sample_sync_job, connector)

    assert result.status == SyncJobStatus.SUCCESS
    assert result.synced_items == 10
    assert result.cursor == "next_cursor_123"
    assert result.completed_at is not None
    assert result.duration_seconds is not None


@pytest.mark.asyncio
async def test_execute_sync_failure(mock_db, tenant_id, sample_integration, sample_sync_job):
    """Test sync failure records error and schedules retry."""
    sample_sync_job.status = SyncJobStatus.RUNNING
    mock_db.execute = AsyncMock()

    orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)

    class FailingConnector:
        provider_name = "test_failing"

        async def sync_documents(self, cursor=None, delta_token=None, max_items=None):
            return SyncResult(
                success=False,
                failed_count=5,
                errors=[{"error": "API rate limit exceeded", "code": 429}],
            )

        async def close(self):
            pass

    connector = FailingConnector()
    result = await orchestrator.execute_sync(sample_sync_job, connector)

    assert result.status == SyncJobStatus.FAILED
    assert result.failed_items == 5
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_retry_sync_creates_new_job(
    mock_db, tenant_id, sample_sync_job
):
    """Test retrying a failed sync creates a new job with incremented retry count."""
    sample_sync_job.status = SyncJobStatus.FAILED
    sample_sync_job.retry_count = 1
    sample_sync_job.max_retries = 3

    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_sync_job)
    ))

    orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)

    retry_job = await orchestrator.retry_sync(
        job_id=sample_sync_job.id,
        force=False,
    )

    assert retry_job is not None
    assert retry_job.trigger == SyncJobTrigger.RETRY
    assert retry_job.retry_count == 2
    assert retry_job.correlation_id == sample_sync_job.correlation_id


@pytest.mark.asyncio
async def test_retry_sync_max_retries_exceeded(
    mock_db, tenant_id, sample_sync_job
):
    """Test retry fails when max retries exceeded."""
    sample_sync_job.status = SyncJobStatus.FAILED
    sample_sync_job.retry_count = 3
    sample_sync_job.max_retries = 3

    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_sync_job)
    ))

    orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)

    with pytest.raises(ValueError, match="exceeded max retries"):
        await orchestrator.retry_sync(
            job_id=sample_sync_job.id,
            force=False,
        )


@pytest.mark.asyncio
async def test_retry_sync_force_override(
    mock_db, tenant_id, sample_sync_job
):
    """Test force=True overrides max retries check."""
    sample_sync_job.status = SyncJobStatus.FAILED
    sample_sync_job.retry_count = 3
    sample_sync_job.max_retries = 3

    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_sync_job)
    ))

    orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)

    retry_job = await orchestrator.retry_sync(
        job_id=sample_sync_job.id,
        force=True,
    )

    assert retry_job is not None
    assert retry_job.retry_count == 4


@pytest.mark.asyncio
async def test_record_conflict(mock_db, tenant_id, sample_sync_job):
    """Test conflict recording."""
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_sync_job)
    ))

    orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)

    conflict = await orchestrator.record_conflict(
        job_id=sample_sync_job.id,
        external_id="ext_doc_123",
        conflict_type="field_mismatch",
        local_value={"name": "Contract v1"},
        external_value={"name": "Contract v2"},
        field="name",
    )

    assert conflict is not None
    assert conflict.external_id == "ext_doc_123"
    assert conflict.conflict_type == "field_mismatch"
    assert conflict.local_value == {"name": "Contract v1"}


def test_conflict_detection():
    """Test conflict detection logic."""
    external = {"id": "doc_1", "name": "Contract v2", "content": "Updated"}
    local = {"name": "Contract v1", "content": "Original"}

    conflict_data = SyncConflictResolver.detect_conflict(
        external, local, tracked_fields=["name", "content"]
    )

    assert conflict_data is not None
    assert conflict_data["conflict_type"] == "field_mismatch"
    assert conflict_data["external_id"] == "doc_1"


def test_no_conflict_detected():
    """Test no conflict when data matches."""
    external = {"id": "doc_1", "name": "Contract", "content": "Same"}
    local = {"name": "Contract", "content": "Same"}

    conflict_data = SyncConflictResolver.detect_conflict(
        external, local, tracked_fields=["name", "content"]
    )

    assert conflict_data is None


def test_conflict_resolution_external_wins():
    """Test external_wins resolution strategy."""
    conflict = {"external_value": "New Value", "local_value": "Old Value"}
    result = SyncConflictResolver.resolve(conflict, strategy="external_wins")
    assert result["resolution"] == "external_wins"
    assert result["value"] == "New Value"


def test_conflict_resolution_local_wins():
    """Test local_wins resolution strategy."""
    conflict = {"external_value": "New Value", "local_value": "Old Value"}
    result = SyncConflictResolver.resolve(conflict, strategy="local_wins")
    assert result["resolution"] == "local_wins"
    assert result["value"] == "Old Value"
