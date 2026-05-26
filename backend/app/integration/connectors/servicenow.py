"""ServiceNow connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class ServiceNowConnector(BaseConnector):
    """ServiceNow API connector."""

    @property
    def provider_name(self) -> str:
        return "servicenow"

    @property
    def base_url(self) -> str:
        instance = self.config.get("instance", "your-instance")
        return f"https://{instance}.service-now.com/api/now"

    async def authenticate(self) -> ConnectorAuth:
        if not self.auth:
            raise RuntimeError("ServiceNow: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "servicenow_sync_records",
            integration_id=str(self.integration_id),
        )
        table = self.config.get("table", "contract")
        client = await self.get_client()
        try:
            params: dict[str, Any] = {
                "sysparm_limit": min(max_items or 100, 1000),
                "sysparm_fields": "sys_id,number,name,contract_type,start_date,end_date,sys_updated_on",
                "sysparm_query": "sys_updated_on>=javascript:gs.dateGenerate('2020-01-01','00:00:00')",
                "sysparm_display_value": "true",
            }
            if cursor:
                params["sysparm_offset"] = int(cursor)
            resp = await client.get(f"/table/{table}", params=params)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("result", [])
            return SyncResult(
                success=True,
                synced_count=len(records),
                cursor=str(int(cursor or 0) + len(records)),
                metadata={"total": len(records)},
            )
        except Exception as exc:
            logger.error("servicenow_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/table/sys_user?sysparm_limit=1")
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
