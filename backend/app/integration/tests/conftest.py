"""
Test fixtures for integration subsystem tests.

Provides mock database sessions, services, and test data factories.
"""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.connectors.base import ConnectorAuth, SyncResult, ConnectorHealth
from app.integration.models.integration import (
    ConnectorProvider,
    Integration,
    IntegrationStatus,
    IntegrationType,
)
from app.integration.models.credential import (
    CredentialType,
    IntegrationCredential,
)
from app.integration.models.sync_job import (
    IntegrationSyncJob,
    SyncConflict,
    SyncJobStatus,
    SyncJobTrigger,
)
from app.integration.models.webhook import (
    IntegrationWebhook,
    WebhookEvent,
    WebhookEventStatus,
    WebhookStatus,
)
from app.integration.models.audit import IntegrationAuditEvent
from app.integration.models.permission import (
    ConnectorPermission,
    PermissionAction,
    PermissionEffect,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.telemetry import IntegrationTelemetry


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def integration_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def correlation_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock async database session."""
    db = AsyncMock(spec=AsyncSession)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_audit(tenant_id: uuid.UUID, mock_db: AsyncMock) -> IntegrationAuditService:
    return IntegrationAuditService(db=mock_db, tenant_id=tenant_id)


@pytest.fixture
def mock_telemetry() -> IntegrationTelemetry:
    return IntegrationTelemetry()


@pytest.fixture
def sample_integration(tenant_id: uuid.UUID, integration_id: uuid.UUID) -> Integration:
    return Integration(
        id=integration_id,
        tenant_id=tenant_id,
        name="Test DocuSign Integration",
        provider=ConnectorProvider.DOCUSIGN,
        integration_type=IntegrationType.OAUTH2,
        status=IntegrationStatus.ACTIVE,
        is_approved=True,
        config={"account_id": "test-account"},
        scopes=["signature", "envelope_read"],
        rate_limit_max=300,
        rate_limit_window_seconds=60,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_credential(
    tenant_id: uuid.UUID, integration_id: uuid.UUID
) -> IntegrationCredential:
    return IntegrationCredential(
        id=uuid.uuid4(),
        integration_id=integration_id,
        tenant_id=tenant_id,
        credential_type=CredentialType.OAUTH2,
        encrypted_access_token="ZW5jcnlwdGVkX3Rva2Vu",
        encrypted_refresh_token="ZW5jcnlwdGVkX3JlZnJlc2g=",
        oauth_provider="docusign",
        oauth_client_id="test-client-id",
        oauth_scopes=["signature", "envelope_read"],
        oauth_access_token_expires_at=datetime.now(timezone.utc),
        oauth_token_type="Bearer",
        is_expired=False,
        is_revoked=False,
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_sync_job(
    tenant_id: uuid.UUID, integration_id: uuid.UUID, correlation_id: uuid.UUID
) -> IntegrationSyncJob:
    return IntegrationSyncJob(
        id=uuid.uuid4(),
        integration_id=integration_id,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        status=SyncJobStatus.PENDING,
        trigger=SyncJobTrigger.MANUAL,
        sync_type="full",
        max_retries=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_webhook(
    tenant_id: uuid.UUID, integration_id: uuid.UUID
) -> IntegrationWebhook:
    return IntegrationWebhook(
        id=uuid.uuid4(),
        integration_id=integration_id,
        tenant_id=tenant_id,
        provider="docusign",
        webhook_id="wh_test_123",
        status=WebhookStatus.ACTIVE,
        secret="test-secret-123",
        signature_header="x-hub-signature-256",
        require_signature=True,
        event_count=0,
        failure_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_webhook_event(
    tenant_id: uuid.UUID, integration_id: uuid.UUID
) -> WebhookEvent:
    return WebhookEvent(
        id=uuid.uuid4(),
        webhook_id=uuid.uuid4(),
        integration_id=integration_id,
        tenant_id=tenant_id,
        idempotency_key="test-idempotency-key",
        event_id="evt_123",
        event_type="envelope.completed",
        raw_payload={"status": "completed", "envelopeId": "env-123"},
        status=WebhookEventStatus.RECEIVED,
        processing_attempts=0,
        max_retries=3,
        received_at=datetime.now(timezone.utc),
        correlation_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_permission(tenant_id: uuid.UUID) -> ConnectorPermission:
    return ConnectorPermission(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        action=PermissionAction.SYNC,
        effect=PermissionEffect.ALLOW,
        priority=100,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_audit_event(
    tenant_id: uuid.UUID, integration_id: uuid.UUID
) -> IntegrationAuditEvent:
    return IntegrationAuditEvent(
        id=uuid.uuid4(),
        integration_id=integration_id,
        tenant_id=tenant_id,
        action="integration_created",
        resource_type="integration",
        resource_id=str(integration_id),
        success=True,
        occurred_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


class MockConnector:
    """Mock connector adapter for testing."""

    provider_name = "test_provider"
    base_url = "https://api.test.com/v1"

    def __init__(self, **kwargs):
        self.auth = kwargs.get("auth")
        self.config = kwargs.get("config", {})
        self.tenant_id = kwargs.get("tenant_id")
        self.integration_id = kwargs.get("integration_id")

    async def authenticate(self):
        return ConnectorAuth(access_token="test-token")

    async def sync_documents(self, cursor=None, delta_token=None, max_items=None):
        return SyncResult(
            success=True,
            synced_count=10,
            cursor="next_cursor_123",
        )

    async def check_health(self):
        return ConnectorHealth(healthy=True, latency_ms=42.0)

    async def get_delta_link(self):
        return None

    async def close(self):
        pass
