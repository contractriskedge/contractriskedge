"""Counterparty litigation change real-time monitoring (V2-021).

Monitors counterparties for litigation events, news sentiment changes,
and credit rating updates. Integrates with external data sources
(PACER, news feeds, credit rating APIs) and emits events to the
obligation event bus when changes are detected.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .event_bus import ObligationEventBus, ObligationEvent, EventType, EventPriority

logger = logging.getLogger(__name__)


@dataclass
class LitigationEvent:
    """A litigation event involving a counterparty."""

    litigation_id: str
    counterparty_name: str
    counterparty_id: str
    court: str
    case_number: str
    case_name: str
    filing_date: str
    case_type: str  # civil, criminal, bankruptcy, regulatory
    case_status: str  # filed, ongoing, dismissed, settled, judgment
    risk_level: str  # low, medium, high, critical
    description: str
    amount_in_controversy: Optional[float] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    source: str = "pacer"  # pacer, news, credit_rating
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "litigation_id": self.litigation_id,
            "counterparty_name": self.counterparty_name,
            "counterparty_id": self.counterparty_id,
            "court": self.court,
            "case_number": self.case_number,
            "case_name": self.case_name,
            "filing_date": self.filing_date,
            "case_type": self.case_type,
            "case_status": self.case_status,
            "risk_level": self.risk_level,
            "description": self.description,
            "amount_in_controversy": self.amount_in_controversy,
            "plaintiff": self.plaintiff,
            "defendant": self.defendant,
            "source": self.source,
            "detected_at": self.detected_at,
        }


@dataclass
class NewsMention:
    """A news mention related to a counterparty."""

    mention_id: str
    counterparty_name: str
    counterparty_id: str
    title: str
    source: str
    url: str
    published_at: str
    sentiment: float  # -1.0 to 1.0
    sentiment_label: str  # negative, neutral, positive
    relevance_score: float  # 0.0 to 1.0
    summary: str
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "mention_id": self.mention_id,
            "counterparty_name": self.counterparty_name,
            "counterparty_id": self.counterparty_id,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at,
            "sentiment": round(self.sentiment, 3),
            "sentiment_label": self.sentiment_label,
            "relevance_score": round(self.relevance_score, 3),
            "summary": self.summary,
            "detected_at": self.detected_at,
        }


@dataclass
class CounterpartyProfile:
    """A monitored counterparty profile."""

    counterparty_id: str
    name: str
    tenant_id: str
    duns_number: Optional[str] = None
    credit_rating: Optional[str] = None
    credit_score: Optional[float] = None
    active_litigation_count: int = 0
    total_litigation_count: int = 0
    news_sentiment_trend: str = "neutral"  # improving, declining, stable, neutral
    overall_risk_score: float = 0.0
    last_checked: Optional[str] = None
    monitored_since: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "counterparty_id": self.counterparty_id,
            "name": self.name,
            "tenant_id": self.tenant_id,
            "duns_number": self.duns_number,
            "credit_rating": self.credit_rating,
            "credit_score": self.credit_score,
            "active_litigation_count": self.active_litigation_count,
            "total_litigation_count": self.total_litigation_count,
            "news_sentiment_trend": self.news_sentiment_trend,
            "overall_risk_score": round(self.overall_risk_score, 2),
            "last_checked": self.last_checked,
            "monitored_since": self.monitored_since,
        }


class LitigationMonitor:
    """Monitors counterparties for litigation and news changes.

    Tracks litigation events from PACER, news sentiment from news feeds,
    and credit rating changes. Emits events to the obligation event bus
    when significant changes are detected.

    Usage:
        monitor = LitigationMonitor(event_bus)
        await monitor.register_counterparty(profile)
        await monitor.record_litigation_event(event)
        report = await monitor.get_counterparty_report("cp-123")
    """

    def __init__(
        self,
        event_bus: ObligationEventBus,
        db_pool: Optional[Any] = None,
    ) -> None:
        """Initialize the litigation monitor.

        Args:
            event_bus: The obligation event bus.
            db_pool: Optional database pool.
        """
        self._event_bus = event_bus
        self._db_pool = db_pool
        self._counterparties: Dict[str, CounterpartyProfile] = {}
        self._litigation_events: List[LitigationEvent] = []
        self._news_mentions: List[NewsMention] = []
        self._contract_counterparty_map: Dict[str, Set[str]] = {}  # contract_id -> counterparty_ids

    async def register_counterparty(self, profile: CounterpartyProfile) -> str:
        """Register a counterparty for monitoring.

        Args:
            profile: The counterparty profile.

        Returns:
            The counterparty ID.
        """
        self._counterparties[profile.counterparty_id] = profile
        logger.info("Registered counterparty %s (%s) for monitoring",
                     profile.name, profile.counterparty_id)
        return profile.counterparty_id

    async def link_counterparty_to_contract(
        self,
        contract_id: str,
        counterparty_id: str,
    ) -> None:
        """Link a counterparty to a contract.

        Args:
            contract_id: The contract identifier.
            counterparty_id: The counterparty identifier.
        """
        if contract_id not in self._contract_counterparty_map:
            self._contract_counterparty_map[contract_id] = set()
        self._contract_counterparty_map[contract_id].add(counterparty_id)

    async def record_litigation_event(self, event: LitigationEvent) -> str:
        """Record a litigation event for a counterparty.

        Updates the counterparty's litigation counts and emits
        an event if the litigation is significant.

        Args:
            event: The litigation event.

        Returns:
            The litigation event ID.
        """
        self._litigation_events.append(event)

        # Update counterparty stats
        cp = self._counterparties.get(event.counterparty_id)
        if cp:
            cp.total_litigation_count += 1
            if event.case_status in ("filed", "ongoing"):
                cp.active_litigation_count += 1
            cp.last_checked = datetime.utcnow().isoformat()
            cp.overall_risk_score = self._compute_risk_score(cp)
            cp.overall_risk_score = round(cp.overall_risk_score, 2)

        # Emit event for significant litigation
        if event.risk_level in ("high", "critical"):
            priority_map = {
                "critical": EventPriority.CRITICAL,
                "high": EventPriority.HIGH,
                "medium": EventPriority.MEDIUM,
                "low": EventPriority.LOW,
            }

            # Find affected contracts
            affected_contracts = self._find_contracts_for_counterparty(event.counterparty_id)

            for contract_id in affected_contracts:
                bus_event = ObligationEventBus.create_event(
                    event_type=EventType.COUNTERPARTY_LITIGATION,
                    contract_id=contract_id,
                    tenant_id=cp.tenant_id if cp else "default",
                    title=f"Litigation alert: {event.counterparty_name}",
                    description=(
                        f"New {event.risk_level}-risk litigation detected for counterparty "
                        f"{event.counterparty_name}: {event.case_name} ({event.court}). "
                        f"Type: {event.case_type}, Status: {event.case_status}"
                    ),
                    priority=priority_map.get(event.risk_level, EventPriority.MEDIUM),
                    risk_score=self._litigation_to_risk_score(event),
                    metadata={
                        "counterparty_id": event.counterparty_id,
                        "counterparty_name": event.counterparty_name,
                        "litigation_id": event.litigation_id,
                        "case_number": event.case_number,
                        "case_type": event.case_type,
                        "case_status": event.case_status,
                        "court": event.court,
                        "amount_in_controversy": event.amount_in_controversy,
                        "source": event.source,
                    },
                )
                await self._event_bus.emit(bus_event)

        logger.info(
            "Recorded litigation event for %s: %s (risk=%s)",
            event.counterparty_name, event.case_name, event.risk_level,
        )

        return event.litigation_id

    async def record_news_mention(self, mention: NewsMention) -> str:
        """Record a news mention for a counterparty.

        Updates the counterparty's news sentiment trend and emits
        an event if sentiment is significantly negative.

        Args:
            mention: The news mention.

        Returns:
            The mention ID.
        """
        self._news_mentions.append(mention)

        # Update counterparty sentiment
        cp = self._counterparties.get(mention.counterparty_id)
        if cp:
            recent_mentions = [
                m for m in self._news_mentions
                if m.counterparty_id == mention.counterparty_id
            ][-20:]  # Last 20 mentions

            if recent_mentions:
                avg_sentiment = sum(m.sentiment for m in recent_mentions) / len(recent_mentions)
                if avg_sentiment < -0.3:
                    cp.news_sentiment_trend = "declining"
                elif avg_sentiment > 0.3:
                    cp.news_sentiment_trend = "improving"
                else:
                    cp.news_sentiment_trend = "neutral"

            cp.last_checked = datetime.utcnow().isoformat()
            cp.overall_risk_score = self._compute_risk_score(cp)
            cp.overall_risk_score = round(cp.overall_risk_score, 2)

        # Emit event for significantly negative news
        if mention.sentiment < -0.5 and mention.relevance_score > 0.7:
            affected_contracts = self._find_contracts_for_counterparty(mention.counterparty_id)
            for contract_id in affected_contracts:
                bus_event = ObligationEventBus.create_event(
                    event_type=EventType.COUNTERPARTY_LITIGATION,
                    contract_id=contract_id,
                    tenant_id=cp.tenant_id if cp else "default",
                    title=f"Negative news alert: {mention.counterparty_name}",
                    description=(
                        f"Significant negative news detected for {mention.counterparty_name}: "
                        f"{mention.title}. Sentiment: {mention.sentiment_label} "
                        f"(score: {mention.sentiment:.2f})."
                    ),
                    priority=EventPriority.MEDIUM,
                    risk_score=round(max(3.0, (1.0 - mention.sentiment) * 5.0), 2),
                    metadata={
                        "counterparty_id": mention.counterparty_id,
                        "counterparty_name": mention.counterparty_name,
                        "mention_id": mention.mention_id,
                        "source": mention.source,
                        "sentiment": mention.sentiment,
                        "sentiment_label": mention.sentiment_label,
                        "url": mention.url,
                    },
                )
                await self._event_bus.emit(bus_event)

        return mention.mention_id

    def _compute_risk_score(self, cp: CounterpartyProfile) -> float:
        """Compute overall counterparty risk score.

        Args:
            cp: The counterparty profile.

        Returns:
            Risk score (0-10).
        """
        score = 0.0

        # Litigation risk
        score += min(4.0, cp.active_litigation_count * 1.5)
        score += min(2.0, cp.total_litigation_count * 0.3)

        # Credit risk
        if cp.credit_score is not None:
            if cp.credit_score < 50:
                score += 3.0
            elif cp.credit_score < 70:
                score += 1.5

        # News sentiment risk
        if cp.news_sentiment_trend == "declining":
            score += 2.0
        elif cp.news_sentiment_trend == "neutral":
            score += 0.5

        return min(10.0, score)

    def _litigation_to_risk_score(self, event: LitigationEvent) -> float:
        """Convert a litigation event to a risk score.

        Args:
            event: The litigation event.

        Returns:
            Risk score (0-10).
        """
        base_scores = {
            "critical": 9.0,
            "high": 7.0,
            "medium": 4.0,
            "low": 2.0,
        }
        score = base_scores.get(event.risk_level, 5.0)

        # Adjust for amount in controversy
        if event.amount_in_controversy:
            if event.amount_in_controversy > 10_000_000:
                score += 1.0
            elif event.amount_in_controversy > 1_000_000:
                score += 0.5

        return min(10.0, score)

    def _find_contracts_for_counterparty(self, counterparty_id: str) -> List[str]:
        """Find all contracts linked to a counterparty.

        Args:
            counterparty_id: The counterparty identifier.

        Returns:
            List of contract IDs.
        """
        contracts = []
        for contract_id, cp_ids in self._contract_counterparty_map.items():
            if counterparty_id in cp_ids:
                contracts.append(contract_id)
        return contracts

    async def get_counterparty_report(self, counterparty_id: str) -> Dict[str, Any]:
        """Get a comprehensive report for a counterparty.

        Args:
            counterparty_id: The counterparty identifier.

        Returns:
            Dict with counterparty details, litigation, and news.
        """
        cp = self._counterparties.get(counterparty_id)
        if not cp:
            return {"error": "Counterparty not found"}

        litigation = [
            e.to_dict() for e in self._litigation_events
            if e.counterparty_id == counterparty_id
        ]
        news = [
            m.to_dict() for m in self._news_mentions
            if m.counterparty_id == counterparty_id
        ]

        return {
            "profile": cp.to_dict(),
            "litigation_events": sorted(litigation, key=lambda x: x["detected_at"], reverse=True),
            "news_mentions": sorted(news, key=lambda x: x["detected_at"], reverse=True),
            "active_litigation": [e.to_dict() for e in self._litigation_events
                                   if e.counterparty_id == counterparty_id and e.case_status in ("filed", "ongoing")],
            "recent_news_sentiment": self._compute_recent_sentiment(counterparty_id),
        }

    def _compute_recent_sentiment(self, counterparty_id: str) -> Dict[str, Any]:
        """Compute recent news sentiment for a counterparty.

        Args:
            counterparty_id: The counterparty identifier.

        Returns:
            Dict with sentiment stats.
        """
        recent = [
            m for m in self._news_mentions
            if m.counterparty_id == counterparty_id
        ][-30:]

        if not recent:
            return {"average_sentiment": 0.0, "trend": "neutral", "mention_count": 0}

        avg = sum(m.sentiment for m in recent) / len(recent)
        negative = sum(1 for m in recent if m.sentiment < 0)
        positive = sum(1 for m in recent if m.sentiment > 0)

        return {
            "average_sentiment": round(avg, 3),
            "trend": "declining" if avg < -0.2 else "improving" if avg > 0.2 else "stable",
            "mention_count": len(recent),
            "negative_mentions": negative,
            "positive_mentions": positive,
        }

    async def get_all_counterparty_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get a summary of all monitored counterparties for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with counterparty summary.
        """
        tenant_cps = [cp for cp in self._counterparties.values() if cp.tenant_id == tenant_id]

        high_risk = sum(1 for cp in tenant_cps if cp.overall_risk_score >= 7.0)
        medium_risk = sum(1 for cp in tenant_cps if 4.0 <= cp.overall_risk_score < 7.0)
        with_litigation = sum(1 for cp in tenant_cps if cp.active_litigation_count > 0)

        return {
            "tenant_id": tenant_id,
            "total_counterparties": len(tenant_cps),
            "risk_breakdown": {
                "high_risk": high_risk,
                "medium_risk": medium_risk,
                "low_risk": len(tenant_cps) - high_risk - medium_risk,
            },
            "with_active_litigation": with_litigation,
            "total_litigation_events": len(self._litigation_events),
            "total_news_mentions": len(self._news_mentions),
        }
