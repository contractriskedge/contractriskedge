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
from app.dependencies import get_db, get_tenant_id, get_current_user
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/obligations", tags=["Obligation Management"])


async def get_obligation_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: UserContext = Depends(get_current_user),
) -> ObligationService:
    return ObligationService(session, tenant_id, user_role=user.role)


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
    contract_id: Optional[str] = Query(None, description="Filter by contract UUID"),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    items, total = await service.list_obligations(
        page, page_size, status, obligation_type, vendor, risk_level,
        sla_status, search, contract_id, sort_by, sort_order,
    )
    return {"data": [i.model_dump() for i in items], "pagination": {"page": page, "page_size": page_size, "total": total, "total_pages": max(1, (total + page_size - 1) // page_size)}}


@router.get("/by-contract/{contract_id}", response_model=None)
async def get_obligations_by_contract(
    contract_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get obligations count and list for a specific contract."""
    items, total = await service.list_obligations(
        page=1, page_size=100, contract_id=contract_id,
    )
    open_count = sum(1 for o in items if o.status in ("pending", "in_progress", "open", "active"))
    completed_count = sum(1 for o in items if o.status == "completed")
    overdue_count = sum(1 for o in items if o.status == "overdue")
    return {
        "total": total,
        "open": open_count,
        "completed": completed_count,
        "overdue": overdue_count,
        "obligations": [o.model_dump() for o in items],
    }


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
@router.get("/export")
async def export_obligation_report(
    format: str = Query("pdf"),
    obligation_id: Optional[str] = Query(
        None, description="Optional — export a single obligation by id. If omitted, exports the full filtered list."),
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
    """Export obligation report as PDF or CSV.

    Same filter set as ``GET /obligations`` so the export is guaranteed
    to contain the exact rows the user is viewing in the UI.
    Supports the same sort_by and sort_order parameters as the list endpoint.
    """
    from fastapi.responses import StreamingResponse
    import io, csv

    if format not in ("pdf", "csv"):
        raise HTTPException(status_code=400, detail="format must be 'pdf' or 'csv'")

    # ── Single-obligation fast path ─────────────────────────────────
    if obligation_id:
        single = await service.get_obligation(obligation_id)
        if not single:
            raise HTTPException(status_code=404, detail="Obligation not found")
        obligations = [single.model_dump()]
        total = 1
    else:
        items, total = await service.list_obligations(
            page, page_size, status, obligation_type, vendor, risk_level,
            sla_status, search, sort_by, sort_order,
        )
        obligations = [i.model_dump() for i in items]

    kpis = (await service.get_kpis()).model_dump()

    # ── CSV branch ──────────────────────────────────────────────────
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Name", "Type", "Status", "Contract", "Vendor", "Owner",
            "Due Date", "Reminder Date", "Completed Date",
            "Risk Level", "Currency", "Financial Impact",
        ])
        for o in obligations:
            writer.writerow([
                o.get("name"),
                o.get("obligation_type"),
                o.get("status"),
                o.get("contract_name") or "",
                o.get("vendor") or "",
                o.get("owner") or "",
                str(o.get("due_date") or "")[:10],
                str(o.get("reminder_date") or "")[:10] if o.get("reminder_date") else "",
                str(o.get("completed_date") or "")[:10] if o.get("completed_date") else "",
                o.get("risk_level") or "",
                o.get("currency") or "USD",
                o.get("financial_impact") or 0,
            ])
        suffix = f"__{obligation_id}" if obligation_id else ""
        filename = f"obligation_report{suffix}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # ── PDF branch ──────────────────────────────────────────────────
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, textColor=HexColor("#1e293b"), spaceAfter=6)
    heading_style = ParagraphStyle("Heading2", parent=styles["Heading2"], fontSize=12, textColor=HexColor("#334155"), spaceAfter=4, spaceBefore=12)
    normal = ParagraphStyle("Normal2", parent=styles["Normal"], fontSize=8, textColor=HexColor("#475569"), spaceAfter=2)

    elements = []

    # Title
    from datetime import date
    title_text = (
        f"Obligation {'Detail' if obligation_id else 'Management'} Report"
    )
    elements.append(Paragraph(title_text, title_style))
    elements.append(Paragraph(f"Generated: {date.today().isoformat()}", normal))
    if not obligation_id:
        # Show the active filter description so the report is self-describing
        filter_bits = []
        if status:         filter_bits.append(f"status={status}")
        if obligation_type: filter_bits.append(f"type={obligation_type}")
        if vendor:         filter_bits.append(f"vendor~{vendor}")
        if risk_level:     filter_bits.append(f"risk={risk_level}")
        if sla_status:     filter_bits.append(f"sla={sla_status}")
        if search:         filter_bits.append(f"search='{search}'")
        if filter_bits:
            elements.append(Paragraph(
                f"Filters: {', '.join(filter_bits)} · Rows: {total}", normal,
            ))
        else:
            elements.append(Paragraph(f"Rows: {total}", normal))
    elements.append(Spacer(1, 12))

    # Section 1: Executive Summary (only meaningful for list exports)
    if not obligation_id:
        elements.append(Paragraph("1. Executive Summary", heading_style))
        total_rows = len(obligations)
        open_count = sum(1 for o in obligations if o.get("status") == "open")
        completed = sum(1 for o in obligations if o.get("status") == "completed")
        overdue = sum(1 for o in obligations if o.get("status") == "overdue")
        escalated = sum(1 for o in obligations if o.get("status") == "escalated")
        compliance_pct = round((completed / max(total_rows, 1)) * 100, 1)

        summary_data = [
            ["Total Obligations", str(total_rows)],
            ["Open", str(open_count)],
            ["Completed", str(completed)],
            ["Overdue", str(overdue)],
            ["Escalated", str(escalated)],
            ["Compliance %", f"{compliance_pct}%"],
        ]
        t = Table(summary_data, colWidths=[2*inch, 1*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#334155")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

    # Section 2: Risk Summary
    elements.append(Paragraph("2. Risk Summary" if not obligation_id else "Risk Summary", heading_style))
    critical = sum(1 for o in obligations if o.get("risk_level") == "critical")
    high = sum(1 for o in obligations if o.get("risk_level") == "high")
    medium = sum(1 for o in obligations if o.get("risk_level") == "medium")
    low = sum(1 for o in obligations if o.get("risk_level") == "low")
    risk_data = [
        ["Risk Level", "Count"],
        ["Critical", str(critical)],
        ["High", str(high)],
        ["Medium", str(medium)],
        ["Low", str(low)],
    ]
    t2 = Table(risk_data, colWidths=[2*inch, 1*inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("TEXTCOLOR", (0, 1), (-1, -1), HexColor("#334155")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 12))

    # Section 3: Overdue Obligations (list only)
    if not obligation_id:
        overdue_obligations = [o for o in obligations if o.get("status") == "overdue"]
        elements.append(Paragraph("3. Overdue Obligations", heading_style))
        if overdue_obligations:
            od_data = [["Obligation", "Contract", "Owner", "Days Overdue", "Risk"]]
            for o in overdue_obligations[:20]:
                od_data.append([o.get("name", ""), o.get("contract_name", ""), o.get("owner", ""), "—", o.get("risk_level", "")])
            t3 = Table(od_data, colWidths=[1.5*inch, 1.2*inch, 1*inch, 0.8*inch, 0.5*inch])
            t3.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
                ("ALIGN", (3, 1), (4, -1), "CENTER"),
            ]))
            elements.append(t3)
        else:
            elements.append(Paragraph("No overdue obligations.", normal))
        elements.append(Spacer(1, 12))

        # Section 4: Upcoming Obligations (Next 30 Days)
        elements.append(Paragraph("4. Upcoming Obligations (Next 30 Days)", heading_style))
        upcoming = [o for o in obligations if o.get("due_date") and o.get("status") not in ("completed", "waived")][:20]
        if upcoming:
            up_data = [["Obligation", "Due Date", "Owner", "Risk"]]
            for o in upcoming:
                up_data.append([o.get("name", ""), str(o.get("due_date", ""))[:10], o.get("owner", ""), o.get("risk_level", "")])
            t4 = Table(up_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 0.6*inch])
            t4.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ]))
            elements.append(t4)
        else:
            elements.append(Paragraph("No upcoming obligations in the next 30 days.", normal))
    else:
        # Single-obligation export: show the full detail
        o = obligations[0]
        elements.append(Paragraph("Obligation Detail", heading_style))
        detail_rows = [
            ["Name", o.get("name", "")],
            ["Type", o.get("obligation_type", "")],
            ["Status", o.get("status", "")],
            ["Contract", o.get("contract_name", "")],
            ["Vendor", o.get("vendor", "")],
            ["Owner", o.get("owner", "")],
            ["Due Date", str(o.get("due_date") or "")[:10]],
            ["Risk Level", o.get("risk_level", "")],
            ["Financial Impact", f"{o.get('financial_impact') or 0} {o.get('currency') or 'USD'}"],
        ]
        t_d = Table(detail_rows, colWidths=[2*inch, 4*inch])
        t_d.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#334155")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
        ]))
        elements.append(t_d)

    doc.build(elements)
    buf.seek(0)
    suffix = f"__{obligation_id}" if obligation_id else ""
    filename = f"Obligation_Report{suffix}_{date.today().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("", response_model=None, include_in_schema=False)
@router.post("/", response_model=None)
async def create_obligation(
    data: ObligationCreate,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    return (await service.create_obligation(data)).model_dump()


@router.get("/{obligation_id}", response_model=None)
async def get_obligation(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a single obligation by ID."""
    result = await service.get_obligation(obligation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return result.model_dump()


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
    """Permanently delete an obligation (admin only — requires contracts:delete)."""
    if not await service.delete_obligation(obligation_id):
        raise HTTPException(status_code=404, detail="Obligation not found")
    return {"status": "deleted"}


# ── Lifecycle Actions ────────────────────────────────────────────

@router.post("/{obligation_id}/complete", response_model=None)
async def complete_obligation(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Mark an obligation as completed."""
    return (await service.complete_obligation(obligation_id)).model_dump()


@router.post("/{obligation_id}/cancel", response_model=None)
async def cancel_obligation(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Cancel an obligation."""
    return (await service.cancel_obligation(obligation_id)).model_dump()


@router.post("/{obligation_id}/reopen", response_model=None)
async def reopen_obligation(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Reopen a completed or cancelled obligation."""
    return (await service.reopen_obligation(obligation_id)).model_dump()


@router.post("/{obligation_id}/archive", response_model=None)
async def archive_obligation(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Archive an obligation (soft-delete for normal users)."""
    return (await service.archive_obligation(obligation_id)).model_dump()


@router.get("/{obligation_id}/audit", response_model=None)
async def get_obligation_audit_history(
    obligation_id: str,
    service: ObligationService = Depends(get_obligation_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get audit history for an obligation."""
    return [a.model_dump() for a in await service.get_audit_history(obligation_id)]


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

