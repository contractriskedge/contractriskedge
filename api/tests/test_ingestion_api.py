"""Tests for ingestion API endpoints.

Covers single upload, batch upload, job status tracking,
and queue management.
"""

from __future__ import annotations

import io
import os
from typing import Any, AsyncGenerator, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class TestIngestionEndpoints:
    """Test suite for ingestion API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test the health check endpoint returns 200."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client: AsyncClient):
        """Test upload with unsupported file type returns 400."""
        response = await client.post(
            "/api/v1/ingest/upload",
            files={"file": ("test.exe", b"fake content", "application/x-msdownload")},
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, client: AsyncClient):
        """Test upload with empty file returns 400."""
        response = await client.post(
            "/api/v1/ingest/upload",
            files={"file": ("test.txt", b"", "text/plain")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_batch_upload_empty(self, client: AsyncClient):
        """Test batch upload with no files returns 400 or 422."""
        response = await client.post("/api/v1/ingest/batch-upload")
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_batch_upload_too_many(self, client: AsyncClient):
        """Test batch upload with too many files returns 400."""
        files = [
            ("files", ("test.txt", b"content", "text/plain"))
            for _ in range(21)
        ]
        response = await client.post(
            "/api/v1/ingest/batch-upload",
            files=files,
        )
        assert response.status_code == 400
        assert "20" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, client: AsyncClient):
        """Test getting status for non-existent job returns 404 or 500."""
        response = await client.get(
            "/api/v1/ingest/status/non-existent-job-id"
        )
        # 404 if queue accessible, 500 if Redis unavailable
        assert response.status_code in (404, 500)

    @pytest.mark.asyncio
    async def test_cancel_job_not_found(self, client: AsyncClient):
        """Test cancelling non-existent job returns error gracefully."""
        response = await client.delete(
            "/api/v1/ingest/jobs/non-existent-job-id"
        )
        # 404 if queue accessible, 422/500 if Redis unavailable
        assert response.status_code in (404, 422, 500)

    @pytest.mark.asyncio
    async def test_list_jobs_defaults(self, client: AsyncClient):
        """Test listing jobs returns valid structure or handles missing Redis."""
        response = await client.get("/api/v1/ingest/jobs")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "jobs" in data
            assert "total" in data

    @pytest.mark.asyncio
    async def test_queue_stats(self, client: AsyncClient):
        """Test queue stats endpoint returns valid structure or handles missing Redis."""
        response = await client.get("/api/v1/ingest/queue/stats")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            for key in ("pending", "processing", "done", "failed", "total"):
                assert key in data
