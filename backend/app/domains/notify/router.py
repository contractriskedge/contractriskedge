"""Notifications and workflow API routers."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.kernel.web.pagination import PaginatedResponse, PaginationMeta
from app.domains.notify.service import NotificationService
from app.domains.notify.repository import NotificationRepository, WorkflowRepository
from app.domains.notify.workflows import WorkflowAutomationService
from app.kernel.events.bus import EventBus

router = APIRouter(tags=["Notifications & Workflows"])


async def get_notif_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
) -> NotificationService:
    return NotificationService(
        repo=NotificationRepository(db, tenant_id=tenant_id),
        event_bus=EventBus(),
        tenant_id=tenant_id
)


async def get_workflow_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
) -> WorkflowAutomationService:
    notif_service = NotificationService(
        repo=NotificationRepository(db, tenant_id=tenant_id),
        event_bus=EventBus(),
        tenant_id=tenant_id
)
    return WorkflowAutomationService(
        repo=WorkflowRepository(db, tenant_id=tenant_id),
        notif_service=notif_service,
        event_bus=EventBus(),
        tenant_id=tenant_id
)


# ── Notifications ──────────────────────────────────────────────────

@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: NotificationService = Depends(get_notif_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List notifications for the current user."""
    items, total = await service.list_notifications(user.id, unread_only, page, page_size
)
    data = [
        {
            "notification_id": str(n.notification_id
),
            "type": n.type, "title": n.title, "body": n.body,
            "severity": n.severity, "is_read": n.is_read,
            "entity_type": n.entity_type, "entity_id": str(n.entity_id
) if n.entity_id else None,
            "action_url": n.action_url, "created_at": n.created_at.isoformat(
),
        }
        for n in items
    ]
    return PaginatedResponse(
        data=data,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=max(1, (total + page_size - 1) // page_size))
)


@router.get("/notifications/unread-count"
)
async def get_unread_count(
    service: NotificationService = Depends(get_notif_service),
    user: UserContext = Depends(get_current_user)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get unread notification count."""
    count = await service.get_unread_count(user.id
)
    return {"unread_count": count}


@router.post("/notifications/{notification_id}/read"
)
async def mark_notification_read(
    notification_id: str,
    service: NotificationService = Depends(get_notif_service),
    user: UserContext = Depends(get_current_user)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Mark a single notification as read."""
    result = await service.mark_read(notification_id, user.id
)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found"
)
    return {"status": "read"}


@router.post("/notifications/read-all"
)
async def mark_all_notifications_read(
    service: NotificationService = Depends(get_notif_service),
    user: UserContext = Depends(get_current_user)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Mark all notifications as read for the current user."""
    count = await service.mark_all_read(user.id
)
    return {"marked_read": count}


# ── Notification Preferences ───────────────────────────────────────

@router.get("/notifications/preferences"
)
async def get_preferences(
    service: NotificationService = Depends(get_notif_service),
    user: UserContext = Depends(get_current_user)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get notification preferences for the current user."""
    prefs = await service.get_preferences(user.id
)
    return {"preferences": [
        {"notification_type": p.notification_type, "channel": p.channel,
         "digest_frequency": p.digest_frequency, "is_muted": p.is_muted}
        for p in prefs
    ]}


@router.put("/notifications/preferences/{notification_type}"
)
async def update_preference(
    notification_type: str,
    channel: str = Query("in_app"),
    digest_frequency: Optional[str] = Query(None),
    is_muted: bool = Query(False),
    service: NotificationService = Depends(get_notif_service),
    user: UserContext = Depends(get_current_user)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Update notification preference for a notification type."""
    await service.update_preference(user.id, notification_type, channel, digest_frequency, is_muted
)
    return {"status": "updated"}


# ── SLA Policies ───────────────────────────────────────────────────

@router.get("/sla-policies"
)
async def list_sla_policies(
    workflow_type: Optional[str] = Query(None),
    service: WorkflowAutomationService = Depends(get_workflow_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """List SLA policies for the tenant."""
    policies = await service.list_sla_policies(workflow_type
)
    return {"policies": [
        {"policy_id": str(p.policy_id
), "name": p.name, "workflow_type": p.workflow_type,
         "priority": p.priority, "target_minutes": p.target_minutes,
         "warning_threshold_percent": p.warning_threshold_percent,
         "escalation_after_minutes": p.escalation_after_minutes}
        for p in policies
    ]}


@router.post("/sla-policies"
)
async def create_sla_policy(
    name: str = Query(...),
    workflow_type: str = Query(...),
    priority: str = Query("normal"),
    target_minutes: int = Query(...),
    warning_threshold: float = Query(0.8),
    escalation_after_minutes: Optional[int] = Query(None),
    service: WorkflowAutomationService = Depends(get_workflow_service)
,
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Create a new SLA policy."""
    policy = await service.create_sla_policy(
        name, workflow_type, priority, target_minutes, warning_threshold, escalation_after_minutes
)
    return {"policy_id": str(policy.policy_id
), "status": "created"}


# ── Escalations ────────────────────────────────────────────────────

@router.get("/escalations"
)
async def list_escalations(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    service: WorkflowAutomationService = Depends(get_workflow_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """List escalation events with optional filters."""
    events = await service.repo.get_escalations(
        service.tenant_id, entity_type, entity_id, status
)
    return {"escalations": [
        {"escalation_id": str(e.escalation_id
), "level": e.level,
         "entity_type": e.entity_type, "entity_id": str(e.entity_id
) if e.entity_id else None,
         "escalated_by": e.escalated_by, "escalated_to": e.escalated_to,
         "reason": e.reason, "status": e.status, "created_at": e.created_at.isoformat(
)}
        for e in events
    ]}
