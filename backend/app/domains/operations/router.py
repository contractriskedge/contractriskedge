"""Operations & Observability API router.

Endpoints:
  GET  /api/v1/operations/health          — System Health Dashboard (all services)
  GET  /api/v1/operations/health/{service} — Single service health
  GET  /api/v1/operations/queues           — Queue status
  GET  /api/v1/operations/scheduler        — Scheduler status
  GET  /api/v1/operations/integrations     — Integration health
  GET  /api/v1/operations/errors           — Error dashboard
  GET  /api/v1/operations/slow             — Slow operations
  GET  /api/v1/operations/alerts           — Active alerts
  POST /api/v1/operations/support-bundle   — Generate support bundle ZIP
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.domains.operations.service import (
    health_registry,
    get_queue_status,
    get_scheduler_status,
    get_integration_health,
    get_error_dashboard,
    get_slow_operations,
    evaluate_alerts,
    generate_support_bundle,
)

router = APIRouter(prefix="/api/v1/operations", tags=["Operations"])


@router.get("/health")
async def system_health(request: Request):
    """Get health status for all services."""
    health = await health_registry.run_all(request.app.state)

    # Compute overall status
    statuses = [s["status"] for s in health.values()]
    if any(s == "failed" for s in statuses):
        overall = "critical"
    elif any(s == "warning" or s == "degraded" for s in statuses):
        overall = "warning"
    else:
        overall = "healthy"

    # Count healthy vs total
    healthy_count = sum(1 for s in statuses if s == "healthy")
    total_count = len(statuses)

    uptime = 0.0
    if hasattr(request.app.state, "startup_time"):
        import time
        uptime = time.time() - request.app.state.startup_time

    return {
        "status": overall,
        "uptime_seconds": round(uptime, 2),
        "version": "1.0.0",
        "environment": request.app.state.environment,
        "healthy_count": healthy_count,
        "total_count": total_count,
        "tenant_count": None,  # Populated if tenant service available
        "services": health,
    }


@router.get("/health/{service}")
async def service_health(request: Request, service: str):
    """Get health status for a single service."""
    health = await health_registry.run_all(request.app.state)
    if service not in health:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")
    return health[service]


@router.get("/queues")
async def queue_status(request: Request):
    """Get background queue depths and status."""
    return await get_queue_status(request.app.state)


@router.get("/scheduler")
async def scheduler_status(request: Request):
    """Get scheduled task status."""
    return await get_scheduler_status(request.app.state)


@router.get("/integrations")
async def integration_health(request: Request):
    """Get health status for all external integrations."""
    return await get_integration_health(request.app.state)


@router.get("/errors")
async def error_dashboard(request: Request):
    """Get error categorization and trends."""
    return await get_error_dashboard(request.app.state)


@router.get("/slow")
async def slow_operations(request: Request):
    """Get top 20 slowest operations by category."""
    return await get_slow_operations(request.app.state)


@router.get("/alerts")
async def alerts(request: Request):
    """Get active alerts based on current system state."""
    return await evaluate_alerts(request.app.state)


@router.post("/support-bundle")
async def support_bundle(request: Request):
    """Generate and download a support bundle ZIP."""
    bundle = await generate_support_bundle(request.app.state)
    return StreamingResponse(
        bundle,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=support-bundle-{request.app.state.environment}.zip",
            "Cache-Control": "no-cache",
        },
    )
