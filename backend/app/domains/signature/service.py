"""E-Signature service layer."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from .models import SignatureRequest, SignatureSigner, SignatureAuditEvent
from .repository import SignatureRepository
from .schemas import (
    SignatureRequestCreate,
    SignatureRequestUpdate,
    SignerCreate,
    SendForSignatureRequest,
    VoidRequest,
)
from .providers import (
    SignatureProvider,
    DocuSignProvider,
    AdobeSignProvider,
    DropboxSignProvider,
    SignerInfo,
)

logger = logging.getLogger(__name__)


class SignatureService:
    """Service for e-signature operations."""

    def __init__(self, repo: SignatureRepository, actor_id: str):
        self.repo = repo
        self.actor_id = actor_id
        self._providers: dict[str, SignatureProvider] = {}

    def register_provider(self, name: str, provider: SignatureProvider) -> None:
        """Register a signature provider implementation."""
        self._providers[name] = provider

    def _get_provider(self, provider_name: str) -> SignatureProvider:
        """Get a registered provider by name."""
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Signature provider '{provider_name}' is not configured")
        return provider

    # ── Signature Requests ──────────────────────────────────────

    async def create_request(
        self, body: SignatureRequestCreate
    ) -> Optional[dict]:
        """Create a new signature request."""
        now = datetime.now(timezone.utc)

        request = SignatureRequest(
            id=str(uuid.uuid4()),
            tenant_id=self.repo.tenant_id,
            contract_id=body.contract_id,
            session_id=body.session_id,
            title=body.title,
            status="draft",
            provider=body.provider,
            expires_at=now + timedelta(days=body.expires_in_days),
            created_by=self.actor_id,
            created_at=now,
            updated_at=now,
        )
        request = await self.repo.create_request(request)

        # Add signers
        for s in body.signers:
            signer = SignatureSigner(
                id=str(uuid.uuid4()),
                request_id=request.id,
                email=s.email,
                name=s.name,
                role=s.role,
                signing_order=s.signing_order,
                status="awaiting",
                created_at=now,
            )
            await self.repo.add_signer(signer)

        return await self._build_response(request.id)

    async def get_request(self, request_id: str) -> Optional[dict]:
        """Get a signature request with signers."""
        return await self._build_response(request_id)

    async def list_requests(
        self, status: Optional[str] = None, page: int = 1, page_size: int = 20
    ) -> dict:
        """List signature requests."""
        requests, total = await self.repo.list_requests(status, page, page_size)
        data = []
        for req in requests:
            signers = await self.repo.get_signers(req.id)
            data.append(self._request_to_dict(req, signers))
        return {"data": data, "total": total, "page": page, "page_size": page_size}

    async def update_request(
        self, request_id: str, body: SignatureRequestUpdate
    ) -> Optional[dict]:
        """Update a signature request."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None
        if body.title is not None:
            request.title = body.title
        request.updated_at = datetime.now(timezone.utc)
        await self.repo.session.flush()
        return await self._build_response(request_id)

    async def delete_request(self, request_id: str) -> bool:
        """Delete a signature request."""
        return await self.repo.delete_request(request_id)

    async def send_for_signature(
        self, request_id: str, body: SendForSignatureRequest
    ) -> Optional[dict]:
        """Send a signature request via the configured provider."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None

        if request.status != "draft":
            raise ValueError(f"Cannot send request with status '{request.status}'")

        provider = self._get_provider(request.provider)
        signers = await self.repo.get_signers(request_id)

        # Build signer info for provider
        signer_infos = [
            SignerInfo(email=s.email, name=s.name, role=s.role, signing_order=s.signing_order)
            for s in signers
        ]

        # TODO: Get document bytes from contract or negotiation
        document_bytes = b""
        document_name = request.title

        # Send via provider
        response = await provider.send_envelope(
            document_bytes=document_bytes,
            document_name=document_name,
            signers=signer_infos,
            email_subject=body.email_subject or f"Please sign: {request.title}",
            email_body=body.email_body or "",
            expires_at=request.expires_at,
        )

        # Update request status
        now = datetime.now(timezone.utc)
        await self.repo.update_request_status(
            request_id,
            status="sent",
            provider_envelope_id=response.envelope_id,
            sent_at=now,
        )

        # Update signer provider IDs
        for signer in signers:
            url = response.signing_urls.get(signer.id)
            if url:
                pass  # Store signing URL if needed

        # Log audit event
        await self._log_audit(request_id, "sent", actor_email=self.actor_id)

        return await self._build_response(request_id)

    async def void_request(self, request_id: str, body: VoidRequest) -> Optional[dict]:
        """Void a signature request."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None

        if request.provider_envelope_id:
            provider = self._get_provider(request.provider)
            await provider.void_envelope(request.provider_envelope_id, body.reason)

        await self.repo.update_request_status(request_id, status="voided")
        await self._log_audit(request_id, "voided", details={"reason": body.reason})

        return await self._build_response(request_id)

    async def remind_signers(self, request_id: str) -> Optional[dict]:
        """Send reminders to pending signers."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None
        # TODO: Implement reminder via provider or email
        await self._log_audit(request_id, "reminder_sent")
        return await self._build_response(request_id)

    # ── Signers ─────────────────────────────────────────────────

    async def add_signer(self, request_id: str, body: SignerCreate) -> Optional[dict]:
        """Add a signer to a request."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None
        signer = SignatureSigner(
            id=str(uuid.uuid4()),
            request_id=request_id,
            email=body.email,
            name=body.name,
            role=body.role,
            signing_order=body.signing_order,
            status="awaiting",
            created_at=datetime.now(timezone.utc),
        )
        await self.repo.add_signer(signer)
        return await self._build_response(request_id)

    async def remove_signer(self, request_id: str, signer_id: str) -> Optional[dict]:
        """Remove a signer from a request."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None
        await self.repo.remove_signer(signer_id)
        return await self._build_response(request_id)

    # ── Audit ───────────────────────────────────────────────────

    async def get_audit_trail(self, request_id: str) -> list[dict]:
        """Get audit trail for a signature request."""
        events = await self.repo.get_audit_events(request_id)
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "actor_email": e.actor_email,
                "details": e.details,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]

    async def get_certificate(self, request_id: str) -> Optional[bytes]:
        """Get the completion certificate for a signed request."""
        request = await self.repo.get_request(request_id)
        if not request or not request.provider_envelope_id:
            return None
        provider = self._get_provider(request.provider)
        return await provider.get_certificate(request.provider_envelope_id)

    # ── Webhooks ────────────────────────────────────────────────

    async def process_webhook(
        self, provider_name: str, headers: dict, body: bytes
    ) -> dict:
        """Process an incoming webhook from a signature provider."""
        provider = self._get_provider(provider_name)
        event = provider.validate_webhook(headers, body)

        # Find the signature request by envelope ID
        # TODO: Look up request by provider_envelope_id
        # Update status based on event
        # Log audit event

        return {
            "event_type": event.event_type,
            "envelope_id": event.envelope_id,
            "status": event.status,
            "message": "Webhook processed",
        }

    # ── Internal ────────────────────────────────────────────────

    async def _build_response(self, request_id: str) -> Optional[dict]:
        """Build a full response dict for a signature request."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None
        signers = await self.repo.get_signers(request_id)
        return self._request_to_dict(request, signers)

    def _request_to_dict(
        self, request: SignatureRequest, signers: list[SignatureSigner]
    ) -> dict:
        return {
            "id": request.id,
            "contract_id": request.contract_id,
            "session_id": request.session_id,
            "title": request.title,
            "status": request.status,
            "provider": request.provider,
            "provider_envelope_id": request.provider_envelope_id,
            "expires_at": request.expires_at.isoformat() if request.expires_at else None,
            "sent_at": request.sent_at.isoformat() if request.sent_at else None,
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
            "created_by": request.created_by,
            "created_at": request.created_at.isoformat() if request.created_at else None,
            "updated_at": request.updated_at.isoformat() if request.updated_at else None,
            "signers": [
                {
                    "id": s.id,
                    "email": s.email,
                    "name": s.name,
                    "role": s.role,
                    "signing_order": s.signing_order,
                    "status": s.status,
                    "signed_at": s.signed_at.isoformat() if s.signed_at else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in signers
            ],
        }

    async def _log_audit(
        self,
        request_id: str,
        event_type: str,
        actor_email: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Log an audit event."""
        event = SignatureAuditEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=event_type,
            actor_email=actor_email,
            details=details or {},
            created_at=datetime.now(timezone.utc),
        )
        await self.repo.add_audit_event(event)
