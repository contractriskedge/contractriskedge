"""Tests for the ingestion queue module."""

from __future__ import annotations

import pytest
from datetime import datetime

from ingestion.models import JobRecord, JobStatus
from ingestion.queue import IngestionQueue, JobNotFoundError, JobStateError


@pytest.mark.asyncio
async def test_enqueue_and_get_job():
    """Test that a job can be enqueued and retrieved."""
    queue = IngestionQueue(redis_url="redis://localhost:6379/0")

    job = JobRecord(
        document_id="doc-123",
        tenant_id="tenant-1",
        user_id="user-1",
        filename="test.pdf",
        content_type="application/pdf",
    )

    job_id = await queue.enqueue(job)
    assert job_id is not None

    retrieved = await queue.get_job(job_id)
    assert retrieved is not None
    assert retrieved.document_id == "doc-123"
    assert retrieved.status == JobStatus.PENDING

    await queue.remove_job(job_id)


@pytest.mark.asyncio
async def test_status_transitions():
    """Test valid and invalid status transitions."""
    queue = IngestionQueue(redis_url="redis://localhost:6379/0")

    job = JobRecord(
        document_id="doc-456",
        tenant_id="tenant-1",
        user_id="user-1",
        filename="test.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    job_id = await queue.enqueue(job)

    # Valid: PENDING -> PROCESSING
    updated = await queue.update_status(job_id, JobStatus.PROCESSING)
    assert updated.status == JobStatus.PROCESSING

    # Valid: PROCESSING -> DONE
    updated = await queue.update_status(job_id, JobStatus.DONE)
    assert updated.status == JobStatus.DONE
    assert updated.completed_at is not None

    await queue.remove_job(job_id)


@pytest.mark.asyncio
async def test_invalid_status_transition():
    """Test that invalid status transitions raise an error."""
    queue = IngestionQueue(redis_url="redis://localhost:6379/0")

    job = JobRecord(
        document_id="doc-789",
        tenant_id="tenant-1",
        user_id="user-1",
        filename="test.txt",
        content_type="text/plain",
    )

    job_id = await queue.enqueue(job)

    # Set to DONE directly (valid)
    await queue.update_status(job_id, JobStatus.PROCESSING)
    await queue.update_status(job_id, JobStatus.DONE)

    # Invalid: DONE -> PROCESSING
    with pytest.raises(JobStateError):
        await queue.update_status(job_id, JobStatus.PROCESSING)

    await queue.remove_job(job_id)


@pytest.mark.asyncio
async def test_job_not_found():
    """Test that querying a non-existent job returns None."""
    queue = IngestionQueue(redis_url="redis://localhost:6379/0")
    job = await queue.get_job("non-existent-id")
    assert job is None


@pytest.mark.asyncio
async def test_enqueue_non_pending_job():
    """Test that enqueuing a non-pending job raises an error."""
    queue = IngestionQueue(redis_url="redis://localhost:6379/0")

    job = JobRecord(
        document_id="doc-999",
        tenant_id="tenant-1",
        user_id="user-1",
        filename="test.pdf",
        content_type="application/pdf",
        status=JobStatus.PROCESSING,
    )

    with pytest.raises(JobStateError):
        await queue.enqueue(job)
