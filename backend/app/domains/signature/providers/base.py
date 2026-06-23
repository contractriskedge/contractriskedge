"""Abstract base class for signature providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SignerInfo:
    """Information about a signature recipient."""
    email: str
    name: str
    role: str = "signer"  # signer, approver, cc
    signing_order: int = 1
    recipient_id: Optional[str] = None


@dataclass
class ProviderResponse:
    """Response from a signature provider after sending an envelope."""
    envelope_id: str
    status: str
    signing_urls: dict[str, str] = field(default_factory=dict)  # recipient_id → url
    expires_at: Optional[datetime] = None
    raw_response: Optional[dict] = None


@dataclass
class ProviderStatus:
    """Current status of an envelope from a provider."""
    envelope_id: str
    status: str  # sent, delivered, signed, completed, declined, voided, expired
    signers: list[dict] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    raw_status: Optional[dict] = None


@dataclass
class WebhookEvent:
    """Parsed webhook event from a provider."""
    event_type: str  # envelope_sent, envelope_signed, envelope_completed, etc.
    envelope_id: str
    status: str
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    event_timestamp: Optional[datetime] = None
    raw_event: Optional[dict] = None


@dataclass
class AuditEvent:
    """A single audit trail entry."""
    event_type: str
    action: str
    timestamp: datetime
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[dict] = None


class SignatureProvider(ABC):
    """Abstract base class for e-signature providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'docusign', 'adobe_sign', 'dropbox_sign')."""
        ...

    @abstractmethod
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
        """Send a document for signature."""
        ...

    @abstractmethod
    async def get_envelope_status(self, envelope_id: str) -> ProviderStatus:
        """Get the current status of an envelope."""
        ...

    @abstractmethod
    async def void_envelope(self, envelope_id: str, reason: str) -> bool:
        """Void/cancel an envelope that has been sent."""
        ...

    @abstractmethod
    async def get_signing_url(self, envelope_id: str, recipient_id: str) -> str:
        """Get the embedded signing URL for a recipient."""
        ...

    @abstractmethod
    async def get_certificate(self, envelope_id: str) -> bytes:
        """Get the completion certificate as a PDF."""
        ...

    @abstractmethod
    async def get_audit_trail(self, envelope_id: str) -> list[AuditEvent]:
        """Get the audit trail for an envelope."""
        ...

    @abstractmethod
    def validate_webhook(self, headers: dict, body: bytes) -> WebhookEvent:
        """Validate and parse an incoming webhook event."""
        ...
