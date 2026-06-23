# Sprint 30: E-Signature Integration

**Goal:** Complete the contract lifecycle by adding electronic signature support.
**Status:** ✅ Foundation complete — awaiting DocuSign API credentials

---

## Strategy: One Provider at a Time

Instead of building three providers simultaneously, this sprint implements:

**Phase 1 (Sprint 30):** Signature framework + **DocuSign only**
**Phase 2 (Future):** Adobe Sign
**Phase 3 (Future):** Dropbox Sign

The abstract `SignatureProvider` interface already supports all three.
No code changes needed to add providers later.

---

## Sprint Breakdown

### Sprint 30.1 — Foundation (✅ Complete)
* Database migrations
* ORM models with enterprise fields
* Repository layer
* Signature service
* REST APIs (CRUD + prepare/send/void/remind)
* UI scaffolding (wizard, list, signer management, audit trail, certificate)

**Deliverable:** Users can create and manage signature requests locally.

### Sprint 30.2 — DocuSign Integration (⏳ Awaiting API Credentials)
* OAuth2 JWT authentication
* Send envelope
* Embedded signing
* Status polling
* Webhook processing
* Audit trail
* Certificate retrieval

**Deliverable:** End-to-end signing with DocuSign sandbox.

### Sprint 30.3 — Contract Lifecycle Integration (✅ In Progress — Parallel Track)
* Central ContractLifecycleService with full state machine
* Contract status transitions (preparing → sent → partially_signed → executed)
* Executed contract storage (PDF + certificate + audit log)
* Notification framework (in-app + email)
* Dashboard updates (pending signatures, executed this month)
* Activity timeline (signature events in existing feed)

**Deliverable:** Fully integrated lifecycle from negotiation through execution.

---

## Parallel Work Tracks

Since Sprint 30.2 is blocked on DocuSign credentials, all
provider-independent work is being done in parallel:

### Track A: Contract Lifecycle (Sprint 30.3)
| Component | Status | Description |
|-----------|--------|-------------|
| ContractLifecycleService | ✅ Complete | Central state machine with full transition map |
| Contract statuses | ✅ Complete | preparing_signature → sent → partially_signed → executed |
| ExecutedDocumentRepository | ✅ Complete | Stores executed PDF, certificate, audit log |
| NotificationService | ✅ Complete | In-app + email notifications for all events |

### Track B: Infrastructure
| Component | Status | Description |
|-----------|--------|-------------|
| EmailService | ✅ Complete | Generic email with SMTP/SendGrid/SES/Console support |
| StorageService | ✅ Complete | Abstract storage with Local/S3/Azure/SharePoint |
| Celery + Redis | ⏳ Pending | Background jobs for async processing |

### Track C: DocuSign Integration (Blocked)
| Component | Status | Description |
|-----------|--------|-------------|
| OAuth2 JWT auth | ⏳ Blocked | Requires DocuSign integration key + private key |
| Send envelope | ⏳ Blocked | Requires working auth |
| Webhook validation | ⏳ Blocked | Requires DocuSign Connect setup |
| Status sync | ⏳ Blocked | Requires webhook endpoint |

---

## Enterprise Workflow

```
Negotiation

↓

Approval

↓

Prepare for Signature   ← NEW — review signers, order, email, expiry

↓

Signature

↓

Executed
```

The "Prepare for Signature" step is critical. Many companies review
the signer list, signing order, email subject, expiry, and reminders
before actually sending.

---

## Contract Statuses

Instead of simple Approved → Executed, use enterprise statuses:

```
approved
preparing_signature    ← NEW
sent_for_signature     ← NEW
partially_signed       ← NEW
completed              ← was "executed"
declined               ← NEW
expired                ← NEW
voided                 ← NEW
```

---

## Architecture: Separation of Concerns

The provider implementation is a **thin adapter**. Business logic stays in the service layer.

```
API Router
    ↓
Signature Service  ← owns: status transitions, audit events, notifications, DB updates
    ↓
Signature Repository  ← owns: data access
    ↓
SignatureProvider Interface  ← thin adapter: send, status, certificate, webhook
           ↓
      DocuSign Provider  ← only: HTTP calls to DocuSign API
```

