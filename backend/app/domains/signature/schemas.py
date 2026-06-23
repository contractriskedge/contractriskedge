"""E-Signature Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Signature Request ───────────────────────────────────────────

class SignerCreate(BaseModel):
    email: str
    name: str
    role: str = "signer"
    signing_order: int = 1


class SignerResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    signing_order: int
    status: str
    signed_at: Optional[datetime] = None
    created_at: datetime


class SignatureRequestCreate(BaseModel):
    contract_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str
    provider: str = "docusign"  # docusign, adobe_sign, dropbox_sign
    signers: list[SignerCreate] = Field(..., min_length=1)
    expires_in_days: int = 30
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


class SignatureRequestUpdate(BaseModel):
    title: Optional[str] = None
    expires_in_days: Optional[int] = None


class SignatureRequestResponse(BaseModel):
    id: str
    contract_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str
    status: str
    provider: str
    provider_envelope_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    signers: list[SignerResponse] = []


class SignatureRequestListResponse(BaseModel):
    data: list[SignatureRequestResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ── Actions ─────────────────────────────────────────────────────

class SendForSignatureRequest(BaseModel):
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


class VoidRequest(BaseModel):
    reason: str = "Request voided by sender"


class RemindRequest(BaseModel):
    email_body: Optional[str] = None


# ── Audit ───────────────────────────────────────────────────────

class AuditEventResponse(BaseModel):
    id: str
    event_type: str
    actor_email: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime


# ── Webhooks ────────────────────────────────────────────────────

class WebhookEventResponse(BaseModel):
    event_type: str
    envelope_id: str
    status: str
    message: str = "Webhook received"
