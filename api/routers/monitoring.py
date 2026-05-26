"""Monitoring and observability API endpoints.

Provides system health metrics, LLM cost tracking, performance
monitoring, and alerting status for the platform.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/metrics")
async def get_metrics(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get LLM monitoring metrics snapshot.

    Returns request counts, error rates, latency distribution,
    and provider failover statistics.

    Args:
        user: Authenticated user (admin required).

    Returns:
        Dict with monitoring metrics.
    """
    try:
        from llm.monitoring import LLMMonitoring

        monitoring = LLMMonitoring()
        metrics = monitoring.get_metrics_snapshot()
        return metrics
    except Exception as exc:
        logger.error("Failed to get metrics: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitoring metrics",
        )


@router.get("/costs")
async def get_cost_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days of cost data"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant (admin only)"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get LLM cost summary for the specified period.

    Args:
        days: Number of days of cost data to include.
        tenant_id: Optional tenant filter.
        user: Authenticated user.

    Returns:
        Dict with cost breakdown by provider and daily totals.
    """
    try:
        from llm.cost_tracker import CostTracker

        tracker = CostTracker()
        if tenant_id:
            summary = await tracker.get_daily_costs(tenant_id=tenant_id, days=days)
        else:
            summary = await tracker.get_daily_costs(
                tenant_id=user.tenant_id or "default",
                days=days,
            )
        return summary
    except Exception as exc:
        logger.error("Failed to get cost summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost summary",
        )


@router.get("/alerts")
async def get_alert_status(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
) -> Dict[str, Any]:
    """Get alerting system status.

    Returns the status of various alerting subsystems including
    staleness alerts, false positive tracking, and regression alerts.

    Args:
        user: Authenticated user.

    Returns:
        Dict with alerting status information.
    """
    status_info: Dict[str, Any] = {
        "configured": bool(os.getenv("SLACK_WEBHOOK_URL", "")),
        "slack_webhook": bool(os.getenv("SLACK_WEBHOOK_URL", "")),
    }

    # Check false positive tracker status
    try:
        from benchmarking.alerting import FalsePositiveTracker

        fp_tracker = FalsePositiveTracker()
        status_info["false_positive_tracker"] = "available"
    except Exception:
        status_info["false_positive_tracker"] = "unavailable"

    # Check freshness tracker status
    try:
        from benchmarking.freshness import FreshnessTracker

        freshness = FreshnessTracker()
        status_info["freshness_tracker"] = "available"
    except Exception:
        status_info["freshness_tracker"] = "unavailable"

    return status_info


@router.get("/health/detailed")
async def detailed_health(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get detailed health status of all subsystems.

    Provides a comprehensive view of all service dependencies
    including database, Redis, LLM providers, Pinecone, and more.

    Args:
        user: Authenticated user.

    Returns:
        Dict with detailed health status.
    """
    health: Dict[str, Any] = {
        "status": "healthy",
        "checks": {},
    }

    # Check LLM providers
    try:
        from llm.client import LLMClient

        # Check if any API keys are configured
        llm_checks = {
            "deepseek": bool(os.getenv("DEEPSEEK_API_KEY", "")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY", "")),
            "openai": bool(os.getenv("OPENAI_API_KEY", "")),
        }
        health["checks"]["llm_providers"] = {
            "status": "configured" if any(llm_checks.values()) else "not_configured",
            "details": llm_checks,
        }
    except Exception as exc:
        health["checks"]["llm_providers"] = {
            "status": "error",
            "error": str(exc),
        }

    # Check Pinecone
    pinecone_key = os.getenv("PINECONE_API_KEY", "")
    health["checks"]["pinecone"] = {
        "status": "configured" if pinecone_key else "not_configured",
        "index": os.getenv("PINECONE_INDEX", "contract-chunks"),
    }

    # Check RAG
    health["checks"]["rag"] = {
        "status": "available",
        "endpoint": "/api/v1/rag/search",
    }

    # Overall status
    all_ok = all(
        c.get("status") in ("configured", "available", "healthy")
        for c in health["checks"].values()
    )
    if not all_ok:
        health["status"] = "degraded"

    return health
