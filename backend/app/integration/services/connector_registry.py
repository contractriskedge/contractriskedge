"""
ConnectorRegistry — central registry for discovering and instantiating
connector adapters. Maps provider names to their adapter classes.
"""

import importlib
from dataclasses import dataclass, field
from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import BaseConnector

logger = get_logger(__name__)


@dataclass
class ConnectorRegistration:
    """Metadata about a registered connector adapter."""

    provider: str
    display_name: str
    version: str
    adapter_class: type[BaseConnector]
    oauth_supported: bool = False
    webhook_supported: bool = False
    delta_sync_supported: bool = False
    rate_limit_default: Optional[int] = None
    scopes_default: list[str] = field(default_factory=list)
    config_schema: Optional[dict[str, Any]] = None
    description: str = ""


class ConnectorRegistry:
    """
    Registry of all available connector adapters.

    Connectors register themselves or are discovered via entry points.
    """

    def __init__(self):
        self._registry: dict[str, ConnectorRegistration] = {}
        self._initialized = False

    def register(self, registration: ConnectorRegistration) -> None:
        """Register a connector adapter."""
        self._registry[registration.provider] = registration
        logger.info(
            "connector_registered",
            provider=registration.provider,
            version=registration.version,
        )

    def get(self, provider: str) -> Optional[ConnectorRegistration]:
        """Get connector registration by provider name."""
        return self._registry.get(provider)

    def get_adapter(self, provider: str, **kwargs: Any) -> Optional[BaseConnector]:
        """Instantiate a connector adapter by provider name."""
        registration = self.get(provider)
        if not registration:
            logger.error("connector_not_found", provider=provider)
            return None
        return registration.adapter_class(**kwargs)

    def list_providers(self) -> list[ConnectorRegistration]:
        """List all registered connector providers."""
        return list(self._registry.values())

    def get_supported_providers(self) -> list[str]:
        """Get list of all supported provider names."""
        return list(self._registry.keys())

    def is_supported(self, provider: str) -> bool:
        """Check if a provider is supported."""
        return provider in self._registry

    def initialize_defaults(self) -> None:
        """Register all built-in connectors."""
        if self._initialized:
            return

        # Lazy imports to avoid circular dependencies
        from app.integration.connectors.docusign import DocuSignConnector
        from app.integration.connectors.sharepoint import SharePointConnector
        from app.integration.connectors.google_drive import GoogleDriveConnector
        from app.integration.connectors.onedrive import OneDriveConnector
        from app.integration.connectors.slack import SlackConnector
        from app.integration.connectors.teams import TeamsConnector
        from app.integration.connectors.jira import JiraConnector
        from app.integration.connectors.servicenow import ServiceNowConnector
        from app.integration.connectors.salesforce import SalesforceConnector
        from app.integration.connectors.sap_ariba import SapAribaConnector

        registrations = [
            ConnectorRegistration(
                provider="docusign",
                display_name="DocuSign",
                version="1.0.0",
                adapter_class=DocuSignConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=True,
                rate_limit_default=300,
                scopes_default=["signature", "envelope_read"],
                description="DocuSign eSignature integration",
            ),
            ConnectorRegistration(
                provider="sharepoint",
                display_name="SharePoint",
                version="1.0.0",
                adapter_class=SharePointConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=True,
                rate_limit_default=600,
                scopes_default=["sites.read.all", "files.read.all"],
                description="Microsoft SharePoint document library integration",
            ),
            ConnectorRegistration(
                provider="google_drive",
                display_name="Google Drive",
                version="1.0.0",
                adapter_class=GoogleDriveConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=True,
                rate_limit_default=1000,
                scopes_default=["https://www.googleapis.com/auth/drive.readonly"],
                description="Google Drive file integration",
            ),
            ConnectorRegistration(
                provider="onedrive",
                display_name="OneDrive",
                version="1.0.0",
                adapter_class=OneDriveConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=True,
                rate_limit_default=600,
                scopes_default=["files.read.all"],
                description="Microsoft OneDrive integration",
            ),
            ConnectorRegistration(
                provider="slack",
                display_name="Slack",
                version="1.0.0",
                adapter_class=SlackConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=False,
                rate_limit_default=50,
                scopes_default=["files:read", "channels:history"],
                description="Slack workspace integration",
            ),
            ConnectorRegistration(
                provider="teams",
                display_name="Microsoft Teams",
                version="1.0.0",
                adapter_class=TeamsConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=False,
                rate_limit_default=300,
                scopes_default=["channelmessage.read.all"],
                description="Microsoft Teams integration",
            ),
            ConnectorRegistration(
                provider="jira",
                display_name="Jira",
                version="1.0.0",
                adapter_class=JiraConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=True,
                rate_limit_default=100,
                scopes_default=["read:jira-work"],
                description="Atlassian Jira integration",
            ),
            ConnectorRegistration(
                provider="servicenow",
                display_name="ServiceNow",
                version="1.0.0",
                adapter_class=ServiceNowConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=True,
                rate_limit_default=100,
                scopes_default=[],
                description="ServiceNow integration",
            ),
            ConnectorRegistration(
                provider="salesforce",
                display_name="Salesforce",
                version="1.0.0",
                adapter_class=SalesforceConnector,
                oauth_supported=True,
                webhook_supported=True,
                delta_sync_supported=True,
                rate_limit_default=100,
                scopes_default=["api", "refresh_token"],
                description="Salesforce CRM integration",
            ),
            ConnectorRegistration(
                provider="sap_ariba",
                display_name="SAP Ariba",
                version="1.0.0",
                adapter_class=SapAribaConnector,
                oauth_supported=True,
                webhook_supported=False,
                delta_sync_supported=True,
                rate_limit_default=50,
                scopes_default=["read_contracts"],
                description="SAP Ariba procurement integration",
            ),
        ]

        for reg in registrations:
            self.register(reg)

        self._initialized = True
        logger.info("connector_registry_initialized", count=len(registrations))


# Global singleton
_global_registry: Optional[ConnectorRegistry] = None


def get_connector_registry() -> ConnectorRegistry:
    """Get or create the global connector registry singleton."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ConnectorRegistry()
        _global_registry.initialize_defaults()
    return _global_registry
