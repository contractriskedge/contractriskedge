"""Executive Dashboard API router — aggregate KPIs across the contract lifecycle."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_tenant_id, get_current_user
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

from .service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def get_dashboard_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> DashboardService:
    return DashboardService(session, tenant_id)


@router.get("/executive-summary")
async def get_executive_summary(
    service: DashboardService = Depends(get_dashboard_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Executive summary KPIs: totals, pending items, high-risk, renewals, obligations."""
    return await service.get_executive_summary()


@router.get("/risk-distribution")
async def get_risk_distribution(
    service: DashboardService = Depends(get_dashboard_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Risk distribution by severity level (critical/high/medium/low)."""
    return await service.get_risk_distribution()


@router.get("/risk-trend")
async def get_risk_trend(
    months: int = Query(12, ge=1, le=36),
    service: DashboardService = Depends(get_dashboard_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Monthly risk score trend for the last N months."""
    return await service.get_risk_trend(months=months)


@router.get("/workflow-distribution")
async def get_workflow_distribution(
    service: DashboardService = Depends(get_dashboard_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Contract counts grouped by lifecycle stage (review, negotiation, approval, signature, executed)."""
    return await service.get_workflow_distribution()


@router.get("/renewal-buckets")
async def get_renewal_buckets(
    service: DashboardService = Depends(get_dashboard_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Contract counts by renewal window (30/60/90 days, expired)."""
    return await service.get_renewal_buckets()


@router.get("/signature-status")
async def get_signature_status_counts(
    service: DashboardService = Depends(get_dashboard_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Signature request counts by status (sent, viewed, signed, declined, expired)."""
    return await service.get_signature_status_counts()
