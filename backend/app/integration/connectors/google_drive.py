"""Google Drive connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class GoogleDriveConnector(BaseConnector):
    """Google Drive API connector."""

    @property
    def provider_name(self) -> str:
        return "google_drive"

    @property
    def base_url(self) -> str:
        return "https://www.googleapis.com/drive/v3"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("GoogleDrive: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "google_drive_sync_documents",
            integration_id=str(self.integration_id),
        )
        client = await self.get_client()
        try:
            params: dict[str, Any] = {
                "pageSize": min(max_items or 100, 1000),
                "fields": "files(id,name,mimeType,modifiedTime,size,parents)",
                "q": "mimeType contains 'application/pdf' or mimeType contains 'application/vnd.openxmlformats-officedocument'",
            }
            if cursor:
                params["pageToken"] = cursor
            resp = await client.get("/files", params=params)
            resp.raise_for_status()
            data = resp.json()
            files = data.get("files", [])
            return SyncResult(
                success=True,
                synced_count=len(files),
                cursor=data.get("nextPageToken"),
            )
        except Exception as exc:
            logger.error("google_drive_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/about", params={"fields": "user"})
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
