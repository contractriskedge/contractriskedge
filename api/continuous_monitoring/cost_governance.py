"""AI cost governance dashboard (V2-027) and tenant quota management (V2-028).

Tracks token usage, per-tenant LLM costs, enforces hard/soft token
limits, and provides cost monitoring dashboards.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenQuota:
    """Token usage quota for a tenant."""

    tenant_id: str
    soft_limit_tokens: int  # Warning threshold
    hard_limit_tokens: int  # Hard enforcement threshold
    period: str = "monthly"  # monthly, daily
    current_usage_tokens: int = 0
    current_usage_cost_usd: float = 0.0
    period_start: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    alerts_enabled: bool = True
    is_over_soft_limit: bool = False
    is_over_hard_limit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "soft_limit_tokens": self.soft_limit_tokens,
            "hard_limit_tokens": self.hard_limit_tokens,
            "period": self.period,
            "current_usage_tokens": self.current_usage_tokens,
            "current_usage_cost_usd": round(self.current_usage_cost_usd, 4),
            "period_start": self.period_start,
            "alerts_enabled": self.alerts_enabled,
            "is_over_soft_limit": self.is_over_soft_limit,
            "is_over_hard_limit": self.is_over_hard_limit,
            "usage_percent": round(
                self.current_usage_tokens / self.hard_limit_tokens * 100, 1
            ) if self.hard_limit_tokens > 0 else 0.0,
        }


@dataclass
class CostRecord:
    """A single cost record for an LLM request."""

    record_id: str
    tenant_id: str
    request_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: float
    cached: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "record_id": self.record_id,
            "tenant_id": self.tenant_id,
            "request_id": self.request_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "duration_ms": round(self.duration_ms, 2),
            "cached": self.cached,
            "timestamp": self.timestamp,
        }


class CostGovernance:
    """AI cost governance and tenant quota management.

    Tracks LLM usage costs across tenants, enforces token quotas,
    and provides cost analytics for the governance dashboard.

    Usage:
        gov = CostGovernance()
        await gov.record_usage(tenant_id="t1", tokens=500, cost=0.01)
        report = await gov.get_tenant_report("t1")
        dashboard = await gov.get_dashboard()
    """

    def __init__(self, db_pool: Optional[Any] = None) -> None:
        """Initialize the cost governance system.

        Args:
            db_pool: Optional database pool for persistence.
        """
        self._db_pool = db_pool
        self._records: List[CostRecord] = []
        self._quotas: Dict[str, TokenQuota] = {}
        self._max_records: int = 100_000

        # Default quotas
        self._default_quotas = {
            "soft_limit": 1_000_000,   # 1M tokens soft limit
            "hard_limit": 2_000_000,   # 2M tokens hard limit
        }

        # Cost per token by provider
        self._cost_rates = {
            "claude-3-5-sonnet": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
            "claude-3-opus": {"input": 15.0 / 1_000_000, "output": 75.0 / 1_000_000},
            "gpt-4o": {"input": 2.5 / 1_000_000, "output": 10.0 / 1_000_000},
            "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.6 / 1_000_000},
            "deepseek-chat": {"input": 0.27 / 1_000_000, "output": 1.10 / 1_000_000},
            "text-embedding-3-large": {"input": 0.13 / 1_000_000, "output": 0.0},
        }

    def set_tenant_quota(
        self,
        tenant_id: str,
        soft_limit: int,
        hard_limit: int,
        period: str = "monthly",
    ) -> TokenQuota:
        """Set token quota for a tenant.

        Args:
            tenant_id: The tenant identifier.
            soft_limit: Soft limit (warning threshold).
            hard_limit: Hard limit (enforcement threshold).
            period: Quota period (monthly, daily).

        Returns:
            The created TokenQuota.
        """
        quota = TokenQuota(
            tenant_id=tenant_id,
            soft_limit_tokens=soft_limit,
            hard_limit_tokens=hard_limit,
            period=period,
        )
        self._quotas[tenant_id] = quota
        logger.info("Set quota for tenant %s: soft=%d, hard=%d (%s)",
                     tenant_id, soft_limit, hard_limit, period)
        return quota

    def get_tenant_quota(self, tenant_id: str) -> TokenQuota:
        """Get the token quota for a tenant.

        Creates a default quota if none exists.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            The tenant's TokenQuota.
        """
        if tenant_id not in self._quotas:
            self._quotas[tenant_id] = TokenQuota(
                tenant_id=tenant_id,
                soft_limit_tokens=self._default_quotas["soft_limit"],
                hard_limit_tokens=self._default_quotas["hard_limit"],
            )
        return self._quotas[tenant_id]

    async def record_usage(
        self,
        tenant_id: str,
        request_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: float = 0.0,
        cached: bool = False,
    ) -> Dict[str, Any]:
        """Record LLM usage and check quota limits.

        Args:
            tenant_id: The tenant identifier.
            request_id: The request identifier.
            provider: The LLM provider.
            model: The model name.
            prompt_tokens: Number of prompt tokens.
            completion_tokens: Number of completion tokens.
            duration_ms: Request duration in ms.
            cached: Whether the response was cached.

        Returns:
            Dict with quota status and cost info.
        """
        total_tokens = prompt_tokens + completion_tokens

        # Compute cost
        rates = self._cost_rates.get(model, {"input": 0.0, "output": 0.0})
        cost_usd = (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])

        # Create record
        record = CostRecord(
            record_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            request_id=request_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            cached=cached,
        )

        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        # Update tenant quota
        quota = self.get_tenant_quota(tenant_id)
        quota.current_usage_tokens += total_tokens
        quota.current_usage_cost_usd += cost_usd

        # Check limits
        quota.is_over_soft_limit = quota.current_usage_tokens > quota.soft_limit_tokens
        quota.is_over_hard_limit = quota.current_usage_tokens > quota.hard_limit_tokens

        status = "ok"
        if quota.is_over_hard_limit:
            status = "blocked"
        elif quota.is_over_soft_limit:
            status = "warning"

        return {
            "record_id": record.record_id,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_usd, 6),
            "quota_status": status,
            "quota_usage_percent": round(
                quota.current_usage_tokens / quota.hard_limit_tokens * 100, 1
            ) if quota.hard_limit_tokens > 0 else 0.0,
            "quota_remaining": max(0, quota.hard_limit_tokens - quota.current_usage_tokens),
        }

    def check_quota(self, tenant_id: str, estimated_tokens: int = 0) -> Dict[str, Any]:
        """Check if a tenant has quota remaining.

        Args:
            tenant_id: The tenant identifier.
            estimated_tokens: Estimated tokens for the upcoming request.

        Returns:
            Dict with quota check result.
        """
        quota = self.get_tenant_quota(tenant_id)
        would_exceed = quota.current_usage_tokens + estimated_tokens > quota.hard_limit_tokens

        return {
            "tenant_id": tenant_id,
            "current_usage": quota.current_usage_tokens,
            "soft_limit": quota.soft_limit_tokens,
            "hard_limit": quota.hard_limit_tokens,
            "estimated_usage_after": quota.current_usage_tokens + estimated_tokens,
            "would_exceed_hard_limit": would_exceed,
            "is_over_soft_limit": quota.is_over_soft_limit,
            "is_over_hard_limit": quota.is_over_hard_limit,
            "allowed": not would_exceed and not quota.is_over_hard_limit,
        }

    async def get_tenant_report(self, tenant_id: str) -> Dict[str, Any]:
        """Get a cost report for a specific tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with tenant cost report.
        """
        tenant_records = [r for r in self._records if r.tenant_id == tenant_id]
        quota = self.get_tenant_quota(tenant_id)

        # Aggregate by provider
        by_provider: Dict[str, Dict[str, Any]] = {}
        for r in tenant_records:
            if r.provider not in by_provider:
                by_provider[r.provider] = {
                    "requests": 0, "total_tokens": 0, "total_cost": 0.0, "models": set()
                }
            by_provider[r.provider]["requests"] += 1
            by_provider[r.provider]["total_tokens"] += r.total_tokens
            by_provider[r.provider]["total_cost"] += r.cost_usd
            by_provider[r.provider]["models"].add(r.model)

        # Aggregate by day
        daily_costs: Dict[str, float] = {}
        for r in tenant_records:
            day = r.timestamp[:10]
            daily_costs[day] = daily_costs.get(day, 0.0) + r.cost_usd

        total_cost = sum(r.cost_usd for r in tenant_records)
        total_tokens = sum(r.total_tokens for r in tenant_records)
        cached_tokens = sum(r.total_tokens for r in tenant_records if r.cached)

        return {
            "tenant_id": tenant_id,
            "total_requests": len(tenant_records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "cached_tokens": cached_tokens,
            "cache_savings_usd": round(cached_tokens * 0.0001, 4),  # Approximate savings
            "quota": quota.to_dict(),
            "by_provider": {
                provider: {
                    "requests": info["requests"],
                    "total_tokens": info["total_tokens"],
                    "total_cost_usd": round(info["total_cost"], 4),
                    "models": list(info["models"]),
                }
                for provider, info in by_provider.items()
            },
            "daily_costs": dict(sorted(daily_costs.items())),
            "average_cost_per_request": round(
                total_cost / len(tenant_records), 6
            ) if tenant_records else 0.0,
        }

    async def get_dashboard(self) -> Dict[str, Any]:
        """Get the cost governance dashboard data.

        Returns:
            Dict with dashboard data.
        """
        total_cost = sum(r.cost_usd for r in self._records)
        total_tokens = sum(r.total_tokens for r in self._records)
        total_requests = len(self._records)

        # Aggregate by provider
        by_provider: Dict[str, Dict[str, Any]] = {}
        for r in self._records:
            if r.provider not in by_provider:
                by_provider[r.provider] = {
                    "requests": 0, "tokens": 0, "cost": 0.0
                }
            by_provider[r.provider]["requests"] += 1
            by_provider[r.provider]["tokens"] += r.total_tokens
            by_provider[r.provider]["cost"] += r.cost_usd

        # Tenants over quota
        tenants_over_quota = [
            q.to_dict() for q in self._quotas.values()
            if q.is_over_soft_limit
        ]

        # Daily cost trend (last 30 days)
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        recent_records = [r for r in self._records if r.timestamp >= thirty_days_ago]

        daily_trend: Dict[str, float] = {}
        for r in recent_records:
            day = r.timestamp[:10]
            daily_trend[day] = daily_trend.get(day, 0.0) + r.cost_usd

        # Cost by model
        by_model: Dict[str, Dict[str, Any]] = {}
        for r in self._records:
            if r.model not in by_model:
                by_model[r.model] = {"requests": 0, "tokens": 0, "cost": 0.0}
            by_model[r.model]["requests"] += 1
            by_model[r.model]["tokens"] += r.total_tokens
            by_model[r.model]["cost"] += r.cost_usd

        return {
            "summary": {
                "total_cost_usd": round(total_cost, 2),
                "total_tokens": total_tokens,
                "total_requests": total_requests,
                "average_cost_per_request": round(total_cost / total_requests, 6) if total_requests else 0.0,
                "tenants_tracked": len(self._quotas),
                "tenants_over_quota": len(tenants_over_quota),
            },
            "by_provider": {
                p: {
                    "requests": d["requests"],
                    "tokens": d["tokens"],
                    "cost_usd": round(d["cost"], 4),
                    "cost_percent": round(d["cost"] / total_cost * 100, 1) if total_cost > 0 else 0.0,
                }
                for p, d in sorted(by_provider.items(), key=lambda x: -x[1]["cost"])
            },
            "by_model": {
                m: {
                    "requests": d["requests"],
                    "tokens": d["tokens"],
                    "cost_usd": round(d["cost"], 4),
                }
                for m, d in sorted(by_model.items(), key=lambda x: -x[1]["cost"])
            },
            "daily_cost_trend": dict(sorted(daily_trend.items())),
            "tenants_over_quota": tenants_over_quota,
        }

    async def get_alerts(self) -> List[Dict[str, Any]]:
        """Get active cost-related alerts.

        Returns:
            List of alert dicts.
        """
        alerts = []
        for tenant_id, quota in self._quotas.items():
            if quota.is_over_hard_limit:
                alerts.append({
                    "tenant_id": tenant_id,
                    "severity": "critical",
                    "message": f"Tenant {tenant_id} has exceeded hard token limit "
                               f"({quota.current_usage_tokens}/{quota.hard_limit_tokens})",
                    "type": "hard_limit_exceeded",
                })
            elif quota.is_over_soft_limit:
                alerts.append({
                    "tenant_id": tenant_id,
                    "severity": "warning",
                    "message": f"Tenant {tenant_id} has exceeded soft token limit "
                               f"({quota.current_usage_tokens}/{quota.soft_limit_tokens})",
                    "type": "soft_limit_exceeded",
                })

        return alerts
