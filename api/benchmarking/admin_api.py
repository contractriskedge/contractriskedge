"""Admin dashboard API for benchmark freshness management.

Provides endpoints for monitoring and managing benchmark corpus
freshness, including segment status, manual refresh triggers,
and alert configuration.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .freshness import FreshnessTracker, FreshnessStatus, SegmentFreshness
from .alerting import StalenessAlerter, AlertResult

logger = logging.getLogger(__name__)


class AdminAPI:
    """Admin API for benchmark freshness management.

    Provides the backend logic for the admin dashboard, including
    freshness monitoring, manual refresh triggers, and alert
    configuration.

    Usage:
        admin = AdminAPI(freshness_tracker, alerter)
        dashboard = admin.get_dashboard_data()
        result = admin.trigger_refresh("liability_caps")
    """

    def __init__(
        self,
        freshness_tracker: FreshnessTracker,
        alerter: Optional[StalenessAlerter] = None,
    ) -> None:
        """Initialize the admin API.

        Args:
            freshness_tracker: The freshness tracker instance.
            alerter: Optional staleness alerter instance.
        """
        self._freshness_tracker = freshness_tracker
        self._alerter = alerter

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for the admin UI.

        Returns:
            Dict with all dashboard data.
        """
        freshness_summary = self._freshness_tracker.get_freshness_summary()
        all_statuses = self._freshness_tracker.get_all_statuses()

        return {
            "freshness_summary": freshness_summary,
            "segments": [
                {
                    "segment_key": key,
                    "clause_type": seg.clause_type,
                    "days_since_update": seg.days_since_update,
                    "status": seg.status.value,
                    "last_updated": seg.last_updated.isoformat() if seg.last_updated else None,
                    "clause_count": seg.clause_count,
                    "description": seg.segment_description,
                }
                for key, seg in all_statuses.items()
            ],
            "alert_config": {
                "webhook_configured": self._alerter.webhook_configured if self._alerter else False,
                "last_alert_time": (
                    self._alerter.last_alert_time.isoformat()
                    if self._alerter and self._alerter.last_alert_time
                    else None
                ),
                "alert_threshold_days": 90,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_segment_detail(
        self, segment_key: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific segment.

        Args:
            segment_key: The segment key.

        Returns:
            Dict with segment details or None.
        """
        freshness = self._freshness_tracker.get_status(segment_key)
        if freshness is None:
            return None

        return {
            "segment_key": freshness.segment_key,
            "clause_type": freshness.clause_type,
            "days_since_update": freshness.days_since_update,
            "status": freshness.status.value,
            "last_updated": freshness.last_updated.isoformat() if freshness.last_updated else None,
            "clause_count": freshness.clause_count,
            "description": freshness.segment_description,
            "actions": {
                "can_refresh": freshness.status != FreshnessStatus.GREEN,
                "can_dismiss_alert": freshness.status == FreshnessStatus.RED,
            },
        }

    def trigger_refresh(
        self,
        segment_key: str,
        initiated_by: str = "admin",
    ) -> Dict[str, Any]:
        """Trigger a manual refresh of a benchmark segment.

        Args:
            segment_key: The segment key to refresh.
            initiated_by: Who initiated the refresh.

        Returns:
            Dict with refresh result.
        """
        freshness = self._freshness_tracker.get_status(segment_key)
        if freshness is None:
            return {
                "success": False,
                "error": f"Segment '{segment_key}' not found",
            }

        # Update the freshness timestamp
        updated = self._freshness_tracker.update_segment(
            segment_key=segment_key,
            clause_type=freshness.clause_type,
            last_updated=datetime.utcnow(),
            clause_count=freshness.clause_count,
            segment_description=freshness.segment_description,
        )

        logger.info(
            "Manual refresh triggered for segment '%s' by %s",
            segment_key, initiated_by,
        )

        return {
            "success": True,
            "segment_key": segment_key,
            "previous_status": freshness.status.value,
            "new_status": updated.status.value,
            "refreshed_at": datetime.utcnow().isoformat(),
            "initiated_by": initiated_by,
        }

    def trigger_all_refresh(
        self, initiated_by: str = "admin"
    ) -> Dict[str, Any]:
        """Trigger a refresh of all stale segments.

        Args:
            initiated_by: Who initiated the refresh.

        Returns:
            Dict with refresh results.
        """
        stale = self._freshness_tracker.get_stale_segments()
        results = []

        for segment in stale:
            result = self.trigger_refresh(segment.segment_key, initiated_by)
            results.append(result)

        return {
            "success": True,
            "segments_refreshed": len(results),
            "results": results,
            "initiated_by": initiated_by,
            "refreshed_at": datetime.utcnow().isoformat(),
        }

    def send_alert_now(self) -> Optional[AlertResult]:
        """Manually trigger a staleness alert.

        Returns:
            AlertResult or None if no alerter configured.
        """
        if self._alerter is None:
            logger.warning("No alerter configured — cannot send alert")
            return None

        return self._alerter.check_and_alert()

    def send_test_alert(self) -> Optional[AlertResult]:
        """Send a test alert to verify configuration.

        Returns:
            AlertResult or None if no alerter configured.
        """
        if self._alerter is None:
            logger.warning("No alerter configured — cannot send test alert")
            return None

        return self._alerter.send_test_alert()

    def update_segment_freshness(
        self,
        segment_key: str,
        clause_type: str,
        last_updated: datetime,
        clause_count: int = 0,
        description: str = "",
    ) -> SegmentFreshness:
        """Update or create a segment's freshness record.

        Args:
            segment_key: The segment key.
            clause_type: The clause type.
            last_updated: When the segment was last updated.
            clause_count: Number of clauses.
            description: Segment description.

        Returns:
            The updated SegmentFreshness.
        """
        return self._freshness_tracker.update_segment(
            segment_key=segment_key,
            clause_type=clause_type,
            last_updated=last_updated,
            clause_count=clause_count,
            segment_description=description,
        )

    def remove_segment(self, segment_key: str) -> bool:
        """Remove a segment from freshness tracking.

        Args:
            segment_key: The segment key to remove.

        Returns:
            True if removed.
        """
        return self._freshness_tracker.remove_segment(segment_key)
