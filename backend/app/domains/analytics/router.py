"""Analytics API router — error analytics, stuck workflows, system health, metrics summary."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.analytics.schemas import (
    ErrorAnalyticsResponse, StuckWorkflowsResponse,
    SystemHealthResponse, MetricsSummaryResponse,
    QueryPerformanceResponse
)
from app.domains.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


async def get_analytics_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
) -> AnalyticsService:
    return AnalyticsService(session=db, tenant_id=tenant_id)


@router.get("/errors", response_model=ErrorAnalyticsResponse)
async def get_error_analytics(
    period_hours: int = Query(24, ge=1, le=168, description="Lookback period in hours"),
    service: AnalyticsService = Depends(get_analytics_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get aggregated error analytics across all domains.

    Returns failure counts by type, domain breakdown, retryable vs non-retryable,
    and top failing uploads.
    """
    return await service.get_error_analytics(period_hours
)


@router.get("/stuck-workflows", response_model=StuckWorkflowsResponse
)
async def get_stuck_workflows(
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Detect potentially stuck or abandoned workflows.

    Checks:
    - Uploads stuck in non-terminal state for >30 min
    - AI runs in processing/pending for >30 min
    - Reviews stuck in draft/ai_analyzed for >24h
    """
    return await service.get_stuck_workflows(
)


@router.get("/health", response_model=SystemHealthResponse
)
async def get_system_health(
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get overall system health status.

    Returns active uploads, AI runs, pending reviews, recent errors, SLA breaches.
    Status: healthy, degraded, or unhealthy based on error thresholds.
    """
    return await service.get_system_health(
)


@router.get("/metrics", response_model=MetricsSummaryResponse
)
async def get_metrics_summary(
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get key system metrics for the metrics dashboard.

    Includes upload/AI success rates, average latency, token usage, cost,
    and counts for uploads, reviews, and findings in the last 24h.
    """
    return await service.get_metrics_summary(
)


@router.get("/upload-trend"
)
async def get_upload_trend(
    days: int = Query(30, ge=7, le=90),
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Upload volume per day for trend chart."""
    return await service.get_upload_trend(days
)


@router.get("/risk-distribution"
)
async def get_risk_distribution(
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Risk score distribution across reviews."""
    return await service.get_risk_distribution(
)


@router.get("/findings-by-clause"
)
async def get_findings_by_clause(
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Findings count grouped by clause type."""
    return await service.get_findings_by_clause(
)


@router.get("/ai-cost-trend"
)
async def get_ai_cost_trend(
    days: int = Query(30, ge=7, le=90),
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """AI cost and tokens per day."""
    return await service.get_ai_cost_trend(days
)


@router.get("/review-aging"
)
async def get_review_aging(
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Review aging buckets for workflow intelligence."""
    return await service.get_review_aging(
)


@router.get("/executive-summary"
)
async def get_executive_summary(
    service: AnalyticsService = Depends(get_analytics_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Executive-level portfolio intelligence."""
    return await service.get_executive_summary(
)


@router.get("/query-performance", response_model=QueryPerformanceResponse
)
async def get_query_performance(
    db: AsyncSession = Depends(get_db)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get database query performance statistics.

    Returns p50/p95/p99 query latency, slow query count, and pool stats.
    """
    from app.kernel.database.session import TenantAwareSessionFactory

    factory = getattr(db, "_parent_factory", None
)
    if not factory or not isinstance(factory, TenantAwareSessionFactory
):
        return QueryPerformanceResponse(
)

    stats = factory.pool_stats
    return QueryPerformanceResponse(
        total_queries=stats.get("queries_executed", 0),
        slow_queries=stats.get("slow_queries", 0),
        p50_query_ms=stats.get("p50_query_ms", 0),
        p95_query_ms=stats.get("p95_query_ms", 0),
        p99_query_ms=stats.get("p99_query_ms", 0),
        connections_created=stats.get("connections_created", 0),
        connections_closed=stats.get("connections_closed", 0),
        pool_size=stats.get("size", 0),
        pool_checked_in=stats.get("checked_in", 0),
        pool_checked_out=stats.get("checked_out", 0),
        pool_overflow=stats.get("overflow", 0)
)
