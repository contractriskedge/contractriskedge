"""Salesforce connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class SalesforceConnector(BaseConnector):
    """Salesforce REST API connector."""

    @property
    def provider_name(self) -> str:
        return "salesforce"

    @property
    def base_url(self) -> str:
        instance_url = self.config.get("instance_url", "https://your-instance.salesforce.com")
        return f"{instance_url}/services/data/v58.0"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("Salesforce: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "salesforce_sync_attachments",
            integration_id=str(self.integration_id),
        )
        client = await self.get_client()
        try:
            soql = (
                "SELECT Id, Name, ParentId, ContentType, BodyLength, "
                "CreatedDate, LastModifiedDate FROM Attachment "
                "ORDER BY LastModifiedDate DESC"
            )
            params: dict[str, Any] = {"q": soql}
            if cursor:
                params["q"] = f"{soql} LIMIT {max_items or 100} OFFSET {int(cursor)}"
            resp = await client.get("/query", params=params)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("records", [])
            return SyncResult(
                success=True,
                synced_count=len(records),
                cursor=str(int(cursor or 0) + len(records)),
                metadata={"total_size": data.get("totalSize")},
            )
        except Exception as exc:
            logger.error("salesforce_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/limits")
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
