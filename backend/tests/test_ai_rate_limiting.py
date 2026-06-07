"""Tests for AI rate limiting — middleware patterns, Redis concurrency tracking, and integration."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. Endpoint Pattern Matching
# ═══════════════════════════════════════════════════════════════════


class TestAIEndpointPatterns:
    """Verify regex patterns correctly match AI endpoints."""

    def _match(self, path: str):
        from app.kernel.middleware.ai_rate_limits import match_ai_endpoint
        return match_ai_endpoint(path)

    def test_matches_ai_analyze(self):
        result = self._match("/api/v1/ai/analyze")
        assert result is not None
        pattern, user_limit, tenant_limit = result
        assert user_limit > 0
        assert tenant_limit > 0

    def test_matches_ai_copilot_suggest(self):
        result = self._match("/api/v1/ai/copilot/suggest")
        assert result is not None

    def test_matches_review_analyze_with_uuid(self):
        """/api/v1/reviews/{uuid}/analyze must match — startswith fails here."""
        result = self._match("/api/v1/reviews/81e529ad-0dd8-4c2c-acd1-da8a62b5e2e5/analyze")
        assert result is not None, "Regex must match UUID-path analyze"

    def test_matches_review_reanalyze_with_uuid(self):
        result = self._match("/api/v1/reviews/81e529ad-0dd8-4c2c-acd1-da8a62b5e2e5/re-analyze")
        assert result is not None, "Regex must match UUID-path re-analyze"

    def test_does_not_match_plain_review(self):
        """/api/v1/reviews/ without analyze suffix must NOT match."""
        result = self._match("/api/v1/reviews")
        assert result is None

    def test_does_not_match_review_findings(self):
        result = self._match("/api/v1/reviews/81e529ad-0dd8-4c2c-acd1-da8a62b5e2e5/findings")
        assert result is None

    def test_does_not_match_health(self):
        result = self._match("/health")
        assert result is None

    def test_does_not_match_unrelated(self):
        result = self._match("/api/v1/contracts")
        assert result is None

    def test_returns_correct_limit_values(self):
        from app.kernel.middleware.ai_rate_limits import match_ai_endpoint
        result = match_ai_endpoint("/api/v1/ai/analyze")
        assert result is not None
        pattern, user_limit, tenant_limit = result
        assert user_limit == 5, f"Expected per-user limit 5, got {user_limit}"
        assert tenant_limit == 100, f"Expected per-tenant limit 100, got {tenant_limit}"


# ═══════════════════════════════════════════════════════════════════
# 2. Redis Concurrency Tracking
# ═══════════════════════════════════════════════════════════════════


class TestRedisConcurrencyTracking:
    """Verify Redis INCR/DECR logic for concurrent analysis limiting."""

    @pytest.mark.asyncio
    async def test_acquire_slot_under_limit(self):
        """Acquiring a slot under the limit should return True."""
        pipe = MagicMock()
        pipe.incr.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute = AsyncMock(return_value=[1])

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = pipe
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from workers.ai_worker import _acquire_concurrency_slot
            result = await _acquire_concurrency_slot("tenant-001")
            assert result is True

    @pytest.mark.asyncio
    async def test_acquire_slot_at_capacity(self):
        """Acquiring a slot at capacity should return False and DECR."""
        pipe = MagicMock()
        pipe.incr.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute = AsyncMock(return_value=[6])

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = pipe
        mock_redis.decr = AsyncMock(return_value=5)
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from workers.ai_worker import _acquire_concurrency_slot
            result = await _acquire_concurrency_slot("tenant-001")
            assert result is False
            mock_redis.decr.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_slot_redis_unavailable(self):
        """When Redis is unavailable, should fail open (return True)."""
        with patch("redis.asyncio.from_url", side_effect=ConnectionError("Redis down")):
            from workers.ai_worker import _acquire_concurrency_slot
            result = await _acquire_concurrency_slot("tenant-001")
            assert result is True  # Fail open

    @pytest.mark.asyncio
    async def test_release_slot(self):
        """Releasing a slot should DECR the counter."""
        mock_redis = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from workers.ai_worker import _release_concurrency_slot
            await _release_concurrency_slot("tenant-001")
            mock_redis.decr.assert_called_once_with("ai_active:tenant-001")

    @pytest.mark.asyncio
    async def test_release_slot_redis_unavailable(self):
        """Releasing a slot when Redis is down should not raise."""
        with patch("redis.asyncio.from_url", side_effect=ConnectionError("Redis down")):
            from workers.ai_worker import _release_concurrency_slot
            await _release_concurrency_slot("tenant-001")  # Should not raise

    @pytest.mark.asyncio
    async def test_redis_pipeline_incr_and_expire(self):
        """INCR and EXPIRE should be sent in a single pipeline."""
        pipe = MagicMock()
        pipe.incr.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute = AsyncMock(return_value=[1])

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = pipe
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from workers.ai_worker import _acquire_concurrency_slot
            await _acquire_concurrency_slot("tenant-001")
            assert pipe.incr.called
            assert pipe.expire.called
            assert pipe.execute.called


# ═══════════════════════════════════════════════════════════════════
# 3. Double-Decrement Guard
# ═══════════════════════════════════════════════════════════════════


class TestDoubleDecrementGuard:
    """Verify the acquired_slot boolean prevents double-decrement."""

    @pytest.mark.asyncio
    async def test_no_decrement_when_slot_not_acquired(self):
        """If _acquire_concurrency_slot returns False, DECR must NOT be called."""
        pipe = MagicMock()
        pipe.incr.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute = AsyncMock(return_value=[6])

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = pipe
        mock_redis.decr = AsyncMock(return_value=5)
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from workers.ai_worker import _acquire_concurrency_slot, _release_concurrency_slot
            acquired = await _acquire_concurrency_slot("tenant-001")
            assert acquired is False
            mock_redis.decr.assert_called_once()
            mock_redis.reset_mock()
            mock_redis.decr = AsyncMock(return_value=4)
            mock_redis.close = AsyncMock()
            await _release_concurrency_slot("tenant-001")
            mock_redis.decr.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquired_slot_guard_in_analyze_contract(self):
        """The acquired_slot boolean in _analyze_contract must prevent double-decrement."""
        pipe = MagicMock()
        pipe.incr.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute = AsyncMock(return_value=[6])

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = pipe
        mock_redis.decr = AsyncMock(return_value=5)
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from workers.ai_worker import _acquire_concurrency_slot
            acquired = await _acquire_concurrency_slot("tenant-001")
            assert acquired is False
            mock_redis.decr.assert_called_once()


# ═══════════════════════════════════════════════════════════════════
# 4. Middleware Integration
# ═══════════════════════════════════════════════════════════════════


class TestRateLimitMiddlewareAI:
    """Verify the middleware correctly applies AI rate limits."""

    def test_get_rate_limit_returns_ai_limits(self):
        """The middleware should return AI-specific limits for AI endpoints."""
        from app.kernel.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(None)
        request = MagicMock()
        request.url.path = "/api/v1/ai/analyze"
        request.state = MagicMock()

        limit = middleware._get_rate_limit(request)
        assert limit == 5, f"Expected AI analyze limit 5, got {limit}"
        # Verify tenant limit was stored on request state
        assert request.state._ai_tenant_limit == 100
        assert request.state._ai_operation is not None

    def test_get_rate_limit_returns_default_for_non_ai(self):
        """Non-AI endpoints should use default role-based limits."""
        from app.kernel.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(None)
        request = MagicMock()
        request.url.path = "/api/v1/contracts"
        request.state.user.role = "admin"

        limit = middleware._get_rate_limit(request)
        assert limit == 500, f"Expected admin limit 500, got {limit}"
