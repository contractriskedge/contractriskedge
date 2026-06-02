"""Commercial Packaging Layer — Developer, Team, Business, Enterprise, Enterprise+ tiers.

Per-tier limits on workflows, AI executions, replay retention, benchmark access, integrations, graph intelligence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProductTier(str, Enum):
    DEVELOPER = "developer"
    TEAM = "team"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    ENTERPRISE_PLUS = "enterprise_plus"


@dataclass
class TierLimits:
    """Resource limits and feature access per tier."""
    tier: ProductTier
    max_contracts: int
    max_users: int
    max_workflows: int
    ai_executions_per_month: int
    replay_retention_days: int
    benchmark_access: bool
    integrations_count: int
    graph_intelligence: bool
    forecasting: bool
    simulation: bool
    custom_prompts: bool
    custom_workflows: bool
    api_rate_limit: str
    support_level: str
    price_monthly: float


# ── Tier Configuration ─────────────────────────────────────────────

TIER_CONFIGS: dict[ProductTier, TierLimits] = {
    ProductTier.DEVELOPER: TierLimits(
        tier=ProductTier.DEVELOPER,
        max_contracts=50,
        max_users=3,
        max_workflows=2,
        ai_executions_per_month=500,
        replay_retention_days=7,
        benchmark_access=False,
        integrations_count=1,
        graph_intelligence=False,
        forecasting=False,
        simulation=False,
        custom_prompts=False,
        custom_workflows=False,
        api_rate_limit="20/min",
        support_level="community",
        price_monthly=0.0,
    ),
    ProductTier.TEAM: TierLimits(
        tier=ProductTier.TEAM,
        max_contracts=500,
        max_users=10,
        max_workflows=5,
        ai_executions_per_month=5000,
        replay_retention_days=30,
        benchmark_access=True,
        integrations_count=3,
        graph_intelligence=True,
        forecasting=False,
        simulation=False,
        custom_prompts=False,
        custom_workflows=True,
        api_rate_limit="100/min",
        support_level="standard",
        price_monthly=999.0,
    ),
    ProductTier.BUSINESS: TierLimits(
        tier=ProductTier.BUSINESS,
        max_contracts=5000,
        max_users=50,
        max_workflows=20,
        ai_executions_per_month=50000,
        replay_retention_days=90,
        benchmark_access=True,
        integrations_count=10,
        graph_intelligence=True,
        forecasting=True,
        simulation=False,
        custom_prompts=True,
        custom_workflows=True,
        api_rate_limit="500/min",
        support_level="premium",
        price_monthly=4999.0,
    ),
    ProductTier.ENTERPRISE: TierLimits(
        tier=ProductTier.ENTERPRISE,
        max_contracts=100000,
        max_users=1000,
        max_workflows=100,
        ai_executions_per_month=500000,
        replay_retention_days=365,
        benchmark_access=True,
        integrations_count=50,
        graph_intelligence=True,
        forecasting=True,
        simulation=True,
        custom_prompts=True,
        custom_workflows=True,
        api_rate_limit="5000/min",
        support_level="enterprise",
        price_monthly=19999.0,
    ),
    ProductTier.ENTERPRISE_PLUS: TierLimits(
        tier=ProductTier.ENTERPRISE_PLUS,
        max_contracts=1000000,
        max_users=10000,
        max_workflows=500,
        ai_executions_per_month=5000000,
        replay_retention_days=2555,
        benchmark_access=True,
        integrations_count=100,
        graph_intelligence=True,
        forecasting=True,
        simulation=True,
        custom_prompts=True,
        custom_workflows=True,
        api_rate_limit="50000/min",
        support_level="dedicated",
        price_monthly=0.0,  # Custom pricing
    ),
}


@dataclass
class CommercialPackagingService:
    """Commercial packaging and tier management.

    Defines product tiers with graduated access to:
    - Workflow capabilities
    - AI execution volume
    - Replay retention
    - Benchmark access
    - Integration count
    - Graph intelligence
    - Forecasting and simulation
    """

    def get_tier_config(self, tier: ProductTier) -> TierLimits:
        """Get configuration for a product tier."""
        config = TIER_CONFIGS.get(tier)
        if not config:
            raise ValueError(f"Unknown tier: {tier}")
        return config

    def get_tier_for_contract_count(self, contract_count: int) -> ProductTier:
        """Get the minimum tier that supports a given contract count."""
        for tier in [ProductTier.DEVELOPER, ProductTier.TEAM, ProductTier.BUSINESS, ProductTier.ENTERPRISE, ProductTier.ENTERPRISE_PLUS]:
            config = TIER_CONFIGS[tier]
            if contract_count <= config.max_contracts:
                return tier
        return ProductTier.ENTERPRISE_PLUS

    def get_upgrade_path(self, current_tier: ProductTier) -> list[dict[str, Any]]:
        """Get available upgrade paths from current tier."""
        tiers = list(ProductTier)
        current_idx = tiers.index(current_tier)
        upgrades = []
        for i in range(current_idx + 1, len(tiers)):
            next_tier = tiers[i]
            config = TIER_CONFIGS[next_tier]
            current_config = TIER_CONFIGS[current_tier]
            upgrades.append({
                "tier": next_tier.value,
                "price": config.price_monthly,
                "additional_contracts": config.max_contracts - current_config.max_contracts,
                "additional_users": config.max_users - current_config.max_users,
                "additional_ai_executions": config.ai_executions_per_month - current_config.ai_executions_per_month,
                "new_features": self._get_new_features(current_config, config),
            })
        return upgrades

    def _get_new_features(self, current: TierLimits, target: TierLimits) -> list[str]:
        """Get features available in target tier but not current."""
        features = []
        if not current.benchmark_access and target.benchmark_access:
            features.append("Benchmark Intelligence")
        if not current.graph_intelligence and target.graph_intelligence:
            features.append("Knowledge Graph Intelligence")
        if not current.forecasting and target.forecasting:
            features.append("Forecasting & Predictions")
        if not current.simulation and target.simulation:
            features.append("What-If Simulation")
        if not current.custom_prompts and target.custom_prompts:
            features.append("Custom Prompt Templates")
        if target.integrations_count > current.integrations_count:
            features.append(f"+{target.integrations_count - current.integrations_count} Integrations")
        if target.replay_retention_days > current.replay_retention_days:
            features.append(f"Extended Replay Retention ({target.replay_retention_days}d)")
        return features

    def check_feature_access(self, tier: ProductTier, feature: str) -> bool:
        """Check if a tier has access to a specific feature."""
        config = TIER_CONFIGS.get(tier)
        if not config:
            return False
        feature_map = {
            "benchmarks": config.benchmark_access,
            "graph_intelligence": config.graph_intelligence,
            "forecasting": config.forecasting,
            "simulation": config.simulation,
            "custom_prompts": config.custom_prompts,
            "custom_workflows": config.custom_workflows,
        }
        return feature_map.get(feature, False)

    def get_tier_summary(self) -> list[dict[str, Any]]:
        """Get a summary of all tiers for the pricing page."""
        return [
            {
                "tier": config.tier.value,
                "name": config.tier.value.replace("_", " ").title(),
                "price": config.price_monthly,
                "contracts": config.max_contracts,
                "users": config.max_users,
                "workflows": config.max_workflows,
                "ai_executions": config.ai_executions_per_month,
                "retention_days": config.replay_retention_days,
                "integrations": config.integrations_count,
                "features": {
                    "benchmarks": config.benchmark_access,
                    "graph": config.graph_intelligence,
                    "forecasting": config.forecasting,
                    "simulation": config.simulation,
                    "custom_prompts": config.custom_prompts,
                    "custom_workflows": config.custom_workflows,
                },
                "support": config.support_level,
            }
            for config in TIER_CONFIGS.values()
        ]


# ── Global singleton ───────────────────────────────────────────────

commercial_packaging = CommercialPackagingService()
