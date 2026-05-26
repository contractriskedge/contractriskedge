"""Analytics schemas — error analytics, failure aggregation, and system metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FailureSummary(BaseModel):
    """Aggregated failure counts by type and domain."""
    failure_type: str
    count: int
    last_occurred: Optional[datetime] = None
    domain: str = "unknown"


class ErrorAnalyticsResponse(BaseModel):
    """Aggregated error analytics response."""
    total_failures: int = 0
    failures_by_type: list[FailureSummary] = Field(default_factory=list)
    failures_by_domain: dict[str, int] = Field(default_factory=dict)
    retryable_failures: int = 0
    non_retryable_failures: int = 0
    retryable_count: int = 0
    non_retryable_count: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_domain: dict[str, int] = Field(default_factory=dict)
    top_failing_uploads: list[dict] = Field(default_factory=list)
    period_hours: int = 24


class SystemHealthResponse(BaseModel):
    """System health and performance overview."""
    status: str = "healthy"  # healthy, degraded, unhealthy
    uptime_seconds: float = 0
    active_uploads: int = 0
    active_ai_runs: int = 0
    pending_reviews: int = 0
    queue_depth: dict[str, int] = Field(default_factory=dict)
    db_pool_stats: dict = Field(default_factory=dict)
    recent_errors_24h: int = 0
    sla_breaches_24h: int = 0
    sla_breaches: int = 0
    upload_success_rate: float = 0.0
    ai_success_rate: float = 0.0


class StuckWorkflowItem(BaseModel):
    """A workflow that may be stuck or abandoned."""
    resource_id: str
    resource_type: str  # upload, ai_run, review
    state: str
    age_minutes: int
    retry_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StuckWorkflowsResponse(BaseModel):
    """Response listing potentially stuck workflows."""
    items: list[StuckWorkflowItem] = Field(default_factory=list)
    total: int = 0
    stuck_uploads: int = 0
    stuck_ai_runs: int = 0
    stuck_reviews: int = 0
    recovery_actions: list[str] = Field(default_factory=list)


class MetricsSummaryResponse(BaseModel):
    """Summary of key system metrics for the metrics dashboard."""
    upload_success_rate: float = 0.0
    ai_success_rate: float = 0.0
    avg_ai_latency_ms: float = 0.0
    avg_upload_latency_ms: float = 0.0
    avg_ingestion_duration_s: float = 0.0
    total_tokens_used: int = 0
    total_ai_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    total_uploads_24h: int = 0
    total_reviews_24h: int = 0
    total_findings_24h: int = 0
    re_analysis_count_24h: int = 0


class QueryPerformanceResponse(BaseModel):
    """Database query performance statistics."""
    total_queries: int = 0
    slow_queries: int = 0
    p50_query_ms: int = 0
    p95_query_ms: int = 0
    p99_query_ms: int = 0
    connections_created: int = 0
    connections_closed: int = 0
    pool_size: int = 0
    pool_checked_in: int = 0
    pool_checked_out: int = 0
    pool_overflow: int = 0
