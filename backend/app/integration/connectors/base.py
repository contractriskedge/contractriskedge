"""
Base connector abstraction for all external service integrations.

Defines the contract that every connector adapter must implement.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx


@dataclass
class ConnectorAuth:
    """Authentication context passed to connector operations."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scopes: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    synced_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    cursor: Optional[str] = None
    delta_token: Optional[str] = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None


@dataclass
class ConnectorHealth:
    """Health check result for a connector."""

    healthy: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset_at: Optional[datetime] = None


class BaseConnector(ABC):
    """
    Abstract base class for all connector adapters.

    Each connector adapter implements the specific API interactions
    for its external service, while the framework handles auth,
    retries, rate-limiting, and observability.
    """

    def __init__(
        self,
        auth: Optional[ConnectorAuth] = None,
        config: Optional[dict[str, Any]] = None,
        tenant_id: Optional[uuid.UUID] = None,
        integration_id: Optional[uuid.UUID] = None,
    ):
        self.auth = auth
        self.config = config or {}
        self.tenant_id = tenant_id
        self.integration_id = integration_id
        self._client: Optional[httpx.AsyncClient] = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'docusign', 'sharepoint')."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for API calls."""
        ...

    @abstractmethod
    async def authenticate(self) -> ConnectorAuth:
        """Authenticate and return auth context."""
        ...

    @abstractmethod
    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        """Sync documents from the external service."""
        ...

    @abstractmethod
    async def check_health(self) -> ConnectorHealth:
        """Check connector health and API reachability."""
        ...

    @abstractmethod
    async def get_delta_link(self) -> Optional[str]:
        """Get a delta link for incremental syncs, if supported."""
        ...

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create an authenticated HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"User-Agent": "ContractRiskEdge-Integration/1.0"}
            if self.auth and self.auth.access_token:
                headers["Authorization"] = (
                    f"{self.auth.token_type} {self.auth.access_token}"
                )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "BaseConnector":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
