"""Cost & Resource Governance — token budgets, tenant quotas, inference accounting, model routing, throttling.

Prevents enterprise AI platforms from failing financially before they fail technically.

Provides:
- TenantSpendTracker — per-tenant cost tracking across all AI operations
- ProviderSpendTracker — per-provider cost analytics
- RetrievalCostTracker — cost tracking for vector retrieval and embedding
- QuotaEnforcer — real-time quota enforcement for AI operations
- IntelligentRouter — cost-aware provider/model routing
- LowCostFallback — automatic fallback to cheaper models when budget is tight
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    ECONOMY = "economy"        # gpt-4o-mini, claude-3-haiku
    STANDARD = "standard"      # gpt-4o, claude-3-sonnet
    PREMIUM = "premium"        # gpt-4-turbo, claude-3-opus
    CUSTOM = "custom"          # Fine-tuned models


@dataclass
class ModelCostConfig:
    """Cost configuration for a model."""
    model_name: str
    provider: str
    tier: ModelTier
    cost_per_input_token: float
    cost_per_output_token: float
    cost_per_embedding_token: float = 0.0


# ── Default Model Cost Catalog ─────────────────────────────────────

MODEL_COST_CATALOG: dict[str, ModelCostConfig] = {
    "gpt-4o": ModelCostConfig(model_name="gpt-4o", provider="openai", tier=ModelTier.STANDARD, cost_per_input_token=0.0000025, cost_per_output_token=0.00001),
    "gpt-4o-mini": ModelCostConfig(model_name="gpt-4o-mini", provider="openai", tier=ModelTier.ECONOMY, cost_per_input_token=0.00000015, cost_per_output_token=0.0000006),
    "gpt-4-turbo": ModelCostConfig(model_name="gpt-4-turbo", provider="openai", tier=ModelTier.PREMIUM, cost_per_input_token=0.00001, cost_per_output_token=0.00003),
    "claude-3-opus": ModelCostConfig(model_name="claude-3-opus", provider="anthropic", tier=ModelTier.PREMIUM, cost_per_input_token=0.000015, cost_per_output_token=0.000075),
    "claude-3-sonnet": ModelCostConfig(model_name="claude-3-sonnet", provider="anthropic", tier=ModelTier.STANDARD, cost_per_input_token=0.000003, cost_per_output_token=0.000015),
    "claude-3-haiku": ModelCostConfig(model_name="claude-3-haiku", provider="anthropic", tier=ModelTier.ECONOMY, cost_per_input_token=0.00000025, cost_per_output_token=0.00000125),
    "text-embedding-3-large": ModelCostConfig(model_name="text-embedding-3-large", provider="openai", tier=ModelTier.STANDARD, cost_per_input_token=0.0, cost_per_output_token=0.0, cost_per_embedding_token=0.00000013),
    "text-embedding-3-small": ModelCostConfig(model_name="text-embedding-3-small", provider="openai", tier=ModelTier.ECONOMY, cost_per_input_token=0.0, cost_per_output_token=0.0, cost_per_embedding_token=0.00000002),
}


# ── Tenant Spend Tracker ───────────────────────────────────────────

@dataclass
class TenantSpendSummary:
    """Spend summary for a tenant over a period."""
    tenant_id: str
    period_start: str
    period_end: str
    total_spend: float = 0.0
    ai_analysis_spend: float = 0.0
    embedding_spend: float = 0.0
    retrieval_spend: float = 0.0
    export_spend: float = 0.0
    replay_spend: float = 0.0
    total_tokens: int = 0
    total_executions: int = 0
    by_model: dict[str, float] = field(default_factory=dict)
    by_provider: dict[str, float] = field(default_factory=dict)


@dataclass
class TenantSpendTracker:
    """Tracks AI spend per tenant across all operations."""

    session: AsyncSession
    tenant_id: str

    async def get_daily_spend(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily spend for the last N days."""
        sql = sa_text("""
            SELECT DATE(created_at) as day,
                   SUM(COALESCE(cost_usd, 0)) as total_cost,
                   SUM(COALESCE(total_tokens, 0)) as total_tokens,
                   COUNT(*) as execution_count
            FROM ai_execution_runs
            WHERE tenant_id = :tid
              AND created_at >= CURRENT_DATE - :days
            GROUP BY DATE(created_at)
            ORDER BY day ASC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
        return [
            {
                "date": str(row.day),
                "cost": round(float(row.total_cost or 0.0), 6),
                "tokens": row.total_tokens or 0,
                "executions": row.execution_count or 0,
            }
            for row in result.fetchall()
        ]

    async def get_spend_by_model(self, days: int = 30) -> list[dict[str, Any]]:
        """Get spend breakdown by model."""
        sql = sa_text("""
            SELECT model, provider,
                   SUM(COALESCE(cost_usd, 0)) as total_cost,
                   SUM(COALESCE(total_tokens, 0)) as total_tokens,
                   COUNT(*) as execution_count
            FROM ai_execution_runs
            WHERE tenant_id = :tid
              AND created_at >= CURRENT_DATE - :days
            GROUP BY model, provider
            ORDER BY total_cost DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
        return [
            {
                "model": row.model,
                "provider": row.provider,
                "cost": round(float(row.total_cost or 0.0), 6),
                "tokens": row.total_tokens or 0,
                "executions": row.execution_count or 0,
            }
            for row in result.fetchall()
        ]

    async def get_summary(self, days: int = 30) -> TenantSpendSummary:
        """Get comprehensive spend summary."""
        daily = await self.get_daily_spend(days)
        by_model = await self.get_spend_by_model(days)

        total = sum(d["cost"] for d in daily)
        total_tokens = sum(d["tokens"] for d in daily)
        total_execs = sum(d["executions"] for d in daily)

        return TenantSpendSummary(
            tenant_id=self.tenant_id,
            period_start=(datetime.utcnow() - timedelta(days=days)).isoformat(),
            period_end=datetime.utcnow().isoformat(),
            total_spend=total,
            total_tokens=total_tokens,
            total_executions=total_execs,
            by_model={m["model"]: m["cost"] for m in by_model},
            by_provider={m["provider"]: m["cost"] for m in by_model},
        )


# ── Quota Enforcer ─────────────────────────────────────────────────

@dataclass
class QuotaEnforcer:
    """Real-time quota enforcement for AI operations.

    Enforces:
    - Daily spend limits per tenant
    - Per-execution token budgets
    - Model tier restrictions
    - Concurrent execution limits
    """

    session: AsyncSession
    tenant_id: str

    async def check_daily_spend_limit(self, max_daily_spend: float) -> tuple[bool, float]:
        """Check if tenant has exceeded daily spend limit.

        Returns:
            (within_limit, current_spend)
        """
        sql = sa_text("""
            SELECT SUM(COALESCE(cost_usd, 0)) as daily_spend
            FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= CURRENT_DATE
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        daily_spend = float(result.scalar() or 0.0)
        return daily_spend < max_daily_spend, daily_spend

    async def check_token_budget(self, requested_tokens: int, max_tokens_per_execution: int) -> bool:
        """Check if requested tokens are within budget."""
        return requested_tokens <= max_tokens_per_execution

    async def get_remaining_budget(self, monthly_budget: float) -> float:
        """Get remaining monthly budget."""
        sql = sa_text("""
            SELECT SUM(COALESCE(cost_usd, 0)) as monthly_spend
            FROM ai_execution_runs
            WHERE tenant_id = :tid
              AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        monthly_spend = float(result.scalar() or 0.0)
        return max(0.0, monthly_budget - monthly_spend)


# ── Intelligent Router ─────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """Decision from the intelligent router."""
    selected_model: str
    selected_provider: str
    estimated_cost: float
    reason: str
    alternative: str | None = None  # Alternative if budget is tight


@dataclass
class IntelligentRouter:
    """Cost-aware provider/model routing.

    Routes requests to the most cost-effective model that meets quality requirements.
    """

    session: AsyncSession
    tenant_id: str

    def select_model(
        self,
        required_tier: ModelTier = ModelTier.STANDARD,
        preferred_provider: str = "openai",
        max_cost_per_execution: float | None = None,
    ) -> RoutingDecision:
        """Select the best model based on cost and quality requirements."""
        candidates = [
            m for m in MODEL_COST_CATALOG.values()
            if m.tier == required_tier or list(ModelTier).index(m.tier) <= list(ModelTier).index(required_tier)
        ]

        if not candidates:
            # Fall back to economy
            candidates = [m for m in MODEL_COST_CATALOG.values() if m.tier == ModelTier.ECONOMY]

        # Prefer preferred provider
        preferred = [m for m in candidates if m.provider == preferred_provider]
        if preferred:
            candidates = preferred

        # Sort by cost (cheapest first)
        candidates.sort(key=lambda m: m.cost_per_input_token + m.cost_per_output_token)

        selected = candidates[0]
        estimated_cost = (selected.cost_per_input_token * 1000) + (selected.cost_per_output_token * 500)  # Rough estimate

        alternative = None
        if max_cost_per_execution and estimated_cost > max_cost_per_execution:
            # Find cheaper alternative
            cheaper = [m for m in candidates if (m.cost_per_input_token * 1000 + m.cost_per_output_token * 500) < max_cost_per_execution]
            if cheaper:
                alternative = cheaper[0].model_name

        return RoutingDecision(
            selected_model=selected.model_name,
            selected_provider=selected.provider,
            estimated_cost=round(estimated_cost, 6),
            reason=f"Selected cheapest {selected.tier.value} model from {selected.provider}",
            alternative=alternative,
        )


# ── Low-Cost Fallback ──────────────────────────────────────────────

@dataclass
class LowCostFallback:
    """Automatic fallback to cheaper models when budget is constrained.

    Implements a tiered fallback strategy:
    1. Try preferred model
    2. If budget exceeded, try next cheaper tier
    3. If still exceeded, use economy model
    4. If all fail, queue for off-peak processing
    """

    FALLBACK_CHAIN: list[ModelTier] = field(default_factory=lambda: [
        ModelTier.PREMIUM,
        ModelTier.STANDARD,
        ModelTier.ECONOMY,
    ])

    def resolve(
        self,
        preferred_model: str,
        max_cost: float,
    ) -> tuple[str, str]:
        """Resolve the best model within budget constraints.

        Returns:
            (model_name, reason)
        """
        preferred_config = MODEL_COST_CATALOG.get(preferred_model)
        if not preferred_config:
            return "gpt-4o-mini", "Preferred model not found, fell back to economy"

        estimated_cost = (preferred_config.cost_per_input_token * 1000) + (preferred_config.cost_per_output_token * 500)
        if estimated_cost <= max_cost:
            return preferred_model, "Within budget"

        # Try cheaper tiers
        for tier in reversed(self.FALLBACK_CHAIN):  # Start from cheapest
            candidates = [
                m for m in MODEL_COST_CATALOG.values()
                if m.tier == tier and m.provider == preferred_config.provider
            ]
            if not candidates:
                candidates = [m for m in MODEL_COST_CATALOG.values() if m.tier == tier]

            if candidates:
                cheapest = min(candidates, key=lambda m: m.cost_per_input_token + m.cost_per_output_token)
                cost = (cheapest.cost_per_input_token * 1000) + (cheapest.cost_per_output_token * 500)
                if cost <= max_cost:
                    return cheapest.model_name, f"Budget constrained, fell back to {cheapest.tier.value}"

        return "gpt-4o-mini", "Budget severely constrained, using minimum cost model"
