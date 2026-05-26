"""Counterparty risk scoring with D&B, Creditsafe, and news sentiment.

Enriches counterparty detection with external financial risk data
from Dun & Bradstreet and Creditsafe APIs, plus news sentiment analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CounterpartyRiskScore:
    """Complete counterparty risk assessment."""

    overall_score: float  # 0-100 (100 = highest risk)
    financial_health: Optional[float] = None
    credit_rating: Optional[str] = None
    litigation_count: int = 0
    news_sentiment: Optional[float] = None
    data_sources: List[str] = field(default_factory=list)
    risk_level: str = "unknown"  # low, medium, high, critical
    details: Dict[str, Any] = field(default_factory=dict)


class CounterpartyRiskScorer:
    """Scores counterparty risk using multiple data sources.

    Combines D&B financial health, Creditsafe credit rating,
    PACER litigation data, and news sentiment into a single score.

    Usage:
        scorer = CounterpartyRiskScorer()
        score = await scorer.score("Acme Corp")
    """

    WEIGHTS = {
        "financial_health": 0.40,
        "credit_rating": 0.30,
        "litigation": 0.20,
        "news_sentiment": 0.10,
    }

    def __init__(self) -> None:
        """Initialize the counterparty risk scorer."""
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def score(
        self,
        company_name: str,
        duns_number: Optional[str] = None,
    ) -> CounterpartyRiskScore:
        """Score a counterparty's risk.

        Args:
            company_name: The counterparty company name.
            duns_number: Optional D&B DUNS number.

        Returns:
            CounterpartyRiskScore with all available data.
        """
        score = CounterpartyRiskScore()

        # Gather data from all sources
        financial = await self._get_financial_health(company_name, duns_number)
        credit = await self._get_credit_rating(company_name)
        litigation = await self._get_litigation_count(company_name)
        sentiment = await self._get_news_sentiment(company_name)

        # Populate score
        if financial is not None:
            score.financial_health = financial
            score.data_sources.append("dnb")
        if credit is not None:
            score.credit_rating = credit
            score.data_sources.append("creditsafe")
        if litigation is not None:
            score.litigation_count = litigation
            score.data_sources.append("pacer")
        if sentiment is not None:
            score.news_sentiment = sentiment
            score.data_sources.append("news")

        # Compute weighted overall score
        components = []
        weights = []

        if financial is not None:
            # Invert: lower financial health = higher risk
            components.append(100 - financial)
            weights.append(self.WEIGHTS["financial_health"])

        if credit is not None:
            credit_score = self._credit_to_score(credit)
            components.append(credit_score)
            weights.append(self.WEIGHTS["credit_rating"])

        if litigation is not None:
            lit_score = min(litigation * 10, 100)
            components.append(lit_score)
            weights.append(self.WEIGHTS["litigation"])

        if sentiment is not None:
            # Invert: negative sentiment = higher risk
            components.append(max(0, 50 - sentiment * 50))
            weights.append(self.WEIGHTS["news_sentiment"])

        if components:
            score.overall_score = round(
                sum(c * w for c, w in zip(components, weights)) / sum(weights),
                1,
            )
        else:
            score.overall_score = 50.0  # Default mid-risk

        # Determine risk level
        if score.overall_score >= 80:
            score.risk_level = "critical"
        elif score.overall_score >= 60:
            score.risk_level = "high"
        elif score.overall_score >= 40:
            score.risk_level = "medium"
        else:
            score.risk_level = "low"

        score.details = {
            "company_name": company_name,
            "duns_number": duns_number,
            "data_sources": score.data_sources,
            "weights_used": {
                k: v for k, v in self.WEIGHTS.items()
                if k.replace("financial_health", "dnb").replace("credit_rating", "creditsafe")
                in score.data_sources
            },
        }

        return score

    async def _get_financial_health(
        self, company_name: str, duns_number: Optional[str] = None
    ) -> Optional[float]:
        """Get financial health score from D&B.

        In production, this calls the D&B Direct+ API.
        Returns a score 0-100 (higher = healthier).

        Args:
            company_name: Company name to look up.
            duns_number: Optional DUNS number.

        Returns:
            Financial health score or None.
        """
        # Placeholder — in production, calls D&B API
        logger.info(
            "D&B lookup for %s (DUNS: %s)", company_name, duns_number
        )
        return None

    async def _get_credit_rating(self, company_name: str) -> Optional[str]:
        """Get credit rating from Creditsafe.

        In production, this calls the Creditsafe API.

        Args:
            company_name: Company name to look up.

        Returns:
            Credit rating string or None.
        """
        logger.info("Creditsafe lookup for %s", company_name)
        return None

    async def _get_litigation_count(self, company_name: str) -> Optional[int]:
        """Get litigation count from PACER.

        In production, this searches PACER for cases involving the company.

        Args:
            company_name: Company name to search.

        Returns:
            Number of litigation cases or None.
        """
        logger.info("PACER search for %s", company_name)
        return None

    async def _get_news_sentiment(self, company_name: str) -> Optional[float]:
        """Get news sentiment score.

        In production, this calls Google News API + VADER sentiment.

        Args:
            company_name: Company name to search.

        Returns:
            Sentiment score -1 to 1 or None.
        """
        logger.info("News sentiment analysis for %s", company_name)
        return None

    @staticmethod
    def _credit_to_score(credit_rating: str) -> float:
        """Convert a credit rating string to a risk score.

        Args:
            credit_rating: Credit rating (e.g., "AAA", "BB+", "D").

        Returns:
            Risk score 0-100.
        """
        rating_map = {
            "AAA": 5, "AA+": 8, "AA": 10, "AA-": 12,
            "A+": 15, "A": 18, "A-": 20,
            "BBB+": 25, "BBB": 30, "BBB-": 35,
            "BB+": 40, "BB": 45, "BB-": 50,
            "B+": 55, "B": 60, "B-": 65,
            "CCC+": 70, "CCC": 75, "CCC-": 80,
            "CC": 85, "C": 90, "D": 95,
        }
        return rating_map.get(credit_rating.upper(), 50)
