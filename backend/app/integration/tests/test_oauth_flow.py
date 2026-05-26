"""
Tests for OAuth2 authorization flow.

Covers:
- Authorization URL generation
- Callback handling
- Token refresh
- Token revocation
- Scope validation
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pytest import approx

from app.integration.models.credential import IntegrationCredential
from app.integration.models.integration import Integration, IntegrationStatus
from app.integration.services.oauth_service import OAuthService


@pytest.mark.asyncio
async def test_generate_authorization_url(mock_db, tenant_id, sample_integration):
    """Test generating OAuth2 authorization URL with state parameter."""
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_integration)
    ))

    service = OAuthService(db=mock_db, tenant_id=tenant_id)
    integration_id = sample_integration.id

    result = service.generate_authorization_url(
        provider="docusign",
        integration_id=integration_id,
        redirect_uri="https://app.contractriskedge.com/oauth/callback",
        scopes=["signature", "envelope_read"],
    )

    assert "authorization_url" in result
    assert "state" in result
    assert "redirect_uri" in result
    assert "scope" in result
    assert result["redirect_uri"] == "https://app.contractriskedge.com/oauth/callback"
    assert "signature" in result["scope"]
    assert len(result["state"]) > 20  # CSRF state token


@pytest.mark.asyncio
async def test_handle_callback_state_mismatch(mock_db, tenant_id, sample_integration):
    """Test callback fails on state mismatch (CSRF protection)."""
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_integration)
    ))

    service = OAuthService(db=mock_db, tenant_id=tenant_id)

    with pytest.raises(ValueError, match="OAuth state mismatch"):
        await service.handle_callback(
            integration_id=sample_integration.id,
            code="auth-code-123",
            state="invalid-state",
            redirect_uri="https://app.contractriskedge.com/oauth/callback",
            expected_state="expected-state-456",
        )


@pytest.mark.asyncio
async def test_handle_callback_success(mock_db, tenant_id, sample_integration):
    """Test successful OAuth callback with token exchange."""
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_integration)
    ))

    service = OAuthService(db=mock_db, tenant_id=tenant_id)

    # Mock the HTTP token exchange
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "signature envelope_read",
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, '_http_client') as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)

        credential = await service.handle_callback(
            integration_id=sample_integration.id,
            code="auth-code-123",
            state="expected-state",
            redirect_uri="https://app.contractriskedge.com/oauth/callback",
            expected_state="expected-state",
        )

        assert credential is not None
        assert credential.credential_type.value == "oauth2"
        assert credential.oauth_provider == "docusign"
        assert credential.oauth_token_type == "Bearer"
        assert credential.oauth_access_token_expires_at is not None

    # Verify integration status updated
    assert sample_integration.status == IntegrationStatus.ACTIVE


@pytest.mark.asyncio
async def test_token_refresh(mock_db, tenant_id, sample_integration, sample_credential):
    """Test OAuth2 token refresh flow."""
    # Make token appear expired
    sample_credential.oauth_access_token_expires_at = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    )

    async def mock_execute_side_effect(*args, **kwargs):
        result = MagicMock()
        # First call returns integration, second returns credential
        if hasattr(args[0], 'where') and 'IntegrationCredential' in str(args[0]):
            result.scalar_one_or_none.return_value = sample_credential
        else:
            result.scalar_one_or_none.return_value = sample_integration
        return result

    mock_db.execute = AsyncMock(side_effect=mock_execute_side_effect)

    service = OAuthService(db=mock_db, tenant_id=tenant_id)

    # Mock HTTP refresh response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "refreshed-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, '_http_client') as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)

        credential = await service.refresh_token(
            integration_id=sample_integration.id,
            force=True,
        )

        assert credential is not None
        assert credential.rotation_count > 0
        assert credential.version > 1


@pytest.mark.asyncio
async def test_token_revocation(mock_db, tenant_id, sample_integration, sample_credential):
    """Test OAuth2 token revocation disables integration."""
    async def mock_execute_side_effect(*args, **kwargs):
        result = MagicMock()
        if hasattr(args[0], 'where') and 'IntegrationCredential' in str(args[0]):
            result.scalar_one_or_none.return_value = sample_credential
        else:
            result.scalar_one_or_none.return_value = sample_integration
        return result

    mock_db.execute = AsyncMock(side_effect=mock_execute_side_effect)

    service = OAuthService(db=mock_db, tenant_id=tenant_id)

    with patch.object(service, '_http_client') as mock_client:
        mock_client.post = AsyncMock()
        await service.revoke_token(integration_id=sample_integration.id)

    assert sample_credential.is_revoked is True
    assert sample_credential.is_expired is True
    assert sample_integration.status == IntegrationStatus.REVOKED


@pytest.mark.asyncio
async def test_validate_scopes(mock_db, tenant_id, sample_credential):
    """Test OAuth2 scope validation."""
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_credential)
    ))

    service = OAuthService(db=mock_db, tenant_id=tenant_id)

    # Should pass with matching scopes
    assert await service.validate_scopes(
        integration_id=uuid.uuid4(),
        required_scopes=["signature", "envelope_read"],
    ) is True

    # Should fail with missing scopes
    assert await service.validate_scopes(
        integration_id=uuid.uuid4(),
        required_scopes=["admin", "signature"],
    ) is False


@pytest.mark.asyncio
async def test_token_refresh_skipped_when_valid(mock_db, tenant_id, sample_integration, sample_credential):
    """Test that token refresh is skipped when token is still valid."""
    sample_credential.oauth_access_token_expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=1)
    )

    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sample_integration)
    ))

    service = OAuthService(db=mock_db, tenant_id=tenant_id)

    # Should not call HTTP endpoint since token is valid
    credential = await service.refresh_token(
        integration_id=sample_integration.id,
        force=False,
    )

    assert credential is not None
