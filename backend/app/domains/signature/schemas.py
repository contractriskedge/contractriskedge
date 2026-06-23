"""E-Signature Pydantic schemas — enterprise-grade."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Signature Request ───────────────────────────────────────────

class SignerCreate(BaseModel):
    email: str
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    role: str = "signer"
    signing_order: int = 1
    routing_order: int = 1
    authentication_type: str = "none"
    phone: Optional[str] = None
    access_code: Optional[str] = None


class SignerUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    signing_order: Optional[int] = None
    routing_order: Optional[int] = None
    authentication_type: Optional[str] = None
    phone: Optional[str] = None
    access_code: Optional[str] = None


class SignerResponse(BaseModel):
    id: str
    email: str
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    role: str
    signing_order: int
    routing_order: int
    authentication_type: str
    phone: Optional[str] = None
    status: str
    signed_at: Optional[datetime] = None
    created_at: datetime


class SignatureRequestCreate(BaseModel):
    contract_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str
    provider: str = "docusign"  # docusign only in Phase 1
    signers: list[SignerCreate] = Field(..., min_length=1)
    email_subject: Optional[str] = None
    email_message: Optional[str] = None
    expires_in_days: int = 30
    reminder_days: int = 3
    allow_decline: bool = True
    allow_print: bool = True
    require_identity_verification: bool = False
    timezone: str = "UTC"
    language: str = "en"


class SignatureRequestUpdate(BaseModel):
    title: Optional[str] = None
    email_subject: Optional[str] = None
    email_message: Optional[str] = None
    expires_in_days: Optional[int] = None
    reminder_days: Optional[int] = None
    allow_decline: Optional[bool] = None
    allow_print: Optional[bool] = None
    require_identity_verification: Optional[bool] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class SignatureRequestResponse(BaseModel):
    id: str
    contract_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str
    status: str
    provider: str
    provider_reference: Optional[str] = None
    provider_metadata: Optional[dict] = None
    email_subject: Optional[str] = None
    email_message: Optional[str] = None
    expires_at: Optional[datetime] = None
    reminder_days: int = 3
    allow_decline: bool = True
    allow_print: bool = True
    require_identity_verification: bool = False
    timezone: str = "UTC"
    language: str = "en"
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
    email_message: Optional[str] = None


class VoidRequest(BaseModel):
    reason: str = "Request voided by sender"


class RemindRequest(BaseModel):
    email_message: Optional[str] = None


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
    provider_reference: str
    status: str
    message: str = "Webhook received"
