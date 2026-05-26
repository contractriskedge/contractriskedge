"""Notifications and workflow repository — data access for all notification, workflow, SLA, and escalation entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.repository.base import BaseRepository
from app.domains.notify.models import (
    Notification, NotificationDelivery, NotificationPreference,
    WorkflowEvent, WorkflowTimer, EscalationRule, EscalationEvent, SLAPolicy,
)


@dataclass
class NotificationRepository(BaseRepository):

    async def create(self, **kwargs) -> Notification:
        notif = Notification(**kwargs)
        self.session.add(notif)
        await self.session.flush()
        return notif

    async def create_delivery(self, notification_id: str, tenant_id: str, channel: str) -> NotificationDelivery:
        delivery = NotificationDelivery(notification_id=notification_id, tenant_id=tenant_id, channel=channel)
        self.session.add(delivery)
        await self.session.flush()
        return delivery

    async def mark_delivery_delivered(self, notification_id: str) -> None:
        """Mark all delivery rows for a notification as delivered (in-app path)."""
        stmt = (
            update(NotificationDelivery)
            .where(NotificationDelivery.notification_id == notification_id)
            .values(status="delivered", delivered_at=func.now())
        )
        await self.session.execute(stmt)

    async def find_by_dedup_key(self, tenant_id: str, user_id: str, dedup_key: str) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.tenant_id == tenant_id, Notification.user_id == user_id,
            Notification.dedup_key == dedup_key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, notification_id: str, tenant_id: str) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.notification_id == notification_id, Notification.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_read(self, notification_id: str, tenant_id: str, user_id: str) -> bool:
        stmt = update(Notification).where(
            Notification.notification_id == notification_id,
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
        ).values(is_read=True, read_at=func.now())
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def mark_all_read(self, tenant_id: str, user_id: str) -> int:
        stmt = update(Notification).where(
            Notification.tenant_id == tenant_id, Notification.user_id == user_id,
            Notification.is_read == False,
        ).values(is_read=True, read_at=func.now())
        result = await self.session.execute(stmt)
        return result.rowcount

    async def list_by_user(self, tenant_id: str, user_id: str, unread_only: bool = False,
                            page: int = 1, page_size: int = 20):
        query = select(Notification).where(
            Notification.tenant_id == tenant_id, Notification.user_id == user_id,
        )
        if unread_only:
            query = query.where(Notification.is_read == False)
        query = query.order_by(Notification.created_at.desc())
        return await self.paginate(query, page, page_size)

    async def count_unread(self, tenant_id: str, user_id: str) -> int:
        stmt = select(func.count()).select_from(Notification).where(
            Notification.tenant_id == tenant_id, Notification.user_id == user_id,
            Notification.is_read == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def upsert_preference(self, tenant_id: str, user_id: str, notif_type: str,
                                 channel: str, digest_frequency: Optional[str] = None,
                                 is_muted: bool = False) -> NotificationPreference:
        stmt = select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notif_type,
        )
        result = await self.session.execute(stmt)
        pref = result.scalar_one_or_none()
        if pref:
            pref.channel = channel
            pref.digest_frequency = digest_frequency
            pref.is_muted = is_muted
        else:
            pref = NotificationPreference(
                tenant_id=tenant_id, user_id=user_id, notification_type=notif_type,
                channel=channel, digest_frequency=digest_frequency, is_muted=is_muted,
            )
            self.session.add(pref)
        await self.session.flush()
        return pref

    async def get_preference(self, tenant_id: str, user_id: str, notif_type: str) -> Optional[NotificationPreference]:
        stmt = select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notif_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_preferences(self, tenant_id: str, user_id: str):
        stmt = select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


@dataclass
class WorkflowRepository(BaseRepository):

    async def create_event(self, **kwargs) -> WorkflowEvent:
        event = WorkflowEvent(**kwargs)
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_events_by_entity(self, tenant_id: str, entity_type: str, entity_id: str):
        stmt = select(WorkflowEvent).where(
            WorkflowEvent.tenant_id == tenant_id,
            WorkflowEvent.entity_type == entity_type,
            WorkflowEvent.entity_id == entity_id,
        ).order_by(WorkflowEvent.created_at)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_timer(self, **kwargs) -> WorkflowTimer:
        timer = WorkflowTimer(**kwargs)
        self.session.add(timer)
        await self.session.flush()
        return timer

    async def get_due_timers(self, tenant_id: str, limit: int = 100):
        stmt = select(WorkflowTimer).where(
            WorkflowTimer.tenant_id == tenant_id,
            WorkflowTimer.target_time <= func.now(),
            WorkflowTimer.fired == False,
            WorkflowTimer.cancelled == False,
        ).order_by(WorkflowTimer.target_time).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_timer_fired(self, timer_id: str) -> None:
        stmt = update(WorkflowTimer).where(WorkflowTimer.timer_id == timer_id).values(
            fired=True, fired_at=func.now(),
        )
        await self.session.execute(stmt)

    async def cancel_timers_for_entity(self, tenant_id: str, entity_type: str, entity_id: str) -> int:
        stmt = update(WorkflowTimer).where(
            WorkflowTimer.tenant_id == tenant_id,
            WorkflowTimer.entity_type == entity_type,
            WorkflowTimer.entity_id == entity_id,
            WorkflowTimer.fired == False,
        ).values(cancelled=True)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_active_escalation_rules(self, tenant_id: str, trigger_event: str) -> list[EscalationRule]:
        stmt = select(EscalationRule).where(
            EscalationRule.tenant_id == tenant_id,
            EscalationRule.trigger_event == trigger_event,
            EscalationRule.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_escalation(self, **kwargs) -> EscalationEvent:
        esc = EscalationEvent(**kwargs)
        self.session.add(esc)
        await self.session.flush()
        return esc

    async def get_active_escalations(self, tenant_id: str, entity_type: str, entity_id: str) -> Optional[EscalationEvent]:
        stmt = select(EscalationEvent).where(
            EscalationEvent.tenant_id == tenant_id,
            EscalationEvent.entity_type == entity_type,
            EscalationEvent.entity_id == entity_id,
            EscalationEvent.status == "open",
        ).order_by(EscalationEvent.level.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_escalations(self, tenant_id: str, entity_type: Optional[str] = None,
                               entity_id: Optional[str] = None, status: Optional[str] = None):
        query = select(EscalationEvent).where(EscalationEvent.tenant_id == tenant_id)
        if entity_type:
            query = query.where(EscalationEvent.entity_type == entity_type)
        if entity_id:
            query = query.where(EscalationEvent.entity_id == entity_id)
        if status:
            query = query.where(EscalationEvent.status == status)
        query = query.order_by(EscalationEvent.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_sla_policy(self, **kwargs) -> SLAPolicy:
        policy = SLAPolicy(**kwargs)
        self.session.add(policy)
        await self.session.flush()
        return policy

    async def get_sla_policies(self, tenant_id: str, workflow_type: str, priority: str) -> list[SLAPolicy]:
        stmt = select(SLAPolicy).where(
            SLAPolicy.tenant_id == tenant_id,
            SLAPolicy.workflow_type == workflow_type,
            SLAPolicy.priority == priority,
            SLAPolicy.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_sla_policies(self, tenant_id: str, workflow_type: Optional[str] = None):
        query = select(SLAPolicy).where(SLAPolicy.tenant_id == tenant_id)
        if workflow_type:
            query = query.where(SLAPolicy.workflow_type == workflow_type)
        query = query.order_by(SLAPolicy.workflow_type, SLAPolicy.priority)
        result = await self.session.execute(query)
        return result.scalars().all()
