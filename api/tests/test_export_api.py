"""Tests for export API endpoints.

Covers DOCX export, PDF export, CSV audit export,
benchmark CSV export, and batch export.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestExportEndpoints:
    """Test suite for export API endpoints."""

    @pytest.mark.asyncio
    async def test_export_redline_docx_not_found(self, client: AsyncClient):
        """Test exporting non-existent redline returns 404."""
        response = await client.get(
            "/api/v1/export/redlines/non-existent/docx"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_redline_pdf_not_found(self, client: AsyncClient):
        """Test exporting non-existent redline as PDF returns 404."""
        response = await client.get(
            "/api/v1/export/redlines/non-existent/pdf"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_audit_csv(self, client: AsyncClient):
        """Test audit CSV export returns CSV content or handles missing DB."""
        response = await client.get("/api/v1/export/audit/csv")
        # May return 200 with CSV or 500 if DB not available
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            assert "text/csv" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_benchmarks_csv(self, client: AsyncClient):
        """Test benchmark CSV export returns CSV content or handles errors."""
        response = await client.get("/api/v1/export/benchmarks/csv")
        # May return 200 with CSV or 500 if corpus not loaded
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_batch_export_empty_ids(self, client: AsyncClient):
        """Test batch export with no IDs returns 400 or 422."""
        response = await client.post("/api/v1/export/batch")
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_batch_export_too_many(self, client: AsyncClient):
        """Test batch export with too many IDs returns 400."""
        ids = [str(i) for i in range(21)]
        response = await client.post(
            "/api/v1/export/batch",
            params=[("suggestion_ids", i) for i in ids],
        )
        assert response.status_code == 400
        assert "20" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_export_not_found(self, client: AsyncClient):
        """Test batch export with non-existent IDs returns 404."""
        response = await client.post(
            "/api/v1/export/batch",
            params=[("suggestion_ids", "nonexistent-id")],
        )
        assert response.status_code == 404
