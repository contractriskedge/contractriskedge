"""Notification service — in-app and email notifications.

Supports:
- In-app notifications (stored in DB, fetched via API)
- Email notifications (via generic email service)
- Multiple channels per notification
- Priority levels
- Read/unread tracking
"""

from __future__ import annotations

import enum
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Notification

logger = logging.getLogger(__name__)


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    BOTH = "both"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationService:
    """Central notification service for all modules.

    Usage:
        notifier = NotificationService(session, tenant_id)
        await notifier.send(
            user_id="user-1",
            title="Contract Executed",
            message="The contract has been fully executed.",
            event_type="contract.executed",
            link="/contracts/abc-123",
        )
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: str,
        email_service=None,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self._email_service = email_service

    # ── Send ────────────────────────────────────────────────────

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: Optional[str] = None,
        event_type: str = "general",
        channel: NotificationChannel | str = NotificationChannel.IN_APP,
        priority: NotificationPriority | str = NotificationPriority.NORMAL,
        link: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Notification:
        """Send a notification to a user.

        Returns the created Notification object.
        If channel includes email, also sends via email service.
        """
        channel_enum = channel if isinstance(channel, NotificationChannel) else NotificationChannel(channel)
        priority_enum = priority if isinstance(priority, NotificationPriority) else NotificationPriority(priority)

        # Create in-app notification
        notification = Notification(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            user_id=user_id,
            title=title,
            message=message,
            event_type=event_type,
            channel=channel_enum.value,
            priority=priority_enum.value,
            link=link,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(notification)
        await self.session.flush()

        # Send email if requested
        if channel_enum in (NotificationChannel.EMAIL, NotificationChannel.BOTH):
            await self._send_email(user_id, title, message, link)

        logger.debug("Notification sent to %s: %s", user_id, title)
        return notification

    async def send_bulk(
        self,
        user_ids: list[str],
        title: str,
        message: Optional[str] = None,
        event_type: str = "general",
        channel: NotificationChannel | str = NotificationChannel.IN_APP,
        priority: NotificationPriority | str = NotificationPriority.NORMAL,
        link: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> list[Notification]:
        """Send the same notification to multiple users."""
        notifications = []
        for uid in user_ids:
            n = await self.send_notification(
                user_id=uid, title=title, message=message,
                event_type=event_type, channel=channel,
                priority=priority, link=link, metadata=metadata,
            )
            notifications.append(n)
        return notifications

    async def send_contract_notification(
        self,
        contract_id: str,
        user_ids: list[str],
        title: str,
        event_type: str,
        message: Optional[str] = None,
    ) -> list[Notification]:
        """Send a contract-related notification to relevant users."""
        link = f"/contracts/{contract_id}"
        return await self.send_bulk(
            user_ids=user_ids,
            title=title,
            message=message,
            event_type=event_type,
            channel=NotificationChannel.BOTH,
            priority=NotificationPriority.NORMAL,
            link=link,
            metadata={"contract_id": contract_id},
        )

    # ── Query ───────────────────────────────────────────────────

    async def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        event_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        """Get notifications for a user."""
        query = select(Notification).where(
            and_(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
            )
        )
        count_query = select(func.count()).select_from(Notification).where(
            and_(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
            )
        )

        if unread_only:
            query = query.where(Notification.read == False)
            count_query = count_query.where(Notification.read == False)

        if event_type:
            query = query.where(Notification.event_type == event_type)
            count_query = count_query.where(Notification.event_type == event_type)

        total = (await self.session.execute(count_query)).scalar() or 0
        query = query.order_by(Notification.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def get_unread_count(self, user_id: str) -> int:
        """Get the number of unread notifications for a user."""
        query = select(func.count()).select_from(Notification).where(
            and_(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
                Notification.read == False,
            )
        )
        return (await self.session.execute(query)).scalar() or 0

    async def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False
        notification.read = True
        notification.read_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user. Returns count."""
        result = await self.session.execute(
            select(Notification).where(
                and_(
                    Notification.tenant_id == self.tenant_id,
                    Notification.user_id == user_id,
                    Notification.read == False,
                )
            )
        )
        count = 0
        for n in result.scalars().all():
            n.read = True
            n.read_at = datetime.now(timezone.utc)
            count += 1
        await self.session.flush()
        return count

    # ── Email ───────────────────────────────────────────────────

    async def _send_email(
        self,
        user_id: str,
        subject: str,
        body: Optional[str],
        link: Optional[str],
    ) -> None:
        """Send an email notification."""
        if not self._email_service:
            logger.debug("Email service not configured — skipping email for: %s", subject)
            return
        try:
            # TODO: Look up user's email from user_id
            # await self._email_service.send(to=email, subject=subject, body=body)
            pass
        except Exception as e:
            logger.error("Failed to send email notification: %s", e)
