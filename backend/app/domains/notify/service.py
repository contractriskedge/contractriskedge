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
from app.config import settings
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

        # Always enqueue email for action notifications (in-app is separate).
        await self._enqueue_email(notif, user_id)

        return notif

    async def _resolve_recipient_email(self, user_id: str) -> Optional[str]:
        """Resolve delivery address: redirect inbox when enabled, else user email."""
        redirect_enabled, redirect_to = await self.repo.get_email_redirect(self.tenant_id)
        if redirect_enabled and redirect_to:
            logger.info(
                "Email redirected: user=%s -> %s (tenant redirect enabled)",
                user_id,
                redirect_to,
            )
            return redirect_to

        recipient = await self.repo.get_user_email(self.tenant_id, user_id)
        if not recipient:
            logger.warning("No email address for user %s — cannot send notification email", user_id)
        return recipient

    async def _enqueue_email(self, notif: Notification, user_id: str) -> None:
        """Enqueue an email notification for async delivery via Resend."""
        try:
            recipient_email = await self._resolve_recipient_email(user_id)
            if not recipient_email:
                return

            # Resolve display name from the admin_users record for a proper greeting
            user_name = await self.repo.get_user_name(self.tenant_id, user_id)
            if user_name:
                display_name = user_name
            else:
                user_email = await self.repo.get_user_email(self.tenant_id, user_id)
                display_name = (user_email or user_id).split("@")[0].replace(".", " ").replace("-", " ").title()

            # Fetch real contract data from the review if entity_id is a review
            contract_name = notif.title
            risk_score = None
            reviewer = None
            current_stage = None
            due_date = None
            priority = None

            if notif.entity_id and notif.entity_type == "review":
                try:
                    from sqlalchemy import select, text as sa_text
                    from app.domains.review.models import ContractReview
                    from app.domains.ingestion.models import UploadSession

                    review_result = await self.repo.session.execute(
                        select(ContractReview).where(
                            ContractReview.review_id == notif.entity_id,
                            ContractReview.tenant_id == self.tenant_id,
                        )
                    )
                    review = review_result.scalar_one_or_none()
                    if review:
                        # Resolve document filename — prefer _document_filename
                        # (set by repository queries that JOIN with uploads),
                        # then try the uploads table, then metadata, then fallback.
                        if hasattr(review, '_document_filename') and review._document_filename:
                            contract_name = review._document_filename
                        else:
                            # Fetch filename from the upload session
                            try:
                                upload_result = await self.repo.session.execute(
                                    select(UploadSession.filename).where(
                                        UploadSession.upload_id == review.upload_id,
                                        UploadSession.tenant_id == self.tenant_id,
                                    )
                                )
                                upload_row = upload_result.fetchone()
                                if upload_row and upload_row.filename:
                                    contract_name = upload_row.filename
                            except Exception:
                                pass

                            # Fallback to metadata if upload lookup failed
                            if not contract_name or contract_name == notif.title:
                                if review.document_metadata:
                                    contract_name = (
                                        review.document_metadata.get("filename")
                                        or review.document_metadata.get("original_filename")
                                        or contract_name
                                    )

                        risk_score = review.document_metadata.get("risk_score") if review.document_metadata else None
                        reviewer = review.assigned_to
                        current_stage = review.workflow_stage or review.status.value if hasattr(review.status, 'value') else str(review.status)
                        due_date = str(review.sla_deadline) if review.sla_deadline else None
                        priority = review.priority.upper() if review.priority else None
                except Exception:
                    logger.warning("Failed to fetch review data for email enrichment", exc_info=True)

            template_data = {
                "recipient_name": display_name,
                "contract_name": contract_name,
                "review_id": str(notif.entity_id) if notif.entity_id else "",
                "subject": notif.title,
                "body": notif.body or "",
                "risk_score": risk_score,
                "reviewer": reviewer,
                "current_stage": current_stage,
                "due_date": due_date,
                "priority": priority,
                "app_url": settings.app_url,
            }

            # For escalation notifications, pass the reason explicitly to the template
            if notif.type == "review.escalated" and notif.body:
                template_data["reason"] = notif.body
                template_data["escalated_by"] = user_id

            await self.repo.enqueue_email(
                tenant_id=self.tenant_id,
                notification_id=notif.notification_id,
                recipient_email=recipient_email,
                subject=notif.title,
                template_name=notif.type,
                template_data=template_data,
            )
            logger.info(
                "Email enqueued: type=%s to=%s notification=%s",
                notif.type,
                recipient_email,
                notif.notification_id,
            )

            # In development, process the queue inline so Celery beat is not required.
            if settings.environment == "development":
                await self._process_email_queue_inline()
        except Exception as exc:
            logger.warning("Failed to enqueue email for %s: %s", user_id, exc)

    async def _process_email_queue_inline(self) -> None:
        """Process pending emails using the current DB session (post-flush)."""
        try:
            from app.workers.email_worker import process_email_queue

            await process_email_queue(batch_size=10, session=self.repo.session)
        except Exception as exc:
            logger.warning("Inline email queue processing failed: %s", exc)

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
            # No dedup_key — every assignment (including re-assignment)
            # should produce a fresh notification and email.
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

    async def send_obligation_created(self, obligation_id: str, review_id: str,
                                       created_by: str, obligation_name: str):
        """Notify the review creator that an obligation was created."""
        await self.send_notification(
            user_id=created_by,
            notif_type="obligation.created",
            title="Obligation Created",
            body=f"Obligation '{obligation_name}' has been created for this contract.",
            severity="medium",
            entity_type="obligation",
            entity_id=obligation_id,
            action_url=f"/reviews/{review_id}",
            dedup_key=f"obligation_created:{obligation_id}",
        )

    async def send_obligation_completed(self, obligation_id: str, review_id: str,
                                         completed_by: str, obligation_name: str):
        """Notify that an obligation has been completed."""
        await self.send_notification(
            user_id=completed_by,
            notif_type="obligation.completed",
            title="Obligation Completed",
            body=f"Obligation '{obligation_name}' has been completed.",
            severity="low",
            entity_type="obligation",
            entity_id=obligation_id,
            action_url=f"/reviews/{review_id}",
            dedup_key=f"obligation_completed:{obligation_id}",
        )

    async def send_contract_closed(self, review_id: str, user_id: str, contract_number: str):
        """Notify that a contract has been closed."""
        await self.send_notification(
            user_id=user_id,
            notif_type="contract.closed",
            title="Contract Closed",
            body=f"Contract {contract_number} has been closed.",
            severity="low",
            entity_type="review",
            entity_id=review_id,
            action_url=f"/reviews/{review_id}",
            dedup_key=f"contract_closed:{review_id}",
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
