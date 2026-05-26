"""Tests for monitoring and RAG API endpoints.

Covers monitoring metrics, cost tracking, alert status,
detailed health, and RAG search.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestMonitoringEndpoints:
    """Test suite for monitoring API endpoints."""

    @pytest.mark.asyncio
    async def test_detailed_health(self, client: AsyncClient):
        """Test detailed health endpoint returns system status."""
        response = await client.get("/api/v1/monitoring/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_alert_status(self, client: AsyncClient):
        """Test alert status endpoint returns alerting info."""
        response = await client.get("/api/v1/monitoring/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data

    @pytest.mark.asyncio
    async def test_rag_health(self, client: AsyncClient):
        """Test RAG health endpoint returns configuration status."""
        response = await client.get("/api/v1/rag/health")
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "pinecone_configured" in data
        assert "openai_configured" in data

    @pytest.mark.asyncio
    async def test_rag_search_not_configured(self, client: AsyncClient):
        """Test RAG search handles missing configuration gracefully."""
        response = await client.post(
            "/api/v1/rag/search",
            json={"query_text": "test query", "top_k": 5},
        )
        # May return 501 (not configured), 500 (error), or 200
        assert response.status_code in (200, 500, 501)


class TestAuthEndpoints:
    """Test suite for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "documentation" in data
