"""Regression detection for risk analysis accuracy.

Monitors evaluation metrics week-over-week and alerts if any category's
F1 score drops by more than 0.02, enabling rapid response to
performance degradation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .metrics import EvaluationMetrics

logger = logging.getLogger(__name__)


@dataclass
class RegressionAlert:
    """An alert triggered by detected regression."""

    category: str
    metric: str
    previous_value: float
    current_value: float
    delta: float
    threshold: float
    severity: str  # warning, critical
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recommendation: str = ""


@dataclass
class RegressionReport:
    """Weekly regression analysis report."""

    week_start: datetime
    week_end: datetime
    total_categories: int
    categories_regressed: int
    alerts: List[RegressionAlert]
    overall_status: str  # healthy, warning, critical
    summary: str


class RegressionDetector:
    """Detects regression in risk analysis accuracy metrics.

    Monitors weekly evaluation results and alerts when any category's
    F1 score drops more than 0.02 week-over-week. Maintains history
    of past evaluations for comparison.

    Usage:
        detector = RegressionDetector(history_path="./evaluation_history")
        detector.record_evaluation(metrics)
        report = detector.check_for_regression()
        if report.categories_regressed > 0:
            # Trigger alert
    """

    F1_THRESHOLD = 0.02  # Alert if F1 drops more than 0.02
    SEVERITY_MAE_THRESHOLD = 0.5  # Alert if MAE increases more than 0.5

    def __init__(
        self,
        history_path: str = "./evaluation_history",
        lookback_weeks: int = 12,
    ) -> None:
        """Initialize the regression detector.

        Args:
            history_path: Path to store evaluation history.
            lookback_weeks: Number of weeks of history to retain.
        """
        self._history_path = history_path
        self._lookback_weeks = lookback_weeks
        self._history: List[Dict[str, Any]] = []

        import os
        os.makedirs(history_path, exist_ok=True)
        self._load_history()

    def _load_history(self) -> None:
        """Load evaluation history from disk."""
        import os
        import glob

        pattern = os.path.join(self._history_path, "eval_*.json")
        for filepath in sorted(glob.glob(pattern)):
            try:
                with open(filepath) as f:
                    entry = json.load(f)
                self._history.append(entry)
            except Exception as exc:
                logger.warning("Failed to load history entry %s: %s", filepath, exc)

        # Keep only recent history
        if len(self._history) > self._lookback_weeks:
            self._history = self._history[-self._lookback_weeks:]

        logger.info("Loaded %d evaluation history entries", len(self._history))

    def record_evaluation(
        self,
        metrics: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an evaluation result for future comparison.

        Args:
            metrics: The evaluation metrics to record (Metrics object or dict).
            metadata: Optional metadata (e.g., model version).

        Returns:
            Path to saved history entry.
        """
        import os

        # Handle both Metrics objects and dicts
        if hasattr(metrics, 'to_dict'):
            metrics_dict = metrics.to_dict()
        else:
            metrics_dict = metrics

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "week_start": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "week_end": datetime.utcnow().isoformat(),
            "metrics": metrics_dict,
            "metadata": metadata or {},
        }

        filename = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(self._history_path, filename)

        with open(path, "w") as f:
            json.dump(entry, f, indent=2, default=str)

        self._history.append(entry)

        # Prune old history
        if len(self._history) > self._lookback_weeks:
            old_entry = self._history.pop(0)
            old_path = os.path.join(
                self._history_path,
                f"eval_{old_entry['timestamp'][:10]}.json",
            )
            try:
                os.remove(old_path)
            except OSError:
                pass

        logger.info("Recorded evaluation in history (%d entries)", len(self._history))
        return path

    def check_for_regression(
        self,
        current_metrics: EvaluationMetrics,
    ) -> RegressionReport:
        """Check current metrics against previous evaluation.

        Compares each category's F1 score and overall metrics against
        the most recent evaluation in history.

        Args:
            current_metrics: Current evaluation metrics.

        Returns:
            RegressionReport with alerts and status.
        """
        alerts: list[RegressionAlert] = []

        if not self._history:
            return RegressionReport(
                week_start=datetime.utcnow() - timedelta(days=7),
                week_end=datetime.utcnow(),
                total_categories=len(current_metrics.category_metrics),
                categories_regressed=0,
                alerts=[],
                overall_status="healthy",
                summary="No previous evaluation data for comparison.",
            )

        # Get previous metrics
        previous = self._history[-1]
        prev_metrics = previous.get("metrics", {})

        # Check per-category F1 regression
        categories_regressed = 0
        for cat, current_cat_metrics in current_metrics.category_metrics.items():
            prev_cat_metrics = prev_metrics.get("category_metrics", {}).get(cat, {})

            current_f1 = current_cat_metrics.f1_score
            prev_f1 = prev_cat_metrics.get("f1_score", 1.0)

            if prev_f1 > 0 and (prev_f1 - current_f1) > self.F1_THRESHOLD:
                delta = current_f1 - prev_f1
                categories_regressed += 1

                severity = "critical" if abs(delta) > 2 * self.F1_THRESHOLD else "warning"

                alerts.append(RegressionAlert(
                    category=cat,
                    metric="f1_score",
                    previous_value=prev_f1,
                    current_value=current_f1,
                    delta=round(delta, 4),
                    threshold=self.F1_THRESHOLD,
                    severity=severity,
                    recommendation=(
                        f"F1 score for '{cat}' dropped by {abs(delta):.4f}. "
                        f"Review recent changes to the model or prompt chain "
                        f"that may have affected this category."
                    ),
                ))

        # Check overall severity MAE regression
        current_mae = current_metrics.severity_mae
        prev_mae = prev_metrics.get("severity_mae", 0.0)

        if prev_mae > 0 and (current_mae - prev_mae) > self.SEVERITY_MAE_THRESHOLD:
            alerts.append(RegressionAlert(
                category="overall",
                metric="severity_mae",
                previous_value=prev_mae,
                current_value=current_mae,
                delta=round(current_mae - prev_mae, 4),
                threshold=self.SEVERITY_MAE_THRESHOLD,
                severity="warning",
                recommendation=(
                    f"Severity MAE increased from {prev_mae:.4f} to {current_mae:.4f}. "
                    f"Review severity scoring calibration."
                ),
            ))

        # Determine overall status
        critical_alerts = sum(1 for a in alerts if a.severity == "critical")
        warning_alerts = sum(1 for a in alerts if a.severity == "warning")

        if critical_alerts > 0:
            overall_status = "critical"
            summary = (
                f"Critical regression detected in {critical_alerts} categories. "
                f"Immediate investigation required."
            )
        elif warning_alerts > 0:
            overall_status = "warning"
            summary = (
                f"Regression warning in {warning_alerts} categories. "
                f"Monitor closely in next evaluation."
            )
        else:
            overall_status = "healthy"
            summary = "No significant regression detected. Performance is stable."

        return RegressionReport(
            week_start=datetime.utcnow() - timedelta(days=7),
            week_end=datetime.utcnow(),
            total_categories=len(current_metrics.category_metrics),
            categories_regressed=categories_regressed,
            alerts=alerts,
            overall_status=overall_status,
            summary=summary,
        )

    def get_trend(self, category: str, metric: str = "f1_score") -> List[Tuple[str, float]]:
        """Get the trend of a metric over time.

        Args:
            category: Risk category.
            metric: Metric name (e.g., 'f1_score', 'precision').

        Returns:
            List of (date, value) tuples in chronological order.
        """
        trend: list[tuple[str, float]] = []

        for entry in self._history:
            cat_metrics = (
                entry.get("metrics", {})
                .get("category_metrics", {})
                .get(category, {})
            )
            value = cat_metrics.get(metric, 0.0)
            date = entry.get("week_end", entry.get("timestamp", ""))

            trend.append((date, value))

        return trend

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of regression detection status.

        Returns:
            Dict with history stats and recent alerts.
        """
        return {
            "history_entries": len(self._history),
            "lookback_weeks": self._lookback_weeks,
            "last_evaluation": (
                self._history[-1]["timestamp"] if self._history else None
            ),
            "categories_monitored": (
                list(
                    self._history[-1]
                    .get("metrics", {})
                    .get("category_metrics", {})
                    .keys()
                )
                if self._history else []
            ),
        }
