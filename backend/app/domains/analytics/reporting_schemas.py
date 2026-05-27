"""Executive Reporting Automation schemas — scheduled reports, anomaly summaries, trend narratives, digests."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────


class ReportFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ReportDay(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class DigestStyle(str, Enum):
    BRIEF = "brief"           # Key metrics only
    STANDARD = "standard"     # Metrics + key findings
    DETAILED = "detailed"     # Full report with all sections


class AnomalySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AnomalyCategory(str, Enum):
    SLA = "sla"
    VOLUME = "volume"
    RISK = "risk"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    COST = "cost"
    WORKLOAD = "workload"


# ── Scheduled Reports ───────────────────────────────────────────────


class ScheduledReportCreate(BaseModel):
    """Create a scheduled executive report."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    frequency: ReportFrequency
    day_of_week: Optional[ReportDay] = None  # required for weekly/biweekly
    day_of_month: Optional[int] = Field(None, ge=1, le=28)  # required for monthly
    time_of_day: str = "08:00"  # HH:MM in UTC
    digest_style: DigestStyle = DigestStyle.STANDARD
    period_days: int = Field(default=30, ge=7, le=365)
    recipients: list[str] = Field(default_factory=list)
    include_trends: bool = True
    include_recommendations: bool = True
    is_active: bool = True
    channels: list[str] = Field(default_factory=lambda: ["in_app"])


class ScheduledReportUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[ReportFrequency] = None
    day_of_week: Optional[ReportDay] = None
    day_of_month: Optional[int] = None
    time_of_day: Optional[str] = None
    digest_style: Optional[DigestStyle] = None
    period_days: Optional[int] = None
    recipients: Optional[list[str]] = None
    include_trends: Optional[bool] = None
    include_recommendations: Optional[bool] = None
    is_active: Optional[bool] = None
    channels: Optional[list[str]] = None


class ScheduledReportResponse(BaseModel):
    """A scheduled executive report configuration."""
    report_id: str
    name: str
    description: Optional[str] = None
    frequency: ReportFrequency
    day_of_week: Optional[ReportDay] = None
    day_of_month: Optional[int] = None
    time_of_day: str = "08:00"
    digest_style: DigestStyle = DigestStyle.STANDARD
    period_days: int = 30
    recipients: list[str] = Field(default_factory=list)
    include_trends: bool = True
    include_recommendations: bool = True
    is_active: bool = True
    channels: list[str] = Field(default_factory=list)
    last_generated_at: Optional[datetime] = None
    next_scheduled_at: Optional[datetime] = None
    total_generations: int = 0
    created_by: str = ""
    created_at: datetime
    updated_at: datetime


class ReportGenerationRecord(BaseModel):
    """Record of a report generation."""
    generation_id: str = ""
    report_id: str
    status: str = "completed"  # 'pending', 'running', 'completed', 'failed'
    generated_at: datetime
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    key_findings_count: int = 0
    recommendations_count: int = 0
    error_message: Optional[str] = None
    delivered_to: list[str] = Field(default_factory=list)


# ── Anomaly Summaries ───────────────────────────────────────────────


class AnomalyDetectionResult(BaseModel):
    """Result of anomaly detection across tenant metrics."""
    anomalies: list[AnomalyItem] = Field(default_factory=list)
    total_anomalies: int = 0
    critical_count: int = 0
    high_count: int = 0
    period: str = "last_24h"
    generated_at: datetime


class AnomalyItem(BaseModel):
    """A single detected anomaly."""
    anomaly_id: str = ""
    category: AnomalyCategory
    severity: AnomalySeverity
    title: str
    description: str = ""
    metric_name: str = ""
    current_value: float = 0.0
    expected_value: float = 0.0
    deviation_pct: float = 0.0
    trend_direction: str = ""  # 'increasing', 'decreasing', 'spike', 'drop'
    affected_area: str = ""
    recommendation: Optional[str] = None
    detected_at: datetime


# ── Trend Narratives ────────────────────────────────────────────────


class TrendNarrative(BaseModel):
    """A natural-language narrative describing a trend."""
    narrative_id: str = ""
    title: str
    summary: str
    metric: str
    direction: str  # 'improving', 'worsening', 'stable', 'volatile'
    change_pct: float = 0.0
    period: str = ""
    supporting_data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class TrendNarrativeSet(BaseModel):
    """Collection of trend narratives for an executive digest."""
    narratives: list[TrendNarrative] = Field(default_factory=list)
    total_narratives: int = 0
    positive_trends: int = 0
    negative_trends: int = 0
    period: str = "last_30_days"


# ── Executive Digest ────────────────────────────────────────────────


class ExecutiveDigest(BaseModel):
    """A concise executive digest — the daily/weekly briefing."""
    digest_id: str = ""
    title: str = "Executive Briefing"
    style: DigestStyle = DigestStyle.STANDARD
    generated_at: datetime
    period: str = ""
    portfolio_snapshot: PortfolioSnapshot
    key_metrics: KeyMetricsSummary
    anomalies: list[AnomalyItem] = Field(default_factory=list)
    narratives: list[TrendNarrative] = Field(default_factory=list)
    top_recommendations: list[str] = Field(default_factory=list)
    critical_alerts: list[str] = Field(default_factory=list)
    full_report_available: bool = False


class PortfolioSnapshot(BaseModel):
    """Quick portfolio snapshot for the digest."""
    total_contracts: int = 0
    active_reviews: int = 0
    critical_contracts: int = 0
    avg_risk_score: float = 0.0
    sla_breaches: int = 0
    at_risk_count: int = 0
    new_contracts_today: int = 0
    completed_reviews_today: int = 0


class KeyMetricsSummary(BaseModel):
    """Key metrics for the executive digest."""
    cycle_time_avg_days: float = 0.0
    reviewer_throughput: float = 0.0  # reviews completed per reviewer per week
    ai_accuracy: float = 0.0
    negotiation_success_rate: float = 0.0
    portfolio_exposure: float = 0.0
    cost_per_review: float = 0.0
    sla_compliance_rate: float = 0.0
