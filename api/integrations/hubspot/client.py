"""HubSpot native integration for contract risk data.

Syncs risk scores to HubSpot Deal records and displays risk
information in the HubSpot CRM sidebar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class HubSpotConfig:
    """HubSpot OAuth 2.0 configuration."""

    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:3000/api/hubspot/callback"
    scopes: str = "crm.objects.deals.read crm.objects.deals.write settings.users.read"


class HubSpotClient:
    """Client for HubSpot CRM API integration.

    Pushes contract risk data to HubSpot Deal records and provides
    data for the HubSpot CRM sidebar card.

    Usage:
        client = HubSpotClient(access_token="...")
        await client.push_risk_score(deal_id="...", risk_score=8.5)
    """

    DEAL_PROPERTIES = {
        "contract_risk_score": "number",
        "top_risk_category": "enumeration",
        "risk_analysis_url": "text",
        "redlines_pending": "number",
        "risk_analysis_date": "date",
    }

    def __init__(self, access_token: str = "") -> None:
        """Initialize the HubSpot client.

        Args:
            access_token: HubSpot OAuth access token.
        """
        self._access_token = access_token
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = "https://api.hubapi.com"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            Configured async HTTP client.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
            )
        return self._client

    def set_access_token(self, token: str) -> None:
        """Set or refresh the OAuth access token.

        Args:
            token: New access token.
        """
        self._access_token = token

    async def push_risk_score(
        self,
        deal_id: str,
        risk_score: float,
        top_category: str = "",
        analysis_url: str = "",
        redlines_pending: int = 0,
    ) -> bool:
        """Push risk score data to a HubSpot Deal record.

        Args:
            deal_id: HubSpot Deal ID.
            risk_score: Overall risk score (1-10).
            top_category: Top risk category name.
            analysis_url: URL to the full risk analysis.
            redlines_pending: Number of pending redlines.

        Returns:
            True if the update succeeded.
        """
        if not self._access_token:
            logger.error("HubSpot access token not set")
            return False

        client = await self._get_client()

        properties = {
            "contract_risk_score": str(risk_score),
            "top_risk_category": top_category,
            "risk_analysis_url": analysis_url,
            "redlines_pending": str(redlines_pending),
            "risk_analysis_date": "today",
        }

        payload = {
            "properties": {k: v for k, v in properties.items() if v},
        }

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.patch(
                f"/crm/v3/objects/deals/{deal_id}",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            logger.info(
                "HubSpot risk score pushed for Deal %s: %.1f",
                deal_id, risk_score,
            )
            return True

        except httpx.HTTPStatusError as exc:
            logger.error(
                "HubSpot push failed for %s: %s",
                deal_id, exc.response.text,
            )
            return False

    async def get_deal(self, deal_id: str) -> Optional[Dict[str, Any]]:
        """Get a HubSpot Deal by ID.

        Args:
            deal_id: HubSpot Deal ID.

        Returns:
            Deal data or None.
        """
        if not self._access_token:
            return None

        client = await self._get_client()
        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = await client.get(
                f"/crm/v3/objects/deals/{deal_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

        except Exception as exc:
            logger.error("Failed to get HubSpot deal: %s", exc)
            return None

    @staticmethod
    def get_sidebar_card_payload(
        risk_score: float,
        top_risks: List[Dict[str, Any]],
        analysis_url: str,
    ) -> Dict[str, Any]:
        """Generate the HubSpot CRM sidebar card payload.

        Args:
            risk_score: Overall risk score.
            top_risks: Top 3 risk flags with category and severity.
            analysis_url: Deep-link to full analysis.

        Returns:
            Card payload for HubSpot CRM card API.
        """
        return {
            "results": [
                {
                    "objectId": 1,
                    "title": "Contract Risk Analysis",
                    "body": (
                        f"Risk Score: {risk_score}/10\n"
                        f"Top Risks:\n" +
                        "\n".join(
                            f"  - {r.get('category', 'Unknown')}: "
                            f"{r.get('severity', 'N/A')}/10"
                            for r in top_risks[:3]
                        )
                    ),
                    "actions": [
                        {
                            "type": "IFRAME",
                            "label": "Open Full Analysis",
                            "url": analysis_url,
                        }
                    ],
                }
            ]
        }
