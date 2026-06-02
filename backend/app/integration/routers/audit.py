"""
Audit event API router.

Endpoints for viewing integration audit trail.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

from app.integration.models.audit import IntegrationAuditEvent
from app.integration.routers.dependencies import get_db, get_tenant_id
from app.integration.schemas.audit import AuditEventListResponse, AuditEventResponse

router = APIRouter(prefix="/audit", tags=["Audit"], dependencies=[Depends(require_permission(Permissions.CONTRACTS_READ))])


@router.get(
    "",
    response_model=AuditEventListResponse,
    summary="List audit events",
)
async def list_audit_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    integration_id: Optional[uuid.UUID] = Query(None),
    action: Optional[str] = Query(None),
    actor_id: Optional[uuid.UUID] = Query(None),
):
    """List integration audit events with pagination and filtering."""
    query = select(IntegrationAuditEvent).where(
        IntegrationAuditEvent.tenant_id == tenant_id,
    )

    if integration_id:
        query = query.where(IntegrationAuditEvent.integration_id == integration_id)
    if action:
        query = query.where(IntegrationAuditEvent.action == action)
    if actor_id:
        query = query.where(IntegrationAuditEvent.actor_id == actor_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(IntegrationAuditEvent.occurred_at.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )
