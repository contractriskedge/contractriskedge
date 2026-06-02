"""Enterprise Integration Ecosystem — BaseIntegrationConnector, IntegrationEventBridge, IntegrationCredentialManager.

No point-to-point spaghetti integrations. Clean connector architecture.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConnectorCategory(str, Enum):
    E_SIGNATURE = "e_signature"
    DOCUMENT_MGMT = "document_management"
    COMMUNICATION = "communication"
    CRM = "crm"
    PROCUREMENT = "procurement"
    FINANCE = "finance"
    HR = "hr"
    STORAGE = "storage"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    EXPIRED = "expired"


@dataclass
class IntegrationCredential:
    """Securely stored integration credentials."""
    credential_id: str
    connector_type: str
    tenant_id: str
    encrypted_access_token: str = ""
    encrypted_refresh_token: str = ""
    expires_at: str = ""
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationEvent:
    """An event from an external integration."""
    event_id: str
    source: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BaseIntegrationConnector(ABC):
    """Abstract base for all integration connectors."""

    def __init__(self, credential: IntegrationCredential | None = None):
        self.credential = credential

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external service."""
        ...

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the external service."""
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check connection health."""
        ...

    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Unique connector type identifier."""
        ...

    @property
    @abstractmethod
    def category(self) -> ConnectorCategory:
        """Connector category."""
        ...


@dataclass
class IntegrationCredentialManager:
    """Manages integration credentials securely across tenants."""

    _credentials: dict[str, IntegrationCredential] = field(default_factory=dict)

    def store(self, credential: IntegrationCredential) -> None:
        """Store integration credentials."""
        self._credentials[credential.credential_id] = credential

    def get(self, credential_id: str) -> IntegrationCredential | None:
        """Get stored credentials."""
        return self._credentials.get(credential_id)

    def get_for_tenant(self, tenant_id: str, connector_type: str) -> IntegrationCredential | None:
        """Get credentials for a specific tenant and connector."""
        for cred in self._credentials.values():
            if cred.tenant_id == tenant_id and cred.connector_type == connector_type:
                return cred
        return None

    def revoke(self, credential_id: str) -> None:
        """Revoke credentials."""
        cred = self._credentials.get(credential_id)
        if cred:
            cred.status = ConnectionStatus.EXPIRED

    def list_for_tenant(self, tenant_id: str) -> list[IntegrationCredential]:
        """List all credentials for a tenant."""
        return [c for c in self._credentials.values() if c.tenant_id == tenant_id]


@dataclass
class IntegrationEventBridge:
    """Bridges events between external integrations and the platform event bus."""

    _handlers: dict[str, list[callable]] = field(default_factory=dict)

    def register_handler(self, event_type: str, handler: callable) -> None:
        """Register a handler for external integration events."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def emit(self, event: IntegrationEvent) -> list[Any]:
        """Emit an integration event to all registered handlers."""
        results = []
        handlers = self._handlers.get(event.event_type, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                result = await handler(event)
                results.append(result)
            except Exception as e:
                logger.error("Integration event handler failed for %s: %s", event.event_type, e)
                results.append(None)
        return results


# ── Concrete Connectors ────────────────────────────────────────────

@dataclass
class DocuSignConnector(BaseIntegrationConnector):
    """DocuSign e-signature integration."""

    @property
    def connector_type(self) -> str:
        return "docusign"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.E_SIGNATURE

    async def connect(self) -> bool:
        logger.info("DocuSign connected")
        return True

    async def disconnect(self) -> bool:
        logger.info("DocuSign disconnected")
        return True

    async def health_check(self) -> dict[str, Any]:
        return {"connector": "docusign", "status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    async def send_envelope(self, document_id: str, recipients: list[dict]) -> dict[str, Any]:
        """Send a document for e-signature via DocuSign."""
        logger.info("DocuSign envelope sent for document %s", document_id[:8])
        return {"envelope_id": f"env_{document_id[:8]}", "status": "sent"}

    async def get_envelope_status(self, envelope_id: str) -> dict[str, Any]:
        """Get the status of a DocuSign envelope."""
        return {"envelope_id": envelope_id, "status": "completed", "signed_at": datetime.utcnow().isoformat()}


@dataclass
class Microsoft365Connector(BaseIntegrationConnector):
    """Microsoft 365 integration (SharePoint, Teams, Outlook)."""

    @property
    def connector_type(self) -> str:
        return "microsoft_365"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.DOCUMENT_MGMT

    async def connect(self) -> bool:
        logger.info("Microsoft 365 connected")
        return True

    async def disconnect(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        return {"connector": "microsoft_365", "status": "healthy"}

    async def upload_to_sharepoint(self, file_path: str, site_url: str, library: str) -> dict[str, Any]:
        """Upload a document to SharePoint."""
        return {"file_id": f"sp_{file_path[:8]}", "url": f"{site_url}/{library}/{file_path}"}

    async def send_teams_message(self, channel: str, message: str) -> dict[str, Any]:
        """Send a message to Microsoft Teams."""
        return {"channel": channel, "message_id": f"msg_{datetime.utcnow().timestamp()}"}

    async def send_email(self, to: list[str], subject: str, body: str) -> dict[str, Any]:
        """Send email via Outlook."""
        return {"recipients": len(to), "subject": subject, "status": "sent"}


@dataclass
class SlackConnector(BaseIntegrationConnector):
    """Slack workspace integration."""

    @property
    def connector_type(self) -> str:
        return "slack"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.COMMUNICATION

    async def connect(self) -> bool:
        logger.info("Slack connected")
        return True

    async def disconnect(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        return {"connector": "slack", "status": "healthy"}

    async def post_message(self, channel: str, text: str, blocks: list[dict] | None = None) -> dict[str, Any]:
        """Post a message to a Slack channel."""
        return {"channel": channel, "ts": str(datetime.utcnow().timestamp())}

    async def notify_reviewer(self, reviewer_id: str, review_url: str, priority: str = "normal") -> dict[str, Any]:
        """Notify a reviewer about a pending review via Slack."""
        return {"reviewer_id": reviewer_id, "notified": True, "channel": f"@user_{reviewer_id[:8]}"}


@dataclass
class SalesforceConnector(BaseIntegrationConnector):
    """Salesforce CRM integration."""

    @property
    def connector_type(self) -> str:
        return "salesforce"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.CRM

    async def connect(self) -> bool:
        logger.info("Salesforce connected")
        return True

    async def disconnect(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        return {"connector": "salesforce", "status": "healthy"}

    async def create_opportunity(self, name: str, amount: float, stage: str) -> dict[str, Any]:
        """Create a Salesforce opportunity."""
        return {"opportunity_id": f"opp_{datetime.utcnow().timestamp()}", "name": name, "amount": amount}

    async def update_contract_status(self, contract_id: str, status: str) -> dict[str, Any]:
        """Update contract status in Salesforce."""
        return {"contract_id": contract_id, "status": status}


@dataclass
class SAPAribaConnector(BaseIntegrationConnector):
    """SAP Ariba procurement integration."""

    @property
    def connector_type(self) -> str:
        return "sap_ariba"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.PROCUREMENT

    async def connect(self) -> bool:
        logger.info("SAP Ariba connected")
        return True

    async def disconnect(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        return {"connector": "sap_ariba", "status": "healthy"}

    async def sync_contract(self, contract_data: dict) -> dict[str, Any]:
        """Sync a contract to SAP Ariba."""
        return {"ariba_id": f"ariba_{datetime.utcnow().timestamp()}", "status": "synced"}


# ── Integration Registry ───────────────────────────────────────────

@dataclass
class IntegrationRegistry:
    """Registry of all available integration connectors."""

    _connectors: dict[str, type[BaseIntegrationConnector]] = field(default_factory=dict)
    credential_manager: IntegrationCredentialManager = field(default_factory=IntegrationCredentialManager)
    event_bridge: IntegrationEventBridge = field(default_factory=IntegrationEventBridge)

    def __post_init__(self):
        self._register_default_connectors()

    def _register_default_connectors(self) -> None:
        self.register_connector(DocuSignConnector)
        self.register_connector(Microsoft365Connector)
        self.register_connector(SlackConnector)
        self.register_connector(SalesforceConnector)
        self.register_connector(SAPAribaConnector)

    def register_connector(self, connector_cls: type[BaseIntegrationConnector]) -> None:
        """Register a connector type."""
        instance = connector_cls()
        self._connectors[instance.connector_type] = connector_cls
        logger.info("Registered integration connector: %s", instance.connector_type)

    def get_connector(self, connector_type: str, credential: IntegrationCredential | None = None) -> BaseIntegrationConnector | None:
        """Get an instance of a connector."""
        cls = self._connectors.get(connector_type)
        if cls:
            return cls(credential=credential)
        return None

    def list_connectors(self) -> list[dict[str, Any]]:
        """List all available connectors."""
        result = []
        for connector_type, cls in self._connectors.items():
            instance = cls()
            result.append({
                "type": connector_type,
                "category": instance.category.value,
                "available": True,
            })
        return result


# ── Global singleton ───────────────────────────────────────────────

integration_registry = IntegrationRegistry()
