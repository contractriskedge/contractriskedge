"""Audit API router — query audit events and get audit summaries."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.audit.schemas import (
    AuditQueryParams, AuditQueryResponse, AuditSummaryResponse
)
from app.domains.audit.service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])


async def get_audit_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
) -> AuditService:
    return AuditService(session=db, tenant_id=tenant_id)


@router.get("/events", response_model=AuditQueryResponse)
async def query_audit_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    status: Optional[str] = Query(None, description="Outcome: success, failure, blocked"),
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: AuditService = Depends(get_audit_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Query audit events with filtering and pagination.

    Searches across governance audit events and review status history.
    All queries are tenant-isolated.
    """
    from datetime import datetime

    params = AuditQueryParams(
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        action=action,
        status=status,
        from_date=datetime.fromisoformat(from_date) if from_date else None,
        to_date=datetime.fromisoformat(to_date) if to_date else None,
        page=page,
        page_size=page_size
)
    return await service.query_events(params
)


@router.get("/summary", response_model=AuditSummaryResponse
)
async def get_audit_summary(
    period_days: int = Query(7, ge=1, le=90, description="Lookback period in days"),
    service: AuditService = Depends(get_audit_service)
,
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get summary of audit activity for the period.

    Returns total events, breakdown by type, unique actors, and unique resources.
    """
    return await service.get_summary(period_days
)
