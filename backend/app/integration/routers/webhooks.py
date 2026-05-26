"""
Webhook API router.

Endpoints for webhook subscription management and event ingestion.
"""

import hashlib
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.models.webhook import IntegrationWebhook, WebhookEvent, WebhookStatus
from app.integration.routers.dependencies import (
    get_audit_service,
    get_db,
    get_tenant_id,
    get_webhook_service,
)
from app.integration.schemas.webhook import (
    WebhookCreate,
    WebhookEventListResponse,
    WebhookEventResponse,
    WebhookResponse,
    WebhookVerificationResult,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/subscriptions",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook subscription",
)
async def create_webhook_subscription(
    body: WebhookCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Register a webhook subscription for an integration."""
    webhook = IntegrationWebhook(
        integration_id=request.state.integration_id,  # Set by middleware
        tenant_id=tenant_id,
        provider=body.provider,
        webhook_id=body.webhook_id,
        secret=body.secret,
        signature_header=body.signature_header,
        verification_token=body.verification_token,
        events_subscribed=body.events_subscribed or [],
        endpoint_url=body.endpoint_url,
        api_version=body.api_version,
        allowed_ips=body.allowed_ips or [],
        status=WebhookStatus.ACTIVE,
        metadata_=body.metadata or {},
    )

    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)

    return webhook


@router.get(
    "/subscriptions",
    response_model=list[WebhookResponse],
    summary="List webhook subscriptions",
)
async def list_webhook_subscriptions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """List all webhook subscriptions for the tenant."""
    result = await db.execute(
        select(IntegrationWebhook).where(
            IntegrationWebhook.tenant_id == tenant_id,
        )
    )
    return list(result.scalars().all())


@router.post(
    "/ingest/{provider}",
    summary="Ingest incoming webhook event",
)
async def ingest_webhook(
    provider: str,
    request: Request,
    webhook_service: WebhookService = Depends(get_webhook_service),
    x_webhook_id: Optional[str] = Header(None, alias="X-Webhook-ID"),
    x_event_id: Optional[str] = Header(None, alias="X-Event-ID"),
    x_event_type: Optional[str] = Header(None, alias="X-Event-Type"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
):
    """
    Ingest an incoming webhook event from an external provider.

    Performs signature verification, replay protection, and idempotent ingestion.
    """
    body = await request.body()
    source_ip = request.client.host if request.client else None

    timestamp = None
    if x_timestamp:
        try:
            timestamp = float(x_timestamp)
        except ValueError:
            pass

    try:
        event = await webhook_service.process_incoming_webhook(
            provider=provider,
            webhook_id=x_webhook_id or "",
            payload=body,
            headers=dict(request.headers),
            signature=x_signature,
            timestamp=timestamp,
            event_id=x_event_id,
            event_type=x_event_type,
            source_ip=source_ip,
        )

        return {
            "status": "received",
            "event_id": str(event.id),
            "idempotency_key": event.idempotency_key,
            "correlation_id": str(event.correlation_id),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/events",
    response_model=WebhookEventListResponse,
    summary="List webhook events",
)
async def list_webhook_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
):
    """List webhook events with pagination and filtering."""
    query = select(WebhookEvent).where(
        WebhookEvent.tenant_id == tenant_id,
    )

    if status_filter:
        query = query.where(WebhookEvent.status == status_filter)
    if event_type:
        query = query.where(WebhookEvent.event_type == event_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(WebhookEvent.received_at.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return WebhookEventListResponse(
        items=[WebhookEventResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get(
    "/events/{event_id}",
    response_model=WebhookEventResponse,
    summary="Get webhook event details",
)
async def get_webhook_event(
    event_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Get details of a specific webhook event."""
    result = await db.execute(
        select(WebhookEvent).where(
            WebhookEvent.id == event_id,
            WebhookEvent.tenant_id == tenant_id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook event not found",
        )
    return event


@router.post(
    "/verify",
    response_model=WebhookVerificationResult,
    summary="Verify webhook signature",
)
async def verify_webhook_signature(
    request: Request,
    provider: str = Query(...),
    signature: str = Header(..., alias="X-Signature"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
):
    """
    Verify a webhook signature without processing the event.

    Useful for initial handshake verification.
    """
    from app.integration.services.webhook_service import WebhookVerifier

    body = await request.body()
    verifier = WebhookVerifier()

    signature_valid = verifier.verify_hmac_signature(
        body, signature, "test-secret"  # In production, look up by provider
    )

    timestamp_valid = True
    if x_timestamp:
        try:
            timestamp_valid = verifier.verify_timestamp(float(x_timestamp))
        except ValueError:
            timestamp_valid = False

    return WebhookVerificationResult(
        verified=signature_valid and timestamp_valid,
        signature_valid=signature_valid,
        timestamp_valid=timestamp_valid,
        replay_detected=not timestamp_valid,
    )
