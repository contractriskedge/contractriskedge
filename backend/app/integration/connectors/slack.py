"""Slack connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class SlackConnector(BaseConnector):
    """Slack API connector."""

    @property
    def provider_name(self) -> str:
        return "slack"

    @property
    def base_url(self) -> str:
        return "https://slack.com/api"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("Slack: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "slack_sync_files",
            integration_id=str(self.integration_id),
        )
        client = await self.get_client()
        try:
            params: dict[str, Any] = {
                "count": min(max_items or 100, 200),
                "types": "files",
            }
            if cursor:
                params["page"] = cursor
            resp = await client.get("/search.files", params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return SyncResult(
                    success=False,
                    failed_count=1,
                    errors=[{"error": data.get("error", "unknown")}],
                )
            files = data.get("files", [])
            return SyncResult(
                success=True,
                synced_count=len(files),
                cursor=data.get("next_cursor"),
            )
        except Exception as exc:
            logger.error("slack_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/api.test")
            data = resp.json()
            return ConnectorHealth(
                healthy=data.get("ok", False),
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
