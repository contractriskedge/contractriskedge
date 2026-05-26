"""
Tests for webhook verification and replay attack protection.

Covers:
- HMAC signature verification
- Timestamp replay protection
- Idempotent event ingestion
- Event deduplication
- Signature validation failure handling
"""

import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integration.models.webhook import WebhookEvent, WebhookEventStatus, WebhookStatus
from app.integration.services.webhook_service import WebhookService, WebhookVerifier


class TestWebhookVerifier:
    """Tests for the WebhookVerifier utility."""

    def test_hmac_signature_valid(self):
        """Test valid HMAC-SHA256 signature verification."""
        secret = "test-secret-key"
        payload = b'{"event": "test", "data": "value"}'

        expected = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        assert WebhookVerifier.verify_hmac_signature(
            payload, expected, secret
        ) is True

    def test_hmac_signature_invalid(self):
        """Test invalid HMAC-SHA256 signature is rejected."""
        secret = "test-secret-key"
        payload = b'{"event": "test"}'

        assert WebhookVerifier.verify_hmac_signature(
            payload, "invalid-signature", secret
        ) is False

    def test_hmac_signature_with_prefix(self):
        """Test signature verification with 'sha256=' prefix."""
        secret = "test-secret"
        payload = b"test payload"

        expected = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        assert WebhookVerifier.verify_hmac_signature(
            payload, f"sha256={expected}", secret
        ) is True

    def test_timestamp_valid(self):
        """Test valid timestamp within window."""
        now = time.time()
        assert WebhookVerifier.verify_timestamp(now, max_age_seconds=300) is True

    def test_timestamp_expired(self):
        """Test expired timestamp is rejected (replay protection)."""
        old_timestamp = time.time() - 600  # 10 minutes old
        assert WebhookVerifier.verify_timestamp(old_timestamp, max_age_seconds=300) is False

    def test_timestamp_none(self):
        """Test None timestamp is rejected."""
        assert WebhookVerifier.verify_timestamp(None) is False

    def test_generate_idempotency_key(self):
        """Test idempotency key generation is deterministic."""
        key1 = WebhookVerifier.generate_idempotency_key(
            event_id="evt_123",
            provider="docusign",
            timestamp=1234567890,
        )
        key2 = WebhookVerifier.generate_idempotency_key(
            event_id="evt_123",
            provider="docusign",
            timestamp=1234567890,
        )
        assert key1 == key2

    def test_generate_idempotency_key_different_events(self):
        """Test different events produce different idempotency keys."""
        key1 = WebhookVerifier.generate_idempotency_key("evt_1", "docusign")
        key2 = WebhookVerifier.generate_idempotency_key("evt_2", "docusign")
        assert key1 != key2

    def test_sha1_signature(self):
        """Test SHA1 signature verification (legacy support)."""
        secret = "test-secret"
        payload = b"test payload"

        expected = hmac.new(
            secret.encode(), payload, hashlib.sha1
        ).hexdigest()

        assert WebhookVerifier.verify_signature_generic(
            payload, expected, secret, algorithm="sha1"
        ) is True

    def test_unsupported_algorithm(self):
        """Test unsupported algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported signature algorithm"):
            WebhookVerifier.verify_signature_generic(
                b"test", "sig", "secret", algorithm="md5"
            )


class TestWebhookService:
    """Tests for the WebhookService."""

    @pytest.mark.asyncio
    async def test_process_incoming_webhook_success(
        self, mock_db, tenant_id, sample_webhook
    ):
        """Test successful webhook event ingestion."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_webhook)
        ))

        service = WebhookService(db=mock_db, tenant_id=tenant_id)

        payload = b'{"status": "completed", "envelopeId": "env-123"}'
        secret = sample_webhook.secret
        expected_sig = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        event = await service.process_incoming_webhook(
            provider="docusign",
            webhook_id="wh_test_123",
            payload=payload,
            headers={"x-hub-signature-256": expected_sig},
            signature=expected_sig,
            timestamp=time.time(),
            event_id="evt_123",
            event_type="envelope.completed",
            source_ip="203.0.113.1",
        )

        assert event is not None
        assert event.event_type == "envelope.completed"
        assert event.idempotency_key is not None
        assert event.signature_valid is True

    @pytest.mark.asyncio
    async def test_process_webhook_subscription_not_found(
        self, mock_db, tenant_id
    ):
        """Test webhook from unknown subscription is rejected."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))

        service = WebhookService(db=mock_db, tenant_id=tenant_id)

        with pytest.raises(ValueError, match="Webhook subscription not found"):
            await service.process_incoming_webhook(
                provider="unknown",
                webhook_id="wh_nonexistent",
                payload=b"{}",
                headers={},
            )

    @pytest.mark.asyncio
    async def test_process_webhook_subscription_inactive(
        self, mock_db, tenant_id, sample_webhook
    ):
        """Test webhook to inactive subscription is rejected."""
        sample_webhook.status = WebhookStatus.DISABLED
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_webhook)
        ))

        service = WebhookService(db=mock_db, tenant_id=tenant_id)

        with pytest.raises(ValueError, match="Webhook subscription is disabled"):
            await service.process_incoming_webhook(
                provider="docusign",
                webhook_id="wh_test_123",
                payload=b"{}",
                headers={},
            )

    @pytest.mark.asyncio
    async def test_event_deduplication(
        self, mock_db, tenant_id, sample_webhook, sample_webhook_event
    ):
        """Test duplicate webhook events are detected and skipped."""
        # First call returns webhook, second returns existing event (duplicate)
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_webhook)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_webhook_event)),
        ]

        service = WebhookService(db=mock_db, tenant_id=tenant_id)

        event = await service.process_incoming_webhook(
            provider="docusign",
            webhook_id="wh_test_123",
            payload=b'{"test": "data"}',
            headers={},
            event_id="evt_123",
            event_type="envelope.completed",
        )

        # Should return existing event (deduplication)
        assert event.id == sample_webhook_event.id

    @pytest.mark.asyncio
    async def test_mark_event_failed_with_retry(
        self, mock_db, tenant_id, sample_webhook_event
    ):
        """Test failed event is scheduled for retry."""
        sample_webhook_event.processing_attempts = 1
        sample_webhook_event.max_retries = 3

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_webhook_event)
        ))

        service = WebhookService(db=mock_db, tenant_id=tenant_id)

        await service.mark_event_failed(
            event_id=sample_webhook_event.id,
            error="Rate limit exceeded",
            should_retry=True,
        )

        assert sample_webhook_event.status == WebhookEventStatus.RETRYING
        assert sample_webhook_event.last_error == "Rate limit exceeded"
        assert sample_webhook_event.next_retry_at is not None

    @pytest.mark.asyncio
    async def test_mark_event_failed_dead_letter(
        self, mock_db, tenant_id, sample_webhook_event
    ):
        """Test event exceeding max retries goes to dead letter."""
        sample_webhook_event.processing_attempts = 3
        sample_webhook_event.max_retries = 3

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_webhook_event)
        ))

        service = WebhookService(db=mock_db, tenant_id=tenant_id)

        await service.mark_event_failed(
            event_id=sample_webhook_event.id,
            error="Permanent failure",
            should_retry=True,
        )

        assert sample_webhook_event.status == WebhookEventStatus.DEAD_LETTER

    @pytest.mark.asyncio
    async def test_get_pending_events(
        self, mock_db, tenant_id, sample_webhook_event
    ):
        """Test retrieving events pending retry."""
        sample_webhook_event.status = WebhookEventStatus.RETRYING
        sample_webhook_event.next_retry_at = datetime.now(timezone.utc) - timedelta(minutes=5)

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=[sample_webhook_event])
                )
            )
        ))

        service = WebhookService(db=mock_db, tenant_id=tenant_id)
        events = await service.get_pending_events(limit=10)

        assert len(events) == 1
        assert events[0].id == sample_webhook_event.id
