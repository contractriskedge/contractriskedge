"""Token counting and cost tracking per LLM request.

Provides persistent cost tracking with database logging, per-tenant
cost aggregation, and cost monitoring capabilities.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import CostRecord, ProviderType

logger = logging.getLogger(__name__)


class CostTracker:
    """Tracks LLM usage costs with database persistence.

    Records cost per request, aggregates by tenant, and provides
    query methods for cost analysis and monitoring. In production,
    costs are logged to the audit_logs table and a dedicated
    llm_costs table.

    Usage:
        tracker = CostTracker()
        await tracker.record_cost(
            request_id="...",
            provider=ProviderType.CLAUDE_SONNET_35,
            model_name="claude-3-5-sonnet-20241022",
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
            cost_usd=0.0045,
            tenant_id="tenant-123",
            duration_ms=1200,
        )
        daily_costs = await tracker.get_daily_costs("tenant-123")
    """

    def __init__(self, db_pool: Optional[Any] = None) -> None:
        """Initialize the cost tracker.

        Args:
            db_pool: Optional database connection pool for persistence.
                     If None, costs are tracked in memory only.
        """
        self._db_pool = db_pool
        self._in_memory_records: List[CostRecord] = []
        self._max_memory_records: int = 10_000

    async def record_cost(
        self,
        request_id: str,
        provider: ProviderType,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        tenant_id: Optional[str] = None,
        duration_ms: float = 0.0,
        cached: bool = False,
    ) -> None:
        """Record the cost of an LLM request.

        Persists to database if available, otherwise stores in memory.

        Args:
            request_id: Unique request identifier.
            provider: The LLM provider used.
            model_name: The specific model name.
            prompt_tokens: Number of prompt tokens.
            completion_tokens: Number of completion tokens.
            total_tokens: Total tokens used.
            cost_usd: Cost in USD.
            tenant_id: Optional tenant identifier.
            duration_ms: Request duration in milliseconds.
            cached: Whether this was a cached response.
        """
        record = CostRecord(
            request_id=request_id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            tenant_id=tenant_id,
            duration_ms=duration_ms,
            cached=cached,
        )

        if self._db_pool is not None:
            await self._persist_to_db(record)
        else:
            self._store_in_memory(record)

        logger.debug(
            "Cost recorded: request=%s provider=%s tokens=%d cost=$%.6f",
            request_id,
            provider.value,
            total_tokens,
            cost_usd,
        )

    async def _persist_to_db(self, record: CostRecord) -> None:
        """Persist a cost record to the database.

        Args:
            record: The cost record to persist.
        """
        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO llm_cost_records (
                        request_id, provider, model_name,
                        prompt_tokens, completion_tokens, total_tokens,
                        cost_usd, tenant_id, duration_ms, cached,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    record.request_id,
                    record.provider.value,
                    record.model_name,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    record.cost_usd,
                    record.tenant_id,
                    record.duration_ms,
                    record.cached,
                    record.timestamp,
                )
        except Exception as exc:
            logger.error("Failed to persist cost record: %s", exc)
            # Fall back to in-memory storage
            self._store_in_memory(record)

    def _store_in_memory(self, record: CostRecord) -> None:
        """Store a cost record in memory.

        Args:
            record: The cost record to store.
        """
        self._in_memory_records.append(record)
        # Prune oldest records if over limit
        if len(self._in_memory_records) > self._max_memory_records:
            self._in_memory_records = self._in_memory_records[
                -self._max_memory_records:
            ]

    async def get_daily_costs(
        self, tenant_id: Optional[str] = None, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily cost breakdown for a tenant.

        Args:
            tenant_id: Optional tenant filter. If None, returns all tenants.
            days: Number of days to look back.

        Returns:
            List of daily cost summaries.
        """
        if self._db_pool is not None:
            return await self._query_daily_costs_db(tenant_id, days)

        return self._compute_daily_costs_memory(tenant_id, days)

    async def _query_daily_costs_db(
        self, tenant_id: Optional[str], days: int
    ) -> List[Dict[str, Any]]:
        """Query daily costs from database.

        Args:
            tenant_id: Optional tenant filter.
            days: Lookback period.

        Returns:
            List of daily cost summaries.
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            async with self._db_pool.acquire() as conn:
                if tenant_id:
                    rows = await conn.fetch(
                        """
                        SELECT
                            DATE(created_at) as day,
                            provider,
                            SUM(total_tokens) as total_tokens,
                            SUM(cost_usd) as total_cost,
                            COUNT(*) as request_count,
                            SUM(prompt_tokens) as prompt_tokens,
                            SUM(completion_tokens) as completion_tokens
                        FROM llm_cost_records
                        WHERE tenant_id = $1 AND created_at >= $2
                        GROUP BY DATE(created_at), provider
                        ORDER BY day DESC
                        """,
                        tenant_id,
                        cutoff,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT
                            DATE(created_at) as day,
                            provider,
                            SUM(total_tokens) as total_tokens,
                            SUM(cost_usd) as total_cost,
                            COUNT(*) as request_count,
                            SUM(prompt_tokens) as prompt_tokens,
                            SUM(completion_tokens) as completion_tokens
                        FROM llm_cost_records
                        WHERE created_at >= $1
                        GROUP BY DATE(created_at), provider
                        ORDER BY day DESC
                        """,
                        cutoff,
                    )
                return [dict(row) for row in rows]
        except Exception as exc:
            logger.error("Failed to query daily costs from DB: %s", exc)
            return []

    def _compute_daily_costs_memory(
        self, tenant_id: Optional[str], days: int
    ) -> List[Dict[str, Any]]:
        """Compute daily costs from in-memory records.

        Args:
            tenant_id: Optional tenant filter.
            days: Lookback period.

        Returns:
            List of daily cost summaries.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        filtered = [
            r
            for r in self._in_memory_records
            if r.timestamp >= cutoff
            and (tenant_id is None or r.tenant_id == tenant_id)
        ]

        daily: Dict[str, Dict[str, Any]] = {}
        for record in filtered:
            day_key = record.timestamp.strftime("%Y-%m-%d")
            prov_key = record.provider.value
            composite_key = f"{day_key}_{prov_key}"

            if composite_key not in daily:
                daily[composite_key] = {
                    "day": day_key,
                    "provider": prov_key,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "request_count": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                }

            entry = daily[composite_key]
            entry["total_tokens"] += record.total_tokens
            entry["total_cost"] += record.cost_usd
            entry["request_count"] += 1
            entry["prompt_tokens"] += record.prompt_tokens
            entry["completion_tokens"] += record.completion_tokens

        return sorted(daily.values(), key=lambda x: x["day"], reverse=True)

    async def get_tenant_summary(
        self, tenant_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get a summary of LLM costs for a tenant.

        Args:
            tenant_id: The tenant to summarize.
            days: Lookback period.

        Returns:
            Summary dict with total costs, token counts, and averages.
        """
        daily = await self.get_daily_costs(tenant_id, days)

        total_cost = sum(d["total_cost"] for d in daily)
        total_tokens = sum(d["total_tokens"] for d in daily)
        total_requests = sum(d["request_count"] for d in daily)

        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "avg_cost_per_request": (
                round(total_cost / total_requests, 6) if total_requests > 0 else 0.0
            ),
            "avg_tokens_per_request": (
                total_tokens // total_requests if total_requests > 0 else 0
            ),
            "daily_breakdown": daily,
        }

    async def get_overall_costs(
        self, days: int = 30
    ) -> Dict[str, Any]:
        """Get overall cost summary across all tenants.

        Args:
            days: Lookback period.

        Returns:
            Summary dict with aggregated costs.
        """
        daily = await self.get_daily_costs(None, days)

        total_cost = sum(d["total_cost"] for d in daily)
        total_tokens = sum(d["total_tokens"] for d in daily)
        total_requests = sum(d["request_count"] for d in daily)

        provider_breakdown: Dict[str, Dict[str, Any]] = {}
        for d in daily:
            prov = d["provider"]
            if prov not in provider_breakdown:
                provider_breakdown[prov] = {
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "request_count": 0,
                }
            provider_breakdown[prov]["total_cost"] += d["total_cost"]
            provider_breakdown[prov]["total_tokens"] += d["total_tokens"]
            provider_breakdown[prov]["request_count"] += d["request_count"]

        return {
            "period_days": days,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "avg_cost_per_request": (
                round(total_cost / total_requests, 6) if total_requests > 0 else 0.0
            ),
            "provider_breakdown": provider_breakdown,
            "daily_breakdown": daily,
        }
