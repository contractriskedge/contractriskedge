"""Freshness tracking for benchmark corpus segments.

Tracks the age of data in each benchmark segment and classifies
freshness as green (<30 days), amber (30-90 days), or red (>90 days).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .models import BenchmarkSegment

logger = logging.getLogger(__name__)

# Freshness thresholds in days
GREEN_THRESHOLD_DAYS = 30
AMBER_THRESHOLD_DAYS = 90


class FreshnessStatus(str, Enum):
    """Freshness status for a benchmark segment."""

    GREEN = "green"      # < 30 days
    AMBER = "amber"      # 30-90 days
    RED = "red"          # > 90 days

    def __str__(self) -> str:
        return self.value


@dataclass
class SegmentFreshness:
    """Freshness information for a single benchmark segment."""

    segment_key: str
    clause_type: str
    days_since_update: int
    status: FreshnessStatus
    last_updated: Optional[datetime]
    clause_count: int
    segment_description: str = ""


class FreshnessTracker:
    """Tracks the freshness of benchmark corpus segments.

    Monitors when each segment was last updated and classifies
    freshness as green (<30 days), amber (30-90 days), or red (>90 days).

    Usage:
        tracker = FreshnessTracker()
        tracker.update_segment("liability_caps::technology", datetime.utcnow())
        status = tracker.get_status("liability_caps::technology")
        all_statuses = tracker.get_all_statuses()
    """

    def __init__(self) -> None:
        """Initialize the freshness tracker."""
        self._segment_freshness: Dict[str, SegmentFreshness] = {}

    def update_segment(
        self,
        segment_key: str,
        clause_type: str,
        last_updated: datetime,
        clause_count: int = 0,
        segment_description: str = "",
    ) -> SegmentFreshness:
        """Update the freshness timestamp for a segment.

        Args:
            segment_key: Unique key for the segment.
            clause_type: The clause type for this segment.
            last_updated: When the segment was last updated.
            clause_count: Number of clauses in the segment.
            segment_description: Human-readable description.

        Returns:
            The updated SegmentFreshness.
        """
        days_since = (datetime.utcnow() - last_updated).days
        status = self._classify_freshness(days_since)

        freshness = SegmentFreshness(
            segment_key=segment_key,
            clause_type=clause_type,
            days_since_update=days_since,
            status=status,
            last_updated=last_updated,
            clause_count=clause_count,
            segment_description=segment_description,
        )

        self._segment_freshness[segment_key] = freshness
        return freshness

    def get_status(self, segment_key: str) -> Optional[SegmentFreshness]:
        """Get the freshness status for a segment.

        Args:
            segment_key: The segment key.

        Returns:
            SegmentFreshness or None if not tracked.
        """
        freshness = self._segment_freshness.get(segment_key)
        if freshness is None:
            return None

        # Recalculate days since and status
        if freshness.last_updated:
            days_since = (datetime.utcnow() - freshness.last_updated).days
            freshness.days_since_update = days_since
            freshness.status = self._classify_freshness(days_since)

        return freshness

    def get_all_statuses(self) -> Dict[str, SegmentFreshness]:
        """Get freshness status for all tracked segments.

        Returns:
            Dict mapping segment keys to SegmentFreshness.
        """
        # Refresh all statuses
        for key, freshness in self._segment_freshness.items():
            if freshness.last_updated:
                days_since = (datetime.utcnow() - freshness.last_updated).days
                freshness.days_since_update = days_since
                freshness.status = self._classify_freshness(days_since)

        return dict(self._segment_freshness)

    def get_segments_by_status(
        self, status: FreshnessStatus
    ) -> List[SegmentFreshness]:
        """Get all segments with a given freshness status.

        Args:
            status: The status to filter by.

        Returns:
            List of matching SegmentFreshness objects.
        """
        return [
            f for f in self.get_all_statuses().values()
            if f.status == status
        ]

    def get_stale_segments(self) -> List[SegmentFreshness]:
        """Get all segments that are stale (amber or red).

        Returns:
            List of stale SegmentFreshness objects.
        """
        return [
            f for f in self.get_all_statuses().values()
            if f.status in (FreshnessStatus.AMBER, FreshnessStatus.RED)
        ]

    def get_expired_segments(self) -> List[SegmentFreshness]:
        """Get all segments that are expired (red, > 90 days).

        Returns:
            List of expired SegmentFreshness objects.
        """
        return self.get_segments_by_status(FreshnessStatus.RED)

    def get_freshness_summary(self) -> Dict[str, Any]:
        """Get a summary of overall corpus freshness.

        Returns:
            Dict with freshness statistics.
        """
        all_statuses = self.get_all_statuses()
        total = len(all_statuses)

        green_count = len(self.get_segments_by_status(FreshnessStatus.GREEN))
        amber_count = len(self.get_segments_by_status(FreshnessStatus.AMBER))
        red_count = len(self.get_segments_by_status(FreshnessStatus.RED))

        return {
            "total_segments": total,
            "green": green_count,
            "amber": amber_count,
            "red": red_count,
            "freshness_score": round(
                (green_count + amber_count * 0.5) / max(1, total), 4
            ),
            "stale_segments": [
                {
                    "segment_key": f.segment_key,
                    "clause_type": f.clause_type,
                    "days_since_update": f.days_since_update,
                    "status": f.status.value,
                }
                for f in self.get_stale_segments()
            ],
        }

    @staticmethod
    def _classify_freshness(days_since_update: int) -> FreshnessStatus:
        """Classify freshness based on days since last update.

        Args:
            days_since_update: Number of days since last update.

        Returns:
            FreshnessStatus classification.
        """
        if days_since_update < GREEN_THRESHOLD_DAYS:
            return FreshnessStatus.GREEN
        elif days_since_update < AMBER_THRESHOLD_DAYS:
            return FreshnessStatus.AMBER
        else:
            return FreshnessStatus.RED

    def remove_segment(self, segment_key: str) -> bool:
        """Remove a segment from freshness tracking.

        Args:
            segment_key: The segment key to remove.

        Returns:
            True if removed, False if not found.
        """
        return self._segment_freshness.pop(segment_key, None) is not None
