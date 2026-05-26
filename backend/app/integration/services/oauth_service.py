"""
OAuth2 Service — complete OAuth2 authorization flow management.

Handles:
- Authorization URL generation
- Callback processing (code exchange)
- Token refresh
- Credential rotation
- Scope validation
- Token revocation
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.integration.models.credential import (
    CredentialType,
    IntegrationCredential,
)
from app.integration.models.integration import (
    ConnectorProvider,
    Integration,
    IntegrationStatus,
    IntegrationType,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.crypto import CredentialEncryption, CredentialVault
from app.integration.services.telemetry import IntegrationTelemetry

logger = get_logger(__name__)


class OAuthProviderConfig:
    """OAuth2 configuration for a specific provider."""

    def __init__(
        self,
        authorization_url: str,
        token_url: str,
        revoke_url: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        extra_params: Optional[dict[str, str]] = None,
    ):
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.revoke_url = revoke_url
        self.scopes = scopes or []
        self.extra_params = extra_params or {}


# Provider OAuth configurations
OAUTH_PROVIDER_CONFIGS: dict[str, OAuthProviderConfig] = {
    "docusign": OAuthProviderConfig(
        authorization_url="https://account.docusign.com/oauth/auth",
        token_url="https://account.docusign.com/oauth/token",
        revoke_url="https://account.docusign.com/oauth/revoke",
        scopes=["signature", "envelope_read", "user_read"],
    ),
    "sharepoint": OAuthProviderConfig(
        authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        revoke_url="https://login.microsoftonline.com/common/oauth2/v2.0/logout",
        scopes=["Sites.Read.All", "Files.Read.All", "offline_access"],
    ),
    "google_drive": OAuthProviderConfig(
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        revoke_url="https://oauth2.googleapis.com/revoke",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    ),
    "onedrive": OAuthProviderConfig(
        authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        revoke_url="https://login.microsoftonline.com/common/oauth2/v2.0/logout",
        scopes=["Files.Read.All", "offline_access"],
    ),
    "slack": OAuthProviderConfig(
        authorization_url="https://slack.com/oauth/v2/authorize",
        token_url="https://slack.com/api/oauth.v2.access",
        revoke_url=None,
        scopes=["files:read", "channels:history"],
    ),
    "teams": OAuthProviderConfig(
        authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        revoke_url=None,
        scopes=["ChannelMessage.Read.All", "offline_access"],
    ),
    "jira": OAuthProviderConfig(
        authorization_url="https://auth.atlassian.com/authorize",
        token_url="https://auth.atlassian.com/oauth/token",
        revoke_url=None,
        scopes=["read:jira-work", "read:jira-user", "offline_access"],
    ),
    "servicenow": OAuthProviderConfig(
        authorization_url="https://your-instance.service-now.com/oauth_auth.do",
        token_url="https://your-instance.service-now.com/oauth_token.do",
        revoke_url=None,
        scopes=[],
    ),
    "salesforce": OAuthProviderConfig(
        authorization_url="https://login.salesforce.com/services/oauth2/authorize",
        token_url="https://login.salesforce.com/services/oauth2/token",
        revoke_url="https://login.salesforce.com/services/oauth2/revoke",
        scopes=["api", "refresh_token", "offline_access"],
    ),
    "sap_ariba": OAuthProviderConfig(
        authorization_url="https://api.ariba.com/v2/oauth/authorize",
        token_url="https://api.ariba.com/v2/oauth/token",
        revoke_url=None,
        scopes=["read_contracts"],
    ),
}


class OAuthService:
    """
    Complete OAuth2 flow management service.

    Generates authorization URLs, handles callbacks, refreshes tokens,
    and manages credential lifecycle.
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        vault: Optional[CredentialVault] = None,
        audit: Optional[IntegrationAuditService] = None,
        telemetry: Optional[IntegrationTelemetry] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.vault = vault or CredentialVault()
        self.audit = audit
        self.telemetry = telemetry
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return self._http_client

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()

    def get_provider_config(self, provider: str) -> Optional[OAuthProviderConfig]:
        return OAUTH_PROVIDER_CONFIGS.get(provider)

    def generate_authorization_url(
        self,
        provider: str,
        integration_id: uuid.UUID,
        redirect_uri: str,
        scopes: Optional[list[str]] = None,
    ) -> dict[str, str]:
        """
        Generate OAuth2 authorization URL with state for CSRF protection.
        """
        config = self.get_provider_config(provider)
        if not config:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        state = secrets.token_urlsafe(32)
        scope = " ".join(scopes or config.scopes)
        client_id = self._get_client_id(provider)

        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            **config.extra_params,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{config.authorization_url}?{query}"

        logger.info(
            "oauth_authorization_url_generated",
            provider=provider,
            integration_id=str(integration_id),
        )

        return {
            "authorization_url": auth_url,
            "state": state,
            "redirect_uri": redirect_uri,
            "scope": scope,
        }

    async def handle_callback(
        self,
        integration_id: uuid.UUID,
        code: str,
        state: str,
        redirect_uri: str,
        expected_state: str,
    ) -> IntegrationCredential:
        """
        Handle OAuth2 callback: validate state, exchange code for tokens.
        """
        if state != expected_state:
            raise ValueError("OAuth state mismatch — possible CSRF attack")

        integration = await self._get_integration(integration_id)
        provider = integration.provider.value
        config = self.get_provider_config(provider)
        if not config:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        client_id = self._get_client_id(provider)
        client_secret = self._get_client_secret(provider)

        http = await self.get_client()
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        resp = await http.post(config.token_url, data=token_data)
        resp.raise_for_status()
        token_response = resp.json()

        # Encrypt tokens
        encrypted_access = self.vault.store_token(
            str(self.tenant_id),
            str(integration_id),
            token_response.get("access_token", ""),
            token_type="access_token",
        )
        encrypted_refresh = None
        if token_response.get("refresh_token"):
            encrypted_refresh = self.vault.store_token(
                str(self.tenant_id),
                str(integration_id),
                token_response["refresh_token"],
                token_type="refresh_token",
            )

        expires_in = token_response.get("expires_in", 3600)
        now = datetime.now(timezone.utc)

        credential = IntegrationCredential(
            integration_id=integration_id,
            tenant_id=self.tenant_id,
            credential_type=CredentialType.OAUTH2,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            oauth_provider=provider,
            oauth_client_id=client_id,
            oauth_scopes=token_response.get("scope", "").split(),
            oauth_access_token_expires_at=now + timedelta(seconds=expires_in),
            oauth_token_type=token_response.get("token_type", "Bearer"),
            oauth_id_token=token_response.get("id_token"),
            last_used_at=now,
        )

        self.db.add(credential)

        # Update integration status
        integration.status = IntegrationStatus.ACTIVE
        integration.scopes = credential.oauth_scopes

        await self.db.flush()

        # Audit
        if self.audit:
            await self.audit.log_event(
                integration_id=integration_id,
                action="oauth_callback_completed",
                resource_type="integration_credential",
                resource_id=str(credential.id),
                new_state={"credential_type": "oauth2", "provider": provider},
                change_summary=f"OAuth2 callback completed for {provider}",
                success=True,
            )

        if self.telemetry:
            self.telemetry.record_oauth_flow(provider=provider, success=True)

        logger.info(
            "oauth_callback_completed",
            integration_id=str(integration_id),
            provider=provider,
        )

        return credential

    async def refresh_token(
        self,
        integration_id: uuid.UUID,
        force: bool = False,
    ) -> IntegrationCredential:
        """
        Refresh an OAuth2 access token.

        Checks expiry before refreshing unless force=True.
        """
        integration = await self._get_integration(integration_id)
        provider = integration.provider.value
        config = self.get_provider_config(provider)
        if not config:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        credential = await self._get_active_credential(integration_id)
        if not credential:
            raise ValueError(f"No active credential for integration {integration_id}")

        # Check if refresh is needed
        if not force and credential.oauth_access_token_expires_at:
            if datetime.now(timezone.utc) < credential.oauth_access_token_expires_at - timedelta(minutes=5):
                logger.info(
                    "token_still_valid",
                    integration_id=str(integration_id),
                    expires_at=str(credential.oauth_access_token_expires_at),
                )
                return credential

        if not credential.encrypted_refresh_token:
            raise ValueError(f"No refresh token available for integration {integration_id}")

        refresh_token = self.vault.retrieve_token(
            str(self.tenant_id),
            str(integration_id),
            credential.encrypted_refresh_token,
            token_type="refresh_token",
        )

        client_id = self._get_client_id(provider)
        client_secret = self._get_client_secret(provider)

        http = await self.get_client()
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            resp = await http.post(config.token_url, data=refresh_data)
            resp.raise_for_status()
            token_response = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "token_refresh_failed",
                integration_id=str(integration_id),
                status_code=exc.response.status_code,
                error=str(exc),
            )
            if self.telemetry:
                self.telemetry.record_oauth_refresh(
                    provider=provider, success=False
                )
            raise

        # Encrypt new tokens
        encrypted_access = self.vault.store_token(
            str(self.tenant_id),
            str(integration_id),
            token_response.get("access_token", ""),
            token_type="access_token",
        )

        encrypted_refresh = credential.encrypted_refresh_token
        if token_response.get("refresh_token"):
            encrypted_refresh = self.vault.store_token(
                str(self.tenant_id),
                str(integration_id),
                token_response["refresh_token"],
                token_type="refresh_token",
            )

        expires_in = token_response.get("expires_in", 3600)
        now = datetime.now(timezone.utc)

        credential.encrypted_access_token = encrypted_access
        credential.encrypted_refresh_token = encrypted_refresh
        credential.oauth_access_token_expires_at = now + timedelta(seconds=expires_in)
        credential.last_used_at = now
        credential.rotation_count += 1
        credential.last_rotated_at = now
        credential.version += 1

        await self.db.flush()

        if self.audit:
            await self.audit.log_event(
                integration_id=integration_id,
                action="token_refreshed",
                resource_type="integration_credential",
                resource_id=str(credential.id),
                change_summary=f"OAuth2 token refreshed for {provider}",
                success=True,
            )

        if self.telemetry:
            self.telemetry.record_oauth_refresh(provider=provider, success=True)

        logger.info(
            "token_refreshed",
            integration_id=str(integration_id),
            provider=provider,
            rotation_count=credential.rotation_count,
        )

        return credential

    async def revoke_token(
        self,
        integration_id: uuid.UUID,
    ) -> None:
        """
        Revoke OAuth2 tokens and disable the integration.
        """
        integration = await self._get_integration(integration_id)
        provider = integration.provider.value
        config = self.get_provider_config(provider)

        credential = await self._get_active_credential(integration_id)
        if not credential:
            raise ValueError(f"No active credential for integration {integration_id}")

        if config and config.revoke_url and credential.encrypted_access_token:
            access_token = self.vault.retrieve_token(
                str(self.tenant_id),
                str(integration_id),
                credential.encrypted_access_token,
            )
            client_id = self._get_client_id(provider)
            client_secret = self._get_client_secret(provider)

            try:
                http = await self.get_client()
                await http.post(
                    config.revoke_url,
                    data={
                        "token": access_token,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )
            except httpx.HTTPError as exc:
                logger.warning("token_revoke_api_failed", error=str(exc))

        now = datetime.now(timezone.utc)
        credential.is_revoked = True
        credential.revoked_at = now
        credential.is_expired = True

        integration.status = IntegrationStatus.REVOKED
        integration.disabled_at = now
        integration.disabled_reason = "OAuth token revoked"

        await self.db.flush()

        if self.audit:
            await self.audit.log_event(
                integration_id=integration_id,
                action="token_revoked",
                resource_type="integration_credential",
                resource_id=str(credential.id),
                previous_state={"status": "active"},
                new_state={"status": "revoked"},
                change_summary=f"OAuth2 token revoked for {provider}",
                success=True,
            )

        logger.info(
            "token_revoked",
            integration_id=str(integration_id),
            provider=provider,
        )

    async def validate_scopes(
        self,
        integration_id: uuid.UUID,
        required_scopes: list[str],
    ) -> bool:
        """
        Validate that an integration's token has the required scopes.
        """
        credential = await self._get_active_credential(integration_id)
        if not credential:
            return False

        if not credential.oauth_scopes:
            return False

        granted = set(credential.oauth_scopes)
        return all(scope in granted for scope in required_scopes)

    async def _get_integration(self, integration_id: uuid.UUID) -> Integration:
        result = await self.db.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.tenant_id == self.tenant_id,
                Integration.is_deleted == False,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")
        return integration

    async def _get_active_credential(
        self, integration_id: uuid.UUID
    ) -> Optional[IntegrationCredential]:
        result = await self.db.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.integration_id == integration_id,
                IntegrationCredential.tenant_id == self.tenant_id,
                IntegrationCredential.is_revoked == False,
                IntegrationCredential.credential_type == CredentialType.OAUTH2,
            ).order_by(IntegrationCredential.version.desc())
        )
        return result.scalar_one_or_none()

    def _get_client_id(self, provider: str) -> str:
        import os
        return os.environ.get(
            f"{provider.upper()}_CLIENT_ID",
            f"dev-{provider}-client-id",
        )

    def _get_client_secret(self, provider: str) -> str:
        import os
        return os.environ.get(
            f"{provider.upper()}_CLIENT_SECRET",
            f"dev-{provider}-client-secret",
        )
