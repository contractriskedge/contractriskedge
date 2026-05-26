"""Jira connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class JiraConnector(BaseConnector):
    """Atlassian Jira Cloud connector."""

    @property
    def provider_name(self) -> str:
        return "jira"

    @property
    def base_url(self) -> str:
        domain = self.config.get("domain", "your-domain.atlassian.net")
        return f"https://{domain}/rest/api/3"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("Jira: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "jira_sync_issues",
            integration_id=str(self.integration_id),
        )
        client = await self.get_client()
        try:
            jql = self.config.get("jql", "updated >= -30d ORDER BY updated DESC")
            params: dict[str, Any] = {
                "jql": jql,
                "maxResults": min(max_items or 100, 100),
                "fields": ["id", "key", "summary", "status", "updated", "attachment"],
            }
            if cursor:
                params["startAt"] = int(cursor)
            resp = await client.get("/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            issues = data.get("issues", [])
            return SyncResult(
                success=True,
                synced_count=len(issues),
                cursor=str(data.get("startAt", 0) + len(issues)),
                metadata={"total": data.get("total")},
            )
        except Exception as exc:
            logger.error("jira_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/serverInfo")
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