This means:
- **Service** owns business rules (status transitions, audit logging, notification dispatch)
- **Provider** only translates between our domain and the vendor API
- Future providers are added by implementing the interface — no service changes needed

---

## Asynchronous Processing

Sending documents, downloading certificates, and processing webhooks should
not block HTTP requests. Use background jobs (Celery / Redis Queue) for:

| Operation              | Why Async                          |
|------------------------|------------------------------------|
| Send envelope          | Provider API latency (1-5s)        |
| Process webhook        | Must not block webhook response    |
| Download completed PDF | Large file, provider API latency   |
| Download certificate   | Provider API latency               |
| Reminder emails        | Scheduled, not user-facing         |
| Retry failed calls     | Exponential backoff                |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Signature Workflow                        │
│                                                              │
│  Contract Review → Negotiation → Approval → Prepare →       │
│  Send → Sign → Completed                                     │
│                                              │               │
│                                              ▼               │
│                                    ┌──────────────────┐      │
│                                    │  SignatureProvider │      │
│                                    │  (Abstract Base)   │      │
│                                    └────────┬─────────┘      │
│                                             │                 │
│                                             ▼                 │
│                                    ┌──────────────────┐      │
│                                    │  DocuSignProvider │      │
│                                    │  (Phase 1 only)   │      │
│                                    └──────────────────┘      │
│                                    AdobeSignProvider  (P2)    │
│                                    DropboxSignProvider (P3)   │
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
    -- draft, preparing, sent, viewed, partially_signed, completed,
    -- declined, expired, voided
    provider        VARCHAR(50) NOT NULL,  -- docusign (adobe_sign, dropbox_sign later)
    provider_reference     VARCHAR(255),   -- provider's envelope/agreement ID
    provider_metadata      JSONB DEFAULT '{}',  -- provider-specific data
    email_subject          VARCHAR(500),
    email_message          TEXT,
    expires_at      TIMESTAMPTZ,
    reminder_days   INTEGER DEFAULT 3,
    allow_decline   BOOLEAN DEFAULT true,
    allow_print     BOOLEAN DEFAULT true,
    require_identity_verification BOOLEAN DEFAULT false,
    timezone        VARCHAR(50) DEFAULT 'UTC',
    language        VARCHAR(10) DEFAULT 'en',
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
    title           VARCHAR(255),            -- Job title
    company         VARCHAR(255),            -- Company name
    role            VARCHAR(50) NOT NULL DEFAULT 'signer',
    -- signer, approver, cc, carbon_copy
    signing_order   INTEGER NOT NULL DEFAULT 1,
    routing_order   INTEGER NOT NULL DEFAULT 1,  -- For parallel signing groups
    status          VARCHAR(50) NOT NULL DEFAULT 'awaiting',
    -- awaiting, sent, viewed, signed, declined
    authentication_type VARCHAR(50) DEFAULT 'none',  -- none, email, access_code, phone, kba
    phone           VARCHAR(50),
    access_code     VARCHAR(255),
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
    -- sent, viewed, signed, declined, expired, voided, reminder_sent,
    -- identity_verified, printed, downloaded, error
    actor_email     VARCHAR(255),
    details         JSONB DEFAULT '{}',
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    raw_payload     JSONB,                   -- Raw webhook payload for debugging
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
POST   /api/v1/signatures/{id}/prepare         Move to preparing status
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
POST   /api/v1/signatures/webhooks/adobe       Adobe Sign webhook receiver (Phase 2)
POST   /api/v1/signatures/webhooks/dropbox     Dropbox Sign webhook receiver (Phase 3)
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
    async def get_status(self, provider_reference: str) -> ProviderStatus:
        ...

    @abstractmethod
    async def void_envelope(self, provider_reference: str, reason: str) -> bool:
        ...

    @abstractmethod
    async def get_signing_url(self, provider_reference: str,
                              recipient_id: str) -> str:
        ...

    @abstractmethod
    async def get_certificate(self, provider_reference: str) -> bytes:
        ...

    @abstractmethod
    async def get_audit_trail(self, provider_reference: str) -> list[AuditEvent]:
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
└── hooks/
    ├── useSignatureRequests.ts      Query hook for signature requests
    └── useSignatureSend.ts          Mutation hook for sending
