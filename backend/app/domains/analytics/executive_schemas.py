"""Executive Analytics schemas — business-level metrics for enterprise buyers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Executive Dashboard ────────────────────────────────────────────


class ExecutiveDashboard(BaseModel):
    """Top-level executive dashboard — what enterprise buyers see first."""
    portfolio_summary: PortfolioSummary
    cycle_time_analytics: CycleTimeAnalytics
    reviewer_efficiency: ReviewerEfficiency
    sla_risk_overview: SLARiskOverview
    negotiation_trends: NegotiationTrends
    contract_exposure: ContractExposure
    throughput_bottlenecks: ThroughputBottlenecks
    cost_governance: CostGovernance = Field(default_factory=lambda: CostGovernance())
    ai_quality_gate: AIQualityGate = Field(default_factory=lambda: AIQualityGate())
    benchmark_analytics: BenchmarkAnalytics = Field(default_factory=lambda: BenchmarkAnalytics())
    risk_score_trend: list[RiskScoreTrendPoint] = Field(default_factory=list)
    review_volume_trend: list[ReviewVolumeTrendPoint] = Field(default_factory=list)
    exposure_trend: list[ExposureTrendPoint] = Field(default_factory=list)
    throughput_trend: list[ThroughputTrendPoint] = Field(default_factory=list)
    period: str = "last_30_days"
    generated_at: datetime


class PortfolioSummary(BaseModel):
    """High-level portfolio overview."""
    total_contracts: int = 0
    active_reviews: int = 0
    contracts_this_period: int = 0
    avg_risk_score: float = 0.0
    risk_distribution: RiskDistribution
    total_exposure: float = 0.0  # aggregate risk exposure
    critical_contracts: int = 0
    high_risk_vendors: int = 0
    escalation_rate: float = 0.0  # % of reviews escalated
    escalated_reviews: int = 0  # count of distinct reviews escalated
    escalation_trend: list[EscalationTrendPoint] = Field(default_factory=list)


class EscalationTrendPoint(BaseModel):
    """A single data point in escalation trend."""
    period: str
    escalated_count: int = 0
    total_reviews: int = 0
    escalation_rate: float = 0.0


class RiskDistribution(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


# ── Cycle Time ─────────────────────────────────────────────────────


class CycleTimeAnalytics(BaseModel):
    """Contract review cycle time metrics."""
    overall_avg_days: float = 0.0
    median_days: float = 0.0
    p95_days: float = 0.0
    by_stage: list[StageCycleTime] = Field(default_factory=list)
    trend: list[CycleTimeTrendPoint] = Field(default_factory=list)
    comparison_to_benchmark: str = ""  # 'faster', 'at_benchmark', 'slower'


class StageCycleTime(BaseModel):
    """Cycle time for a specific workflow stage."""
    stage: str  # 'ingestion', 'ai_analysis', 'review', 'negotiation', 'approval'
    avg_days: float = 0.0
    median_days: float = 0.0
    p95_days: float = 0.0
    sample_count: int = 0


class CycleTimeTrendPoint(BaseModel):
    """A single data point in cycle time trend."""
    period: str  # e.g., '2024-01', 'Week 3'
    avg_days: float = 0.0
    contract_count: int = 0


# ── Reviewer Efficiency ─────────────────────────────────────────────


class ReviewerEfficiency(BaseModel):
    """Reviewer productivity and efficiency metrics."""
    total_reviewers: int = 0
    active_reviewers: int = 0
    avg_reviews_per_reviewer: float = 0.0
    avg_review_completion_hours: float = 0.0
    reviewer_backlog: int = 0  # total pending across all reviewers
    overloaded_reviewers: int = 0
    reviewer_details: list[ReviewerMetric] = Field(default_factory=list)
    trend: list[EfficiencyTrendPoint] = Field(default_factory=list)


class ReviewerMetric(BaseModel):
    """Metrics for a single reviewer."""
    reviewer_id: str
    reviewer_name: str = ""
    active_reviews: int = 0
    completed_reviews: int = 0
    avg_completion_hours: float = 0.0
    backlog_hours: float = 0.0
    is_overloaded: bool = False
    sla_breach_count: int = 0
    acceptance_rate: float = 0.0  # redline acceptance rate


class EfficiencyTrendPoint(BaseModel):
    """A single data point in reviewer efficiency trend."""
    period: str
    avg_completion_hours: float = 0.0
    reviews_completed: int = 0


# ── SLA Risk ────────────────────────────────────────────────────────


class SLARiskOverview(BaseModel):
    """SLA risk assessment across active reviews."""
    total_active_reviews: int = 0
    on_track: int = 0
    at_risk: int = 0  # >50% SLA consumed
    critical: int = 0  # >80% SLA consumed
    breached: int = 0
    avg_sla_remaining_pct: float = 0.0
    at_risk_reviews: list[SLARiskItem] = Field(default_factory=list)
    breach_prediction: BreachPrediction


class SLARiskItem(BaseModel):
    """A single review at SLA risk."""
    review_id: str
    document_name: str = ""
    assigned_to: str = ""
    status: str = ""
    sla_deadline: Optional[datetime] = None
    sla_remaining_pct: float = 0.0
    risk_level: str = "on_track"  # 'on_track', 'at_risk', 'critical'
    breach_probability: float = 0.0
    days_remaining: float = 0.0


class BreachPrediction(BaseModel):
    """Predicted SLA breaches in the next period."""
    predicted_breaches_next_7d: int = 0
    predicted_breaches_next_30d: int = 0
    high_risk_reviews: list[str] = Field(default_factory=list)
    primary_risk_factors: list[str] = Field(default_factory=list)


# ── Negotiation Trends ──────────────────────────────────────────────


class NegotiationTrends(BaseModel):
    """Trends in contract negotiations."""
    total_redlines_proposed: int = 0
    acceptance_rate: float = 0.0
    avg_rounds_per_clause: float = 0.0
    by_clause_type: list[ClauseNegotiationMetric] = Field(default_factory=list)
    most_contested_clauses: list[str] = Field(default_factory=list)
    trend: list[NegotiationTrendPoint] = Field(default_factory=list)


class ClauseNegotiationMetric(BaseModel):
    """Negotiation metrics for a single clause type."""
    clause_type: str
    proposed: int = 0
    accepted: int = 0
    acceptance_rate: float = 0.0
    avg_rounds: float = 0.0
    avg_risk_reduction: float = 0.0


class NegotiationTrendPoint(BaseModel):
    """A single data point in negotiation trend."""
    period: str
    proposed: int = 0
    accepted: int = 0
    acceptance_rate: float = 0.0


# ── Contract Exposure ──────────────────────────────────────────────


class ContractExposure(BaseModel):
    """Aggregate contract risk exposure."""
    total_exposure_score: float = 0.0
    by_category: list[CategoryExposure] = Field(default_factory=list)
    top_risk_drivers: list[RiskDriver] = Field(default_factory=list)
    exposure_trend: list[ExposureTrendPoint] = Field(default_factory=list)
    concentration_risk: str = ""  # 'diversified', 'concentrated', 'highly_concentrated'
    top_riskiest_contracts: list[RiskiestContract] = Field(default_factory=list)


class CategoryExposure(BaseModel):
    """Risk exposure for a single clause category."""
    category: str
    exposure_score: float = 0.0
    exposure_share_pct: float = 0.0
    contract_count: int = 0
    avg_severity: str = "medium"
    trend: str = "stable"  # 'improving', 'worsening', 'stable'


class RiskDriver(BaseModel):
    """A primary driver of portfolio risk."""
    clause_type: str
    contribution_pct: float = 0.0
    severity: str = ""
    affected_contracts: int = 0
    recommendation: str = ""


class ExposureTrendPoint(BaseModel):
    """A single data point in exposure trend."""
    period: str
    exposure_score: float = 0.0
    contract_count: int = 0


# ── Throughput Bottlenecks ─────────────────────────────────────────


class ThroughputBottlenecks(BaseModel):
    """Identified bottlenecks in the contract review pipeline."""
    bottlenecks: list[Bottleneck] = Field(default_factory=list)
    overall_throughput: float = 0.0  # contracts per day
    queue_depth: int = 0
    avg_wait_time_hours: float = 0.0
    trend: list[ThroughputTrendPoint] = Field(default_factory=list)


class Bottleneck(BaseModel):
    """A detected bottleneck in the workflow."""
    stage: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    queue_depth: int = 0
    avg_wait_time_hours: float = 0.0
    resource_constraint: str = ""  # 'reviewer_capacity', 'ai_capacity', 'approval_backlog'
    recommendation: str = ""
    affected_reviews: int = 0


class ThroughputTrendPoint(BaseModel):
    """A single data point in throughput trend."""
    period: str
    contracts_completed: int = 0
    avg_cycle_time_days: float = 0.0


# ── Cost Governance ────────────────────────────────────────────────


class CostTrendPoint(BaseModel):
    """A single data point in AI cost trend."""
    period: str
    ai_reviews: int = 0
    estimated_cost: float = 0.0


class CostGovernance(BaseModel):
    """AI cost and usage metrics."""
    total_ai_reviews: int = 0
    estimated_ai_cost: float = 0.0
    cost_per_contract: float = 0.0
    monthly_projection: float = 0.0
    trend: list[CostTrendPoint] = Field(default_factory=list)


# ── AI Quality Gate ────────────────────────────────────────────────


class AIQualityGate(BaseModel):
    """AI analysis quality monitoring."""
    success_rate: float = 0.0
    completed_runs: int = 0
    failed_runs: int = 0
    avg_findings: float = 0.0
    avg_processing_seconds: float = 0.0


# ── Exposure Enhancements ──────────────────────────────────────────


class RiskiestContract(BaseModel):
    """A single contract with elevated risk exposure."""
    review_id: str
    document_name: str = ""
    risk_score: float = 0.0
    exposure_score: float = 0.0
    top_finding: str = ""


# ── Benchmark Analytics ────────────────────────────────────────────


class BenchmarkAnalytics(BaseModel):
    """Operational benchmarks comparing current performance against targets."""
    cycle_time_vs_benchmark: str = ""  # 'ahead', 'on_track', 'behind'
    sla_vs_benchmark: str = ""  # 'ahead', 'on_track', 'behind'
    reviewer_efficiency_vs_benchmark: str = ""  # 'ahead', 'on_track', 'behind'
    benchmark_cycle_time_days: float = 0.0
    benchmark_sla_pct: float = 0.0
    benchmark_reviewer_load: int = 0
    # Actual current values for display
    current_cycle_time_days: float = 0.0
    current_sla_pct: float = 0.0
    current_reviewer_load: float = 0.0


# ── Executive Trend Visualizations ─────────────────────────────────


class RiskScoreTrendPoint(BaseModel):
    """A single data point in risk score trend."""
    period: str
    avg_risk_score: float = 0.0
    contract_count: int = 0


class ReviewVolumeTrendPoint(BaseModel):
    """A single data point in review volume trend."""
    period: str
    reviews_created: int = 0
    reviews_completed: int = 0


# ── Report Generation ──────────────────────────────────────────────


class ExecutiveReportRequest(BaseModel):
    """Request to generate an executive report."""
    period_days: int = Field(default=30, ge=7, le=365)
    include_trends: bool = True
    include_recommendations: bool = True
    format: str = "json"  # 'json', 'pdf'


class ExecutiveReport(BaseModel):
    """Generated executive report."""
    report_id: str
    title: str = "Executive Contract Risk Report"
    period_days: int = 30
    generated_at: datetime
    dashboard: ExecutiveDashboard
    key_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    format: str = "json"
