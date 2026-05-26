"""Salesforce bidirectional sync client for contract risk data.

Pushes risk scores to Salesforce Opportunity records and receives
updates when Opportunity stages change.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SalesforceConfig:
    """Salesforce OAuth 2.0 and connection configuration."""

    client_id: str
    client_secret: str
    username: str
    password: str
    security_token: str = ""
    sandbox: bool = False
    api_version: str = "60.0"

    @property
    def login_url(self) -> str:
        if self.sandbox:
            return "https://test.salesforce.com/services/oauth2/token"
        return "https://login.salesforce.com/services/oauth2/token"


class SalesforceClient:
    """Client for Salesforce REST API integration.

    Syncs contract risk scores to Salesforce Opportunity records
    and handles inbound updates from Salesforce.

    Usage:
        config = SalesforceConfig(
            client_id="...", client_secret="...",
            username="...", password="...",
        )
        client = SalesforceClient(config)
        await client.push_risk_score(opportunity_id="...", risk_score=8.5)
    """

    RISK_FIELD_MAP = {
        "contract_risk_score__c": "number",
        "top_risk_category__c": "text",
        "risk_analysis_url__c": "text",
        "risk_analysis_date__c": "datetime",
        "redlines_pending__c": "number",
    }

    def __init__(self, config: SalesforceConfig) -> None:
        """Initialize the Salesforce client.

        Args:
            config: Salesforce connection configuration.
        """
        self._config = config
        self._access_token: Optional[str] = None
        self._instance_url: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            Configured async HTTP client.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def authenticate(self) -> bool:
        """Authenticate with Salesforce using OAuth 2.0 password flow.

        Returns:
            True if authentication succeeded.
        """
        client = await self._get_client()

        data = {
            "grant_type": "password",
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "username": self._config.username,
            "password": f"{self._config.password}{self._config.security_token}",
        }

        try:
            response = await client.post(self._config.login_url, data=data)
            response.raise_for_status()
            result = response.json()

            self._access_token = result["access_token"]
            self._instance_url = result["instance_url"]

            logger.info("Salesforce authentication successful")
            return True

        except Exception as exc:
            logger.error("Salesforce authentication failed: %s", exc)
            return False

    async def push_risk_score(
        self,
        opportunity_id: str,
        risk_score: float,
        top_category: str = "",
        analysis_url: str = "",
        redlines_pending: int = 0,
    ) -> bool:
        """Push risk score data to a Salesforce Opportunity.

        Args:
            opportunity_id: Salesforce Opportunity ID.
            risk_score: Overall risk score (1-10).
            top_category: Top risk category name.
            analysis_url: URL to the full risk analysis.
            redlines_pending: Number of pending redlines.

        Returns:
            True if the update succeeded.
        """
        if not self._access_token:
            if not await self.authenticate():
                return False

        client = await self._get_client()
        url = (
            f"{self._instance_url}/services/data/v{self._config.api_version}"
            f"/sobjects/Opportunity/{opportunity_id}"
        )

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "Contract_Risk_Score__c": risk_score,
            "Top_Risk_Category__c": top_category,
            "Risk_Analysis_URL__c": analysis_url,
            "Risk_Analysis_Date__c": "now",
            "Redlines_Pending__c": redlines_pending,
        }

        try:
            response = await client.patch(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(
                "Salesforce risk score pushed for Opportunity %s: %.1f",
                opportunity_id, risk_score,
            )
            return True

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Salesforce push failed for %s: %s",
                opportunity_id, exc.response.text,
            )
            return False

    async def get_opportunity_stage(self, opportunity_id: str) -> Optional[str]:
        """Get the current stage of a Salesforce Opportunity.

        Args:
            opportunity_id: Salesforce Opportunity ID.

        Returns:
            Stage name or None.
        """
        if not self._access_token:
            if not await self.authenticate():
                return None

        client = await self._get_client()
        url = (
            f"{self._instance_url}/services/data/v{self._config.api_version}"
            f"/sobjects/Opportunity/{opportunity_id}"
        )

        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("StageName")

        except Exception as exc:
            logger.error("Failed to get Opportunity stage: %s", exc)
            return None
