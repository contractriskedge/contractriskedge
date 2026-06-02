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
from app.domains.analytics.executive_schemas import (
    ExecutiveDashboard,
    ExecutiveReport, ExecutiveReportRequest,
)
from app.domains.analytics.reporting_schemas import (
    ScheduledReportCreate, ScheduledReportUpdate, ScheduledReportResponse,
    AnomalyDetectionResult,
    TrendNarrativeSet,
    ExecutiveDigest, DigestStyle,
)
from app.domains.analytics.service import AnalyticsService
from app.domains.analytics.executive_service import ExecutiveAnalyticsService
from app.domains.analytics.reporting_service import (
    ReportScheduler, AnomalyDetector, NarrativeGenerator, DigestGenerator,
)

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


# ── Prediction Endpoints ─────────────────────────────────────────


@router.get("/predict/sla-breach")
async def predict_sla_breach(
    review_id: str = Query(..., description="Review ID to evaluate"),
    service: AnalyticsService = Depends(get_analytics_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Predict SLA breach probability for a specific review.

    Combines historical stage durations, current elapsed time,
    risk score, priority, and escalation history.
    """
    return await service.predict_sla_breach(review_id)


@router.get("/predict/batch-sla-breaches")
async def predict_batch_sla_breaches(
    limit: int = Query(100, ge=1, le=500),
    service: AnalyticsService = Depends(get_analytics_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Predict SLA breach probability for all active reviews.

    Returns list sorted by breach probability descending.
    """
    return await service.predict_batch_sla_breaches(limit=limit)


@router.get("/predict/stage-durations")
async def get_stage_duration_percentiles(
    service: AnalyticsService = Depends(get_analytics_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get P50/P75/P95 duration percentiles per workflow stage.

    Computed from historical ReviewStatusHistory data.
    Falls back to reasonable defaults when insufficient data.
    """
    return await service.get_stage_duration_percentiles()


@router.get("/predict/escalation-risk")
async def predict_escalation_risk(
    review_id: str = Query(..., description="Review ID to evaluate"),
    service: AnalyticsService = Depends(get_analytics_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Predict escalation probability for a review.

    Factors: SLA status, risk score, existing escalations,
    tenant escalation rate.
    """
    return await service.predict_escalation_risk(review_id)


@router.get("/predict/bottlenecks")
async def predict_bottlenecks(
    service: AnalyticsService = Depends(get_analytics_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Predict workflow bottlenecks before they occur.

    Detects reviews exceeding P95 stage duration and
    reviewers approaching capacity limits.
    """
    return await service.predict_bottlenecks()


@router.get("/predict/reviewer-workload")
async def predict_reviewer_workload(
    service: AnalyticsService = Depends(get_analytics_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Predict workload risk for all active reviewers.

    Returns overload probability, average completion time,
    and predicted backlog hours per reviewer.
    """
    return await service.predict_reviewer_workload()


# ── Simulation Endpoints ─────────────────────────────────────────


@router.get("/simulate/policy-change")
async def simulate_policy_change(
    removed_approval_role: Optional[str] = None,
    added_approval_role: Optional[str] = None,
    changed_escalation_hours: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Simulate the impact of changing approval chain policies.

    What-if analysis:
    - Remove a role from approval chain
    - Add a role to approval chain
    - Change escalation timeout

    Returns projected turnaround time and risk warnings.
    """
    from app.domains.analytics.simulator import WorkflowSimulator

    sim = WorkflowSimulator(db, tenant_id)
    return await sim.simulate_policy_change(
        removed_approval_role=removed_approval_role,
        added_approval_role=added_approval_role,
        changed_escalation_hours=changed_escalation_hours,
    )


@router.get("/simulate/threshold-change")
async def simulate_threshold_change(
    risk_threshold: int = 50,
    new_routing_role: str = "compliance",
    current_routing_role: str = "reviewer",
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Simulate the impact of changing routing thresholds.

    Example: "What if all reviews with risk score >= 50 go to Compliance?"
    """
    from app.domains.analytics.simulator import WorkflowSimulator

    sim = WorkflowSimulator(db, tenant_id)
    return await sim.simulate_threshold_change(
        risk_threshold=risk_threshold,
        new_routing_role=new_routing_role,
        current_routing_role=current_routing_role,
    )


@router.get("/simulate/sla-policy-change")
async def simulate_sla_policy_change(
    new_sla_hours: int = 24,
    workflow_type: str = "legal_review",
    priority: str = "normal",
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Simulate the impact of changing SLA policy targets.

    Example: "What if we tighten SLA from 48h to 24h for normal priority?"
    """
    from app.domains.analytics.simulator import WorkflowSimulator

    sim = WorkflowSimulator(db, tenant_id)
    return await sim.simulate_sla_policy_change(
        new_sla_hours=new_sla_hours,
        workflow_type=workflow_type,
        priority=priority,
    )


# ── Tenant Health Endpoints ──────────────────────────────────────


@router.get("/health-score")
async def get_tenant_health_score(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get composite health score for the current tenant.

    Evaluates SLA compliance, backlog pressure, escalation rate,
    delivery reliability, replay stability, and worker health.
    """
    from app.domains.analytics.health_score import TenantHealthScorer

    scorer = TenantHealthScorer(db)
    return await scorer.score_tenant(tenant_id)


@router.get("/health-score/history")
async def get_tenant_health_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get health score history for trend analysis.

    Returns daily scores for the lookback period.
    """
    from app.domains.analytics.health_score import TenantHealthScorer

    scorer = TenantHealthScorer(db)
    return await scorer.get_health_history(tenant_id, days=days)


@router.get("/health-score/all-tenants")
async def get_all_tenant_health_scores(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Get health scores for all active tenants.

    Sorted by score ascending (worst first). Admin-only.
    """
    from app.domains.analytics.health_score import TenantHealthScorer

    scorer = TenantHealthScorer(db)
    return await scorer.score_all_tenants()


# ── Executive Analytics ──────────────────────────────────────────


@router.get("/executive/dashboard", response_model=ExecutiveDashboard)
async def get_executive_dashboard(
    period_days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get executive dashboard — portfolio summary, cycle time, reviewer efficiency, SLA risk.

    Enterprise buyer visibility layer.
    """
    service = ExecutiveAnalyticsService(session=db, tenant_id=tenant_id)
    return await service.get_dashboard(period_days=period_days)


@router.post("/executive/report", response_model=ExecutiveReport)
async def generate_executive_report(
    request: ExecutiveReportRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Generate an executive report with key findings and recommendations.

    Useful for quarterly business reviews and stakeholder updates.
    """
    service = ExecutiveAnalyticsService(session=db, tenant_id=tenant_id)
    return await service.generate_report(request)


# ── Scheduled Reports ───────────────────────────────────────────


@router.post("/executive/schedules", response_model=ScheduledReportResponse, status_code=201)
async def create_scheduled_report(
    schedule: ScheduledReportCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Create a scheduled executive report configuration."""
    scheduler = ReportScheduler(session=db, tenant_id=tenant_id)
    return await scheduler.create_schedule(schedule, actor=user.id)


@router.get("/executive/schedules", response_model=list[ScheduledReportResponse])
async def list_scheduled_reports(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all scheduled reports for the tenant."""
    scheduler = ReportScheduler(session=db, tenant_id=tenant_id)
    return await scheduler.list_schedules()


@router.get("/executive/schedules/{report_id}", response_model=ScheduledReportResponse)
async def get_scheduled_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a specific scheduled report configuration."""
    scheduler = ReportScheduler(session=db, tenant_id=tenant_id)
    report = await scheduler.get_schedule(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    return report


@router.put("/executive/schedules/{report_id}", response_model=ScheduledReportResponse)
async def update_scheduled_report(
    report_id: str,
    update: ScheduledReportUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Update a scheduled report configuration."""
    scheduler = ReportScheduler(session=db, tenant_id=tenant_id)
    report = await scheduler.update_schedule(report_id, update)
    if not report:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    return report


@router.delete("/executive/schedules/{report_id}")
async def delete_scheduled_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Delete a scheduled report."""
    scheduler = ReportScheduler(session=db, tenant_id=tenant_id)
    deleted = await scheduler.delete_schedule(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    return {"status": "deleted"}


# ── Anomaly Detection ────────────────────────────────────────────


@router.get("/anomalies", response_model=AnomalyDetectionResult)
async def detect_anomalies_short(
    lookback_hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Detect anomalies in tenant metrics (SLA, volume, risk, performance)."""
    detector = AnomalyDetector(session=db, tenant_id=tenant_id)
    return await detector.detect_anomalies(lookback_hours=lookback_hours)


@router.get("/executive/anomalies", response_model=AnomalyDetectionResult)
async def detect_anomalies(
    lookback_hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Detect anomalies in tenant metrics (SLA, volume, risk, performance)."""
    detector = AnomalyDetector(session=db, tenant_id=tenant_id)
    return await detector.detect_anomalies(lookback_hours=lookback_hours)


# ── Trend Narratives ─────────────────────────────────────────────


@router.get("/executive/narratives", response_model=TrendNarrativeSet)
async def generate_trend_narratives(
    period_days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Generate natural-language trend narratives from analytics data."""
    narrator = NarrativeGenerator(session=db, tenant_id=tenant_id)
    return await narrator.generate_narratives(period_days=period_days)


# ── Executive Digest ─────────────────────────────────────────────


@router.post("/executive/digest", response_model=ExecutiveDigest)
async def generate_executive_digest(
    style: DigestStyle = Query(DigestStyle.STANDARD, description="Digest detail level"),
    period_days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Generate an executive digest — the daily/weekly briefing with anomalies and narratives."""
    generator = DigestGenerator(session=db, tenant_id=tenant_id)
    return await generator.generate_digest(style=style, period_days=period_days)


# ── Executive AI Briefing ────────────────────────────────────────
# Phase 2 Session 6 — LLM-powered executive intelligence narrative.


@router.post("/executive/briefing")
async def generate_executive_briefing(
    style: DigestStyle = Query(DigestStyle.STANDARD, description="Briefing detail level"),
    period_days: int = Query(7, ge=1, le=90),
    include_recommendations: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Generate an AI-powered executive briefing with natural-language narrative synthesis.

    Composes data from:
    - Executive dashboard (portfolio, SLA, bottlenecks, exposure)
    - Anomaly detection
    - Trend narratives
    - OpenAI LLM (narrative synthesis)

    Returns structured briefing with executive summary, key findings,
    recommendations, and risk escalations.
    """
    from app.domains.analytics.briefing_service import ExecutiveBriefingGenerator

    generator = ExecutiveBriefingGenerator(session=db, tenant_id=tenant_id)
    briefing = await generator.generate_briefing(
        style=style,
        lookback_days=period_days,
        include_recommendations=include_recommendations,
    )
    return briefing.to_dict()


@router.post("/executive/briefing/escalation")
async def generate_risk_escalation_briefing(
    lookback_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Generate an AI-powered risk escalation briefing for urgent situations.

    Focuses on:
    - Anomaly spike analysis
    - Root cause identification
    - Impact assessment
    - Recommended actions
    """
    from app.domains.analytics.briefing_service import ExecutiveBriefingGenerator

    generator = ExecutiveBriefingGenerator(session=db, tenant_id=tenant_id)
    briefing = await generator.generate_risk_escalation(
        lookback_days=max(1, lookback_hours // 24),
    )
    return briefing.to_dict()