```

---

## Contract Detail Signature Tab

```
┌─────────────────────────────────────────────┐
│  Review │ Negotiation │ Approval │ SIGNATURE │ Obligations │ History │
├─────────────────────────────────────────────┤
│                                             │
│  Recipients  ─────────────────────────────  │
│  [Name] [Email] [Role] [Order] [Status]     │
│                                             │
│  Status: Sent for Signature                 │
│  Provider: DocuSign                         │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Audit Trail                        │   │
│  │  ───────────────────────────────    │   │
│  │  📨 Sent - John (john@co.com)       │   │
│  │  👁 Viewed - John (john@co.com)     │   │
│  │  ✍️ Signed - John (john@co.com)     │   │
│  │  ✅ Completed                       │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [Download Certificate] [Download PDF]      │
│  [Send Reminder]                            │
└─────────────────────────────────────────────┘
```

---

## Webhook Requirements

Every webhook must:
1. ✅ Validate signature (HMAC / API secret)
2. ✅ Reject duplicates (idempotency key)
3. ✅ Log raw payload to `signature_audit_events.raw_payload`
4. ✅ Retry on failure (queue-based)
5. ✅ Be idempotent (status transitions only forward)

---

## DocuSign Integration Details

- API: eSignature REST API v2.1
- Auth: OAuth2 JWT Grant (application-level, no user interaction)
- Sandbox: https://demo.docusign.net
- Webhooks: DocuSign Connect (HMAC validation)
- Support: Embedded signing + email delivery

### Configuration
```python
DOCUSIGN_INTEGRATION_KEY=your_key
DOCUSIGN_USER_ID=your_user_id
DOCUSIGN_ACCOUNT_ID=your_account_id
DOCUSIGN_PRIVATE_KEY=...  # RSA private key for JWT
DOCUSIGN_BASE_URL=https://demo.docusign.net/restapi
```

---

## Testing (Sandbox Only)

| Test Case                | Expected Result              |
|--------------------------|------------------------------|
| One signer               | Envelope sent, signed, done  |
| Multiple signers         | Sequential signing works     |
| Parallel signing         | Signers can sign in any order|
| Decline                  | Status → declined            |
| Expiration               | Status → expired             |
| Reminder                 | Email sent to pending signers|
| Void                     | Status → voided              |
| Resend                   | New email to pending signers |
| Webhook replay           | Duplicates rejected          |
| Certificate download     | PDF returned                 |
| Audit trail              | All events listed            |

---

---

## Definition of Done

Before Sprint 30 can be marked complete, ALL of the following must pass:

### Foundation (Sprint 30.1)
- [ ] Create signature request with signers
- [ ] Add multiple signers with signing order
- [ ] Update signer details
- [ ] Remove signer from request
- [ ] Move request through workflow: draft → preparing → sent
- [ ] Void signature request
- [ ] List and filter signature requests by status
- [ ] No TypeScript errors
- [ ] No backend lint/type issues

### DocuSign Integration (Sprint 30.2)
- [ ] OAuth2 JWT authentication with DocuSign
- [ ] Send envelope to DocuSign
- [ ] Sequential signing order works
- [ ] Embedded signing flow works
- [ ] Email signing flow works
- [ ] Webhook validation (HMAC signature)
- [ ] Duplicate webhook handling (idempotency)
- [ ] Status transitions: sent → viewed → signed → completed
- [ ] Decline handling: sent → declined
- [ ] Expiration handling: sent → expired
- [ ] Audit trail generation from webhook events
- [ ] Completion certificate download (PDF)
- [ ] Executed PDF storage

### Lifecycle Integration (Sprint 30.3)
- [ ] Contract status updated to "preparing_signature" when request created
- [ ] Contract status updated to "sent_for_signature" when sent
- [ ] Contract status updated to "partially_signed" on partial completion
- [ ] Contract status updated to "completed" when fully executed
- [ ] Contract status updated to "declined" / "expired" / "voided" as appropriate
- [ ] Signature request button in negotiation center
- [ ] Signature tab in contract detail view
- [ ] Reminder functionality for pending signers
- [ ] End-to-end tests passing with DocuSign sandbox
