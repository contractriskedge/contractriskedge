"""Renewal risk forecasting ML model (V2-022).

Predicts the probability of contract renewal and generates churn signals
based on contract attributes, historical patterns, risk scores, and
engagement metrics. Provides a probability score and key risk factors.
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .event_bus import ObligationEventBus, ObligationEvent, EventType, EventPriority

logger = logging.getLogger(__name__)


@dataclass
class RenewalForecast:
    """Forecast result for a contract renewal."""

    forecast_id: str
    contract_id: str
    tenant_id: str
    contract_name: str
    renewal_date: str
    days_until_renewal: int
    renewal_probability: float  # 0.0 - 1.0
    churn_risk_score: float  # 0.0 - 10.0
    churn_risk_level: str  # very_low, low, medium, high, very_high
    key_risk_factors: List[Dict[str, Any]]
    positive_factors: List[str]
    recommended_actions: List[str]
    forecast_confidence: str  # low, medium, high
    model_version: str = "v1.0"
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str = ""

    def __post_init__(self) -> None:
        """Set default expiration to 7 days from generation."""
        if not self.expires_at:
            self.expires_at = (
                datetime.utcnow() + timedelta(days=7)
            ).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "forecast_id": self.forecast_id,
            "contract_id": self.contract_id,
            "tenant_id": self.tenant_id,
            "contract_name": self.contract_name,
            "renewal_date": self.renewal_date,
            "days_until_renewal": self.days_until_renewal,
            "renewal_probability": round(self.renewal_probability, 4),
            "churn_risk_score": round(self.churn_risk_score, 2),
            "churn_risk_level": self.churn_risk_level,
            "key_risk_factors": self.key_risk_factors,
            "positive_factors": self.positive_factors,
            "recommended_actions": self.recommended_actions,
            "forecast_confidence": self.forecast_confidence,
            "model_version": self.model_version,
            "generated_at": self.generated_at,
            "expires_at": self.expires_at,
        }


class RenewalForecastEngine:
    """ML-powered renewal risk forecasting engine.

    Predicts renewal probability and churn risk using a weighted
    scoring model based on contract attributes, risk scores,
    engagement metrics, and historical patterns.

    Usage:
        engine = RenewalForecastEngine(event_bus)
        forecast = await engine.forecast_renewal(contract_data)
        report = await engine.get_portfolio_forecast("tenant-123")
    """

    def __init__(
        self,
        event_bus: ObligationEventBus,
        db_pool: Optional[Any] = None,
    ) -> None:
        """Initialize the forecast engine.

        Args:
            event_bus: The obligation event bus.
            db_pool: Optional database pool.
        """
        self._event_bus = event_bus
        self._db_pool = db_pool
        self._forecasts: Dict[str, RenewalForecast] = {}

        # Model weights for different risk factors
        self._weights = {
            "risk_score": 0.25,
            "contract_tenure": 0.10,
            "obligation_breaches": 0.20,
            "engagement_score": 0.15,
            "counterparty_risk": 0.15,
            "market_conditions": 0.05,
            "auto_renewal_clause": 0.10,
        }

        # Churn signal thresholds
        self._churn_thresholds = {
            "very_high": (0.8, 1.0),
            "high": (0.6, 0.8),
            "medium": (0.4, 0.6),
            "low": (0.2, 0.4),
            "very_low": (0.0, 0.2),
        }

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Update model weights for risk factor computation.

        Args:
            new_weights: Dict of factor name -> weight (must sum to ~1.0).
        """
        self._weights.update(new_weights)
        # Normalize weights
        total = sum(self._weights.values())
        if total > 0:
            for key in self._weights:
                self._weights[key] /= total
        logger.info("Updated forecast model weights: %s", self._weights)

    async def forecast_renewal(
        self,
        contract_data: Dict[str, Any],
    ) -> RenewalForecast:
        """Generate a renewal forecast for a contract.

        Args:
            contract_data: Contract data including:
                - contract_id, tenant_id, filename
                - end_date or renewal_date
                - risk_score (overall contract risk)
                - counterparty_risk_score
                - obligation_breach_count
                - engagement_metrics (login frequency, report views, etc.)
                - has_auto_renewal_clause
                - contract_type
                - created_at

        Returns:
            RenewalForecast with probability and risk factors.
        """
        contract_id = contract_data.get("contract_id", "unknown")
        tenant_id = contract_data.get("tenant_id", "default")
        contract_name = contract_data.get("filename", contract_id)

        renewal_date_str = contract_data.get("end_date") or contract_data.get("renewal_date")
        if not renewal_date_str:
            raise ValueError(f"Contract {contract_id} has no end_date or renewal_date")

        try:
            renewal_date = datetime.fromisoformat(renewal_date_str)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid date format: {renewal_date_str}")

        today = datetime.utcnow()
        days_until_renewal = (renewal_date - today).days

        # Compute risk factors
        risk_factors: List[Dict[str, Any]] = []
        positive_factors: List[str] = []

        # 1. Overall contract risk score
        risk_score = contract_data.get("risk_score", 5.0)
        risk_factors.append({
            "factor": "contract_risk_score",
            "value": risk_score,
            "weight": self._weights["risk_score"],
            "impact": "negative" if risk_score > 5.0 else "positive",
            "description": f"Overall contract risk score: {risk_score:.1f}/10",
        })
        if risk_score <= 3.0:
            positive_factors.append("Low overall contract risk score")

        # 2. Obligation breaches
        breach_count = contract_data.get("obligation_breach_count", 0)
        breach_impact = min(1.0, breach_count * 0.15)
        risk_factors.append({
            "factor": "obligation_breaches",
            "value": breach_count,
            "weight": self._weights["obligation_breaches"],
            "impact": "negative" if breach_count > 0 else "neutral",
            "description": f"{breach_count} obligation breach(es) detected",
        })
        if breach_count == 0:
            positive_factors.append("No obligation breaches recorded")

        # 3. Counterparty risk
        cp_risk = contract_data.get("counterparty_risk_score", 0.0)
        if cp_risk > 0:
            risk_factors.append({
                "factor": "counterparty_risk",
                "value": cp_risk,
                "weight": self._weights["counterparty_risk"],
                "impact": "negative" if cp_risk > 5.0 else "positive",
                "description": f"Counterparty risk score: {cp_risk:.1f}/10",
            })
            if cp_risk <= 3.0:
                positive_factors.append("Low counterparty risk")

        # 4. Engagement score
        engagement = contract_data.get("engagement_score", 0.5)
        engagement_impact = 1.0 - engagement
        risk_factors.append({
            "factor": "engagement_score",
            "value": engagement,
            "weight": self._weights["engagement_score"],
            "impact": "negative" if engagement < 0.4 else "positive",
            "description": f"Engagement score: {engagement:.2f}",
        })
        if engagement > 0.7:
            positive_factors.append("High contract engagement and activity")

        # 5. Auto-renewal clause
        has_auto_renewal = contract_data.get("has_auto_renewal_clause", False)
        risk_factors.append({
            "factor": "auto_renewal_clause",
            "value": 1.0 if has_auto_renewal else 0.0,
            "weight": self._weights["auto_renewal_clause"],
            "impact": "positive" if has_auto_renewal else "negative",
            "description": "Auto-renewal clause present" if has_auto_renewal else "No auto-renewal clause",
        })
        if has_auto_renewal:
            positive_factors.append("Contract has auto-renewal clause")

        # 6. Contract tenure
        created_at_str = contract_data.get("created_at")
        tenure_years = 0
        if created_at_str:
            try:
                created = datetime.fromisoformat(created_at_str)
                tenure_years = (today - created).days / 365.0
            except (ValueError, TypeError):
                pass

        tenure_impact = min(1.0, tenure_years / 5.0)  # Normalize to 5 years
        risk_factors.append({
            "factor": "contract_tenure",
            "value": round(tenure_years, 1),
            "weight": self._weights["contract_tenure"],
            "impact": "positive" if tenure_years > 2 else "neutral",
            "description": f"Contract tenure: {tenure_years:.1f} years",
        })
        if tenure_years > 3:
            positive_factors.append("Long-standing contract relationship (>3 years)")

        # Compute churn risk score (0-10)
        churn_score = 0.0
        for factor in risk_factors:
            if factor["impact"] == "negative":
                churn_score += factor["value"] / 10.0 * factor["weight"] * 10.0
            elif factor["impact"] == "positive":
                churn_score -= (factor["value"] / 10.0 if factor["value"] <= 10 else 1.0) * factor["weight"] * 10.0 * 0.5

        # Adjust for days until renewal (closer = more urgent)
        if days_until_renewal < 30:
            churn_score += 1.5
        elif days_until_renewal < 90:
            churn_score += 0.5

        churn_score = max(0.0, min(10.0, churn_score))

        # Convert to renewal probability
        renewal_probability = 1.0 - (churn_score / 10.0)

        # Determine churn risk level
        churn_risk_level = "medium"
        for level, (lower, upper) in self._churn_thresholds.items():
            if lower <= churn_score / 10.0 < upper:
                churn_risk_level = level
                break

        # Determine forecast confidence
        confidence = self._compute_confidence(days_until_renewal, risk_factors)

        # Generate recommended actions
        recommended_actions = self._generate_recommendations(
            churn_risk_level, risk_factors, days_until_renewal, has_auto_renewal
        )

        forecast = RenewalForecast(
            forecast_id=str(uuid.uuid4()),
            contract_id=contract_id,
            tenant_id=tenant_id,
            contract_name=contract_name,
            renewal_date=renewal_date_str,
            days_until_renewal=days_until_renewal,
            renewal_probability=renewal_probability,
            churn_risk_score=round(churn_score, 2),
            churn_risk_level=churn_risk_level,
            key_risk_factors=risk_factors,
            positive_factors=positive_factors,
            recommended_actions=recommended_actions,
            forecast_confidence=confidence,
        )

        self._forecasts[forecast.forecast_id] = forecast

        # Emit event for high churn risk
        if churn_risk_level in ("high", "very_high"):
            event = ObligationEventBus.create_event(
                event_type=EventType.RENEWAL_APPROACHING,
                contract_id=contract_id,
                tenant_id=tenant_id,
                title=f"High renewal churn risk: {contract_name}",
                description=(
                    f"Renewal forecast for {contract_name} shows {churn_risk_level} churn risk "
                    f"(probability: {renewal_probability:.1%}). "
                    f"{days_until_renewal} days until renewal."
                ),
                priority=EventPriority.HIGH if churn_risk_level == "high" else EventPriority.CRITICAL,
                due_date=renewal_date_str,
                days_until_due=days_until_renewal,
                risk_score=churn_score,
                metadata={
                    "forecast_id": forecast.forecast_id,
                    "renewal_probability": renewal_probability,
                    "churn_risk_level": churn_risk_level,
                    "days_until_renewal": days_until_renewal,
                },
            )
            await self._event_bus.emit(event)

        logger.info(
            "Renewal forecast for %s: prob=%.2f, churn=%s (score=%.2f, confidence=%s)",
            contract_id, renewal_probability, churn_risk_level, churn_score, confidence,
        )

        return forecast

    def _compute_confidence(
        self,
        days_until_renewal: int,
        risk_factors: List[Dict[str, Any]],
    ) -> str:
        """Compute forecast confidence based on data availability.

        Args:
            days_until_renewal: Days until contract renewal.
            risk_factors: List of risk factors used.

        Returns:
            Confidence level: low, medium, high.
        """
        # More data factors = higher confidence
        data_factor_count = sum(1 for f in risk_factors if f.get("value", 0) > 0)

        if data_factor_count >= 5 and days_until_renewal > 30:
            return "high"
        elif data_factor_count >= 3:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        churn_risk_level: str,
        risk_factors: List[Dict[str, Any]],
        days_until_renewal: int,
        has_auto_renewal: bool,
    ) -> List[str]:
        """Generate recommended actions based on forecast.

        Args:
            churn_risk_level: The churn risk level.
            risk_factors: List of risk factors.
            days_until_renewal: Days until renewal.
            has_auto_renewal: Whether auto-renewal clause exists.

        Returns:
            List of recommendation strings.
        """
        recommendations = []

        if churn_risk_level in ("very_high", "high"):
            recommendations.append("URGENT: Schedule executive-level renewal review immediately")
            if days_until_renewal < 30:
                recommendations.append("CRITICAL: Initiate emergency renewal negotiation process")

        if churn_risk_level == "medium":
            recommendations.append("Schedule renewal review within 2 weeks")
            recommendations.append("Prepare renewal proposal with updated terms")

        if churn_risk_level in ("low", "very_low"):
            recommendations.append("Monitor renewal timeline - standard process")
            recommendations.append("Consider upsell/cross-sell opportunities")

        if not has_auto_renewal:
            recommendations.append("Evaluate adding auto-renewal clause to reduce future churn risk")

        # Factor-specific recommendations
        for factor in risk_factors:
            if factor["factor"] == "obligation_breaches" and factor["value"] > 0:
                recommendations.append("Address outstanding obligation breaches before renewal discussion")
            if factor["factor"] == "counterparty_risk" and factor.get("value", 0) > 5:
                recommendations.append("Review counterparty risk exposure before committing to renewal")
            if factor["factor"] == "engagement_score" and factor.get("value", 0) < 0.3:
                recommendations.append("Increase account engagement - low usage detected")
            if factor["factor"] == "contract_risk_score" and factor.get("value", 0) > 7:
                recommendations.append("Address high-risk clauses before renewal negotiation")

        return recommendations[:5]  # Max 5 recommendations

    async def forecast_portfolio(
        self,
        contracts: List[Dict[str, Any]],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Generate renewal forecasts for an entire portfolio.

        Args:
            contracts: List of contract data dicts.
            tenant_id: The tenant identifier.

        Returns:
            Dict with portfolio forecast summary.
        """
        forecasts: List[RenewalForecast] = []
        errors: List[str] = []

        for contract in contracts:
            try:
                forecast = await self.forecast_renewal(contract)
                forecasts.append(forecast)
            except (ValueError, KeyError) as exc:
                errors.append(f"Contract {contract.get('contract_id', 'unknown')}: {exc}")

        # Compute portfolio stats
        high_risk = sum(1 for f in forecasts if f.churn_risk_level in ("high", "very_high"))
        medium_risk = sum(1 for f in forecasts if f.churn_risk_level == "medium")
        low_risk = sum(1 for f in forecasts if f.churn_risk_level in ("low", "very_low"))

        avg_probability = sum(f.renewal_probability for f in forecasts) / max(len(forecasts), 1)
        avg_churn = sum(f.churn_risk_score for f in forecasts) / max(len(forecasts), 1)

        # Contracts expiring within 90 days
        expiring_soon = [
            {"contract_id": f.contract_id, "name": f.contract_name,
             "days": f.days_until_renewal, "churn_risk": f.churn_risk_level}
            for f in forecasts if 0 <= f.days_until_renewal <= 90
        ]

        return {
            "tenant_id": tenant_id,
            "total_forecasts": len(forecasts),
            "errors": errors,
            "portfolio_summary": {
                "high_churn_risk": high_risk,
                "medium_churn_risk": medium_risk,
                "low_churn_risk": low_risk,
                "average_renewal_probability": round(avg_probability, 3),
                "average_churn_risk_score": round(avg_churn, 2),
            },
            "expiring_soon": sorted(expiring_soon, key=lambda x: x["days"]),
            "forecasts": [f.to_dict() for f in forecasts],
        }

    async def get_forecast(self, forecast_id: str) -> Optional[RenewalForecast]:
        """Get a specific forecast by ID.

        Args:
            forecast_id: The forecast identifier.

        Returns:
            RenewalForecast or None.
        """
        return self._forecasts.get(forecast_id)

    async def get_contract_forecast(
        self,
        contract_id: str,
    ) -> Optional[RenewalForecast]:
        """Get the latest forecast for a contract.

        Args:
            contract_id: The contract identifier.

        Returns:
            Latest RenewalForecast or None.
        """
        contract_forecasts = [
            f for f in self._forecasts.values()
            if f.contract_id == contract_id
        ]
        if not contract_forecasts:
            return None
        return max(contract_forecasts, key=lambda f: f.generated_at)

    async def get_portfolio_forecast(self, tenant_id: str) -> Dict[str, Any]:
        """Get a portfolio-level forecast summary for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with portfolio forecast data.
        """
        tenant_forecasts = [
            f for f in self._forecasts.values()
            if f.tenant_id == tenant_id
        ]

        if not tenant_forecasts:
            return {
                "tenant_id": tenant_id,
                "total_forecasts": 0,
                "message": "No forecasts available for this tenant",
            }

        # Latest forecast per contract
        latest: Dict[str, RenewalForecast] = {}
        for f in tenant_forecasts:
            if f.contract_id not in latest or f.generated_at > latest[f.contract_id].generated_at:
                latest[f.contract_id] = f

        high_risk_contracts = [
            f.to_dict() for f in latest.values()
            if f.churn_risk_level in ("high", "very_high")
        ]

        return {
            "tenant_id": tenant_id,
            "total_contracts_forecasted": len(latest),
            "high_risk_contracts": high_risk_contracts,
            "average_renewal_probability": round(
                sum(f.renewal_probability for f in latest.values()) / max(len(latest), 1), 3
            ),
            "average_churn_risk": round(
                sum(f.churn_risk_score for f in latest.values()) / max(len(latest), 1), 2
            ),
            "risk_distribution": {
                "very_high": sum(1 for f in latest.values() if f.churn_risk_level == "very_high"),
                "high": sum(1 for f in latest.values() if f.churn_risk_level == "high"),
                "medium": sum(1 for f in latest.values() if f.churn_risk_level == "medium"),
                "low": sum(1 for f in latest.values() if f.churn_risk_level == "low"),
                "very_low": sum(1 for f in latest.values() if f.churn_risk_level == "very_low"),
            },
        }
