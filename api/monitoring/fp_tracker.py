"""Weekly false positive rate calculation per risk category with alerting.

Tracks false positive rates across risk categories on a weekly basis,
providing alerting when rates exceed configurable thresholds.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .feedback import FeedbackCollector, FeedbackRecord, FeedbackType

logger = logging.getLogger(__name__)


@dataclass
class CategoryFPRate:
    """False positive rate for a single category."""

    category: str
    total_flags: int
    false_positives: int
    fp_rate: float
    weekly_change: Optional[float] = None  # Change from previous week


@dataclass
class FPTrackingReport:
    """Weekly false positive tracking report."""

    week_start: datetime
    week_end: datetime
    overall_fp_rate: float
    total_flags_reviewed: int
    total_false_positives: int
    categories: List[CategoryFPRate]
    alert_categories: List[str]  # Categories exceeding threshold
    alert_threshold: float
    summary: str


class FalsePositiveTracker:
    """Tracks false positive rates per risk category with alerting.

    Calculates weekly false positive rates from user feedback,
    monitors trends, and alerts when FP rates exceed thresholds.

    Usage:
        feedback_collector = FeedbackCollector()
        tracker = FalsePositiveTracker(feedback_collector)
        report = tracker.calculate_weekly_fp_rate()
        if report.alert_categories:
            # Send alert
    """

    def __init__(
        self,
        feedback_collector: FeedbackCollector,
        alert_threshold: float = 0.07,  # 7% default threshold
        history_path: Optional[str] = None,
    ) -> None:
        """Initialize the false positive tracker.

        Args:
            feedback_collector: The feedback collector instance.
            alert_threshold: FP rate threshold for alerts (default 7%).
            history_path: Optional path for history persistence.
        """
        self._feedback = feedback_collector
        self._alert_threshold = alert_threshold
        self._history_path = history_path
        self._weekly_history: List[Dict[str, Any]] = []

        if history_path:
            self._load_history()

    def _load_history(self) -> None:
        """Load weekly history from disk."""
        import os

        if not os.path.exists(self._history_path):
            return

        try:
            with open(self._history_path) as f:
                self._weekly_history = json.load(f)
            logger.info(
                "Loaded %d weekly FP history entries", len(self._weekly_history)
            )
        except Exception as exc:
            logger.warning("Failed to load FP history: %s", exc)

    def _save_history(self) -> None:
        """Save weekly history to disk."""
        if not self._history_path:
            return

        try:
            with open(self._history_path, "w") as f:
                json.dump(self._weekly_history[-52:], f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Failed to save FP history: %s", exc)

    def calculate_weekly_fp_rate(
        self,
        tenant_id: Optional[str] = None,
        weeks_back: int = 1,
    ) -> FPTrackingReport:
        """Calculate false positive rates for the past week.

        Args:
            tenant_id: Optional tenant filter.
            weeks_back: Number of weeks to look back.

        Returns:
            FPTrackingReport with per-category FP rates.
        """
        week_start = datetime.utcnow() - timedelta(weeks=weeks_back)
        week_end = datetime.utcnow()

        # Get all feedback records
        all_records = self._get_feedback_records(tenant_id)

        # Filter to the relevant week
        week_records = [
            r for r in all_records
            if week_start <= r.created_at <= week_end
        ]

        if not week_records:
            return FPTrackingReport(
                week_start=week_start,
                week_end=week_end,
                overall_fp_rate=0.0,
                total_flags_reviewed=0,
                total_false_positives=0,
                categories=[],
                alert_categories=[],
                alert_threshold=self._alert_threshold,
                summary="No feedback data for the specified period.",
            )

        # Group by category
        category_data: Dict[str, Dict[str, int]] = {}
        for record in week_records:
            cat = record.category
            if cat not in category_data:
                category_data[cat] = {"total": 0, "false_positives": 0}

            category_data[cat]["total"] += 1
            if record.feedback_type == FeedbackType.FALSE_POSITIVE:
                category_data[cat]["false_positives"] += 1

        # Get previous week data for comparison
        prev_week_data = self._get_previous_week_data(tenant_id)

        # Compute per-category rates
        categories: list[CategoryFPRate] = []
        total_flags = 0
        total_fp = 0
        alert_categories: list[str] = []

        for cat, data in sorted(category_data.items()):
            total = data["total"]
            fp = data["false_positives"]
            rate = fp / total if total > 0 else 0.0

            # Weekly change
            prev_rate = prev_week_data.get(cat, 0.0)
            weekly_change = rate - prev_rate if prev_week_data else None

            cat_fp = CategoryFPRate(
                category=cat,
                total_flags=total,
                false_positives=fp,
                fp_rate=rate,
                weekly_change=weekly_change,
            )
            categories.append(cat_fp)

            total_flags += total
            total_fp += fp

            if rate > self._alert_threshold:
                alert_categories.append(cat)

        overall_rate = total_fp / total_flags if total_flags > 0 else 0.0

        # Save to history
        history_entry = {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "overall_fp_rate": overall_rate,
            "total_flags": total_flags,
            "total_fp": total_fp,
            "category_rates": {
                c.category: c.fp_rate for c in categories
            },
        }
        self._weekly_history.append(history_entry)
        self._save_history()

        # Generate summary
        if alert_categories:
            summary = (
                f"ALERT: {len(alert_categories)} categories exceed "
                f"{self._alert_threshold:.0%} FP threshold: "
                f"{', '.join(alert_categories)}. "
                f"Overall FP rate: {overall_rate:.2%}"
            )
            logger.warning(summary)
        else:
            summary = (
                f"FP rates within threshold. "
                f"Overall FP rate: {overall_rate:.2%} "
                f"({total_fp}/{total_flags} flags)"
            )
            logger.info(summary)

        return FPTrackingReport(
            week_start=week_start,
            week_end=week_end,
            overall_fp_rate=overall_rate,
            total_flags_reviewed=total_flags,
            total_false_positives=total_fp,
            categories=categories,
            alert_categories=alert_categories,
            alert_threshold=self._alert_threshold,
            summary=summary,
        )

    def _get_feedback_records(
        self, tenant_id: Optional[str]
    ) -> List[FeedbackRecord]:
        """Get feedback records, simulating the collector's method.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            List of feedback records.
        """
        # In production, this would query the database
        # For now, use the collector's in-memory records
        stats = self._feedback.get_feedback_stats(tenant_id)
        # We need to access records - use the collector's internal method
        return self._feedback._get_records(tenant_id)

    def _get_previous_week_data(
        self, tenant_id: Optional[str]
    ) -> Dict[str, float]:
        """Get previous week's FP rates for comparison.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            Dict mapping category to previous FP rate.
        """
        if len(self._weekly_history) < 2:
            return {}

        prev_entry = self._weekly_history[-2]
        return prev_entry.get("category_rates", {})

    def get_fp_trend(
        self, category: str, weeks: int = 12
    ) -> List[Tuple[str, float]]:
        """Get the FP rate trend for a category.

        Args:
            category: Risk category.
            weeks: Number of weeks to look back.

        Returns:
            List of (week_label, fp_rate) tuples.
        """
        trend: list[tuple[str, float]] = []
        for entry in self._weekly_history[-weeks:]:
            week_label = entry.get("week_end", "")[:10]
            rate = entry.get("category_rates", {}).get(category, 0.0)
            trend.append((week_label, rate))
        return trend

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of FP tracking status.

        Returns:
            Dict with tracking statistics.
        """
        if not self._weekly_history:
            return {"status": "no_data"}

        latest = self._weekly_history[-1]
        return {
            "total_weeks_tracked": len(self._weekly_history),
            "latest_week": latest.get("week_end"),
            "latest_overall_fp_rate": latest.get("overall_fp_rate", 0.0),
            "latest_total_reviewed": latest.get("total_flags", 0),
            "alert_threshold": self._alert_threshold,
            "categories_with_alerts": (
                self.calculate_weekly_fp_rate().alert_categories
            ),
        }
