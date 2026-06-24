"""E-Signature ORM models — enterprise-grade with full audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.database.base import Base


# ── Status Constants ────────────────────────────────────────────

SIGNATURE_REQUEST_STATUSES = [
    "draft", "preparing", "sent", "viewed", "partially_signed",
    "completed", "declined", "expired", "voided",
]

SIGNER_STATUSES = ["awaiting", "sent", "viewed", "signed", "declined"]

SIGNER_ROLES = ["signer", "approver", "cc", "carbon_copy"]

AUTHENTICATION_TYPES = ["none", "email", "access_code", "phone", "kba", "sms"]


class SignatureRequest(Base):
    __tablename__ = "signature_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    contract_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("contract_reviews.review_id"), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("negotiation_sessions.session_id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)

    # Provider fields (future-proof: single provider reference + JSON metadata)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # docusign
    provider_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # envelope ID
    provider_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)  # provider-specific data

    # Enterprise communication fields
    email_subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scheduling & reminders
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Enterprise options
    allow_decline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_print: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_identity_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    # Timestamps
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    request_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict)

    __table_args__ = (
        Index("idx_sig_req_tenant", "tenant_id"),
        Index("idx_sig_req_contract", "contract_id"),
        Index("idx_sig_req_status", "status"),
        Index("idx_sig_req_provider", "provider"),
    )


class SignatureSigner(Base):
    __tablename__ = "signature_signers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("signature_requests.id", ondelete="CASCADE"), nullable=False)

    # Identity
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)       # Job title
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)     # Company name

    # Role & routing
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="signer")
    signing_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    routing_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Parallel signing groups

    # Authentication
    authentication_type: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    access_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="awaiting", index=True)
    provider_recipient_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_sig_signer_request", "request_id"),
        Index("idx_sig_signer_email", "email"),
    )


class SignatureAuditEvent(Base):
    __tablename__ = "signature_audit_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("signature_requests.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Raw webhook payload
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_sig_audit_request", "request_id"),
    )
