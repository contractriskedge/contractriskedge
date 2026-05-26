"""Continuous Contract Monitoring API endpoints (Sprints 11-13).

Provides REST API endpoints for:
- Obligation event bus management
- Auto-renewal alerts
- SLA deadline tracking
- Insurance certificate monitoring
- Compliance drift detection
- Counterparty litigation monitoring
- Renewal risk forecasting
- Semantic search
- AI cost governance
- Model routing
- Batch inference scheduling
- Benchmark corpus pipeline
- Industry segmentation
- Benchmark confidence scoring
- Procurement integrations (SAP Ariba / Coupa)
- Vendor onboarding workflow
- Supplier concentration analysis
- V2.2 launch readiness QA
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Continuous Monitoring"])


def _get_event_bus(request: Request):
    """Get the event bus from app state."""
    bus = getattr(request.app.state, "obligation_event_bus", None)
    if bus is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Obligation event bus not initialized",
        )
    return bus


def _get_renewal_monitor(request: Request):
    """Get the renewal monitor from app state."""
    monitor = getattr(request.app.state, "renewal_monitor", None)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Renewal monitor not initialized",
        )
    return monitor


def _get_sla_tracker(request: Request):
    """Get the SLA tracker from app state."""
    tracker = getattr(request.app.state, "sla_tracker", None)
    if tracker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SLA tracker not initialized",
        )
    return tracker


def _get_insurance_monitor(request: Request):
    """Get the insurance monitor from app state."""
    monitor = getattr(request.app.state, "insurance_monitor", None)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Insurance monitor not initialized",
        )
    return monitor


def _get_compliance_monitor(request: Request):
    """Get the compliance monitor from app state."""
    monitor = getattr(request.app.state, "compliance_monitor", None)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Compliance monitor not initialized",
        )
    return monitor


def _get_litigation_monitor(request: Request):
    """Get the litigation monitor from app state."""
    monitor = getattr(request.app.state, "litigation_monitor", None)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Litigation monitor not initialized",
        )
    return monitor


def _get_forecast_engine(request: Request):
    """Get the forecast engine from app state."""
    engine = getattr(request.app.state, "renewal_forecast_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Renewal forecast engine not initialized",
        )
    return engine


# ── Obligation Event Bus Endpoints ───────────────────────────────────────────


@router.get("/events", summary="List obligation events")
async def list_events(
    request: Request,
    contract_id: Optional[str] = Query(None, description="Filter by contract"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    unresolved_only: bool = Query(False, description="Only unresolved events"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """List obligation events with optional filters."""
    bus = _get_event_bus(request)
    events = await bus.get_events(
        contract_id=contract_id,
        tenant_id=user.tenant_id,
        event_type=event_type,
        priority=priority,
        unresolved_only=unresolved_only,
        limit=limit,
        offset=offset,
    )
    return {
        "events": [e.to_dict() for e in events],
        "total": len(events),
        "limit": limit,
        "offset": offset,
    }


@router.get("/events/stats", summary="Event statistics")
async def get_event_stats(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get obligation event statistics."""
    bus = _get_event_bus(request)
    return await bus.get_event_stats(tenant_id=user.tenant_id)


