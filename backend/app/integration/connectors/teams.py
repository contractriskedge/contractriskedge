"""Microsoft Teams connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class TeamsConnector(BaseConnector):
    """Microsoft Teams connector via Graph API."""

    @property
    def provider_name(self) -> str:
        return "teams"

    @property
    def base_url(self) -> str:
        return "https://graph.microsoft.com/v1.0"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("Teams: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "teams_sync_messages",
            integration_id=str(self.integration_id),
        )
        team_id = self.config.get("team_id", "")
        channel_id = self.config.get("channel_id", "")
        client = await self.get_client()
        try:
            params: dict[str, Any] = {"$top": max_items or 50}
            if cursor:
                params["$skip"] = int(cursor)
            resp = await client.get(
                f"/teams/{team_id}/channels/{channel_id}/messages",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            messages = data.get("value", [])
            return SyncResult(
                success=True,
                synced_count=len(messages),
                cursor=str(len(messages) + int(cursor or 0)),
            )
        except Exception as exc:
            logger.error("teams_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/teams?$top=1")
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
