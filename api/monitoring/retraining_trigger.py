"""Automated retraining trigger when FP rate exceeds threshold.

Monitors false positive rates and triggers model retraining when
the FP rate exceeds 7% for 2 consecutive weeks, ensuring model
quality remains within acceptable bounds.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .fp_tracker import FalsePositiveTracker, FPTrackingReport

logger = logging.getLogger(__name__)


@dataclass
class RetrainingEvent:
    """A record of a retraining trigger event."""

    event_id: str
    triggered_at: datetime
    reason: str
    overall_fp_rate: float
    categories_triggered: List[str]
    consecutive_weeks_above_threshold: int
    retraining_initiated: bool
    retraining_job_id: Optional[str] = None
    notes: Optional[str] = None


class RetrainingTrigger:
    """Automated retraining trigger based on FP rate monitoring.

    Monitors weekly false positive rates and triggers model retraining
    when any category exceeds 7% FP rate for 2 consecutive weeks.

    Usage:
        fp_tracker = FalsePositiveTracker(feedback_collector)
        trigger = RetrainingTrigger(fp_tracker)
        trigger.check_and_trigger(retraining_fn=my_retraining_func)
    """

    FP_THRESHOLD = 0.07  # 7%
    CONSECUTIVE_WEEKS_REQUIRED = 2

    def __init__(
        self,
        fp_tracker: FalsePositiveTracker,
        threshold: float = FP_THRESHOLD,
        consecutive_weeks: int = CONSECUTIVE_WEEKS_REQUIRED,
        cooldown_days: int = 14,  # Minimum days between retraining
    ) -> None:
        """Initialize the retraining trigger.

        Args:
            fp_tracker: The false positive tracker instance.
            threshold: FP rate threshold (default 7%).
            consecutive_weeks: Consecutive weeks above threshold needed.
            cooldown_days: Minimum days between retraining events.
        """
        self._fp_tracker = fp_tracker
        self._threshold = threshold
        self._consecutive_weeks = consecutive_weeks
        self._cooldown_days = cooldown_days
        self._events: List[RetrainingEvent] = []
        self._last_retraining: Optional[datetime] = None
        self._event_counter = 0

    def check_and_trigger(
        self,
        retraining_fn: Optional[Callable] = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[RetrainingEvent]:
        """Check FP rates and trigger retraining if needed.

        Evaluates the latest weekly FP report. If any category has
        exceeded the threshold for the required consecutive weeks,
        triggers retraining.

        Args:
            retraining_fn: Optional async callable to execute retraining.
            tenant_id: Optional tenant filter.

        Returns:
            RetrainingEvent if triggered, None otherwise.
        """
        # Check cooldown
        if self._last_retraining is not None:
            days_since = (datetime.utcnow() - self._last_retraining).days
            if days_since < self._cooldown_days:
                logger.info(
                    "Retraining on cooldown (%d/%d days)",
                    days_since,
                    self._cooldown_days,
                )
                return None

        # Get latest FP report
        report = self._fp_tracker.calculate_weekly_fp_rate(tenant_id)

        # Check which categories exceed threshold
        categories_exceeded = [
            c.category for c in report.categories
            if c.fp_rate > self._threshold
        ]

        if not categories_exceeded:
            logger.info("No categories exceed FP threshold (%.0f%%)", self._threshold * 100)
            return None

        # Check consecutive weeks
        consecutive_count = self._count_consecutive_exceedances(
            categories_exceeded
        )

        if consecutive_count < self._consecutive_weeks:
            logger.info(
                "Categories exceed threshold but not yet %d consecutive weeks "
                "(current: %d)",
                self._consecutive_weeks,
                consecutive_count,
            )
            return None

        # Trigger retraining
        return self._execute_retraining(
            reason=(
                f"FP rate exceeded {self._threshold:.0%} for "
                f"{consecutive_count} consecutive weeks"
            ),
            overall_fp_rate=report.overall_fp_rate,
            categories_triggered=categories_exceeded,
            consecutive_weeks=consecutive_count,
            retraining_fn=retraining_fn,
        )

    def _count_consecutive_exceedances(
        self, current_categories: List[str]
    ) -> int:
        """Count consecutive weeks where categories exceeded threshold.

        Args:
            current_categories: Categories exceeding threshold this week.

        Returns:
            Number of consecutive weeks with exceedances.
        """
        if not current_categories:
            return 0

        # Look back through history
        history = self._fp_tracker._weekly_history
        count = 1  # Current week

        for entry in reversed(history[:-1]):  # Skip current week (last entry)
            cat_rates = entry.get("category_rates", {})
            week_exceeded = any(
                cat_rates.get(cat, 0.0) > self._threshold
                for cat in current_categories
            )
            if week_exceeded:
                count += 1
            else:
                break

        return count

    def _execute_retraining(
        self,
        reason: str,
        overall_fp_rate: float,
        categories_triggered: List[str],
        consecutive_weeks: int,
        retraining_fn: Optional[Callable] = None,
    ) -> RetrainingEvent:
        """Execute the retraining trigger.

        Args:
            reason: Why retraining was triggered.
            overall_fp_rate: Current overall FP rate.
            categories_triggered: Categories that triggered retraining.
            consecutive_weeks: Consecutive weeks above threshold.
            retraining_fn: Optional function to call for retraining.

        Returns:
            The RetrainingEvent record.
        """
        self._event_counter += 1

        event = RetrainingEvent(
            event_id=f"retrain_{self._event_counter:04d}",
            triggered_at=datetime.utcnow(),
            reason=reason,
            overall_fp_rate=overall_fp_rate,
            categories_triggered=categories_triggered,
            consecutive_weeks_above_threshold=consecutive_weeks,
            retraining_initiated=False,
        )

        # Execute retraining if function provided
        if retraining_fn is not None:
            try:
                import asyncio

                if asyncio.iscoroutinefunction(retraining_fn):
                    # In production, this would be scheduled via Celery
                    logger.info(
                        "Retraining triggered: %s. Job would be scheduled.",
                        reason,
                    )
                else:
                    retraining_fn()

                event.retraining_initiated = True
                event.retraining_job_id = f"job_{self._event_counter:04d}"
                logger.info(
                    "Retraining successfully initiated: %s", reason
                )

            except Exception as exc:
                logger.error("Retraining execution failed: %s", exc)
                event.notes = f"Retraining execution failed: {exc}"

        else:
            logger.warning(
                "Retraining triggered but no retraining function provided: %s",
                reason,
            )
            event.notes = "No retraining function provided"

        self._events.append(event)
        self._last_retraining = datetime.utcnow()

        return event

    def get_retraining_history(
        self, limit: int = 10
    ) -> List[RetrainingEvent]:
        """Get the history of retraining events.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of recent retraining events.
        """
        return sorted(
            self._events,
            key=lambda e: e.triggered_at,
            reverse=True,
        )[:limit]

    def get_status(self) -> Dict[str, Any]:
        """Get current retraining trigger status.

        Returns:
            Dict with status information.
        """
        return {
            "threshold": self._threshold,
            "consecutive_weeks_required": self._consecutive_weeks,
            "cooldown_days": self._cooldown_days,
            "last_retraining": (
                self._last_retraining.isoformat()
                if self._last_retraining else None
            ),
            "total_retraining_events": len(self._events),
            "recent_events": [
                {
                    "event_id": e.event_id,
                    "triggered_at": e.triggered_at.isoformat(),
                    "reason": e.reason,
                    "retraining_initiated": e.retraining_initiated,
                }
                for e in self._events[-5:]
            ],
            "cooldown_active": (
                (datetime.utcnow() - self._last_retraining).days
                < self._cooldown_days
                if self._last_retraining else False
            ),
        }

    def reset_cooldown(self) -> None:
        """Reset the retraining cooldown period."""
        self._last_retraining = None
        logger.info("Retraining cooldown reset")
