"""Notification service — in-app delivery, email abstraction, deduplication, and preference-aware sending."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.domains.notify.models import (
    Notification, NotificationDelivery, NotificationPreference,
    DeliveryStatus,
)
from app.domains.notify.repository import NotificationRepository
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)


@dataclass
class NotificationService:
    """Orchestrates notification creation, delivery, preference filtering, and deduplication."""

    repo: NotificationRepository
    event_bus: EventBus
    tenant_id: str

    async def send_notification(
        self,
        user_id: str,
        notif_type: str,
        title: str,
        body: Optional[str] = None,
        severity: str = "info",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action_url: Optional[str] = None,
        channel: str = "in_app",
        dedup_key: Optional[str] = None,
    ) -> Optional[Notification]:
        """Create and dispatch a notification with preference checking and deduplication.

        Returns None if the user has muted this notification type.
        """
        # Check preferences
        prefs = await self.repo.get_preference(self.tenant_id, user_id, notif_type)
        if prefs and prefs.is_muted:
            return None
        if prefs and prefs.channel == "none":
            return None

        effective_channel = prefs.channel if prefs and prefs.channel != "in_app" else channel

        # Dedup check
        if dedup_key:
            existing = await self.repo.find_by_dedup_key(self.tenant_id, user_id, dedup_key)
            if existing:
                return existing

        # Create notification
        notif = await self.repo.create(
            tenant_id=self.tenant_id,
            user_id=user_id,
            type=notif_type,
            title=title,
            body=body,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
            channel=effective_channel,
            dedup_key=dedup_key,
        )

        # Create delivery record
        await self.repo.create_delivery(notif.notification_id, self.tenant_id, effective_channel)

        # In-app: mark delivered in-process so API requests are not blocked when Celery/Redis is down.
        if effective_channel == "in_app":
            await self.repo.mark_delivery_delivered(notif.notification_id)
        else:
            try:
                from workers.notifications import deliver_notification_task

                deliver_notification_task.delay(
                    notification_id=str(notif.notification_id),
                    tenant_id=self.tenant_id,
                    user_id=user_id,
                    channel=effective_channel,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to enqueue notification delivery for %s: %s",
                    notif.notification_id,
                    exc,
                )

        return notif

    async def send_review_assigned(self, review_id: str, assignee_id: str, assigned_by: str):
        await self.send_notification(
            user_id=assignee_id,
            notif_type="review.assigned",
            title="Review Assigned",
            body=f"A contract review has been assigned to you by {assigned_by}.",
            severity="medium",
            entity_type="review",
            entity_id=review_id,
            action_url=f"/reviews/{review_id}",
            dedup_key=f"review_assigned:{review_id}:{assignee_id}",
        )

    async def send_escalation_notification(self, escalation, review_id: str):
        if escalation.escalated_to:
            await self.send_notification(
                user_id=escalation.escalated_to,
                notif_type="review.escalated",
                title=f"Review Escalated (Level {escalation.level})",
                body=escalation.reason,
                severity="high",
                entity_type="review",
                entity_id=review_id,
                action_url=f"/reviews/{review_id}",
                dedup_key=f"escalation:{review_id}:{escalation.level}",
            )

    async def send_approval_requested(self, review_id: str, approver_id: str):
        await self.send_notification(
            user_id=approver_id,
            notif_type="approval.requested",
            title="Approval Requested",
            body="A contract review requires your approval.",
            severity="medium",
            entity_type="review",
            entity_id=review_id,
            action_url=f"/reviews/{review_id}",
        )

    async def send_sla_warning(self, review_id: str, assignee_id: str, remaining_minutes: int):
        await self.send_notification(
            user_id=assignee_id,
            notif_type="sla.breach_warning",
            title="SLA Warning",
            body=f"Review SLA deadline approaching. {remaining_minutes} minutes remaining.",
            severity="high",
            entity_type="review",
            entity_id=review_id,
            action_url=f"/reviews/{review_id}",
            dedup_key=f"sla_warning:{review_id}",
        )

    async def send_finalized_notification(self, review_id: str, created_by: str, finalized_by: str):
        """Notify the review creator that their review has been finalized."""
        await self.send_notification(
            user_id=created_by,
            notif_type="workflow.completed",
            title="Review Finalized",
            body=f"Your contract review has been finalized by {finalized_by}. The final approved document is ready.",
            severity="medium",
            entity_type="review",
            entity_id=review_id,
            action_url=f"/reviews/{review_id}",
            dedup_key=f"finalized:{review_id}",
        )

    async def send_version_generated_notification(self, review_id: str, user_id: str,
                                                    version_number: int, label: str):
        """Notify a user that a new document version has been generated."""
        await self.send_notification(
            user_id=user_id,
            notif_type="workflow.completed",
            title=f"Document Version v{version_number} Generated",
            body=f"New document version '{label}' (v{version_number}) is ready for review.",
            severity="low",
            entity_type="review",
            entity_id=review_id,
            action_url=f"/reviews/{review_id}/versions",
            dedup_key=f"version:{review_id}:v{version_number}",
        )

    async def send_reanalysis_complete_notification(self, review_id: str, user_id: str,
                                                      new_version: int, preserved_redlines: int):
        """Notify that re-analysis completed with preservation."""
        await self.send_notification(
            user_id=user_id,
            notif_type="ai.analysis_complete",
            title=f"Re-Analysis Complete (v{new_version})",
            body=f"Re-analysis finished. {preserved_redlines} previously accepted redlines preserved.",
            severity="low",
            entity_type="review",
            entity_id=review_id,
            action_url=f"/reviews/{review_id}",
            dedup_key=f"reanalysis:{review_id}:v{new_version}",
        )

    async def send_archived_notification(self, review_id: str, user_id: str):
        """Notify that a review has been archived."""
        await self.send_notification(
            user_id=user_id,
            notif_type="workflow.completed",
            title="Review Archived",
            body="A contract review has been archived.",
            severity="low",
            entity_type="review",
            entity_id=review_id,
            action_url=f"/reviews/{review_id}",
            dedup_key=f"archived:{review_id}",
        )

    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        return await self.repo.mark_read(notification_id, self.tenant_id, user_id)

    async def mark_all_read(self, user_id: str) -> int:
        return await self.repo.mark_all_read(self.tenant_id, user_id)

    async def list_notifications(self, user_id: str, unread_only: bool = False, page: int = 1, page_size: int = 20):
        return await self.repo.list_by_user(self.tenant_id, user_id, unread_only, page, page_size)

    async def get_unread_count(self, user_id: str) -> int:
        return await self.repo.count_unread(self.tenant_id, user_id)

    async def update_preference(self, user_id: str, notif_type: str, channel: str, digest_frequency: Optional[str] = None, is_muted: bool = False):
        return await self.repo.upsert_preference(self.tenant_id, user_id, notif_type, channel, digest_frequency, is_muted)

    async def get_preferences(self, user_id: str):
        return await self.repo.get_preferences(self.tenant_id, user_id)
