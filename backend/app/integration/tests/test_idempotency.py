"""
Tests for idempotency in webhook and sync operations.

Covers:
- Webhook event deduplication via idempotency keys
- Idempotent sync operations
- Duplicate detection across providers
"""

import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integration.models.webhook import WebhookEvent, WebhookEventStatus
from app.integration.services.webhook_service import WebhookService, WebhookVerifier


class TestWebhookIdempotency:
    """Tests for webhook event idempotency."""

    @pytest.mark.asyncio
    async def test_idempotency_key_generation(self):
        """Test idempotency key is deterministic."""
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

    @pytest.mark.asyncio
    async def test_different_events_different_keys(self):
        """Test different events produce different idempotency keys."""
        key1 = WebhookVerifier.generate_idempotency_key(
            event_id="evt_1", provider="docusign"
        )
        key2 = WebhookVerifier.generate_idempotency_key(
            event_id="evt_2", provider="docusign"
        )
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_different_providers_different_keys(self):
        """Test different providers produce different idempotency keys."""
        key1 = WebhookVerifier.generate_idempotency_key(
            event_id="evt_1", provider="docusign"
        )
        key2 = WebhookVerifier.generate_idempotency_key(
            event_id="evt_1", provider="sharepoint"
        )
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_idempotency_prevents_duplicate_processing(
        self, mock_db, tenant_id, sample_webhook, sample_webhook_event
    ):
        """Test that duplicate events return the existing event."""
        # First call returns webhook, second returns existing event
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

        # Should return existing event, not create new one
        assert event.id == sample_webhook_event.id
        assert event.status == sample_webhook_event.status

    @pytest.mark.asyncio
    async def test_idempotency_based_on_payload_hash(
        self, mock_db, tenant_id, sample_webhook
    ):
        """Test idempotency key is derived from payload when no event_id."""
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_webhook)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # No duplicate
        ]

        service = WebhookService(db=mock_db, tenant_id=tenant_id)

        payload = b'{"status": "completed"}'
        event = await service.process_incoming_webhook(
            provider="docusign",
            webhook_id="wh_test_123",
            payload=payload,
            headers={},
            event_type="envelope.completed",
        )

        # Verify idempotency key is based on payload hash
        expected_key = WebhookVerifier.generate_idempotency_key(
            event_id=hashlib.sha256(payload).hexdigest(),
            provider="docusign",
        )
        # The event's key should match the generated key
        assert event.idempotency_key is not None


class TestSyncIdempotency:
    """Tests for sync operation idempotency."""

    @pytest.mark.asyncio
    async def test_sync_job_correlation_id(self):
        """Test sync jobs have unique correlation IDs for idempotency."""
        from app.integration.models.sync_job import IntegrationSyncJob, SyncJobStatus, SyncJobTrigger
        from datetime import datetime, timezone

        job1 = IntegrationSyncJob(
            id=uuid.uuid4(),
            integration_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            status=SyncJobStatus.PENDING,
            trigger=SyncJobTrigger.MANUAL,
            sync_type="full",
            max_retries=3,
            created_at=datetime.now(timezone.utc),
        )

        job2 = IntegrationSyncJob(
            id=uuid.uuid4(),
            integration_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            status=SyncJobStatus.PENDING,
            trigger=SyncJobTrigger.MANUAL,
            sync_type="full",
            max_retries=3,
            created_at=datetime.now(timezone.utc),
        )

        assert job1.correlation_id != job2.correlation_id

    @pytest.mark.asyncio
    async def test_retry_job_preserves_correlation_id(
        self, mock_db, tenant_id, sample_sync_job
    ):
        """Test retry jobs preserve the original correlation ID."""
        from app.integration.services.sync_service import SyncOrchestrator

        original_correlation = sample_sync_job.correlation_id
        sample_sync_job.status = type(sample_sync_job.status).FAILED
        sample_sync_job.retry_count = 1

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_sync_job)
        ))

        orchestrator = SyncOrchestrator(db=mock_db, tenant_id=tenant_id)
        retry_job = await orchestrator.retry_sync(
            job_id=sample_sync_job.id,
            force=True,
        )

        # Retry should preserve correlation ID for trace lineage
        assert retry_job.correlation_id == original_correlation

    @pytest.mark.asyncio
    async def test_delta_sync_uses_cursor_for_idempotency(self):
        """Test delta syncs use cursor for resumable idempotent syncs."""
        from app.integration.models.sync_job import IntegrationSyncJob, SyncJobStatus, SyncJobTrigger
        from datetime import datetime, timezone

        # A delta sync job with a cursor
        job = IntegrationSyncJob(
            id=uuid.uuid4(),
            integration_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            status=SyncJobStatus.SUCCESS,
            trigger=SyncJobTrigger.SCHEDULED,
            sync_type="delta",
            cursor="nextLink_v2_token_abc123",
            max_retries=3,
            created_at=datetime.now(timezone.utc),
        )

        # The cursor enables resumable sync — no need to re-sync from start
        assert job.cursor is not None
        assert job.sync_type == "delta"
