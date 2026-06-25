"""E-Signature service layer — enterprise-grade with prepare step."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_

from .models import SignatureRequest, SignatureSigner, SignatureAuditEvent
from .repository import SignatureRepository
from .schemas import (
    SignatureRequestCreate,
    SignatureRequestUpdate,
    SignerCreate,
    SignerUpdate,
    SendForSignatureRequest,
    VoidRequest,
)
from .providers import (
    SignatureProvider,
    SignerInfo,
)

logger = logging.getLogger(__name__)

# ── Status Transition Map ──────────────────────────────────────
# Only allow forward transitions (idempotent webhook processing)
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"preparing", "sent"},
    "preparing": {"sent"},
    "sent": {"viewed", "partially_signed", "completed", "declined"},
    "viewed": {"partially_signed", "completed", "declined"},
    "partially_signed": {"completed", "declined"},
    "completed": set(),  # terminal
    "declined": set(),    # terminal
    "expired": set(),     # terminal
    "voided": set(),      # terminal
}

# Map DocuSign webhook event types to internal statuses
_WEBHOOK_STATUS_MAP: dict[str, str] = {
    "envelope_sent": "sent",
    "envelope_delivered": "viewed",
    "envelope_completed": "completed",
    "envelope_declined": "declined",
    "envelope_voided": "voided",
    "envelope_expired": "expired",
    "recipient_sent": "sent",
    "recipient_delivered": "viewed",
    "recipient_signed": "partially_signed",
    "recipient_completed": "completed",
    "recipient_declined": "declined",
}


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
        """Create a new signature request in draft status."""
        now = datetime.now(timezone.utc)

        request = SignatureRequest(
            id=str(uuid.uuid4()),
            tenant_id=self.repo.tenant_id,
            contract_id=body.contract_id,
            session_id=body.session_id,
            title=body.title,
            status="draft",
            provider=body.provider,
            email_subject=body.email_subject,
            email_message=body.email_message,
            expires_at=now + timedelta(days=body.expires_in_days),
            reminder_days=body.reminder_days,
            allow_decline=body.allow_decline,
            allow_print=body.allow_print,
            require_identity_verification=body.require_identity_verification,
            timezone=body.timezone,
            language=body.language,
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
                title=s.title,
                company=s.company,
                role=s.role,
                signing_order=s.signing_order,
                routing_order=s.routing_order,
                authentication_type=s.authentication_type,
                phone=s.phone,
                access_code=s.access_code,
                status="awaiting",
                created_at=now,
            )
            await self.repo.add_signer(signer)

        # Log audit event
        await self._log_audit(
            request.id,
            "signature_request_created",
            actor_email=self.actor_id,
            details={
                "provider": body.provider,
                "contract_id": body.contract_id,
                "signer_count": len(body.signers),
                "signers": [{"email": s.email, "name": s.name} for s in body.signers],
            },
        )

        # Also log to governance_audit_events for the contract timeline
        if body.contract_id:
            try:
                from sqlalchemy import text as sa_text
                await self.repo.session.execute(
                    sa_text("""
                        INSERT INTO governance_audit_events (
                            event_id, tenant_id, event_type, entity_type, entity_id,
                            actor_id, previous_state, new_state, change_summary, metadata, created_at
                        ) VALUES (
                            gen_random_uuid(), :tenant_id, 'signature.request_created',
                            'contract', :contract_id, :actor_id,
                            '{}', '{"status": "draft"}',
                            :summary, :metadata, NOW()
                        )
                    """),
                    {
                        "tenant_id": self.repo.tenant_id,
                        "contract_id": body.contract_id,
                        "actor_id": self.actor_id,
                        "summary": f"Signature request created: {body.title}",
                        "metadata": json.dumps({
                            "provider": body.provider,
                            "signer_count": len(body.signers),
                            "request_id": request.id,
                        }),
                    },
                )
                await self.repo.session.flush()
            except Exception as exc:
                logger.warning("Failed to log governance audit event: %s", exc)

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
        if body.email_subject is not None:
            request.email_subject = body.email_subject
        if body.email_message is not None:
            request.email_message = body.email_message
        if body.expires_in_days is not None:
            request.expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
        if body.reminder_days is not None:
            request.reminder_days = body.reminder_days
        if body.allow_decline is not None:
            request.allow_decline = body.allow_decline
        if body.allow_print is not None:
            request.allow_print = body.allow_print
        if body.require_identity_verification is not None:
            request.require_identity_verification = body.require_identity_verification
        if body.timezone is not None:
            request.timezone = body.timezone
        if body.language is not None:
            request.language = body.language
        request.updated_at = datetime.now(timezone.utc)
        await self.repo.session.flush()
        return await self._build_response(request_id)

    async def delete_request(self, request_id: str) -> bool:
        """Delete a signature request."""
        return await self.repo.delete_request(request_id)

    async def prepare_request(self, request_id: str) -> Optional[dict]:
        """Move a request to 'preparing' status for final review before sending."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None
        if request.status != "draft":
            raise ValueError(f"Cannot prepare request with status '{request.status}'")
        await self.repo.update_request_status(request_id, status="preparing")
        return await self._build_response(request_id)

    async def send_for_signature(
        self, request_id: str, body: SendForSignatureRequest
    ) -> Optional[dict]:
        """Send a signature request via the configured provider.

        Gets the document from storage, creates a DocuSign envelope,
        and updates the request status to 'sent'.
        """
        request = await self.repo.get_request(request_id)
        if not request:
            return None

        if request.status not in ("draft", "preparing"):
            raise ValueError(f"Cannot send request with status '{request.status}'")

        provider = self._get_provider(request.provider)
        signers = await self.repo.get_signers(request_id)

        # Build signer info for provider
        signer_infos = [
            SignerInfo(
                email=s.email, name=s.name,
                title=s.title or "", company=s.company or "",
                role=s.role, signing_order=s.signing_order,
                client_user_id=s.id if hasattr(s, 'id') and s.id else None,
            )
            for s in signers
        ]

        # Get document bytes from storage
        document_bytes = b""
        document_name = request.title
        try:
            from app.integrations.storage.s3 import storage_service
            from sqlalchemy import text as sa_text

            # Find the upload session for this contract
            row = await self.repo.session.execute(
                sa_text("""
                    SELECT us.storage_bucket, us.storage_key, us.filename
                    FROM upload_sessions us
                    JOIN contract_reviews cr ON cr.upload_id = us.upload_id
                    WHERE cr.review_id = :contract_id
                      AND cr.tenant_id = :tenant_id
                    LIMIT 1
                """),
                {"contract_id": request.contract_id, "tenant_id": self.repo.tenant_id},
            )
            upload = row.fetchone()
            if upload and upload.storage_bucket and upload.storage_key:
                document_bytes = await storage_service.download_fileobj(
                    upload.storage_bucket, upload.storage_key
                )
                document_name = upload.filename or request.title
                logger.info(
                    "Loaded document %s (%d bytes) for signature",
                    document_name, len(document_bytes),
                )
            else:
                logger.warning(
                    "No document found for contract %s, sending empty placeholder",
                    request.contract_id,
                )
                # Create a minimal PDF placeholder so DocuSign has something to send
                document_bytes = (
                    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
                    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
                    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj "
                    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
                    b"0000000058 00000 n \n0000000115 00000 n \ntrailer"
                    b"<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
                )
        except Exception as exc:
            logger.warning("Failed to load document from storage: %s", exc)
            raise ValueError(f"Could not load document for signature: {exc}")

        # Send via provider
        response = await provider.send_envelope(
            document_bytes=document_bytes,
            document_name=document_name,
            signers=signer_infos,
            email_subject=body.email_subject or request.email_subject or f"Please sign: {request.title}",
            email_body=body.email_message or request.email_message or "",
            expires_at=request.expires_at,
        )

        # Update request with provider reference
        now = datetime.now(timezone.utc)
        await self.repo.update_request_status(
            request_id,
            status="sent",
            provider_reference=response.envelope_id,
            provider_metadata=response.raw_response or {},
            sent_at=now,
        )

        # Update signer provider recipient IDs
        for signer in signers:
            recipient_id = response.signing_urls.get(signer.id)
            if recipient_id:
                await self.repo.update_signer_status(
                    signer.id, status="sent",
                    provider_recipient_id=recipient_id,
                )

        # Log audit event
        await self._log_audit(
            request_id, "sent",
            actor_email=self.actor_id,
            details={"provider": request.provider, "provider_reference": response.envelope_id},
        )

        # Log to governance_audit_events for contract timeline
        if request.contract_id:
            try:
                from sqlalchemy import text as sa_text
                await self.repo.session.execute(
                    sa_text("""
                        INSERT INTO governance_audit_events (
                            event_id, tenant_id, event_type, entity_type, entity_id,
                            actor_id, previous_state, new_state, change_summary, metadata, created_at
                        ) VALUES (
                            gen_random_uuid(), :tenant_id, 'signature.sent',
                            'contract', :contract_id, :actor_id,
                            '{"status": "draft"}', '{"status": "sent"}',
                            :summary, :metadata, NOW()
                        )
                    """),
                    {
                        "tenant_id": self.repo.tenant_id,
                        "contract_id": request.contract_id,
                        "actor_id": self.actor_id,
                        "summary": f"Sent for signature via {request.provider}: {request.title}",
                        "metadata": json.dumps({
                            "envelope_id": response.envelope_id,
                            "provider": request.provider,
                            "signer_count": len(signers),
                        }),
                    },
                )
                await self.repo.session.flush()
            except Exception as exc:
                logger.warning("Failed to log governance audit event: %s", exc)

        logger.info(
            "Signature request %s sent via %s (envelope: %s)",
            request_id, request.provider, response.envelope_id,
        )

        return await self._build_response(request_id)

    async def void_request(self, request_id: str, body: VoidRequest) -> Optional[dict]:
        """Void a signature request."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None

        if request.provider_reference:
            provider = self._get_provider(request.provider)
            await provider.void_envelope(request.provider_reference, body.reason)

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
            title=body.title,
            company=body.company,
            role=body.role,
            signing_order=body.signing_order,
            routing_order=body.routing_order,
            authentication_type=body.authentication_type,
            phone=body.phone,
            access_code=body.access_code,
            status="awaiting",
            created_at=datetime.now(timezone.utc),
        )
        await self.repo.add_signer(signer)
        return await self._build_response(request_id)

    async def update_signer(
        self, request_id: str, signer_id: str, body: SignerUpdate
    ) -> Optional[dict]:
        """Update a signer's details."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None
        # Fetch and update signer
        signers = await self.repo.get_signers(request_id)
        target = next((s for s in signers if s.id == signer_id), None)
        if not target:
            return None
        for field in ("email", "name", "title", "company", "role",
                       "signing_order", "routing_order", "authentication_type",
                       "phone", "access_code"):
            val = getattr(body, field, None)
            if val is not None:
                setattr(target, field, val)
        await self.repo.session.flush()
        return await self._build_response(request_id)

    async def remove_signer(self, request_id: str, signer_id: str) -> Optional[dict]:
        """Remove a signer from a request."""
        request = await self.repo.get_request(request_id)
        if not request:
            return None
        await self.repo.remove_signer(signer_id)
        return await self._build_response(request_id)

    # ── Audit & Certificate ─────────────────────────────────────

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
        if not request or not request.provider_reference:
            return None
        provider = self._get_provider(request.provider)
        return await provider.get_certificate(request.provider_reference)

    # ── Webhooks ────────────────────────────────────────────────

    async def process_webhook(
        self, provider_name: str, headers: dict, body: bytes
    ) -> dict:
        """Process an incoming webhook from a signature provider.

        Every webhook must:
        1. Validate signature (HMAC / API secret)
        2. Look up the signature request by provider reference
        3. Transition status forward only (idempotent)
        4. Update signer status if recipient event
        5. Log raw payload to audit trail
        6. Trigger lifecycle transitions on completion/decline
        """
        provider = self._get_provider(provider_name)
        event = provider.validate_webhook(headers, body)

        # Log raw payload first (always, even if duplicate)
        await self._log_audit(
            event.envelope_id,
            f"webhook_{event.event_type}",
            actor_email=event.recipient_email,
            details={
                "provider": provider_name,
                "raw_event": event.raw_event,
            },
        )

        # Map webhook event type to internal status
        new_status = _WEBHOOK_STATUS_MAP.get(event.event_type)
        if not new_status:
            logger.warning("Unknown webhook event type: %s", event.event_type)
            return {
                "event_type": event.event_type,
                "status": "ignored",
                "message": f"Unknown event type: {event.event_type}",
            }

        # Find the signature request by provider reference (envelope ID)
        request = await self.repo.find_by_provider_reference(event.envelope_id)
        if not request:
            logger.warning(
                "No signature request found for provider reference: %s",
                event.envelope_id,
            )
            return {
                "event_type": event.event_type,
                "provider_reference": event.envelope_id,
                "status": "not_found",
                "message": "No matching signature request found",
            }

        # Idempotent status transition — only move forward
        current = request.status
        allowed = _ALLOWED_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            logger.info(
                "Ignoring webhook %s → %s for request %s (current: %s, allowed: %s)",
                current, new_status, request.id, current, allowed,
            )
            return {
                "event_type": event.event_type,
                "provider_reference": event.envelope_id,
                "status": current,
                "message": f"Ignored — cannot transition from {current} to {new_status}",
            }

        # Update request status
        extra = {"updated_at": datetime.now(timezone.utc)}
        if new_status == "completed":
            extra["completed_at"] = datetime.now(timezone.utc)
        elif new_status == "sent":
            extra["sent_at"] = datetime.now(timezone.utc)

        await self.repo.update_request_status(request.id, new_status, **extra)

        # Update signer status if recipient email is known
        if event.recipient_email:
            signers = await self.repo.get_signers(request.id)
            for signer in signers:
                if signer.email == event.recipient_email:
                    signer_status = "signed" if new_status in ("completed", "partially_signed") else new_status
                    await self.repo.update_signer_status(
                        signer.id, signer_status,
                        signed_at=datetime.now(timezone.utc) if new_status in ("completed", "partially_signed") else None,
                    )
                    break

        # Trigger lifecycle transitions
        await self._trigger_lifecycle(request, new_status, current)

        # Send notifications
        await self._send_signature_notification(request, new_status, event.recipient_email)

        logger.info(
            "Webhook processed: %s → %s for request %s",
            current, new_status, request.id,
        )

        return {
            "event_type": event.event_type,
            "provider_reference": event.envelope_id,
            "request_id": request.id,
            "from_status": current,
            "to_status": new_status,
            "message": "Webhook processed",
        }

    async def _trigger_lifecycle(
        self, request: SignatureRequest, new_status: str, old_status: str
    ) -> None:
        """Trigger contract lifecycle transitions based on signature status."""
        if not request.contract_id:
            return

        try:
            from app.domains.contracts.lifecycle import ContractLifecycleService

            lifecycle = ContractLifecycleService()
            if new_status == "completed":
                await lifecycle.on_signature_complete(request.contract_id)
            elif new_status == "declined":
                await lifecycle.on_signature_declined(request.contract_id)
            elif new_status == "sent":
                await lifecycle.on_signature_sent(request.contract_id)
            elif new_status == "partially_signed":
                await lifecycle.on_signature_partial(request.contract_id)
        except Exception as exc:
            logger.warning(
                "Lifecycle transition failed for contract %s: %s",
                request.contract_id, exc,
            )

    async def _send_signature_notification(
        self, request: SignatureRequest, new_status: str, recipient_email: Optional[str] = None
    ) -> None:
        """Send notifications for signature status changes."""
        try:
            from app.domains.notify.service import NotificationService
            from app.kernel.database.session import db_session

            session = db_session.get()
            if not session:
                return

            notify = NotificationService(
                repo=None,  # Will be initialized properly
                event_bus=None,
                tenant_id=request.tenant_id,
            )

            notification_map = {
                "sent": ("contract.signature.sent", "Contract sent for signature"),
                "viewed": ("contract.signature.viewed", "Signature invitation viewed"),
                "partially_signed": ("contract.signature.partial", "Some signers have completed"),
                "completed": ("contract.signature.completed", "Contract fully executed"),
                "declined": ("contract.signature.declined", "Signature was declined"),
                "expired": ("contract.signature.expired", "Signature request expired"),
            }

            entry = notification_map.get(new_status)
            if entry:
                notif_type, title = entry
                await notify.send_notification(
                    user_id=request.created_by,
                    notif_type=notif_type,
                    title=title,
                    body=f"Signature request '{request.title}' is now {new_status}",
                    entity_type="signature",
                    entity_id=request.id,
                )
        except Exception as exc:
            logger.warning("Signature notification failed: %s", exc)

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
            "provider_reference": request.provider_reference,
            "provider_metadata": request.provider_metadata,
            "email_subject": request.email_subject,
            "email_message": request.email_message,
            "expires_at": request.expires_at.isoformat() if request.expires_at else None,
            "reminder_days": request.reminder_days,
            "allow_decline": request.allow_decline,
            "allow_print": request.allow_print,
            "require_identity_verification": request.require_identity_verification,
            "timezone": request.timezone,
            "language": request.language,
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
                    "title": s.title,
                    "company": s.company,
                    "role": s.role,
                    "signing_order": s.signing_order,
                    "routing_order": s.routing_order,
                    "authentication_type": s.authentication_type,
                    "phone": s.phone,
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
        raw_payload: Optional[dict] = None,
    ) -> None:
        """Log an audit event."""
        event = SignatureAuditEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=event_type,
            actor_email=actor_email,
            details=details or {},
            raw_payload=raw_payload,
            created_at=datetime.now(timezone.utc),
        )
        await self.repo.add_audit_event(event)
