"""Webhook management API endpoints.

Provides endpoints for registering, listing, and deleting webhook
endpoints that receive notifications on ingestion job completion.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# In-memory webhook registration store for development
_webhook_registrations: Dict[str, Dict[str, Any]] = {}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_webhook(
    url: str = Query(..., description="Webhook callback URL"),
    secret: Optional[str] = Query(None, description="Secret for HMAC signing"),
    events: List[str] = Query(
        ["ingestion.completed", "ingestion.failed"],
        description="Events to subscribe to",
    ),
    description: Optional[str] = Query(None, description="Webhook description"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_INTEGRATIONS)),
) -> Dict[str, Any]:
    """Register a new webhook endpoint.

    Args:
        url: The webhook callback URL (must be HTTPS).
        secret: Optional secret for HMAC-SHA256 signing.
        events: List of events to subscribe to.
        description: Optional description.
        user: Authenticated user.

    Returns:
        Dict with webhook registration details.

    Raises:
        HTTPException: If URL is invalid.
    """
    # Validate URL
    if not url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL must use HTTPS",
        )

    # Validate events
    valid_events = {"ingestion.completed", "ingestion.failed", "risk.analyzed", "redline.created"}
    invalid_events = [e for e in events if e not in valid_events]
    if invalid_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid events: {invalid_events}. Valid: {valid_events}",
        )

    webhook_id = str(uuid.uuid4())
    tenant_id = user.tenant_id or "default"

    registration: Dict[str, Any] = {
        "webhook_id": webhook_id,
        "tenant_id": tenant_id,
        "user_id": user.sub,
        "url": url,
        "events": events,
        "description": description or "",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    if secret:
        registration["has_secret"] = True
        # Store a hash of the secret for verification; not the secret itself
        registration["secret_hash"] = hashlib.sha256(
            secret.encode("utf-8")
        ).hexdigest()
    else:
        registration["has_secret"] = False

    _webhook_registrations[webhook_id] = registration

    logger.info(
        "Webhook registered: %s for tenant %s, events: %s",
        webhook_id,
        tenant_id,
        events,
    )

    return registration


@router.get("/")
async def list_webhooks(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_INTEGRATIONS)),
) -> Dict[str, Any]:
    """List registered webhooks for the current tenant.

    Args:
        user: Authenticated user.

    Returns:
        Dict with webhook registrations.
    """
    tenant_id = user.tenant_id or "default"

    webhooks = [
        wh
        for wh in _webhook_registrations.values()
        if wh.get("tenant_id") == tenant_id
    ]

    return {
        "webhooks": webhooks,
        "total": len(webhooks),
    }


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_INTEGRATIONS)),
) -> Dict[str, Any]:
    """Get a specific webhook registration.

    Args:
        webhook_id: The webhook identifier.
        user: Authenticated user.

    Returns:
        Webhook registration details.
    """
    webhook = _webhook_registrations.get(webhook_id)
    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    if webhook.get("tenant_id") != (user.tenant_id or "default"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return webhook


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    url: Optional[str] = Query(None, description="New webhook URL"),
    events: Optional[List[str]] = Query(None, description="Updated event list"),
    is_active: Optional[bool] = Query(None, description="Activate/deactivate"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_INTEGRATIONS)),
) -> Dict[str, Any]:
    """Update a webhook registration.

    Args:
        webhook_id: The webhook to update.
        url: New callback URL.
        events: Updated event subscriptions.
        is_active: Whether the webhook is active.
        user: Authenticated user.

    Returns:
        Updated webhook registration.
    """
    webhook = _webhook_registrations.get(webhook_id)
    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    if webhook.get("tenant_id") != (user.tenant_id or "default"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if url is not None:
        if not url.startswith("https://"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook URL must use HTTPS",
            )
        webhook["url"] = url

    if events is not None:
        valid_events = {"ingestion.completed", "ingestion.failed", "risk.analyzed", "redline.created"}
        invalid_events = [e for e in events if e not in valid_events]
        if invalid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid events: {invalid_events}",
            )
        webhook["events"] = events

    if is_active is not None:
        webhook["is_active"] = is_active

    webhook["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _webhook_registrations[webhook_id] = webhook

    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_INTEGRATIONS)),
) -> None:
    """Delete a webhook registration.

    Args:
        webhook_id: The webhook to delete.
        user: Authenticated user.
    """
    webhook = _webhook_registrations.get(webhook_id)
    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    if webhook.get("tenant_id") != (user.tenant_id or "default"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    del _webhook_registrations[webhook_id]
    logger.info("Webhook %s deleted by user %s", webhook_id, user.sub)
