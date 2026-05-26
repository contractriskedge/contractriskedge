"""
Tests for rate-limit handling.

Covers:
- Token bucket rate limiting
- Rate limit enforcement
- Rate limit tracking from API responses
- Redis-backed rate limiting (mock)
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integration.services.rate_limiter import RateLimiter, RateLimitTracker


class TestRateLimiter:
    """Tests for the RateLimiter."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self):
        """Test requests within rate limit are allowed."""
        limiter = RateLimiter()
        integration_id = uuid.uuid4()

        for _ in range(5):
            allowed = await limiter.check_sync_rate_limit(
                integration_id=integration_id,
                max_requests=10,
                window_seconds=60,
            )
            assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_when_exceeded(self):
        """Test requests exceeding rate limit are blocked."""
        limiter = RateLimiter()
        integration_id = uuid.uuid4()

        # Exhaust the limit
        for _ in range(5):
            await limiter.check_sync_rate_limit(
                integration_id=integration_id,
                max_requests=5,
                window_seconds=60,
            )

        # Next request should be blocked
        allowed = await limiter.check_sync_rate_limit(
            integration_id=integration_id,
            max_requests=5,
            window_seconds=60,
        )
        assert allowed is False

    @pytest.mark.asyncio
    async def test_rate_limit_no_limit_configured(self):
        """Test no rate limit configured always returns True."""
        limiter = RateLimiter()
        integration_id = uuid.uuid4()

        allowed = await limiter.check_sync_rate_limit(
            integration_id=integration_id,
            max_requests=None,  # No limit
        )
        assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_reset(self):
        """Test resetting rate limit for an integration."""
        limiter = RateLimiter()
        integration_id = uuid.uuid4()

        # Exhaust limit
        for _ in range(3):
            await limiter.check_sync_rate_limit(
                integration_id=integration_id,
                max_requests=3,
                window_seconds=60,
            )

        assert await limiter.check_sync_rate_limit(
            integration_id=integration_id,
            max_requests=3,
            window_seconds=60,
        ) is False

        # Reset
        limiter.reset(integration_id)

        # Should be allowed again
        allowed = await limiter.check_sync_rate_limit(
            integration_id=integration_id,
            max_requests=3,
            window_seconds=60,
        )
        assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_get_remaining(self):
        """Test getting remaining requests."""
        limiter = RateLimiter()
        integration_id = uuid.uuid4()

        # Use some requests
        for _ in range(3):
            await limiter.check_sync_rate_limit(
                integration_id=integration_id,
                max_requests=10,
                window_seconds=60,
            )

        remaining = limiter.get_remaining(integration_id)
        assert remaining is not None
        assert remaining <= 7  # Some tokens may have been consumed

    @pytest.mark.asyncio
    async def test_rate_limit_different_integrations_independent(self):
        """Test rate limits are independent per integration."""
        limiter = RateLimiter()
        int_a = uuid.uuid4()
        int_b = uuid.uuid4()

        # Exhaust int_a
        for _ in range(3):
            await limiter.check_sync_rate_limit(
                integration_id=int_a,
                max_requests=3,
                window_seconds=60,
            )

        # int_a should be blocked
        assert await limiter.check_sync_rate_limit(
            integration_id=int_a,
            max_requests=3,
            window_seconds=60,
        ) is False

        # int_b should still be allowed
        assert await limiter.check_sync_rate_limit(
            integration_id=int_b,
            max_requests=3,
            window_seconds=60,
        ) is True


class TestRateLimitTracker:
    """Tests for the RateLimitTracker."""

    def test_record_response(self):
        """Test recording rate limit headers from API response."""
        tracker = RateLimitTracker()
        tracker.record_response(
            provider="docusign",
            remaining=45,
            limit=100,
            reset_at=time.time() + 60,
        )

        status = tracker.get_status("docusign")
        assert status is not None
        assert status["remaining"] == 45
        assert status["limit"] == 100

    def test_is_throttled(self):
        """Test throttling detection."""
        tracker = RateLimitTracker()
        tracker.record_response(
            provider="docusign",
            remaining=3,
            limit=100,
            reset_at=time.time() + 60,
        )

        assert tracker.is_throttled("docusign", min_remaining=5) is True
        assert tracker.is_throttled("docusign", min_remaining=2) is False

    def test_is_throttled_no_data(self):
        """Test throttling check with no data returns False."""
        tracker = RateLimitTracker()
        assert tracker.is_throttled("unknown_provider") is False

    def test_multiple_providers(self):
        """Test tracking multiple providers independently."""
        tracker = RateLimitTracker()

        tracker.record_response("docusign", remaining=50, limit=100, reset_at=None)
        tracker.record_response("sharepoint", remaining=200, limit=300, reset_at=None)

        assert tracker.get_status("docusign")["remaining"] == 50
        assert tracker.get_status("sharepoint")["remaining"] == 200
