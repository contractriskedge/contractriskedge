"""Health check endpoints for liveness and readiness probes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(request: Request):
    """Liveness probe — returns 200 if the application is running."""
    uptime = time.time() - request.app.state.startup_time
    db_factory = getattr(request.app.state, "db_factory", None)
    pool_stats = db_factory.pool_stats if db_factory else {}

    return {
        "status": "healthy",
        "service": "contractrisk-api",
        "version": "1.0.0",
        "uptime_seconds": round(uptime, 2),
        "environment": request.app.state.environment,
        "database": {
            "ready": request.app.state.db_ready,
            "pool": pool_stats,
        },
    }


@router.get("/ready")
async def readiness_check(request: Request):
    """Readiness probe — returns 200 if the application is ready to serve traffic."""
    db_ok = request.app.state.db_ready
    db_factory = getattr(request.app.state, "db_factory", None)
    pool_stats = db_factory.pool_stats if db_factory else {}

    return {
        "status": "ready" if db_ok else "not_ready",
        "database": {
            "connected": db_ok,
            "pool": pool_stats,
        },
    }