@router.post("/events/{event_id}/acknowledge", summary="Acknowledge an event")
async def acknowledge_event(
    request: Request,
    event_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Acknowledge an obligation event."""
    bus = _get_event_bus(request)
    event = await bus.acknowledge_event(event_id, user.sub or "unknown")
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


@router.post("/events/{event_id}/resolve", summary="Resolve an event")
async def resolve_event(
    request: Request,
    event_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Resolve an obligation event."""
    bus = _get_event_bus(request)
    event = await bus.resolve_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


# ── Renewal Monitoring Endpoints ────────────────────────────────────────────


@router.get("/renewals", summary="List active renewal alerts")
async def list_renewal_alerts(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get active renewal alerts for the tenant."""
    monitor = _get_renewal_monitor(request)
    alerts = await monitor.get_active_alerts(user.tenant_id or "default")
    summary = await monitor.get_renewal_summary(user.tenant_id or "default")
    return {
        "alerts": alerts,
        "summary": summary,
    }


@router.post("/renewals/check", summary="Run renewal check")
async def run_renewal_check(
    request: Request,
    contracts: List[Dict[str, Any]],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Check contracts for upcoming renewals and emit events."""
    monitor = _get_renewal_monitor(request)
    events = await monitor.check_renewals(contracts, tenant_id=user.tenant_id)
    return {
        "events_emitted": len(events),
        "events": [e.to_dict() for e in events],
    }


@router.post("/renewals/configure", summary="Configure renewal alert lead times")
async def configure_renewal_alerts(
    request: Request,
    config: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Configure renewal alert lead times for the tenant."""
    monitor = _get_renewal_monitor(request)
    tenant_id = user.tenant_id or "default"
    monitor.configure_tenant(
        tenant_id=tenant_id,
        lead_time_days_90=config.get("lead_time_days_90", True),
        lead_time_days_60=config.get("lead_time_days_60", True),
        lead_time_days_30=config.get("lead_time_days_30", True),
        custom_lead_days=config.get("custom_lead_days"),
    )
    return {"status": "configured", "config": monitor.get_tenant_config(tenant_id)}


# ── SLA Tracking Endpoints ───────────────────────────────────────────────────


@router.get("/sla", summary="List SLA obligations")
async def list_sla_obligations(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get SLA breach risk report for the tenant."""
    tracker = _get_sla_tracker(request)
    report = await tracker.get_breach_risk_report(user.tenant_id or "default")
    return report


@router.post("/sla/register", summary="Register SLA obligations")
async def register_sla_obligations(
    request: Request,
    slas: List[Dict[str, Any]],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Register SLA obligations for tracking."""
    from continuous_monitoring.sla_tracker import SLAObligation

    tracker = _get_sla_tracker(request)
    registered = []
    for sla_data in slas:
        sla = SLAObligation(
            sla_id=sla_data.get("sla_id", f"sla-{len(registered)}"),
            contract_id=sla_data["contract_id"],
            tenant_id=user.tenant_id or "default",
            title=sla_data["title"],
            description=sla_data.get("description", ""),
            category=sla_data.get("category", "general"),
            target_value=sla_data.get("target_value", ""),
            due_date=sla_data.get("due_date"),
            severity=sla_data.get("severity", "medium"),
            assigned_to=sla_data.get("assigned_to"),
        )
        sla_id = await tracker.register_obligation(sla)
        registered.append(sla_id)

    return {"registered": len(registered), "sla_ids": registered}


@router.post("/sla/check", summary="Run SLA deadline check")
async def run_sla_check(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Check all SLA obligations for approaching deadlines."""
    tracker = _get_sla_tracker(request)
    alerts = await tracker.check_deadlines()
    return {
        "alerts_generated": len(alerts),
        "alerts": alerts,
    }


@router.get("/sla/{sla_id}/escalation", summary="Get SLA escalation path")
async def get_sla_escalation(
    request: Request,
    sla_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get the escalation path for an SLA obligation."""
    tracker = _get_sla_tracker(request)
    return await tracker.get_escalation_path(sla_id)


# ── Insurance Monitoring Endpoints ───────────────────────────────────────────


@router.get("/insurance", summary="List insurance certificates")
async def list_insurance_certificates(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get insurance expiration report for the tenant."""
    monitor = _get_insurance_monitor(request)
    report = await monitor.get_expiration_report(user.tenant_id or "default")
    return report


@router.post("/insurance/register", summary="Register insurance certificates")
async def register_insurance_certificates(
    request: Request,
    certificates: List[Dict[str, Any]],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Register insurance certificates for monitoring."""
    from continuous_monitoring.insurance_monitor import InsuranceCertificate

    monitor = _get_insurance_monitor(request)
    registered = []
    for cert_data in certificates:
        cert = InsuranceCertificate(
            cert_id=cert_data.get("cert_id", f"cert-{len(registered)}"),
            contract_id=cert_data["contract_id"],
            tenant_id=user.tenant_id or "default",
            provider=cert_data["provider"],
            policy_type=cert_data.get("policy_type", "general_liability"),
            policy_number=cert_data["policy_number"],
            coverage_amount=cert_data.get("coverage_amount"),
            effective_date=cert_data.get("effective_date"),
            expiration_date=cert_data.get("expiration_date"),
            min_coverage_required=cert_data.get("min_coverage_required"),
        )
        cert_id = await monitor.register_certificate(cert)
        registered.append(cert_id)

    return {"registered": len(registered), "cert_ids": registered}


@router.post("/insurance/check", summary="Run insurance expiration check")
async def run_insurance_check(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Check all insurance certificates for approaching expirations."""
    monitor = _get_insurance_monitor(request)
    alerts = await monitor.check_expirations()
    return {
        "alerts_generated": len(alerts),
        "alerts": alerts,
    }


# ── Compliance Monitoring Endpoints ──────────────────────────────────────────


@router.get("/compliance/frameworks", summary="List regulatory frameworks")
async def list_frameworks(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all available regulatory frameworks."""
    monitor = _get_compliance_monitor(request)
    return {"frameworks": monitor.get_available_frameworks()}


@router.post("/compliance/check", summary="Run compliance check")
async def run_compliance_check(
    request: Request,
    contract_id: str = Query(..., description="Contract ID"),
    framework: str = Query(..., description="Regulatory framework key"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Check a contract's compliance against a regulatory framework."""
    body = await request.json()
    clauses = body.get("clauses", [])
    contract_id = body.get("contract_id", contract_id)
    framework = body.get("framework", framework)
    monitor = _get_compliance_monitor(request)
    result = await monitor.check_compliance(
        contract_id=contract_id,
        tenant_id=user.tenant_id or "default",
        clauses=clauses,
        framework=framework,
    )
    return result.to_dict()


@router.get("/compliance/drift-report", summary="Compliance drift report")
async def get_compliance_drift_report(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get compliance drift report for the tenant."""
    monitor = _get_compliance_monitor(request)
    return await monitor.get_drift_report(user.tenant_id or "default")


# ── Counterparty Litigation Endpoints ────────────────────────────────────────


@router.get("/counterparties", summary="List monitored counterparties")
async def list_counterparties(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get counterparty monitoring summary for the tenant."""
    monitor = _get_litigation_monitor(request)
    return await monitor.get_all_counterparty_summary(user.tenant_id or "default")


@router.get("/counterparties/{counterparty_id}", summary="Counterparty report")
async def get_counterparty_report(
    request: Request,
    counterparty_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get comprehensive report for a counterparty."""
    monitor = _get_litigation_monitor(request)
    return await monitor.get_counterparty_report(counterparty_id)


@router.post("/counterparties/register", summary="Register counterparty")
async def register_counterparty(
    request: Request,
    counterparty: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Register a counterparty for litigation monitoring."""
    from continuous_monitoring.litigation_monitor import CounterpartyProfile

    monitor = _get_litigation_monitor(request)
    profile = CounterpartyProfile(
        counterparty_id=counterparty.get("counterparty_id", f"cp-{counterparty.get('name', 'unknown')}"),
        name=counterparty["name"],
        tenant_id=user.tenant_id or "default",
        duns_number=counterparty.get("duns_number"),
        credit_rating=counterparty.get("credit_rating"),
        credit_score=counterparty.get("credit_score"),
    )
    cp_id = await monitor.register_counterparty(profile)

    # Link to contracts if provided
    for contract_id in counterparty.get("contract_ids", []):
        await monitor.link_counterparty_to_contract(contract_id, cp_id)

    return {"counterparty_id": cp_id, "status": "registered"}


# ── Renewal Forecasting Endpoints ────────────────────────────────────────────


@router.post("/forecast", summary="Forecast contract renewal")
async def forecast_renewal(
    request: Request,
    contract_data: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Generate a renewal forecast for a contract."""
    engine = _get_forecast_engine(request)
    contract_data["tenant_id"] = user.tenant_id or "default"
    forecast = await engine.forecast_renewal(contract_data)
    return forecast.to_dict()


@router.post("/forecast/portfolio", summary="Forecast portfolio renewals")
async def forecast_portfolio(
    request: Request,
    contracts: List[Dict[str, Any]],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Generate renewal forecasts for a portfolio of contracts."""
    engine = _get_forecast_engine(request)
    return await engine.forecast_portfolio(contracts, user.tenant_id or "default")


@router.get("/forecast/portfolio", summary="Get portfolio forecast summary")
async def get_portfolio_forecast(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get portfolio-level renewal forecast summary."""
    engine = _get_forecast_engine(request)
    return await engine.get_portfolio_forecast(user.tenant_id or "default")


@router.get("/forecast/{forecast_id}", summary="Get forecast by ID")
async def get_forecast_by_id(
    request: Request,
    forecast_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get a specific renewal forecast by ID."""
    engine = _get_forecast_engine(request)
    forecast = await engine.get_forecast(forecast_id)
    if forecast is None:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return forecast.to_dict()


# ── Monitoring Dashboard Endpoints ───────────────────────────────────────────


@router.get("/dashboard", summary="Monitoring dashboard overview")
async def get_monitoring_dashboard(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get a consolidated monitoring dashboard overview for the tenant.

    Aggregates data from all monitoring subsystems into a single
    dashboard response for the obligations calendar view.
    """
    tenant_id = user.tenant_id or "default"

    # Gather data from all monitors
    dashboard: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }

    # Event bus stats
    try:
        bus = _get_event_bus(request)
        dashboard["event_stats"] = await bus.get_event_stats(tenant_id)
    except HTTPException:
        dashboard["event_stats"] = {"error": "not_available"}

    # Renewal summary
    try:
        monitor = _get_renewal_monitor(request)
        dashboard["renewals"] = await monitor.get_renewal_summary(tenant_id)
    except HTTPException:
        dashboard["renewals"] = {"error": "not_available"}

    # SLA report
    try:
        tracker = _get_sla_tracker(request)
        dashboard["sla"] = await tracker.get_breach_risk_report(tenant_id)
    except HTTPException:
        dashboard["sla"] = {"error": "not_available"}

    # Insurance report
    try:
        ins = _get_insurance_monitor(request)
        dashboard["insurance"] = await ins.get_expiration_report(tenant_id)
    except HTTPException:
        dashboard["insurance"] = {"error": "not_available"}

    # Compliance drift
    try:
        comp = _get_compliance_monitor(request)
        dashboard["compliance"] = await comp.get_drift_report(tenant_id)
    except HTTPException:
        dashboard["compliance"] = {"error": "not_available"}

    # Counterparty summary
    try:
        cp = _get_litigation_monitor(request)
        dashboard["counterparties"] = await cp.get_all_counterparty_summary(tenant_id)
    except HTTPException:
        dashboard["counterparties"] = {"error": "not_available"}

    # Forecast summary
    try:
        fc = _get_forecast_engine(request)
        dashboard["forecast"] = await fc.get_portfolio_forecast(tenant_id)
    except HTTPException:
        dashboard["forecast"] = {"error": "not_available"}

    return dashboard


@router.get("/calendar", summary="Obligations calendar view")
async def get_obligations_calendar(
    request: Request,
    months: int = Query(3, ge=1, le=12, description="Number of months to show"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get a calendar view of all upcoming obligation events.

    Returns events grouped by month for calendar rendering.
    """
    bus = _get_event_bus(request)
    events = await bus.get_events(
        tenant_id=user.tenant_id,
        unresolved_only=True,
        limit=1000,
    )

    from datetime import datetime, timedelta
    today = datetime.utcnow()
    cutoff = today + timedelta(days=30 * months)

    # Filter events within the requested time range
    calendar_events = []
    for event in events:
        if event.due_date:
            try:
                due = datetime.fromisoformat(event.due_date)
                if today <= due <= cutoff:
                    calendar_events.append(event.to_dict())
            except (ValueError, TypeError):
                pass

    # Group by month
    months_data: Dict[str, List[Dict[str, Any]]] = {}
    for evt in calendar_events:
        try:
            due = datetime.fromisoformat(evt["due_date"])
            month_key = due.strftime("%Y-%m")
            if month_key not in months_data:
                months_data[month_key] = []
            months_data[month_key].append(evt)
        except (ValueError, TypeError):
            pass

    return {
        "tenant_id": user.tenant_id,
        "months_shown": months,
        "total_events": len(calendar_events),
        "calendar": {
            month: {
                "events": events_list,
                "count": len(events_list),
            }
            for month, events_list in sorted(months_data.items())
        },
    }


# ── Sprint 12: Semantic Search Endpoints ─────────────────────────────────────


def _get_semantic_search(request: Request):
    """Get the semantic search engine from app state."""
    engine = getattr(request.app.state, "semantic_search_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search engine not initialized",
        )
    return engine


def _get_search_index(request: Request):
    """Get the search index pipeline from app state."""
    pipeline = getattr(request.app.state, "search_index_pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search index pipeline not initialized",
        )
    return pipeline


def _get_cost_governance(request: Request):
    """Get the cost governance system from app state."""
    gov = getattr(request.app.state, "cost_governance", None)
    if gov is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cost governance not initialized",
        )
    return gov


def _get_model_router(request: Request):
    """Get the model router from app state."""
    router_inst = getattr(request.app.state, "model_router", None)
    if router_inst is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model router not initialized",
        )
    return router_inst


def _get_batch_scheduler(request: Request):
    """Get the batch scheduler from app state."""
    scheduler = getattr(request.app.state, "batch_scheduler", None)
    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batch scheduler not initialized",
        )
    return scheduler


# ── Semantic Search ──────────────────────────────────────────────────────────


@router.post("/search", summary="Cross-contract semantic search")
async def semantic_search(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Execute a semantic search across all contracts."""
    body = await request.json()
    query = body.get("query", "")
    filters = body.get("filters")
    max_results = body.get("max_results", 20)
    engine = _get_semantic_search(request)
    return await engine.search(
        query=query,
        tenant_id=user.tenant_id or "default",
        filters=filters,
        max_results=max_results,
    )


@router.get("/search/history", summary="Search history")
async def get_search_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get recent search history for the tenant."""
    engine = _get_semantic_search(request)
    history = await engine.get_search_history(user.tenant_id or "default", limit)
    popular = await engine.get_popular_searches(user.tenant_id or "default")
    return {"history": history, "popular_searches": popular}


@router.get("/search/index/status", summary="Search index status")
async def get_search_index_status(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get the search index pipeline status."""
    pipeline = _get_search_index(request)
    return await pipeline.get_index_status(user.tenant_id or "default")


@router.post("/search/index/rebuild", summary="Rebuild search index")
async def rebuild_search_index(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Rebuild the search index for the tenant."""
    pipeline = _get_search_index(request)
    return await pipeline.rebuild_index(user.tenant_id or "default")


# ── Cost Governance ──────────────────────────────────────────────────────────


@router.get("/costs/dashboard", summary="Cost governance dashboard")
async def get_cost_dashboard(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get the AI cost governance dashboard."""
    gov = _get_cost_governance(request)
    return await gov.get_dashboard()


@router.get("/costs/tenant", summary="Tenant cost report")
async def get_tenant_cost_report(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get cost report for the current tenant."""
    gov = _get_cost_governance(request)
    return await gov.get_tenant_report(user.tenant_id or "default")


@router.post("/costs/record", summary="Record LLM usage")
async def record_llm_usage(
    request: Request,
    usage: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Record LLM usage and check quota."""
    gov = _get_cost_governance(request)
    return await gov.record_usage(
        tenant_id=usage.get("tenant_id", user.tenant_id or "default"),
        request_id=usage["request_id"],
        provider=usage["provider"],
        model=usage["model"],
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        duration_ms=usage.get("duration_ms", 0.0),
        cached=usage.get("cached", False),
    )


@router.post("/costs/quota", summary="Set tenant quota")
async def set_tenant_quota(
    request: Request,
    quota: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Set token quota for a tenant."""
    gov = _get_cost_governance(request)
    quota_obj = gov.set_tenant_quota(
        tenant_id=quota.get("tenant_id", user.tenant_id or "default"),
        soft_limit=quota["soft_limit"],
        hard_limit=quota["hard_limit"],
        period=quota.get("period", "monthly"),
    )
    return quota_obj.to_dict()


@router.get("/costs/alerts", summary="Cost alerts")
async def get_cost_alerts(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get active cost-related alerts."""
    gov = _get_cost_governance(request)
    alerts = await gov.get_alerts()
    return {"alerts": alerts, "total": len(alerts)}


# ── Model Routing ────────────────────────────────────────────────────────────


@router.get("/models", summary="List available models")
async def list_models(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get the model catalog."""
    router_inst = _get_model_router(request)
    return {"models": router_inst.get_model_catalog()}


@router.post("/models/select", summary="Select optimal model")
async def select_model(
    request: Request,
    selection: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Select the optimal model for a task."""
    router_inst = _get_model_router(request)
    return router_inst.select_model(
        task_type=selection["task_type"],
        complexity=selection["complexity"],
        tenant_id=selection.get("tenant_id", user.tenant_id),
        estimated_input_tokens=selection.get("estimated_input_tokens", 1000),
        estimated_output_tokens=selection.get("estimated_output_tokens", 500),
        required_capabilities=selection.get("required_capabilities"),
    )


@router.get("/models/rules", summary="Get routing rules")
async def get_routing_rules(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get the current model routing rules."""
    router_inst = _get_model_router(request)
    return {"rules": router_inst.get_routing_rules()}


# ── Batch Inference ──────────────────────────────────────────────────────────


@router.post("/batch/submit", summary="Submit batch job")
async def submit_batch_job(
    request: Request,
    job: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Submit a batch inference job."""
    from continuous_monitoring.batch_scheduler import JobPriority

    scheduler = _get_batch_scheduler(request)
    job_id = await scheduler.submit_job(
        tenant_id=job.get("tenant_id", user.tenant_id or "default"),
        job_type=job["job_type"],
        items=job["items"],
        priority=JobPriority(job.get("priority", "normal")),
        created_by=user.sub,
    )
    return {"job_id": job_id, "status": "submitted"}


@router.get("/batch/{job_id}", summary="Get batch job status")
async def get_batch_job(
    request: Request,
    job_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get the status and results of a batch job."""
    scheduler = _get_batch_scheduler(request)
    job_data = await scheduler.get_job(job_id)
    if job_data is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_data


@router.post("/batch/{job_id}/cancel", summary="Cancel batch job")
async def cancel_batch_job(
    request: Request,
    job_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Cancel a pending batch job."""
    scheduler = _get_batch_scheduler(request)
    cancelled = await scheduler.cancel_job(job_id)
    return {"job_id": job_id, "cancelled": cancelled}


@router.get("/batch/queue/status", summary="Batch queue status")
async def get_batch_queue_status(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get the batch queue status."""
    scheduler = _get_batch_scheduler(request)
    return await scheduler.get_queue_status(tenant_id=user.tenant_id)


# ── Sprint 13: Benchmark Corpus Pipeline (V2-031) ────────────────────────────


def _get_benchmark_corpus(request: Request):
    pipeline = getattr(request.app.state, "benchmark_corpus_pipeline", None)
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Benchmark corpus pipeline not initialized")
    return pipeline


@router.post("/benchmark/corpus/agree", summary="Opt-in to benchmark contribution")
async def opt_in_benchmark(
    request: Request,
    agreement: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Register tenant agreement to contribute anonymized benchmark data."""
    pipeline = _get_benchmark_corpus(request)
    result = await pipeline.register_agreement(
        tenant_id=user.tenant_id or "default",
        organization_name=agreement["organization_name"],
        scope=agreement.get("scope", "full"),
        data_categories=agreement.get("data_categories"),
        anonymization_level=agreement.get("anonymization_level", "high"),
    )
    return result.to_dict()


@router.post("/benchmark/corpus/contribute", summary="Contribute contract to benchmark")
async def contribute_to_benchmark(
    request: Request,
    contribution: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Contribute a contract's anonymized data to the benchmark corpus."""
    pipeline = _get_benchmark_corpus(request)
    return await pipeline.contribute_contract(
        tenant_id=user.tenant_id or "default",
        contract_id=contribution["contract_id"],
        contract_type=contribution.get("contract_type", "other"),
        clauses=contribution.get("clauses", []),
    )


@router.get("/benchmark/corpus/contributions", summary="Tenant contribution history")
async def get_benchmark_contributions(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get contribution history for the tenant."""
    pipeline = _get_benchmark_corpus(request)
    return await pipeline.get_tenant_contributions(user.tenant_id or "default")


@router.get("/benchmark/corpus/stats", summary="Corpus statistics")
async def get_benchmark_corpus_stats(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get overall benchmark corpus statistics."""
    pipeline = _get_benchmark_corpus(request)
    return await pipeline.get_corpus_stats()


# ── Sprint 13: Industry Segmentation (V2-032) ────────────────────────────────


def _get_industry_segmentation(request: Request):
    seg = getattr(request.app.state, "industry_segmentation", None)
    if seg is None:
        raise HTTPException(status_code=503, detail="Industry segmentation not initialized")
    return seg


@router.get("/benchmark/industries", summary="List industry verticals")
async def list_industries(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all available industry verticals for segmentation."""
    seg = _get_industry_segmentation(request)
    return await seg.get_all_verticals()


@router.post("/benchmark/industries/classify", summary="Classify contract industry")
async def classify_industry(
    request: Request,
    data: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Classify a contract into an industry vertical."""
    seg = _get_industry_segmentation(request)
    return await seg.classify_industry(
        contract_text=data["contract_text"],
        contract_type=data.get("contract_type"),
    )


@router.get("/benchmark/industries/{industry}/segments", summary="Segment benchmarks")
async def get_industry_benchmarks(
    request: Request,
    industry: str,
    sub_vertical: Optional[str] = Query(None),
    user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get benchmark data for an industry segment."""
    seg = _get_industry_segmentation(request)
    return await seg.get_segment_benchmarks(industry, sub_vertical)


# ── Sprint 13: Benchmark Confidence Scoring (V2-033) ─────────────────────────


def _get_benchmark_confidence(request: Request):
    scorer = getattr(request.app.state, "benchmark_confidence_scorer", None)
    if scorer is None:
        raise HTTPException(status_code=503, detail="Benchmark confidence scorer not initialized")
    return scorer


@router.post("/benchmark/confidence", summary="Compute benchmark confidence")
async def compute_benchmark_confidence(
    request: Request,
    data: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Compute confidence score for a benchmark segment."""
    scorer = _get_benchmark_confidence(request)
    confidence = scorer.compute_confidence(
        segment_id=data["segment_id"],
        segment_type=data.get("segment_type", "industry"),
        segment_name=data["segment_name"],
        sample_size=data["sample_size"],
        values=data.get("values", []),
        data_timestamp=data.get("data_timestamp"),
        variance=data.get("variance"),
    )
    return confidence.to_dict()


@router.get("/benchmark/confidence/{segment_id}", summary="Get reliability indicators")
async def get_reliability_indicators(
    request: Request,
    segment_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get reliability indicators for a benchmark segment."""
    scorer = _get_benchmark_confidence(request)
    return scorer.get_reliability_indicators(segment_id)


# ── Sprint 13: Procurement Integrations (V2-034) ─────────────────────────────


def _get_procurement_integration(request: Request):
    integration = getattr(request.app.state, "procurement_integration", None)
    if integration is None:
        raise HTTPException(status_code=503, detail="Procurement integration not initialized")
    return integration


@router.post("/procurement/configure", summary="Configure procurement platform")
async def configure_procurement(
    request: Request,
    config: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Configure a connection to SAP Ariba or Coupa."""
    from continuous_monitoring.procurement_integration import ProcurementPlatform, SyncDirection

    integration = _get_procurement_integration(request)
    result = await integration.configure_connection(
        tenant_id=user.tenant_id or "default",
        platform=ProcurementPlatform(config["platform"]),
        api_endpoint=config["api_endpoint"],
        api_key=config["api_key"],
        sync_direction=SyncDirection(config.get("sync_direction", "bidirectional")),
        sync_interval_minutes=config.get("sync_interval_minutes", 60),
        metadata_mapping=config.get("metadata_mapping"),
    )
    return result.to_dict()


@router.post("/procurement/import", summary="Import purchase orders")
async def import_purchase_orders(
    request: Request,
    platform: str = Query(..., description="Procurement platform (sap_ariba or coupa)"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Import purchase orders from a procurement platform."""
    from continuous_monitoring.procurement_integration import ProcurementPlatform

    integration = _get_procurement_integration(request)
    pos = await integration.import_purchase_orders(
        tenant_id=user.tenant_id or "default",
        platform=ProcurementPlatform(platform),
    )
    return {"purchase_orders": pos, "total": len(pos)}


@router.post("/procurement/link", summary="Link PO to contract")
async def link_po_to_contract(
    request: Request,
    link: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Link a purchase order to a contract for risk linkage."""
    integration = _get_procurement_integration(request)
    linked = await integration.link_po_to_contract(
        po_id=link["po_id"],
        contract_id=link["contract_id"],
    )
    return {"linked": linked}


@router.get("/procurement/risk-summary", summary="PO risk summary")
async def get_po_risk_summary(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get risk summary across purchase orders."""
    integration = _get_procurement_integration(request)
    return await integration.get_po_risk_summary(user.tenant_id or "default")


# ── Sprint 13: Vendor Onboarding (V2-035) ────────────────────────────────────


def _get_vendor_onboarding(request: Request):
    workflow = getattr(request.app.state, "vendor_onboarding_workflow", None)
    if workflow is None:
        raise HTTPException(status_code=503, detail="Vendor onboarding workflow not initialized")
    return workflow


@router.post("/vendors/onboard", summary="Initiate vendor onboarding")
async def initiate_vendor_onboarding(
    request: Request,
    vendor: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Initiate a new vendor onboarding request."""
    workflow = _get_vendor_onboarding(request)
    onboarding = await workflow.initiate_onboarding(
        tenant_id=user.tenant_id or "default",
        vendor_name=vendor["vendor_name"],
        vendor_email=vendor["vendor_email"],
        vendor_type=vendor.get("vendor_type", "supplier"),
        contract_value=vendor.get("contract_value", 0.0),
        currency=vendor.get("currency", "USD"),
        created_by=user.sub,
    )
    return onboarding.to_dict()


@router.post("/vendors/{onboarding_id}/risk-gate", summary="Run AI risk gate")
async def run_vendor_risk_gate(
    request: Request,
    onboarding_id: str,
    vendor_data: Optional[Dict[str, Any]] = None,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Run the AI risk gate review for a vendor onboarding."""
    workflow = _get_vendor_onboarding(request)
    result = await workflow.run_ai_risk_gate(onboarding_id, vendor_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Onboarding not found")
    return result


@router.post("/vendors/{onboarding_id}/advance", summary="Advance onboarding stage")
async def advance_onboarding_stage(
    request: Request,
    onboarding_id: str,
    action: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Advance the onboarding to the next stage."""
    workflow = _get_vendor_onboarding(request)
    onboarding = await workflow.advance_stage(
        onboarding_id=onboarding_id,
        approved=action.get("approved", True),
        performed_by=user.sub,
        notes=action.get("notes", ""),
    )
    if onboarding is None:
        raise HTTPException(status_code=404, detail="Onboarding not found")
    return onboarding.to_dict()


@router.get("/vendors/onboarding/pipeline", summary="Onboarding pipeline summary")
async def get_onboarding_pipeline(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get vendor onboarding pipeline summary."""
    workflow = _get_vendor_onboarding(request)
    return await workflow.get_pipeline_summary(user.tenant_id or "default")


# ── Sprint 13: Supplier Concentration (V2-036) ───────────────────────────────


def _get_supplier_analyzer(request: Request):
    analyzer = getattr(request.app.state, "supplier_concentration_analyzer", None)
    if analyzer is None:
        raise HTTPException(status_code=503, detail="Supplier concentration analyzer not initialized")
    return analyzer


@router.post("/suppliers/analyze", summary="Analyze supplier concentration")
async def analyze_supplier_concentration(
    request: Request,
    contracts: List[Dict[str, Any]],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Analyze supplier concentration across a contract portfolio."""
    analyzer = _get_supplier_analyzer(request)
    return await analyzer.analyze_portfolio(contracts)


@router.get("/suppliers/heatmap", summary="Supplier risk heatmap")
async def get_supplier_heatmap(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Generate supplier risk heatmap data."""
    analyzer = _get_supplier_analyzer(request)
    return await analyzer.generate_heatmap(user.tenant_id or "default")


@router.get("/suppliers/concentration-report", summary="Concentration report")
async def get_concentration_report(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Generate complete supplier concentration report."""
    analyzer = _get_supplier_analyzer(request)
    return await analyzer.get_report(user.tenant_id or "default")


@router.get("/suppliers/category-analysis", summary="Category concentration analysis")
async def get_category_analysis(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get concentration analysis by contract category."""
    analyzer = _get_supplier_analyzer(request)
    return {"categories": await analyzer.get_category_analysis()}


# ── Sprint 13: V2.2 Launch Readiness QA (V2-038) ────────────────────────────


@router.post("/qa/sweep", summary="Run V2.2 QA sweep")
async def run_qa_sweep(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Run the complete V2.2 launch readiness QA sweep."""
    from continuous_monitoring.qa_readiness import run_qa_sweep as _run_sweep

    report = await _run_sweep()
    return report


@router.get("/qa/status", summary="Launch readiness status")
async def get_launch_readiness(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get V2.2 launch readiness status summary."""
    # Check all critical modules are importable
    critical_modules = [
        ("api.main", "FastAPI Application"),
        ("api.middleware.auth", "Auth Middleware"),
        ("api.routers.contracts", "Contracts Router"),
        ("api.routers.risks", "Risks Router"),
        ("api.routers.relationships", "Relationships Router"),
        ("api.routers.continuous_monitoring", "Monitoring Router"),
        ("api.continuous_monitoring.event_bus", "Event Bus"),
        ("api.continuous_monitoring.semantic_search", "Semantic Search"),
        ("api.continuous_monitoring.cost_governance", "Cost Governance"),
        ("api.continuous_monitoring.procurement_integration", "Procurement Integration"),
        ("api.continuous_monitoring.vendor_onboarding", "Vendor Onboarding"),
        ("api.continuous_monitoring.supplier_concentration", "Supplier Analysis"),
        ("api.continuous_monitoring.qa_readiness", "QA Readiness"),
    ]

    import importlib
    statuses = []
    all_ok = True
    for module_path, module_name in critical_modules:
        try:
            importlib.import_module(module_path)
            statuses.append({"module": module_name, "status": "ok"})
        except Exception as exc:
            statuses.append({"module": module_name, "status": "error", "error": str(exc)})
            all_ok = False

    return {
        "v2_2_launch_readiness": "ready" if all_ok else "issues_detected",
        "all_modules_ok": all_ok,
        "module_count": len(critical_modules),
        "modules": statuses,
        "recommendation": "Proceed with launch" if all_ok else "Review module errors before launch",
    }
