"""Obligation Management API router — CRUD, timeline, financial, AI, and notifications."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.obligations.schemas import (
    ObligationCreate, ObligationUpdate, ObligationResponse,
    ObligationKpiResponse, PaginatedObligations,
    TimelineEventResponse, FinancialExposureResponse, ValueAtRiskResponse,
    RiskAnalysisResponse, ObligationEscalationResponse, AnomalyResponse,
    AiReviewRequest, ObligationReminderCreate, ObligationReminderResponse,
    ObligationEscalationCreate, NotificationHistoryResponse,
    SlaMetricResponse, SlaBreachResponse, VendorRiskResponse, SlaPredictionResponse,
)
from app.domains.obligations.service import ObligationService
from app.dependencies import get_db, get_tenant_id
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/obligations", tags=["Obligation Management"])


async def get_obligation_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ObligationService:
    return ObligationService(session, tenant_id)


@router.get("", response_model=None, include_in_schema=False)
@router.get("/", response_model=None)
async def list_obligations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    obligation_type: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    sla_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    items, total = await service.list_obligations(
        page, page_size, status, obligation_type, vendor, risk_level,
        sla_status, search, sort_by, sort_order,
    )
    return {"data": [i.model_dump() for i in items], "pagination": {"page": page, "page_size": page_size, "total": total, "total_pages": max(1, (total + page_size - 1) // page_size)}}


@router.get("/kpis", response_model=None)
async def get_kpis(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return (await service.get_kpis()).model_dump()


@router.get("/calendar", response_model=None)
async def get_calendar(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [e.model_dump() for e in await service.get_calendar(start_date, end_date)]


@router.get("/upcoming", response_model=None)
async def get_upcoming(
    days: int = Query(30, ge=1),
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [o.model_dump() for o in await service.get_upcoming(days)]


@router.get("/overdue", response_model=None)
async def get_overdue(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [o.model_dump() for o in await service.get_overdue()]


@router.get("/financial-exposure", response_model=None)
async def get_financial_exposure(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [f.model_dump() for f in await service.get_financial_exposure()]


@router.get("/penalties", response_model=None)
async def get_penalties(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return await service.get_penalties()


@router.get("/value-at-risk", response_model=None)
async def get_value_at_risk(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return (await service.get_value_at_risk()).model_dump()


@router.get("/risk-analysis/{obligation_id}", response_model=None)
async def get_risk_analysis(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return (await service.get_risk_analysis(obligation_id)).model_dump()


@router.get("/escalations", response_model=None)
async def get_escalations(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [e.model_dump() for e in await service.get_escalations()]


@router.get("/anomalies", response_model=None)
async def get_anomalies(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [a.model_dump() for a in await service.get_anomalies()]


@router.post("/ai-review", response_model=None)
async def ai_review(
    req: AiReviewRequest,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    return await service.ai_review(req)


@router.get("/{obligation_id}", response_model=None)
async def get_obligation(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    result = await service.get_obligation(obligation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return result.model_dump()


@router.post("/", response_model=None)
async def create_obligation(
    data: ObligationCreate,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    return (await service.create_obligation(data)).model_dump()


@router.put("/{obligation_id}", response_model=None)
async def update_obligation(
    obligation_id: str,
    data: ObligationUpdate,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    result = await service.update_obligation(obligation_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return result.model_dump()


@router.delete("/{obligation_id}", response_model=None)
async def delete_obligation(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_DELETE)),
):
    if not await service.delete_obligation(obligation_id):
        raise HTTPException(status_code=404, detail="Obligation not found")
    return {"status": "deleted"}


@router.post("/reminders", response_model=None)
async def create_reminder(
    data: ObligationReminderCreate,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    return (await service.create_reminder(data)).model_dump()


@router.post("/escalations", response_model=None)
async def create_escalation(
    data: ObligationEscalationCreate,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    return (await service.create_escalation(data)).model_dump()


@router.get("/notification-history", response_model=None)
async def get_notification_history(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [n.model_dump() for n in await service.get_notification_history()]


# ── SLA Performance / Breaches / Vendor Risk / Predictions ────────────

@router.get("/sla-performance", response_model=None)
async def get_sla_performance(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [m.model_dump() for m in await service.get_sla_performance()]


@router.get("/sla-breaches", response_model=None)
async def get_sla_breaches(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [m.model_dump() for m in await service.get_sla_breaches()]


@router.get("/vendor-risk", response_model=None)
async def get_vendor_risk(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [m.model_dump() for m in await service.get_vendor_risk()]


@router.get("/sla-predictions", response_model=None)
async def get_sla_predictions(
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [m.model_dump() for m in await service.get_sla_predictions()]
