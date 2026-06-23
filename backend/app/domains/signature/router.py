"""E-Signature API router."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

from .repository import SignatureRepository
from .service import SignatureService
from .schemas import (
    SignatureRequestCreate,
    SignatureRequestUpdate,
    SignatureRequestResponse,
    SignatureRequestListResponse,
    SignerCreate,
    SignerUpdate,
    SignerResponse,
    SendForSignatureRequest,
    VoidRequest,
    AuditEventResponse,
    WebhookEventResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signatures", tags=["E-Signature"])


async def get_repo(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> SignatureRepository:
    return SignatureRepository(session, tenant_id)


async def get_service(
    repo: SignatureRepository = Depends(get_repo),
    user: UserContext = Depends(get_current_user),
) -> SignatureService:
    return SignatureService(repo, actor_id=user.id)


# ── Signature Requests ──────────────────────────────────────────


@router.post("", response_model=SignatureRequestResponse, status_code=201)
async def create_signature_request(
    body: SignatureRequestCreate,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new signature request."""
    result = await service.create_request(body)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create signature request")
    return result


@router.get("", response_model=SignatureRequestListResponse)
async def list_signature_requests(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List signature requests."""
    return await service.list_requests(status, page, page_size)


@router.get("/{request_id}", response_model=SignatureRequestResponse)
async def get_signature_request(
    request_id: str,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a signature request with signers."""
    result = await service.get_request(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Signature request not found")
    return result


@router.patch("/{request_id}", response_model=SignatureRequestResponse)
async def update_signature_request(
    request_id: str,
    body: SignatureRequestUpdate,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a signature request."""
    result = await service.update_request(request_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Signature request not found")
    return result


@router.delete("/{request_id}", status_code=204)
async def delete_signature_request(
    request_id: str,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Delete a signature request."""
    deleted = await service.delete_request(request_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Signature request not found")


# ── Actions ─────────────────────────────────────────────────────


@router.post("/{request_id}/prepare", response_model=SignatureRequestResponse)
async def prepare_signature_request(
    request_id: str,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Move a signature request to 'preparing' status for final review."""
    try:
        result = await service.prepare_request(request_id)
        if not result:
            raise HTTPException(status_code=404, detail="Signature request not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{request_id}/send", response_model=SignatureRequestResponse)
async def send_for_signature(
    request_id: str,
    body: SendForSignatureRequest,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Send a signature request for signing."""
    try:
        result = await service.send_for_signature(request_id, body)
        if not result:
            raise HTTPException(status_code=404, detail="Signature request not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{request_id}/void", response_model=SignatureRequestResponse)
async def void_signature_request(
    request_id: str,
    body: VoidRequest,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Void a signature request."""
    result = await service.void_request(request_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Signature request not found")
    return result


@router.post("/{request_id}/remind", response_model=SignatureRequestResponse)
async def remind_signers(
    request_id: str,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Send reminders to pending signers."""
    result = await service.remind_signers(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Signature request not found")
    return result


# ── Signers ─────────────────────────────────────────────────────


@router.post("/{request_id}/signers", response_model=SignatureRequestResponse)
async def add_signer(
    request_id: str,
    body: SignerCreate,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Add a signer to a signature request."""
    result = await service.add_signer(request_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Signature request not found")
    return result


@router.patch("/{request_id}/signers/{signer_id}", response_model=SignatureRequestResponse)
async def update_signer(
    request_id: str,
    signer_id: str,
    body: SignerUpdate,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a signer's details."""
    result = await service.update_signer(request_id, signer_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Signature request or signer not found")
    return result


@router.delete("/{request_id}/signers/{signer_id}", response_model=SignatureRequestResponse)
async def remove_signer(
    request_id: str,
    signer_id: str,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Remove a signer from a signature request."""
    result = await service.remove_signer(request_id, signer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Signature request or signer not found")
    return result


# ── Audit & Certificate ─────────────────────────────────────────


@router.get("/{request_id}/audit", response_model=list[AuditEventResponse])
async def get_audit_trail(
    request_id: str,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get the audit trail for a signature request."""
    return await service.get_audit_trail(request_id)


@router.get("/{request_id}/certificate")
async def get_certificate(
    request_id: str,
    service: SignatureService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Download the completion certificate."""
    cert = await service.get_certificate(request_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not available")
    from fastapi.responses import Response
    return Response(content=cert, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=certificate-{request_id}.pdf"})


# ── Webhooks ────────────────────────────────────────────────────


@router.post("/webhooks/{provider_name}")
async def receive_webhook(
    provider_name: str,
    request: Request,
    service: SignatureService = Depends(get_service),
):
    """Receive a webhook from a signature provider."""
    headers = dict(request.headers)
    body = await request.body()
    try:
        result = await service.process_webhook(provider_name, headers, body)
        return result
    except ValueError as e:
        logger.warning(f"Invalid webhook from {provider_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
