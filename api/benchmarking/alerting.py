"""Automated Slack alert for stale benchmark segments.

Monitors benchmark segment freshness and sends automated Slack alerts
when any segment exceeds the 90-day staleness threshold.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from .freshness import FreshnessTracker, FreshnessStatus, SegmentFreshness

logger = logging.getLogger(__name__)


@dataclass
class AlertResult:
    """Result of an alert operation."""

    success: bool
    alerts_sent: int
    stale_segments: List[SegmentFreshness]
    error: Optional[str] = None
    sent_at: Optional[datetime] = None


class StalenessAlerter:
    """Automated alerting for stale benchmark segments.

    Checks segment freshness and sends Slack alerts when any segment
    exceeds the 90-day staleness threshold. Supports configurable
    webhook URLs and alert frequency.

    Usage:
        alerter = StalenessAlerter(
            webhook_url="https://hooks.slack.com/...",
            freshness_tracker=tracker,
        )
        result = alerter.check_and_alert()
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        freshness_tracker: Optional[FreshnessTracker] = None,
        alert_threshold_days: int = 90,
        channel: str = "#benchmark-alerts",
    ) -> None:
        """Initialize the staleness alerter.

        Args:
            webhook_url: Slack webhook URL for sending alerts.
                         If None, alerts are logged but not sent.
            freshness_tracker: FreshnessTracker instance.
            alert_threshold_days: Days after which to alert (default: 90).
            channel: Slack channel to send alerts to.
        """
        self._webhook_url = webhook_url
        self._freshness_tracker = freshness_tracker or FreshnessTracker()
        self._alert_threshold_days = alert_threshold_days
        self._channel = channel
        self._last_alert_time: Optional[datetime] = None

    def check_and_alert(self) -> AlertResult:
        """Check all segments and send alerts for stale ones.

        Returns:
            AlertResult with details of sent alerts.
        """
        stale_segments = self._freshness_tracker.get_expired_segments()

        if not stale_segments:
            logger.info("No stale benchmark segments found — no alert needed")
            return AlertResult(
                success=True,
                alerts_sent=0,
                stale_segments=[],
            )

        if not self._webhook_url:
            logger.warning(
                "Found %d stale segments but no webhook configured. "
                "Set webhook_url to enable Slack alerts.",
                len(stale_segments),
            )
            return AlertResult(
                success=False,
                alerts_sent=0,
                stale_segments=stale_segments,
                error="No webhook URL configured",
            )

        return self._send_slack_alert(stale_segments)

    def _send_slack_alert(
        self,
        stale_segments: List[SegmentFreshness],
    ) -> AlertResult:
        """Send a Slack alert for stale segments.

        Args:
            stale_segments: List of stale segments.

        Returns:
            AlertResult.
        """
        try:
            message = self._build_slack_message(stale_segments)
            response = httpx.post(
                self._webhook_url,
                json=message,
                timeout=30.0,
            )
            response.raise_for_status()

            self._last_alert_time = datetime.utcnow()

            logger.info(
                "Sent Slack alert for %d stale segments",
                len(stale_segments),
            )

            return AlertResult(
                success=True,
                alerts_sent=1,
                stale_segments=stale_segments,
                sent_at=self._last_alert_time,
            )

        except httpx.TimeoutException:
            logger.error("Slack webhook timed out")
            return AlertResult(
                success=False,
                alerts_sent=0,
                stale_segments=stale_segments,
                error="Slack webhook timed out",
            )
        except httpx.HTTPStatusError as exc:
            logger.error("Slack webhook returned %s: %s", exc.response.status_code, exc.response.text)
            return AlertResult(
                success=False,
                alerts_sent=0,
                stale_segments=stale_segments,
                error=f"HTTP {exc.response.status_code}: {exc.response.text}",
            )
        except Exception as exc:
            logger.error("Failed to send Slack alert: %s", exc, exc_info=True)
            return AlertResult(
                success=False,
                alerts_sent=0,
                stale_segments=stale_segments,
                error=str(exc),
            )

    def _build_slack_message(
        self,
        stale_segments: List[SegmentFreshness],
    ) -> Dict[str, Any]:
        """Build a Slack message payload for stale segments.

        Args:
            stale_segments: List of stale segments.

        Returns:
            Slack message payload dict.
        """
        # Group by days overdue
        critical = [s for s in stale_segments if s.days_since_update > 180]
        warning = [s for s in stale_segments if 90 <= s.days_since_update <= 180]

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Benchmark Corpus Staleness Alert",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"The following benchmark segments have not been updated in over "
                        f"{self._alert_threshold_days} days and require attention."
                    ),
                },
            },
            {"type": "divider"},
        ]

        if critical:
            critical_text = "*🔴 Critical — Over 180 days stale:*\n"
            for seg in critical:
                critical_text += (
                    f"• *{seg.segment_key}* — {seg.days_since_update} days stale, "
                    f"{seg.clause_count} clauses\n"
                )
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": critical_text},
            })

        if warning:
            warning_text = "*🟡 Warning — 90-180 days stale:*\n"
            for seg in warning:
                warning_text += (
                    f"• *{seg.segment_key}* — {seg.days_since_update} days stale, "
                    f"{seg.clause_count} clauses\n"
                )
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": warning_text},
            })

        blocks.extend([
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"🤖 AI Contract Risk Analyzer | "
                            f"Alert sent: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                        ),
                    },
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Dashboard"},
                        "url": "/benchmarks/admin/freshness",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Dismiss"},
                        "style": "danger",
                    },
                ],
            },
        ])

        return {
            "channel": self._channel,
            "blocks": blocks,
            "username": "Benchmark Monitor",
            "icon_emoji": ":bar_chart:",
        }

    def send_test_alert(self) -> AlertResult:
        """Send a test alert to verify webhook configuration.

        Returns:
            AlertResult.
        """
        test_segment = SegmentFreshness(
            segment_key="test_alert",
            clause_type="test",
            days_since_update=95,
            status=FreshnessStatus.RED,
            last_updated=datetime.utcnow() - timedelta(days=95),
            clause_count=0,
            segment_description="Test alert — no action required",
        )

        return self._send_slack_alert([test_segment])

    @property
    def last_alert_time(self) -> Optional[datetime]:
        """Get the timestamp of the last sent alert.

        Returns:
            Datetime of last alert, or None.
        """
        return self._last_alert_time

    @property
    def webhook_configured(self) -> bool:
        """Check if a webhook URL is configured.

        Returns:
            True if webhook is configured.
        """
        return self._webhook_url is not None
