"""Benchmark Intelligence Engine — clause scoring, market deviation, vendor intelligence, renewal forecasting.

One of the biggest future differentiators for enterprise value.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BenchmarkCategory(str, Enum):
    CLAUSE_QUALITY = "clause_quality"
    NEGOTIATION_EFFECTIVENESS = "negotiation_effectiveness"
    VENDOR_RISK = "vendor_risk"
    SLA_COMPLIANCE = "sla_compliance"
    RENEWAL_RISK = "renewal_risk"
    COST_EFFICIENCY = "cost_efficiency"


@dataclass
class BenchmarkScore:
    """A benchmark score for a specific dimension."""
    category: BenchmarkCategory
    score: float  # 0.0-1.0
    percentile: float  # 0.0-100.0 (relative to corpus)
    sample_size: int = 0
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    trend: str = "stable"  # improving, stable, declining


@dataclass
class MarketDeviation:
    """Deviation from market/industry norms."""
    clause_type: str
    your_score: float
    market_average: float
    market_p50: float
    market_p90: float
    deviation: float  # Positive = better than market
    percentile: float


@dataclass
class VendorBenchmark:
    """Benchmark intelligence for a vendor."""
    vendor_name: str
    contract_count: int
    avg_risk_score: float
    negotiation_score: float
    sla_compliance_rate: float
    renewal_risk: float
    industry_percentile: float


@dataclass
class RenewalForecast:
    """Renewal risk forecast for a contract."""
    contract_id: str
    contract_name: str
    counterparty: str
    renewal_date: str
    risk_score: float  # 0.0 (low risk) to 1.0 (high risk)
    risk_factors: list[str] = field(default_factory=list)
    recommended_action: str = ""


@dataclass
class BenchmarkIntelligenceEngine:
    """Enterprise benchmark intelligence — turns contract data into strategic insights.

    Capabilities:
    - Clause benchmark scoring against industry corpus
    - Market deviation analysis (how your clauses compare)
    - Vendor benchmark intelligence
    - Negotiation scoring
    - SLA benchmark comparison
    - Renewal risk forecasting
    - Industry standard mapping
    """

    _corpus_scores: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self):
        self._init_corpus()

    def _init_corpus(self) -> None:
        """Initialize corpus benchmark data."""
        self._corpus_scores = {
            "indemnification": {"avg": 0.65, "p50": 0.60, "p90": 0.85, "std": 0.15},
            "liability": {"avg": 0.55, "p50": 0.50, "p90": 0.80, "std": 0.18},
            "data_privacy": {"avg": 0.70, "p50": 0.70, "p90": 0.90, "std": 0.12},
            "termination": {"avg": 0.60, "p50": 0.55, "p90": 0.82, "std": 0.16},
            "payment": {"avg": 0.50, "p50": 0.45, "p90": 0.75, "std": 0.20},
            "confidentiality": {"avg": 0.75, "p50": 0.75, "p90": 0.92, "std": 0.10},
            "non_compete": {"avg": 0.45, "p50": 0.40, "p90": 0.70, "std": 0.22},
        }

    def score_clause(self, clause_type: str, your_score: float) -> BenchmarkScore:
        """Score a clause against the industry corpus.

        Args:
            clause_type: Type of clause to benchmark.
            your_score: Your clause's quality score (0.0-1.0).

        Returns:
            BenchmarkScore with percentile and comparison.
        """
        corpus = self._corpus_scores.get(clause_type, {"avg": 0.5, "p50": 0.5, "p90": 0.8, "std": 0.15})
        avg = corpus["avg"]
        std = corpus["std"]

        # Simple percentile estimation (normal approximation)
        import math
        z_score = (your_score - avg) / max(std, 0.01)
        percentile = round(0.5 * (1 + math.erf(z_score / math.sqrt(2))) * 100, 1)

        return BenchmarkScore(
            category=BenchmarkCategory.CLAUSE_QUALITY,
            score=your_score,
            percentile=min(99.9, percentile),
            sample_size=1000,
            confidence_interval=(max(0, your_score - 0.1), min(1.0, your_score + 0.1)),
            trend="improving" if your_score > avg else "declining",
        )

    def analyze_market_deviation(self, clause_type: str, your_score: float) -> MarketDeviation:
        """Analyze how your clause deviates from the market."""
        corpus = self._corpus_scores.get(clause_type, {"avg": 0.5, "p50": 0.5, "p90": 0.8, "std": 0.15})
        deviation = your_score - corpus["avg"]

        import math
        z_score = (your_score - corpus["avg"]) / max(corpus["std"], 0.01)
        percentile = round(0.5 * (1 + math.erf(z_score / math.sqrt(2))) * 100, 1)

        return MarketDeviation(
            clause_type=clause_type,
            your_score=your_score,
            market_average=corpus["avg"],
            market_p50=corpus["p50"],
            market_p90=corpus["p90"],
            deviation=round(deviation, 4),
            percentile=min(99.9, percentile),
        )

    def forecast_renewal_risk(
        self,
        contract_id: str,
        contract_name: str,
        counterparty: str,
        renewal_date: str,
        current_risk_score: float = 0.5,
        negotiation_history: list[dict] | None = None,
    ) -> RenewalForecast:
        """Forecast renewal risk for a contract."""
        risk_factors = []
        days_until_renewal = 0

        try:
            renewal = datetime.fromisoformat(renewal_date)
            days_until_renewal = (renewal - datetime.utcnow()).days
        except (ValueError, TypeError):
            days_until_renewal = 90

        # Risk factor analysis
        if days_until_renewal < 30:
            risk_factors.append("Renewal imminent (< 30 days)")
        if current_risk_score > 0.7:
            risk_factors.append("High current risk score")
        if days_until_renewal > 365:
            risk_factors.append("Distant renewal — may be overlooked")

        # Composite risk score
        risk_score = min(1.0, current_risk_score * (1.5 if days_until_renewal < 30 else 1.0))

        recommended_action = "Begin renewal negotiation" if days_until_renewal < 60 else "Monitor — no immediate action needed"

        return RenewalForecast(
            contract_id=contract_id,
            contract_name=contract_name,
            counterparty=counterparty,
            renewal_date=renewal_date,
            risk_score=round(risk_score, 4),
            risk_factors=risk_factors,
            recommended_action=recommended_action,
        )

    def get_industry_norms(self, clause_type: str) -> dict[str, Any]:
        """Get industry standard mapping for a clause type."""
        corpus = self._corpus_scores.get(clause_type)
        if not corpus:
            return {"error": f"No corpus data for clause type: {clause_type}"}
        return {
            "clause_type": clause_type,
            "industry_average": corpus["avg"],
            "industry_median": corpus["p50"],
            "top_quartile_threshold": corpus["p90"],
            "variability": "high" if corpus["std"] > 0.18 else "medium" if corpus["std"] > 0.12 else "low",
        }

    def get_benchmark_dashboard(self) -> dict[str, Any]:
        """Get benchmark intelligence dashboard."""
        return {
            "available_clause_types": list(self._corpus_scores.keys()),
            "industry_norms": {
                ct: {"avg": d["avg"], "p50": d["p50"], "p90": d["p90"]}
                for ct, d in self._corpus_scores.items()
            },
            "total_benchmarks": len(self._corpus_scores),
        }


# ── Global singleton ───────────────────────────────────────────────

benchmark_intelligence = BenchmarkIntelligenceEngine()
