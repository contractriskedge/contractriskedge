"""SAP Ariba connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class SapAribaConnector(BaseConnector):
    """SAP Ariba Procurement API connector."""

    @property
    def provider_name(self) -> str:
        return "sap_ariba"

    @property
    def base_url(self) -> str:
        realm = self.config.get("realm", "your-realm")
        base = self.config.get("base_url", "https://api.ariba.com")
        return f"{base}/v2/procurement/{realm}"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("SAP Ariba: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "sap_ariba_sync_contracts",
            integration_id=str(self.integration_id),
        )
        client = await self.get_client()
        try:
            params: dict[str, Any] = {
                "limit": min(max_items or 50, 200),
                "sort": "-lastModifiedDate",
            }
            if cursor:
                params["offset"] = int(cursor)
            resp = await client.get("/contracts", params=params)
            resp.raise_for_status()
            data = resp.json()
            contracts = data.get("data", [])
            return SyncResult(
                success=True,
                synced_count=len(contracts),
                cursor=str(int(cursor or 0) + len(contracts)),
                metadata={"total": data.get("totalCount")},
            )
        except Exception as exc:
            logger.error("sap_ariba_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/contracts", params={"limit": 1})
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
