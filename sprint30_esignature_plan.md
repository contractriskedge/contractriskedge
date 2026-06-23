# Sprint 30: E-Signature Integration

**Goal:** Complete the contract lifecycle by adding electronic signature support.
**Duration:** 2 weeks
**Status:** ✅ Complete

---

## Overview

Without execution, the contract lifecycle stops. This sprint adds the full
signature workflow: Negotiation → Approval → Signature → Executed.

Support for three major providers:
- DocuSign
- Adobe Sign
- Dropbox Sign

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Signature Workflow                        │
│                                                              │
│  Contract Review → Negotiation → Approval → SIGN → Executed │
│                                              │               │
│                                              ▼               │
│                                    ┌──────────────────┐      │
│                                    │  SignatureProvider │      │
│                                    │  (Abstract Base)   │      │
│                                    └────────┬─────────┘      │
│                                             │                 │
│                          ┌──────────────────┼──────────────────┐
│                          ▼                  ▼                  ▼
│                   ┌──────────┐      ┌──────────┐      ┌──────────┐
│                   │ DocuSign │      │Adobe Sign│      │Dropbox   │
│                   │ Provider │      │ Provider  │      │Sign Prov │
│                   └──────────┘      └──────────┘      └──────────┘
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### signature_requests
```sql
CREATE TABLE signature_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(36) NOT NULL,
    contract_id     VARCHAR(36) REFERENCES contract_reviews(review_id),
    session_id      VARCHAR(36) REFERENCES negotiation_sessions(session_id),
    title           VARCHAR(500) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'draft',
    -- draft, sent, viewed, signed, completed, declined, expired, voided
    provider        VARCHAR(50) NOT NULL,  -- docusign, adobe_sign, dropbox_sign
    provider_envelope_id  VARCHAR(255),
    expires_at      TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_by      VARCHAR(36) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_sig_req_tenant ON signature_requests(tenant_id);
CREATE INDEX idx_sig_req_contract ON signature_requests(contract_id);
CREATE INDEX idx_sig_req_status ON signature_requests(status);
CREATE INDEX idx_sig_req_provider ON signature_requests(provider);
```

### signature_signers
```sql
CREATE TABLE signature_signers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID NOT NULL REFERENCES signature_requests(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    name            VARCHAR(255) NOT NULL,
    role            VARCHAR(50) NOT NULL DEFAULT 'signer',
    -- signer, approver, cc, carbon_copy
    signing_order   INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(50) NOT NULL DEFAULT 'awaiting',
    -- awaiting, sent, viewed, signed, declined
    provider_recipient_id  VARCHAR(255),
    signed_at       TIMESTAMPTZ,
    reminded_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sig_signer_request ON signature_signers(request_id);
CREATE INDEX idx_sig_signer_email ON signature_signers(email);
```

### signature_audit_events
```sql
CREATE TABLE signature_audit_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID NOT NULL REFERENCES signature_requests(id) ON DELETE CASCADE,
    event_type      VARCHAR(100) NOT NULL,
    -- sent, viewed, signed, declined, expired, voided, reminder_sent, error
    actor_email     VARCHAR(255),
    details         JSONB DEFAULT '{}',
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sig_audit_request ON signature_audit_events(request_id);
```

---

## Backend API Endpoints

### Signature Requests
```
POST   /api/v1/signatures/                     Create signature request
GET    /api/v1/signatures/                     List signature requests
GET    /api/v1/signatures/{id}                 Get signature request detail
PATCH  /api/v1/signatures/{id}                 Update signature request
DELETE /api/v1/signatures/{id}                 Delete/cancel signature request
POST   /api/v1/signatures/{id}/send            Send for signature
POST   /api/v1/signatures/{id}/void            Void signature request
POST   /api/v1/signatures/{id}/remind          Send reminder
GET    /api/v1/signatures/{id}/certificate     Download completion certificate
GET    /api/v1/signatures/{id}/audit           Get audit trail
```

### Signers
```
POST   /api/v1/signatures/{id}/signers         Add signer
GET    /api/v1/signatures/{id}/signers         List signers
PATCH  /api/v1/signatures/{id}/signers/{sid}   Update signer
DELETE /api/v1/signatures/{id}/signers/{sid}   Remove signer
```

