"""ROI Measurement Engine — tracks and quantifies enterprise value from platform adoption.

Executives buy ROI, not architecture. This layer becomes critical for sales.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ROIMetric:
    """A single ROI metric with baseline and current values."""
    name: str
    display_name: str
    unit: str  # hours, dollars, percentage, count
    baseline_value: float = 0.0
    current_value: float = 0.0
    improvement: float = 0.0
    improvement_pct: float = 0.0
    estimated_annual_savings: float = 0.0
    trend: str = "stable"  # improving, stable, declining


@dataclass
class ROIReport:
    """A complete ROI measurement report."""
    title: str
    summary: str
    total_annual_savings: float = 0.0
    roi_metrics: list[ROIMetric] = field(default_factory=list)
    payback_period_months: float = 0.0
    confidence_score: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ROIMeasurementEngine:
    """Measures and tracks enterprise ROI from platform adoption.

    Tracks:
    - Review time reduction (hours saved per review)
    - Negotiation acceleration (days reduced)
    - SLA improvement (breach rate reduction)
    - Reviewer efficiency gains (reviews per reviewer per day)
    - False-positive reduction (AI accuracy improvement)
    - Contract cycle reduction (time from upload to completion)
    - Avoided risk exposure (dollars of risk mitigated)
    - Renewal optimization (value captured from better terms)
    """

    _baselines: dict[str, float] = field(default_factory=dict)
    _current: dict[str, float] = field(default_factory=dict)
    _cost_assumptions: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self._cost_assumptions = {
            "avg_reviewer_hourly_cost": 150.0,
            "avg_legal_hourly_cost": 350.0,
            "avg_contract_value": 50000.0,
            "avg_breach_cost": 100000.0,
            "avg_negotiation_cycle_cost": 5000.0,
        }

    def set_baseline(self, metric: str, value: float) -> None:
        """Set a baseline (pre-platform) value for a metric."""
        self._baselines[metric] = value

    def set_current(self, metric: str, value: float) -> None:
        """Set the current (post-platform) value for a metric."""
        self._current[metric] = value

    def set_cost_assumption(self, key: str, value: float) -> None:
        """Override a cost assumption."""
        self._cost_assumptions[key] = value

    def measure_review_time_reduction(self, baseline_hours: float, current_hours: float, reviews_per_year: int) -> ROIMetric:
        """Measure time saved per review."""
        hours_saved = baseline_hours - current_hours
        annual_savings = hours_saved * reviews_per_year * self._cost_assumptions["avg_reviewer_hourly_cost"]
        return ROIMetric(
            name="review_time",
            display_name="Review Time Reduction",
            unit="hours",
            baseline_value=baseline_hours,
            current_value=current_hours,
            improvement=hours_saved,
            improvement_pct=round(hours_saved / baseline_hours * 100, 1) if baseline_hours > 0 else 0,
            estimated_annual_savings=annual_savings,
            trend="improving" if hours_saved > 0 else "declining",
        )

    def measure_negotiation_acceleration(self, baseline_days: float, current_days: float, negotiations_per_year: int) -> ROIMetric:
        """Measure days saved per negotiation cycle."""
        days_saved = baseline_days - current_days
        annual_savings = days_saved * negotiations_per_year * (self._cost_assumptions["avg_negotiation_cycle_cost"] / 30)
        return ROIMetric(
            name="negotiation_cycle",
            display_name="Negotiation Acceleration",
            unit="days",
            baseline_value=baseline_days,
            current_value=current_days,
            improvement=days_saved,
            improvement_pct=round(days_saved / baseline_days * 100, 1) if baseline_days > 0 else 0,
            estimated_annual_savings=annual_savings,
            trend="improving" if days_saved > 0 else "declining",
        )

    def measure_sla_improvement(self, baseline_breach_rate: float, current_breach_rate: float, workflows_per_year: int) -> ROIMetric:
        """Measure SLA breach rate reduction."""
        breach_reduction = baseline_breach_rate - current_breach_rate
        breaches_prevented = breach_reduction * workflows_per_year
        annual_savings = breaches_prevented * self._cost_assumptions["avg_breach_cost"]
        return ROIMetric(
            name="sla_compliance",
            display_name="SLA Improvement",
            unit="%",
            baseline_value=baseline_breach_rate * 100,
            current_value=current_breach_rate * 100,
            improvement=breach_reduction * 100,
            improvement_pct=round(breach_reduction / max(baseline_breach_rate, 0.01) * 100, 1),
            estimated_annual_savings=annual_savings,
            trend="improving" if breach_reduction > 0 else "declining",
        )

    def measure_reviewer_efficiency(self, baseline_reviews_per_day: float, current_reviews_per_day: float, reviewers: int) -> ROIMetric:
        """Measure reviewer productivity gains."""
        gain = current_reviews_per_day - baseline_reviews_per_day
        additional_capacity = gain * reviewers * 250  # working days per year
        annual_savings = additional_capacity * self._cost_assumptions["avg_reviewer_hourly_cost"] * 4  # hours per review
        return ROIMetric(
            name="reviewer_efficiency",
            display_name="Reviewer Efficiency Gain",
            unit="reviews/day",
            baseline_value=baseline_reviews_per_day,
            current_value=current_reviews_per_day,
            improvement=gain,
            improvement_pct=round(gain / max(baseline_reviews_per_day, 0.1) * 100, 1),
            estimated_annual_savings=annual_savings,
            trend="improving" if gain > 0 else "declining",
        )

    def measure_false_positive_reduction(self, baseline_fp_rate: float, current_fp_rate: float, findings_per_year: int) -> ROIMetric:
        """Measure reduction in false-positive AI findings."""
        fp_reduction = baseline_fp_rate - current_fp_rate
        false_positives_prevented = fp_reduction * findings_per_year
        time_saved = false_positives_prevented * 0.25  # 15 min per false positive review
        annual_savings = time_saved * self._cost_assumptions["avg_reviewer_hourly_cost"]
        return ROIMetric(
            name="false_positive_rate",
            display_name="False Positive Reduction",
            unit="%",
            baseline_value=baseline_fp_rate * 100,
            current_value=current_fp_rate * 100,
            improvement=fp_reduction * 100,
            improvement_pct=round(fp_reduction / max(baseline_fp_rate, 0.01) * 100, 1),
            estimated_annual_savings=annual_savings,
            trend="improving" if fp_reduction > 0 else "declining",
        )

    def measure_contract_cycle_reduction(self, baseline_hours: float, current_hours: float, contracts_per_year: int) -> ROIMetric:
        """Measure reduction in end-to-end contract cycle time."""
        hours_saved = baseline_hours - current_hours
        annual_savings = hours_saved * contracts_per_year * self._cost_assumptions["avg_legal_hourly_cost"]
        return ROIMetric(
            name="contract_cycle",
            display_name="Contract Cycle Reduction",
            unit="hours",
            baseline_value=baseline_hours,
            current_value=current_hours,
            improvement=hours_saved,
            improvement_pct=round(hours_saved / baseline_hours * 100, 1) if baseline_hours > 0 else 0,
            estimated_annual_savings=annual_savings,
            trend="improving" if hours_saved > 0 else "declining",
        )

    def generate_full_report(self, annual_contracts: int = 1000) -> ROIReport:
        """Generate a comprehensive ROI report from all tracked metrics."""
        metrics = []
        total_savings = 0.0

        # Review time
        if "review_time_hours" in self._baselines and "review_time_hours" in self._current:
            m = self.measure_review_time_reduction(
                self._baselines["review_time_hours"], self._current["review_time_hours"], annual_contracts
            )
            metrics.append(m)
            total_savings += m.estimated_annual_savings

        # Negotiation cycle
        if "negotiation_days" in self._baselines and "negotiation_days" in self._current:
            m = self.measure_negotiation_acceleration(
                self._baselines["negotiation_days"], self._current["negotiation_days"], annual_contracts // 2
            )
            metrics.append(m)
            total_savings += m.estimated_annual_savings

        # SLA breaches
        if "sla_breach_rate" in self._baselines and "sla_breach_rate" in self._current:
            m = self.measure_sla_improvement(
                self._baselines["sla_breach_rate"], self._current["sla_breach_rate"], annual_contracts
            )
            metrics.append(m)
            total_savings += m.estimated_annual_savings

        # Reviewer efficiency
        if "reviews_per_day" in self._baselines and "reviews_per_day" in self._current:
            m = self.measure_reviewer_efficiency(
                self._baselines["reviews_per_day"], self._current["reviews_per_day"], 10
            )
            metrics.append(m)
            total_savings += m.estimated_annual_savings

        # False positives
        if "fp_rate" in self._baselines and "fp_rate" in self._current:
            m = self.measure_false_positive_reduction(
                self._baselines["fp_rate"], self._current["fp_rate"], annual_contracts * 10
            )
            metrics.append(m)
            total_savings += m.estimated_annual_savings

        # Contract cycle
        if "contract_cycle_hours" in self._baselines and "contract_cycle_hours" in self._current:
            m = self.measure_contract_cycle_reduction(
                self._baselines["contract_cycle_hours"], self._current["contract_cycle_hours"], annual_contracts
            )
            metrics.append(m)
            total_savings += m.estimated_annual_savings

        improving = sum(1 for m in metrics if m.trend == "improving")
        confidence = improving / max(len(metrics), 1)

        return ROIReport(
            title="Enterprise AI Platform — ROI Assessment",
            summary=f"Total estimated annual savings: ${total_savings:,.0f} across {len(metrics)} measured dimensions",
            total_annual_savings=total_savings,
            roi_metrics=metrics,
            payback_period_months=round(12 / max(total_savings / 100000, 0.1), 1),
            confidence_score=round(confidence, 4),
        )


# ── Global singleton ───────────────────────────────────────────────

roi_engine = ROIMeasurementEngine()
