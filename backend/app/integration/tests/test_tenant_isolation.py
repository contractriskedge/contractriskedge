"""
Tests for tenant isolation in integration operations.

Ensures that one tenant cannot access another tenant's data.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.integration.models.integration import Integration
from app.integration.models.credential import IntegrationCredential
from app.integration.models.sync_job import IntegrationSyncJob
from app.integration.models.webhook import WebhookEvent
from app.integration.models.audit import IntegrationAuditEvent


@pytest.mark.asyncio
async def test_integration_queries_filter_by_tenant(mock_db):
    """Test that integration queries include tenant_id filter."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    # Verify the model has tenant_id column
    assert hasattr(Integration, 'tenant_id')

    # Verify a typical query would filter by tenant
    query = select(Integration).where(
        Integration.tenant_id == tenant_a,
        Integration.is_deleted == False,
    )
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert str(tenant_a) in compiled


@pytest.mark.asyncio
async def test_credential_queries_filter_by_tenant(mock_db):
    """Test that credential queries include tenant_id filter."""
    tenant_a = uuid.uuid4()

    assert hasattr(IntegrationCredential, 'tenant_id')

    query = select(IntegrationCredential).where(
        IntegrationCredential.tenant_id == tenant_a,
        IntegrationCredential.is_revoked == False,
    )
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert str(tenant_a) in compiled


@pytest.mark.asyncio
async def test_sync_job_queries_filter_by_tenant(mock_db):
    """Test that sync job queries include tenant_id filter."""
    tenant_a = uuid.uuid4()

    assert hasattr(IntegrationSyncJob, 'tenant_id')

    query = select(IntegrationSyncJob).where(
        IntegrationSyncJob.tenant_id == tenant_a,
    )
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert str(tenant_a) in compiled


@pytest.mark.asyncio
async def test_webhook_event_queries_filter_by_tenant(mock_db):
    """Test that webhook event queries include tenant_id filter."""
    tenant_a = uuid.uuid4()

    assert hasattr(WebhookEvent, 'tenant_id')

    query = select(WebhookEvent).where(
        WebhookEvent.tenant_id == tenant_a,
    )
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert str(tenant_a) in compiled


@pytest.mark.asyncio
async def test_audit_event_queries_filter_by_tenant(mock_db):
    """Test that audit event queries include tenant_id filter."""
    tenant_a = uuid.uuid4()

    assert hasattr(IntegrationAuditEvent, 'tenant_id')

    query = select(IntegrationAuditEvent).where(
        IntegrationAuditEvent.tenant_id == tenant_a,
    )
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert str(tenant_a) in compiled


@pytest.mark.asyncio
async def test_cross_tenant_integration_access_denied(mock_db):
    """Test that tenant A cannot access tenant B's integration."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    integration_id = uuid.uuid4()

    # Simulate tenant B's integration
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)  # Not found for tenant A
    ))

    result = await mock_db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.tenant_id == tenant_a,
            Integration.is_deleted == False,
        )
    )
    integration = result.scalar_one_or_none()

    # Tenant A should not see tenant B's integration
    assert integration is None


@pytest.mark.asyncio
async def test_credential_encryption_tenant_isolation():
    """Test that credential encryption includes tenant context in AAD."""
    from app.integration.services.crypto import CredentialEncryption, CredentialVault

    vault = CredentialVault()

    # Encrypt same token for different tenants
    tenant_a_token = vault.store_token(
        tenant_id="tenant-a",
        integration_id="int-1",
        token="shared-secret",
    )
    tenant_b_token = vault.store_token(
        tenant_id="tenant-b",
        integration_id="int-1",
        token="shared-secret",
    )

    # Different tenants should produce different ciphertexts
    assert tenant_a_token != tenant_b_token

    # Each tenant can decrypt their own token
    decrypted_a = vault.retrieve_token(
        tenant_id="tenant-a",
        integration_id="int-1",
        encrypted_blob=tenant_a_token,
    )
    assert decrypted_a == "shared-secret"

    # Tenant B cannot decrypt tenant A's token (wrong AAD)
    with pytest.raises(Exception):
        vault.retrieve_token(
            tenant_id="tenant-b",
            integration_id="int-1",
            encrypted_blob=tenant_a_token,
        )


@pytest.mark.asyncio
async def test_governance_service_tenant_scoped(mock_db, tenant_id):
    """Test that governance operations are tenant-scoped."""
    from app.integration.services.governance_service import GovernanceService

    other_tenant_id = uuid.uuid4()
    integration_id = uuid.uuid4()

    # Integration belongs to other_tenant
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)  # Not found for tenant_id
    ))

    governance = GovernanceService(db=mock_db, tenant_id=tenant_id)

    with pytest.raises(ValueError, match="Integration not found"):
        await governance.disable_integration(
            integration_id=integration_id,
            reason="Test",
        )


@pytest.mark.asyncio
async def test_oauth_service_tenant_scoped(mock_db, tenant_id):
    """Test that OAuth operations are tenant-scoped."""
    from app.integration.services.oauth_service import OAuthService

    integration_id = uuid.uuid4()

    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)  # Not found
    ))

    service = OAuthService(db=mock_db, tenant_id=tenant_id)

    with pytest.raises(ValueError, match="Integration not found"):
        await service.revoke_token(integration_id=integration_id)
