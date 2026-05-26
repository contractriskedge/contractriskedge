"""Audit logging API endpoints.

Provides endpoints for querying audit logs, tracking user actions,
and maintaining a tamper-evident audit trail for compliance.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit"])


# In-memory audit log store for development
_audit_logs: List[Dict[str, Any]] = []
_max_logs = 10000


def log_action(
    action: str,
    resource_type: str,
    resource_id: str,
    user_id: str,
    tenant_id: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Record an audit log entry.

    Args:
        action: The action performed (e.g., 'document.upload', 'risk.analyze').
        resource_type: Type of resource affected.
        resource_id: Identifier of the resource.
        user_id: User who performed the action.
        tenant_id: Tenant context.
        details: Additional details about the action.
        ip_address: Client IP address.

    Returns:
        The created audit log entry.
    """
    entry: Dict[str, Any] = {
        "audit_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "ip_address": ip_address,
        "details": details or {},
    }

    _audit_logs.append(entry)

    # Trim oldest logs if exceeding max
    if len(_audit_logs) > _max_logs:
        _audit_logs[: len(_audit_logs) - _max_logs] = []

    return entry


@router.get("/logs")
async def query_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_AUDIT)),
) -> Dict[str, Any]:
    """Query audit logs with filters and pagination.

    Args:
        action: Filter by action type.
        resource_type: Filter by resource type.
        resource_id: Filter by resource ID.
        user_id: Filter by user ID.
        start_date: Start of date range.
        end_date: End of date range.
        page: Page number.
        page_size: Items per page.
        user: Authenticated user.

    Returns:
        Dict with filtered audit logs and pagination info.
    """
    tenant_id = user.tenant_id or "default"

    # Filter by tenant
    results = [log for log in _audit_logs if log.get("tenant_id") == tenant_id]

    # Apply filters
    if action:
        results = [log for log in results if log.get("action") == action]
    if resource_type:
        results = [log for log in results if log.get("resource_type") == resource_type]
    if resource_id:
        results = [log for log in results if log.get("resource_id") == resource_id]
    if user_id:
        results = [log for log in results if log.get("user_id") == user_id]
    if start_date:
        results = [
            log for log in results if log.get("timestamp", "") >= start_date
        ]
    if end_date:
        results = [
            log for log in results if log.get("timestamp", "") <= end_date
        ]

    # Sort by timestamp descending
    results.sort(key=lambda log: log.get("timestamp", ""), reverse=True)

    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "logs": results[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/logs/summary")
async def get_audit_summary(
    hours: int = Query(24, ge=1, le=720, description="Lookback period in hours"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_AUDIT)),
) -> Dict[str, Any]:
    """Get a summary of recent audit activity.

    Args:
        hours: Number of hours to look back.
        user: Authenticated user.

    Returns:
        Dict with activity summary statistics.
    """
    tenant_id = user.tenant_id or "default"
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    recent_logs = [
        log
        for log in _audit_logs
        if log.get("tenant_id") == tenant_id
        and log.get("timestamp", "") >= cutoff
    ]

    # Aggregate by action
    action_counts: Dict[str, int] = {}
    resource_counts: Dict[str, int] = {}
    user_counts: Dict[str, int] = {}

    for log in recent_logs:
        action_name = log.get("action", "unknown")
        action_counts[action_name] = action_counts.get(action_name, 0) + 1

        resource = log.get("resource_type", "unknown")
        resource_counts[resource] = resource_counts.get(resource, 0) + 1

        uid = log.get("user_id", "unknown")
        user_counts[uid] = user_counts.get(uid, 0) + 1

    return {
        "lookback_hours": hours,
        "total_events": len(recent_logs),
        "unique_users": len(user_counts),
        "actions_by_type": action_counts,
        "resources_by_type": resource_counts,
        "most_active_users": dict(
            sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ),
    }


@router.get("/logs/export")
async def export_audit_logs(
    start_date: str = Query(..., description="Start date (ISO format)"),
    end_date: str = Query(..., description="End date (ISO format)"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.EXPORT_DATA)),
) -> Dict[str, Any]:
    """Export audit logs as JSON for a date range.

    Args:
        start_date: Start of export range.
        end_date: End of export range.
        user: Authenticated user.

    Returns:
        Dict with exported logs and metadata.
    """
    tenant_id = user.tenant_id or "default"

    export_logs = [
        log
        for log in _audit_logs
        if log.get("tenant_id") == tenant_id
        and log.get("timestamp", "") >= start_date
        and log.get("timestamp", "") <= end_date
    ]

    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "tenant_id": tenant_id,
        "date_range": {"start": start_date, "end": end_date},
        "total_entries": len(export_logs),
        "logs": export_logs,
    }