### Provider Webhooks
```
POST   /api/v1/signatures/webhooks/docusign    DocuSign webhook receiver
POST   /api/v1/signatures/webhooks/adobe       Adobe Sign webhook receiver
POST   /api/v1/signatures/webhooks/dropbox     Dropbox Sign webhook receiver
```

---

## Provider Interface

```python
class SignatureProvider(ABC):
    @abstractmethod
    async def send_envelope(self, request: SignatureRequest, document: bytes,
                            signers: list[Signer]) -> ProviderResponse:
        ...

    @abstractmethod
    async def get_status(self, envelope_id: str) -> ProviderStatus:
        ...

    @abstractmethod
    async def void_envelope(self, envelope_id: str, reason: str) -> bool:
        ...

    @abstractmethod
    async def get_signing_url(self, envelope_id: str,
                              recipient_id: str) -> str:
        ...

    @abstractmethod
    async def get_certificate(self, envelope_id: str) -> bytes:
        ...

    @abstractmethod
    async def get_audit_trail(self, envelope_id: str) -> list[AuditEvent]:
        ...

    @abstractmethod
    def validate_webhook(self, headers: dict, body: bytes) -> WebhookEvent:
        ...
```

---

## Frontend Components

```
frontend/components/dashboard/signature/
├── index.ts                         Barrel export
├── types.ts                         Signature types
├── SignatureProvider.tsx            Main orchestrator
├── SignatureRequestList.tsx         List of signature requests
├── SignatureRequestCard.tsx         Card for a signature request
├── SignatureCreateWizard.tsx        Wizard to create signature request
├── SignatureStatusBadge.tsx         Status badge
├── SignerList.tsx                   List of signers
├── SignerRow.tsx                    Single signer row
├── SignerAddDialog.tsx             Dialog to add signer
├── SignatureAuditTrail.tsx          Audit trail view
├── SignatureCertificate.tsx         Certificate download view
├── SignatureWebhookSetup.tsx        Webhook configuration
└── hooks/
    ├── useSignatureRequests.ts      Query hook for signature requests
    └── useSignatureSend.ts          Mutation hook for sending
```

---

## Integration Details

### DocuSign
- Uses DocuSign eSignature REST API v2.1
- OAuth2 JWT authentication
- Webhook events via DocuSign Connect
- Supports embedded signing and email delivery

### Adobe Sign
- Uses Adobe Sign REST API v6
- OAuth2 authorization code grant
- Webhook events via Adobe Sign webhook API
- Supports embedded signing and email delivery

### Dropbox Sign (HelloSign)
- Uses Dropbox Sign API v3
- API Key authentication
- Webhook events via Dropbox Sign callback API
- Supports embedded signing and email delivery

---

## Signature Workflow

```
1. User creates signature request
   - Selects contract/negotiation
   - Uploads or selects document
   - Adds signers with signing order
   - Selects provider

2. User sends for signature
   - Provider creates envelope
   - Envelope ID stored in DB
   - Signers receive email notifications
   - Status updated to 'sent'

3. Signers complete signing
   - Provider webhook received
   - Status updated to 'signed' or 'completed'
   - Audit events recorded
   - Contract status updated to 'executed'

4. Completion
   - Certificate downloaded and stored
   - Audit trail available
   - Executed PDF stored
   - Notification sent to creator
```

---

## Sprint Tasks

### Day 1-2: Foundation
- [ ] Create database migration for signature tables
- [ ] Create ORM models
- [ ] Create abstract SignatureProvider interface
- [ ] Create base repository

### Day 3-5: Backend API
- [ ] Implement signature request CRUD endpoints
- [ ] Implement signer management endpoints
- [ ] Implement send/void/remind actions
- [ ] Implement certificate and audit trail endpoints
- [ ] Implement webhook receivers

### Day 6-8: Provider Integrations
- [ ] Implement DocuSign provider
- [ ] Implement Adobe Sign provider
- [ ] Implement Dropbox Sign provider
- [ ] Add provider configuration (API keys, OAuth)

### Day 9-11: Frontend
- [ ] Build SignatureCreateWizard
- [ ] Build SignatureRequestList
- [ ] Build SignerList with add/edit/remove
- [ ] Build SignatureAuditTrail
- [ ] Build SignatureCertificate

### Day 12-14: Integration & Testing
- [ ] Wire signature into contract lifecycle
- [ ] Add signature status to contract detail
- [ ] Add signature request button to negotiation center
- [ ] E2E testing with provider sandboxes
- [ ] Error handling and webhook reliability
