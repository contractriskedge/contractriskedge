"""DocuSign connector adapter."""

from typing import Any, Optional

from structlog import get_logger

from app.integration.connectors.base import (
    BaseConnector,
    ConnectorAuth,
    ConnectorHealth,
    SyncResult,
)

logger = get_logger(__name__)


class DocuSignConnector(BaseConnector):
    """DocuSign eSignature API connector."""

    @property
    def provider_name(self) -> str:
        return "docusign"

    @property
    def base_url(self) -> str:
        account_id = self.config.get("account_id", "")
        base = self.config.get("base_url", "https://demo.docusign.net/restapi")
        return f"{base}/v2.1/accounts/{account_id}"

    async def authenticate(self) -> ConnectorAuth:
        logger.info("docusign_authenticate", integration_id=str(self.integration_id))
        # OAuth2 token exchange handled by OAuthService
        if not self.auth:
            raise RuntimeError("DocuSign: no auth context provided")
        return self.auth

    async def sync_documents(
        self,
        cursor: Optional[str] = None,
        delta_token: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> SyncResult:
        logger.info(
            "docusign_sync_documents",
            integration_id=str(self.integration_id),
            cursor=cursor,
        )
        client = await self.get_client()
        limit = max_items or 100
        try:
            resp = await client.get(
                "/envelopes",
                params={
                    "from_date": cursor or "2020-01-01T00:00:00Z",
                    "status": "completed",
                    "count": limit,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            envelopes = data.get("envelopes", [])
            return SyncResult(
                success=True,
                synced_count=len(envelopes),
                cursor=data.get("result_set_cursor"),
                metadata={"total_set_size": data.get("total_set_size")},
            )
        except Exception as exc:
            logger.error("docusign_sync_failed", error=str(exc))
            return SyncResult(
                success=False,
                failed_count=1,
                errors=[{"error": str(exc)}],
            )

    async def check_health(self) -> ConnectorHealth:
        try:
            client = await self.get_client()
            resp = await client.get("/")
            return ConnectorHealth(
                healthy=resp.is_success,
                latency_ms=resp.elapsed.total_seconds() * 1000,
            )
        except Exception as exc:
            return ConnectorHealth(healthy=False, error=str(exc))

    async def get_delta_link(self) -> Optional[str]:
        return None
