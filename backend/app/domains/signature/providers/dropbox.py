"""Dropbox Sign (HelloSign) provider implementation."""

from __future__ import annotations

import logging
from datetime import datetime
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


class DropboxSignProvider(SignatureProvider):
    """Dropbox Sign (HelloSign) API v3 provider."""

    @property
    def provider_name(self) -> str:
        return "dropbox_sign"

    def __init__(self, api_key: str, client_id: Optional[str] = None):
        self.api_key = api_key
        self.client_id = client_id

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
        """Send a document via Dropbox Sign for signature."""
        # TODO: Implement signature request creation
        # POST /v3/signature_request/send
        raise NotImplementedError("Dropbox Sign send not yet implemented")

    async def get_envelope_status(self, envelope_id: str) -> ProviderStatus:
        """Get signature request status from Dropbox Sign."""
        # TODO: Implement status retrieval
        # GET /v3/signature_request/{signature_request_id}
        raise NotImplementedError("Dropbox Sign status not yet implemented")

    async def void_envelope(self, envelope_id: str, reason: str) -> bool:
        """Cancel a Dropbox Sign signature request."""
        # TODO: Implement signature request cancellation
        # POST /v3/signature_request/cancel/{signature_request_id}
        raise NotImplementedError("Dropbox Sign void not yet implemented")

    async def get_signing_url(self, envelope_id: str, recipient_id: str) -> str:
        """Get embedded signing URL from Dropbox Sign."""
        # TODO: Implement embedded signing URL
        raise NotImplementedError("Dropbox Sign signing URL not yet implemented")

    async def get_certificate(self, envelope_id: str) -> bytes:
        """Get Dropbox Sign completion certificate."""
        # TODO: Implement certificate download
        # GET /v3/signature_request/files/{signature_request_id}/certificate
        raise NotImplementedError("Dropbox Sign certificate not yet implemented")

    async def get_audit_trail(self, envelope_id: str) -> list[AuditEvent]:
        """Get Dropbox Sign audit trail."""
        # TODO: Implement audit trail retrieval
        raise NotImplementedError("Dropbox Sign audit trail not yet implemented")

    def validate_webhook(self, headers: dict, body: bytes) -> WebhookEvent:
        """Validate and parse a Dropbox Sign webhook callback."""
        # TODO: Implement webhook validation
        # Verify HMAC signature in X-Dropbox-Sign-Signature header
        raise NotImplementedError("Dropbox Sign webhook not yet implemented")
