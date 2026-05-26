"""OneDrive connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class OneDriveConnector(BaseConnector):
    """Microsoft OneDrive connector via Graph API."""

    @property
    def provider_name(self) -> str:
        return "onedrive"

    @property
    def base_url(self) -> str:
        return "https://graph.microsoft.com/v1.0"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("OneDrive: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "onedrive_sync_documents",
            integration_id=str(self.integration_id),
        )
        client = await self.get_client()
        try:
            endpoint = "/me/drive/root/delta"
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
            logger.error("onedrive_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/me/drive")
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
