"""Regression tests for UTC-aware datetime handling in analytics/recovery."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.analytics.service import AnalyticsService
from app.kernel.datetime_utils import age_minutes, ensure_utc, utc_now


class TestDatetimeUtils:
    def test_utc_now_is_aware(self) -> None:
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_ensure_utc_naive_treated_as_utc(self) -> None:
        naive = datetime(2026, 5, 17, 12, 0, 0)
        aware = ensure_utc(naive)
        assert aware is not None
        assert aware.tzinfo == timezone.utc

    def test_age_minutes_naive_vs_aware_no_type_error(self) -> None:
        """Reproduces production bug: utcnow() - timestamptz from DB."""
        now = utc_now()
        db_updated_at = datetime(2026, 5, 17, 11, 0, 0)  # naive, as asyncpg may return
        minutes = age_minutes(now, db_updated_at)
        assert minutes >= 0

    def test_age_minutes_aware_offset(self) -> None:
        later = datetime(2026, 5, 17, 13, 0, 0, tzinfo=timezone.utc)
        earlier = datetime(2026, 5, 17, 12, 30, 0, tzinfo=timezone.utc)
        assert age_minutes(later, earlier) == pytest.approx(30.0)

    def test_subtraction_without_utils_raises(self) -> None:
        naive = datetime.utcnow()
        aware = datetime.now(timezone.utc)
        with pytest.raises(TypeError):
            _ = aware - naive


class TestStuckWorkflowAgeCalculation:
    @pytest.mark.asyncio
    async def test_get_stuck_workflows_with_naive_db_timestamps(self) -> None:
        """Stuck workflow detection must not fail on naive DB timestamps."""
        tenant_id = "00000000-0000-4000-8000-000000000001"
        stuck_time = datetime.utcnow() - timedelta(hours=1)

        upload_row = SimpleNamespace(
            upload_id="3e999e6e-73e2-4691-a38d-c7944df90bc7",
            ingestion_state="ocr_processing",
            retry_count=0,
            ingestion_error=None,
            created_at=stuck_time,
            updated_at=stuck_time,
        )

        session = AsyncMock()
        call_count = 0

        async def execute_side_effect(sql, params=None):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.fetchall.return_value = [upload_row]
            else:
                result.fetchall.return_value = []
            return result

        session.execute = AsyncMock(side_effect=execute_side_effect)

        service = AnalyticsService(session=session, tenant_id=tenant_id)
        response = await service.get_stuck_workflows()

        assert response.total == 1
        assert response.items[0].resource_type == "upload"
        assert response.items[0].age_minutes >= 59


class TestErrorAnalyticsPeriodFilter:
    @pytest.mark.asyncio
    async def test_get_error_analytics_uses_datetime_cutoff_not_interval_string(self) -> None:
        """asyncpg rejects interval params bound as strings like '24 hours'."""
        tenant_id = "00000000-0000-4000-8000-000000000001"
        session = AsyncMock()
        result = MagicMock()
        result.fetchall.return_value = []
        result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=result)

        service = AnalyticsService(session=session, tenant_id=tenant_id)
        await service.get_error_analytics(period_hours=24)

        for call in session.execute.call_args_list:
            params = call.args[1] if len(call.args) > 1 else call.kwargs
            if not params:
                continue
            for key, value in params.items():
                if key == "since":
                    assert isinstance(value, datetime)
                    assert value.tzinfo is not None
                assert not (isinstance(value, str) and value.endswith("hours"))

    @pytest.mark.asyncio
    async def test_get_error_analytics_builds_by_type_from_failure_summary(self) -> None:
        """Response by_type must use failure_type field, not a nonexistent .type attr."""
        tenant_id = "00000000-0000-4000-8000-000000000001"
        session = AsyncMock()
        call_count = 0

        async def execute_side_effect(sql, params=None):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.fetchall.return_value = [
                    SimpleNamespace(
                        failure_type="timeout",
                        error_message="timed out",
                        retry_count=1,
                        created_at=datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
                    ),
                ]
            elif call_count == 2:
                result.fetchall.return_value = [
                    SimpleNamespace(
                        upload_id="3e999e6e-73e2-4691-a38d-c7944df90bc7",
                        ingestion_error="timeout",
                        retry_count=2,
                        updated_at=datetime(2026, 5, 18, 13, 0, 0, tzinfo=timezone.utc),
                    ),
                ]
            else:
                result.fetchall.return_value = []
            result.scalar.return_value = 0
            return result

        session.execute = AsyncMock(side_effect=execute_side_effect)

        service = AnalyticsService(session=session, tenant_id=tenant_id)
        response = await service.get_error_analytics(period_hours=24)

        assert response.total_failures == 2
        assert response.by_type == {"timeout": 1, "INGESTION_FAILURE": 1}
        assert len(response.failures_by_type) == 2


class TestTrendChartPeriodFilter:
    @pytest.mark.asyncio
    async def test_get_upload_trend_uses_datetime_cutoff_not_interval_string(self) -> None:
        tenant_id = "00000000-0000-4000-8000-000000000001"
        session = AsyncMock()
        result = MagicMock()
        result.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result)

        service = AnalyticsService(session=session, tenant_id=tenant_id)
        await service.get_upload_trend(days=30)

        params = session.execute.call_args.args[1]
        assert isinstance(params["since"], datetime)
        assert params["since"].tzinfo is not None
        assert "days" not in params or not isinstance(params.get("days"), str)

    @pytest.mark.asyncio
    async def test_get_ai_cost_trend_uses_datetime_cutoff_not_interval_string(self) -> None:
        tenant_id = "00000000-0000-4000-8000-000000000001"
        session = AsyncMock()
        result = MagicMock()
        result.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result)

        service = AnalyticsService(session=session, tenant_id=tenant_id)
        await service.get_ai_cost_trend(days=30)

        params = session.execute.call_args.args[1]
        assert isinstance(params["since"], datetime)
        assert params["since"].tzinfo is not None
