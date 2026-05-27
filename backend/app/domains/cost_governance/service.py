"""Cost & Resource Governance service — budget enforcement, quotas, inference accounting, model routing, throttling."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.cost_governance.schemas import (
    BudgetPeriod, BudgetAlertLevel, ModelTier, RoutingStrategy, ResourceType,
    TokenBudgetConfig, TokenBudgetUsage, BudgetAlert,
    BudgetConfigCreate, BudgetConfigUpdate,
    TenantQuota, QuotaUsage, QuotaCheckResult,
    InferenceRecord, InferenceSummary, ModelInferenceSummary, PromptInferenceSummary,
    ModelCapability, ModelRoute, RoutingDecision, RoutingRule,
    CacheROIMetrics,
    ThrottleRule, ThrottleDecision,
    CostGovernanceDashboard, CostDriver,
)

logger = logging.getLogger(__name__)

# ── Default model catalog ───────────────────────────────────────────

_DEFAULT_MODEL_CATALOG: dict[str, ModelRoute] = {
    "gpt-4o": ModelRoute(
        model_name="gpt-4o",
        provider="openai",
        tier=ModelTier.STANDARD,
        capabilities=ModelCapability(
            quality_score=9.5,
            max_context_window=128000,
            max_output_tokens=4096,
        ),
        cost_per_input_token=0.0000025,
        cost_per_output_token=0.00001,
    ),
    "gpt-4o-mini": ModelRoute(
        model_name="gpt-4o-mini",
        provider="openai",
        tier=ModelTier.ECONOMY,
        capabilities=ModelCapability(
            quality_score=7.5,
            max_context_window=128000,
            max_output_tokens=16384,
        ),
        cost_per_input_token=0.00000015,
        cost_per_output_token=0.0000006,
    ),
    "gpt-4-turbo": ModelRoute(
        model_name="gpt-4-turbo",
        provider="openai",
        tier=ModelTier.PREMIUM,
        capabilities=ModelCapability(
            quality_score=9.0,
            max_context_window=128000,
            max_output_tokens=4096,
        ),
        cost_per_input_token=0.00001,
        cost_per_output_token=0.00003,
    ),
    "claude-3.5-sonnet": ModelRoute(
        model_name="claude-3.5-sonnet",
        provider="anthropic",
        tier=ModelTier.PREMIUM,
        capabilities=ModelCapability(
            quality_score=9.8,
            max_context_window=200000,
            max_output_tokens=8192,
        ),
        cost_per_input_token=0.000003,
        cost_per_output_token=0.000015,
    ),
}


@dataclass
class TokenBudgetService:
    """Manages and enforces per-tenant token budgets."""

    session: AsyncSession
    tenant_id: str

    async def get_config(self) -> Optional[TokenBudgetConfig]:
        """Get the current budget configuration for the tenant."""
        sql = sa_text("""
            SELECT * FROM token_budgets
            WHERE tenant_id = :tid AND is_active = TRUE
            ORDER BY created_at DESC LIMIT 1
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        row = result.fetchone()
        if row:
            return TokenBudgetConfig(
                budget_id=str(row.budget_id),
                tenant_id=str(row.tenant_id),
                period=row.period,
                token_limit=row.token_limit,
                cost_limit_usd=row.cost_limit_usd,
                alert_level=row.alert_level,
                alert_threshold_pct=row.alert_threshold_pct,
                hard_block=row.hard_block,
                notification_channels=row.notification_channels or [],
                is_active=row.is_active,
                created_at=row.created_at,
            )
        # Return default config if none set
        return TokenBudgetConfig(
            budget_id="default",
            tenant_id=self.tenant_id,
            period=BudgetPeriod.DAILY,
            token_limit=1_000_000,
            cost_limit_usd=10.0,
            alert_level=BudgetAlertLevel.WARNING,
            alert_threshold_pct=80.0,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    async def update_config(self, config: BudgetConfigUpdate) -> TokenBudgetConfig:
        """Create or update the budget configuration."""
        now = datetime.now(timezone.utc)
        budget_id = uuid.uuid4().hex[:12]

        existing = await self.get_config()
        token_limit = config.token_limit or (existing.token_limit if existing else 1_000_000)
        cost_limit = config.cost_limit_usd or (existing.cost_limit_usd if existing else 10.0)

        sql = sa_text("""
            INSERT INTO token_budgets (budget_id, tenant_id, period, token_limit,
                cost_limit_usd, alert_level, alert_threshold_pct, hard_block,
                notification_channels, is_active, created_at)
            VALUES (:bid, :tid, :period, :tlimit,
                :climit, :alert, :threshold, :hard,
                :channels, TRUE, :now)
            ON CONFLICT (tenant_id, period) WHERE is_active = TRUE
            DO UPDATE SET token_limit = :tlimit, cost_limit_usd = :climit,
                alert_level = :alert, alert_threshold_pct = :threshold,
                hard_block = :hard, notification_channels = :channels,
                updated_at = :now
            RETURNING budget_id, tenant_id, period, token_limit, cost_limit_usd,
                alert_level, alert_threshold_pct, hard_block,
                notification_channels, is_active, created_at
        """)
        result = await self.session.execute(sql, {
            "bid": budget_id,
            "tid": self.tenant_id,
            "period": config.period.value if config.period else BudgetPeriod.DAILY.value,
            "tlimit": token_limit,
            "climit": cost_limit,
            "alert": config.alert_level.value if config.alert_level else BudgetAlertLevel.WARNING.value,
            "threshold": config.alert_threshold_pct or 80.0,
            "hard": config.hard_block or False,
            "channels": config.notification_channels or [],
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return TokenBudgetConfig(
            budget_id=str(row.budget_id),
            tenant_id=str(row.tenant_id),
            period=row.period,
            token_limit=row.token_limit,
            cost_limit_usd=row.cost_limit_usd,
            alert_level=row.alert_level,
            alert_threshold_pct=row.alert_threshold_pct,
            hard_block=row.hard_block,
            notification_channels=row.notification_channels or [],
            is_active=row.is_active,
            created_at=row.created_at,
        )

    async def get_current_usage(self) -> TokenBudgetUsage:
        """Get current token/cost usage against the budget."""
        config = await self.get_config()
        now = datetime.now(timezone.utc)

        # Determine period start
        if config.period == BudgetPeriod.DAILY:
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif config.period == BudgetPeriod.WEEKLY:
            period_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif config.period == BudgetPeriod.MONTHLY:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # quarterly
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            period_start = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Compute reset time
        if config.period == BudgetPeriod.DAILY:
            reset_at = period_start + timedelta(days=1)
        elif config.period == BudgetPeriod.WEEKLY:
            reset_at = period_start + timedelta(days=7)
        elif config.period == BudgetPeriod.MONTHLY:
            if period_start.month == 12:
                reset_at = period_start.replace(year=period_start.year + 1, month=1)
            else:
                reset_at = period_start.replace(month=period_start.month + 1)
        else:
            reset_at = period_start + timedelta(days=90)

        # Query actual usage
        sql = sa_text("""
            SELECT
                COALESCE(SUM(total_tokens), 0)::int AS tokens,
                COALESCE(SUM(cost_usd), 0)::float AS cost
            FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= :period_start
        """)
        result = await self.session.execute(sql, {
            "tid": self.tenant_id,
            "period_start": period_start,
        })
        row = result.fetchone()
        tokens_used = row.tokens if row else 0
        cost_used = row.cost if row else 0.0

        usage_pct = (tokens_used / config.token_limit * 100) if config.token_limit > 0 else 0.0
        cost_pct = (cost_used / config.cost_limit_usd * 100) if config.cost_limit_usd > 0 else 0.0
        max_pct = max(usage_pct, cost_pct)

        alert_level = BudgetAlertLevel.INFO
        if max_pct >= 100 and config.hard_block:
            alert_level = BudgetAlertLevel.HARD_BLOCK
        elif max_pct >= 100:
            alert_level = BudgetAlertLevel.CRITICAL
        elif max_pct >= config.alert_threshold_pct:
            alert_level = config.alert_level

        return TokenBudgetUsage(
            budget_id=config.budget_id,
            tenant_id=self.tenant_id,
            period=config.period,
            token_limit=config.token_limit,
            cost_limit_usd=config.cost_limit_usd,
            tokens_used=tokens_used,
            cost_usd=round(cost_used, 4),
            usage_pct=round(usage_pct, 1),
            remaining_tokens=max(0, config.token_limit - tokens_used),
            remaining_cost_usd=round(max(0.0, config.cost_limit_usd - cost_used), 4),
            alert_level=alert_level,
            is_exceeded=tokens_used >= config.token_limit or cost_used >= config.cost_limit_usd,
            reset_at=reset_at,
        )

    async def check_budget(self, estimated_tokens: int = 0, estimated_cost: float = 0.0) -> BudgetAlertLevel:
        """Check if an operation would exceed the budget. Call BEFORE inference."""
        usage = await self.get_current_usage()
        config = await self.get_config()

        would_exceed_tokens = (usage.tokens_used + estimated_tokens) > config.token_limit
        would_exceed_cost = (usage.cost_usd + estimated_cost) > config.cost_limit_usd

        if would_exceed_tokens or would_exceed_cost:
            if config.hard_block:
                return BudgetAlertLevel.HARD_BLOCK
            return BudgetAlertLevel.CRITICAL

        # Check if we're approaching the threshold
        projected_pct = max(
            ((usage.tokens_used + estimated_tokens) / config.token_limit * 100) if config.token_limit > 0 else 0,
            ((usage.cost_usd + estimated_cost) / config.cost_limit_usd * 100) if config.cost_limit_usd > 0 else 0,
        )
        if projected_pct >= config.alert_threshold_pct:
            return config.alert_level

        return BudgetAlertLevel.INFO

    async def record_usage(self, tokens: int, cost: float) -> Optional[BudgetAlert]:
        """Record token/cost usage and check if alert threshold crossed."""
        usage = await self.get_current_usage()
        config = await self.get_config()

        # Check if we just crossed a threshold
        pct_before = ((usage.tokens_used - tokens) / config.token_limit * 100) if config.token_limit > 0 else 100
        pct_after = (usage.tokens_used / config.token_limit * 100) if config.token_limit > 0 else 100

        if pct_before < config.alert_threshold_pct <= pct_after:
            alert = BudgetAlert(
                alert_id=uuid.uuid4().hex[:12],
                tenant_id=self.tenant_id,
                budget_id=config.budget_id,
                alert_level=config.alert_level,
                metric="tokens",
                current_value=float(usage.tokens_used),
                threshold_value=float(config.token_limit),
                message=f"Token usage ({pct_after:.0f}%) crossed alert threshold ({config.alert_threshold_pct:.0f}%)",
                created_at=datetime.now(timezone.utc),
            )
            return alert

        return None


@dataclass
class QuotaEnforcementService:
    """Enforces tenant resource quotas."""

    session: AsyncSession
    tenant_id: str

    async def get_quotas(self) -> TenantQuota:
        """Get the current quota configuration for the tenant."""
        sql = sa_text("""
            SELECT plan, max_users, max_documents, features
            FROM tenants WHERE tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        row = result.fetchone()

        plan = row.plan if row else "starter"
        max_users = row.max_users if row else 10
        max_documents = row.max_documents if row else 1000
        features = row.features if row else []

        # Plan-based scaling
        plan_limits = {
            "starter": {"inferences": 100, "monthly": 3000, "storage": 100_000_000, "api_rate": 30, "concurrent": 2, "exports": 10, "tiers": [ModelTier.ECONOMY]},
            "pro": {"inferences": 500, "monthly": 15000, "storage": 1_000_000_000, "api_rate": 100, "concurrent": 5, "exports": 50, "tiers": [ModelTier.ECONOMY, ModelTier.STANDARD]},
            "enterprise": {"inferences": 5000, "monthly": 150000, "storage": 10_000_000_000, "api_rate": 500, "concurrent": 20, "exports": 500, "tiers": [ModelTier.ECONOMY, ModelTier.STANDARD, ModelTier.PREMIUM]},
            "enterprise_plus": {"inferences": 50000, "monthly": 1500000, "storage": 100_000_000_000, "api_rate": 2000, "concurrent": 100, "exports": 5000, "tiers": [ModelTier.ECONOMY, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.CUSTOM]},
        }
        limits = plan_limits.get(plan, plan_limits["starter"])

        return TenantQuota(
            tenant_id=self.tenant_id,
            max_users=max_users,
            max_documents=max_documents,
            max_daily_inferences=limits["inferences"],
            max_monthly_inferences=limits["monthly"],
            max_storage_bytes=limits["storage"],
            max_api_requests_per_min=limits["api_rate"],
            max_concurrent_analyses=limits["concurrent"],
            max_exports_per_day=limits["exports"],
            allowed_model_tiers=limits["tiers"],
            allowed_features=features,
        )

    async def get_usage(self) -> QuotaUsage:
        """Get current usage against all quotas."""
        quotas = await self.get_quotas()

        # Current users
        user_sql = sa_text("SELECT COUNT(*)::int FROM admin_users WHERE tenant_id = :tid")
        users = await self.session.execute(user_sql, {"tid": self.tenant_id})

        # Current documents
        doc_sql = sa_text("SELECT COUNT(*)::int FROM upload_sessions WHERE tenant_id = :tid")
        docs = await self.session.execute(doc_sql, {"tid": self.tenant_id})

        # Inferences today
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        inf_today_sql = sa_text("""
            SELECT COUNT(*)::int FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= :today
        """)
        inf_today = await self.session.execute(inf_today_sql, {"tid": self.tenant_id, "today": today})

        # Inferences this month
        month_start = today.replace(day=1)
        inf_month_sql = sa_text("""
            SELECT COUNT(*)::int FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= :month_start
        """)
        inf_month = await self.session.execute(inf_month_sql, {"tid": self.tenant_id, "month_start": month_start})

        # Exports today
        export_sql = sa_text("""
            SELECT COUNT(*)::int FROM export_jobs
            WHERE tenant_id = :tid AND created_at >= :today
        """)
        exports = await self.session.execute(export_sql, {"tid": self.tenant_id, "today": today})

        # Concurrent analyses
        concurrent_sql = sa_text("""
            SELECT COUNT(*)::int FROM ai_execution_runs
            WHERE tenant_id = :tid AND status IN ('pending', 'processing')
        """)
        concurrent = await self.session.execute(concurrent_sql, {"tid": self.tenant_id})

        current_users = users.scalar() or 0
        current_docs = docs.scalar() or 0
        inferences_today = inf_today.scalar() or 0
        inferences_month = inf_month.scalar() or 0
        exports_today = exports.scalar() or 0
        concurrent_count = concurrent.scalar() or 0

        exceeded = []
        if current_users > quotas.max_users:
            exceeded.append("max_users")
        if current_docs > quotas.max_documents:
            exceeded.append("max_documents")
        if inferences_today > quotas.max_daily_inferences:
            exceeded.append("max_daily_inferences")
        if inferences_month > quotas.max_monthly_inferences:
            exceeded.append("max_monthly_inferences")
        if exports_today > quotas.max_exports_per_day:
            exceeded.append("max_exports_per_day")
        if concurrent_count > quotas.max_concurrent_analyses:
            exceeded.append("max_concurrent_analyses")

        return QuotaUsage(
            tenant_id=self.tenant_id,
            current_users=current_users,
            current_documents=current_docs,
            inferences_today=inferences_today,
            inferences_this_month=inferences_month,
            exports_today=exports_today,
            concurrent_analyses=concurrent_count,
            quotas=quotas,
            any_exceeded=len(exceeded) > 0,
            exceeded_quotas=exceeded,
        )

    async def check_operation(self, resource: ResourceType, estimated_cost: float = 0.0) -> QuotaCheckResult:
        """Check if a specific operation is allowed under current quotas."""
        usage = await self.get_usage()
        quotas = usage.quotas

        if resource == ResourceType.AI_INFERENCE:
            remaining = max(0, quotas.max_daily_inferences - usage.inferences_today)
            return QuotaCheckResult(
                allowed=usage.inferences_today < quotas.max_daily_inferences,
                reason=f"Daily inference limit: {usage.inferences_today}/{quotas.max_daily_inferences}" if usage.inferences_today >= quotas.max_daily_inferences else "",
                resource=resource,
                current_usage=float(usage.inferences_today),
                limit=float(quotas.max_daily_inferences),
                remaining=float(remaining),
            )

        return QuotaCheckResult(allowed=True, resource=resource)


@dataclass
class ModelRouter:
    """Routes inference requests to the optimal model based on cost, quality, and tenant constraints."""

    def __init__(self):
        self._catalog = dict(_DEFAULT_MODEL_CATALOG)
        self._rules: list[RoutingRule] = []

    def register_model(self, route: ModelRoute) -> None:
        """Register or update a model in the catalog."""
        self._catalog[route.model_name] = route

    def add_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def route(
        self,
        prompt_key: str,
        tenant_tier: ModelTier = ModelTier.STANDARD,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        max_cost: Optional[float] = None,
    ) -> RoutingDecision:
        """Route a request to the optimal model."""
        # Find matching rules
        import fnmatch
        matched_rules = [r for r in self._rules if fnmatch.fnmatch(prompt_key, r.prompt_key_pattern) and r.is_active]
        rule = matched_rules[0] if matched_rules else None

        effective_strategy = rule.strategy if rule else strategy

        # Filter available models
        available = [
            m for m in self._catalog.values()
            if m.is_active and m.tier in self._tiers_up_to(tenant_tier)
        ]

        if rule and rule.preferred_model and rule.preferred_model in self._catalog:
            preferred = self._catalog[rule.preferred_model]
            if preferred.is_active and preferred.tier in self._tiers_up_to(tenant_tier):
                return RoutingDecision(
                    selected_model=preferred.model_name,
                    selected_provider=preferred.provider,
                    tier=preferred.tier,
                    estimated_cost=self._estimate_cost(preferred, 1000, 500),
                    strategy_used=RoutingStrategy.TENANT_PREFERRED,
                    alternatives=[m.model_name for m in available if m.model_name != preferred.model_name][:3],
                    reason=f"Preferred model: {preferred.model_name}",
                )

        if effective_strategy == RoutingStrategy.COST_FIRST:
            cheapest = min(available, key=lambda m: m.cost_per_input_token)
            return RoutingDecision(
                selected_model=cheapest.model_name,
                selected_provider=cheapest.provider,
                tier=cheapest.tier,
                estimated_cost=self._estimate_cost(cheapest, 1000, 500),
                strategy_used=RoutingStrategy.COST_FIRST,
                alternatives=[m.model_name for m in available if m.model_name != cheapest.model_name][:3],
                reason=f"Cost-optimized: cheapest tier ({cheapest.tier.value})",
            )

        if effective_strategy == RoutingStrategy.QUALITY_FIRST:
            best = max(available, key=lambda m: m.capabilities.quality_score)
            return RoutingDecision(
                selected_model=best.model_name,
                selected_provider=best.provider,
                tier=best.tier,
                estimated_cost=self._estimate_cost(best, 1000, 500),
                strategy_used=RoutingStrategy.QUALITY_FIRST,
                alternatives=[m.model_name for m in available if m.model_name != best.model_name][:3],
                reason=f"Quality-optimized: highest score ({best.capabilities.quality_score})",
            )

        # BALANCED: score by quality/cost ratio
        def _balanced_score(m: ModelRoute) -> float:
            quality = m.capabilities.quality_score
            cost_per_1k = m.cost_per_input_token * 1000 + m.cost_per_output_token * 500
            if cost_per_1k == 0:
                return quality
            return quality / (cost_per_1k * 1000)  # quality per micro-dollar

        best_balanced = max(available, key=_balanced_score)
        return RoutingDecision(
            selected_model=best_balanced.model_name,
            selected_provider=best_balanced.provider,
            tier=best_balanced.tier,
            estimated_cost=self._estimate_cost(best_balanced, 1000, 500),
            strategy_used=RoutingStrategy.BALANCED,
            alternatives=[m.model_name for m in available if m.model_name != best_balanced.model_name][:3],
            reason=f"Balanced: quality/cost optimized ({best_balanced.model_name})",
        )

    def _tiers_up_to(self, tier: ModelTier) -> list[ModelTier]:
        """Get all tiers up to and including the given tier."""
        order = [ModelTier.ECONOMY, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.CUSTOM]
        idx = order.index(tier) if tier in order else 0
        return order[:idx + 1]

    def _estimate_cost(self, model: ModelRoute, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens * model.cost_per_input_token) + (completion_tokens * model.cost_per_output_token)

    def get_models(self, tier: Optional[ModelTier] = None) -> list[ModelRoute]:
        """List available models, optionally filtered by tier."""
        if tier:
            return [m for m in self._catalog.values() if m.tier == tier and m.is_active]
        return [m for m in self._catalog.values() if m.is_active]


@dataclass
class InferenceAccountingService:
    """Records and queries inference usage for cost attribution."""

    session: AsyncSession
    tenant_id: str

    async def get_summary(
        self,
        period_days: int = 30,
    ) -> InferenceSummary:
        """Get inference usage summary for a period."""
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=period_days)

        sql = sa_text("""
            SELECT
                model, provider,
                COUNT(*)::int AS inferences,
                COALESCE(SUM(total_tokens), 0)::int AS tokens,
                COALESCE(SUM(cost_usd), 0)::float AS cost,
                COALESCE(AVG(latency_ms), 0)::float AS avg_latency
            FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= :period_start
            GROUP BY model, provider
            ORDER BY cost DESC
        """)
        result = await self.session.execute(sql, {
            "tid": self.tenant_id,
            "period_start": period_start,
        })

        by_model: dict[str, ModelInferenceSummary] = {}
        total_inferences = 0
        total_tokens = 0
        total_cost = 0.0
        total_latency = 0.0
        model_count = 0

        for row in result.fetchall():
            by_model[row.model] = ModelInferenceSummary(
                model=row.model,
                inferences=row.inferences,
                tokens=row.tokens,
                cost_usd=round(row.cost, 4),
                avg_latency_ms=round(row.avg_latency, 1),
            )
            total_inferences += row.inferences
            total_tokens += row.tokens
            total_cost += row.cost
            total_latency += row.avg_latency
            model_count += 1

        # By prompt key
        prompt_sql = sa_text("""
            SELECT
                COALESCE(prompt_key, 'unknown') AS prompt_key,
                COUNT(*)::int AS inferences,
                COALESCE(SUM(total_tokens), 0)::int AS tokens,
                COALESCE(SUM(cost_usd), 0)::float AS cost,
                COALESCE(AVG(latency_ms), 0)::float AS avg_latency
            FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= :period_start
            GROUP BY prompt_key
            ORDER BY cost DESC
        """)
        prompt_result = await self.session.execute(prompt_sql, {
            "tid": self.tenant_id,
            "period_start": period_start,
        })
        by_prompt = {
            str(r.prompt_key): PromptInferenceSummary(
                prompt_key=str(r.prompt_key),
                inferences=r.inferences,
                tokens=r.tokens,
                cost_usd=round(r.cost, 4),
                avg_latency_ms=round(r.avg_latency, 1),
            )
            for r in prompt_result.fetchall()
        }

        return InferenceSummary(
            tenant_id=self.tenant_id,
            period_start=period_start,
            period_end=now,
            total_inferences=total_inferences,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 4),
            by_model=by_model,
            by_prompt=by_prompt,
            avg_latency_ms=round(total_latency / model_count, 1) if model_count > 0 else 0.0,
        )


@dataclass
class CostGovernanceService:
    """Orchestrates all cost and resource governance."""

    session: AsyncSession
    tenant_id: str

    async def get_dashboard(self) -> CostGovernanceDashboard:
        """Get the complete cost governance dashboard."""
        budget_service = TokenBudgetService(self.session, self.tenant_id)
        quota_service = QuotaEnforcementService(self.session, self.tenant_id)
        accounting = InferenceAccountingService(self.session, self.tenant_id)

        budget_usage = await budget_service.get_current_usage()
        quota_usage = await quota_service.get_usage()
        inference_summary = await accounting.get_summary(period_days=30)

        # Top cost drivers
        cost_drivers = []
        for model_name, summary in sorted(inference_summary.by_model.items(), key=lambda x: -x[1].cost_usd):
            pct = (summary.cost_usd / inference_summary.total_cost_usd * 100) if inference_summary.total_cost_usd > 0 else 0
            cost_drivers.append(CostDriver(
                resource=f"model:{model_name}",
                cost_usd=summary.cost_usd,
                percentage=round(pct, 1),
                recommendation=f"Consider switching to economy tier for non-critical {model_name} tasks" if pct > 30 else "",
            ))

        # Savings opportunities
        savings = []
        if cost_drivers and cost_drivers[0].percentage > 30:
            savings.append(f"Model '{cost_drivers[0].resource}' represents {cost_drivers[0].percentage}% of costs — evaluate if economy tier is sufficient")

        return CostGovernanceDashboard(
            tenant_id=self.tenant_id,
            budget_usage=[budget_usage],
            quota_usage=quota_usage,
            inference_summary=inference_summary,
            top_cost_drivers=cost_drivers[:5],
            savings_opportunities=savings,
        )
