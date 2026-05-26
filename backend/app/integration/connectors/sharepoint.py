"""SharePoint connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class SharePointConnector(BaseConnector):
    """Microsoft SharePoint Online connector via Graph API."""

    @property
    def provider_name(self) -> str:
        return "sharepoint"

    @property
    def base_url(self) -> str:
        return "https://graph.microsoft.com/v1.0"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("SharePoint: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "sharepoint_sync_documents",
            integration_id=str(self.integration_id),
            delta_token=delta_token,
        )
        site_id = self.config.get("site_id", "")
        drive_id = self.config.get("drive_id", "")
        client = await self.get_client()
        try:
            endpoint = f"/sites/{site_id}/drives/{drive_id}/root/delta"
            params: dict[str, Any] = {"$top": max_items or 100}
            if delta_token:
                params["token"] = delta_token
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("value", [])
            return SyncResult(
                success=True,
                synced_count=len(items),
                delta_token=data.get("@odata.deltaLink"),
                cursor=data.get("@odata.nextLink"),
            )
        except Exception as exc:
            logger.error("sharepoint_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/sites?$top=1")
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
