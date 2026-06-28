"""Development auto-sign provider — automatically simulates signing flow.

This provider is intended for DEVELOPMENT / TESTING environments only.
Instead of sending documents to DocuSign (which requires human interaction),
it immediately creates a simulated envelope and returns "completed" status.

Flow:
1. send_envelope() — Creates a fake envelope ID, immediately returns "completed"
2. get_envelope_status() — Always returns "completed" with signed recipients
3. get_signing_url() — Returns a placeholder URL
4. void_envelope() — No-op, always succeeds
5. get_certificate() — Returns an empty PDF placeholder
6. get_audit_trail() — Returns simulated audit events
7. validate_webhook() — Returns a simulated "envelope_completed" event
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from .base import (
    AuditEvent,
    ProviderResponse,
    ProviderStatus,
    SignatureProvider,
    SignerInfo,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


class DevAutoSignProvider(SignatureProvider):
    """Development auto-sign provider.

    Automatically completes all signature requests without human interaction.
    Only use in development/test environments.
    """

    @property
    def provider_name(self) -> str:
        return "dev_auto_sign"

    async def send_envelope(
        self,
        document_bytes: bytes,
        document_name: str,
        signers: list[SignerInfo],
        email_subject: str,
        email_body: str,
        expires_at: Optional[datetime] = None,
        signing_order_enabled: bool = True,
    ) -> ProviderResponse:
        """Simulate sending an envelope — immediately return completed status.

        Generates a deterministic fake envelope ID and marks all signers as signed.
        """
        # Generate a deterministic fake envelope ID based on content hash
        content_hash = hashlib.sha256(document_bytes).hexdigest()[:16]
        envelope_id = f"dev-auto-{content_hash}-{uuid.uuid4().hex[:12]}"

        logger.info(
            "DevAutoSign: Simulated envelope %s for %s (%d signers)",
            envelope_id, document_name, len(signers),
        )

        # Generate fake signing URLs for each signer
        signing_urls: dict[str, str] = {}
        for signer in signers:
            signing_urls[signer.email] = (
                f"https://dev-auto-sign.example.com/envelope/{envelope_id}/sign/{signer.email}"
            )

        return ProviderResponse(
            envelope_id=envelope_id,
            status="completed",
            signing_urls=signing_urls,
            expires_at=expires_at,
            raw_response={
                "envelopeId": envelope_id,
                "status": "completed",
                "auto_signed": True,
                "simulated_at": datetime.now(timezone.utc).isoformat(),
                "signers": [
                    {
                        "email": s.email,
                        "name": s.name,
                        "status": "completed",
                        "signed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    for s in signers
                ],
            },
        )

    async def get_envelope_status(self, envelope_id: str) -> ProviderStatus:
        """Return completed status for any envelope."""
        return ProviderStatus(
            envelope_id=envelope_id,
            status="completed",
            signers=[
                {
                    "email": "auto-signed@dev.local",
                    "name": "Auto Signer",
                    "status": "completed",
                    "signed_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            last_updated=datetime.now(timezone.utc),
            raw_status={
                "envelopeId": envelope_id,
                "status": "completed",
                "auto_signed": True,
            },
        )

    async def void_envelope(self, envelope_id: str, reason: str) -> bool:
        """Simulate voiding an envelope — always succeeds."""
        logger.info("DevAutoSign: Simulated void of envelope %s (reason: %s)", envelope_id, reason)
        return True

    async def get_signing_url(self, envelope_id: str, recipient_id: str) -> str:
        """Return a placeholder signing URL."""
        return f"https://dev-auto-sign.example.com/envelope/{envelope_id}/sign/{recipient_id}"

    async def get_certificate(self, envelope_id: str) -> bytes:
        """Return a minimal placeholder PDF certificate."""
        return (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj "
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
            b"0000000058 00000 n \n0000000115 00000 n \ntrailer"
            b"<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
        )

    async def get_audit_trail(self, envelope_id: str) -> list[AuditEvent]:
        """Return simulated audit events."""
        now = datetime.now(timezone.utc)
        return [
            AuditEvent(
                event_type="envelope_created",
                action="Created",
                timestamp=now,
                actor_email="system@dev.local",
                actor_name="Dev Auto Sign System",
                details={"envelope_id": envelope_id, "auto_signed": True},
            ),
            AuditEvent(
                event_type="envelope_sent",
                action="Sent",
                timestamp=now,
                actor_email="system@dev.local",
                actor_name="Dev Auto Sign System",
                details={"envelope_id": envelope_id},
            ),
            AuditEvent(
                event_type="envelope_completed",
                action="Completed",
                timestamp=now,
                actor_email="system@dev.local",
                actor_name="Dev Auto Sign System",
                details={"envelope_id": envelope_id, "auto_signed": True},
            ),
        ]

    def validate_webhook(self, headers: dict, body: bytes) -> WebhookEvent:
        """Return a simulated webhook event for envelope completion.

        Since there's no real webhook in dev mode, this creates a fake
        completion event that can be used for testing the webhook pipeline.
        """
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}

        envelope_id = payload.get("envelopeId", f"dev-auto-{uuid.uuid4().hex[:16]}")

        return WebhookEvent(
            event_type="envelope_completed",
            envelope_id=envelope_id,
            status="completed",
            recipient_email="auto-signed@dev.local",
            recipient_name="Auto Signer",
            event_timestamp=datetime.now(timezone.utc),
            raw_event={
                "envelopeId": envelope_id,
                "status": "completed",
                "auto_signed": True,
                "simulated": True,
            },
        )
