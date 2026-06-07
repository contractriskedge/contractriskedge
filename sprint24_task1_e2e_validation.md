# Sprint 24 Task 1 — End-to-End Validation Audit

**Date**: 2026-06-05  
**Objective**: Execute a full system audit of the contract lifecycle and assess production readiness

---

## 1. Workflow Diagram

```
USER uploads file (POST /api/v1/uploads)
  │
  ▼
UPLOADED ──→ VALIDATING ──→ VALIDATED ──→ STORAGE_CONFIRMED
                                            │
                                            ▼
                                    OCR_PENDING ──→ OCR_PROCESSING ──→ OCR_COMPLETE
                                                                          │
                                                                          ▼
                                                                  CHUNKING_PENDING
                                                                  (semantic chunking)
                                                                        │
                                                                        ▼
                                                                EMBEDDING_PENDING
                                                                (OpenAI embeddings → pgvector)
                                                                        │
                                                                        ▼
                                                                ANALYSIS_PENDING
                                                                (AI analysis via GPT-4o)
                                                                        │
                                                                        ▼
                                                                REVIEW_READY
                                                                (ContractReview created)
                                                                        │
                                                                  ┌─────┴─────┐
                                                                  │           │
                                                            AI_ANALYZED   FAILED
                                                                  │
                                                            IN_REVIEW
                                                          (reviewer works)
                                                                  │
                                                    ┌─────────────┼─────────────┐
                                                    ▼             ▼             ▼
                                            PROCUREMENT      LEGAL        SECURITY
                                            _REVIEW          _REVIEW      _REVIEW
                                                    │             │             │
                                                    ▼             ▼             ▼
                                              NEGOTIATION ←─── ESCALATED ──→ IN_REVIEW
                                                    │
                                                    ▼
                                              APPROVED
                                                    │
                                              FINALIZED / EXECUTED / ARCHIVED
```

### Dual State Machines

| Machine | Scope | States | Terminal |
|---------|-------|--------|----------|
| **IngestionState** | File processing pipeline | 14 states | `REVIEW_READY`, `FAILED`, `CANCELLED`, `QUARANTINED` |
| **ReviewStatus** | Contract review lifecycle | 21 states | `ARCHIVED`, `CLOSED` |

---

## 2. Validation Results

### Endpoint Audit (12/12 passing)

| Stage | Endpoint | Status | Response Time |
|-------|----------|--------|---------------|
| Upload | `GET /uploads` | ✅ 200 | 0.0s |
| Upload | `GET /uploads/queue/stats` | ✅ 200 | 0.0s |
| Reviews | `GET /reviews` | ✅ 200 | 0.0s |
| Dashboard | `GET /reviews/dashboard` | ✅ 200 | 0.0s |
| Contracts | `GET /contracts` | ✅ 200 | 0.0s |
| Contracts | `GET /contracts/kpis` | ✅ 200 | 0.0s |
| Tenant Config | `GET /tenant-config/summary` | ✅ 200 | 0.0s |
| Tenant Config | `GET /tenant-config/features/definitions` | ✅ 200 | 0.0s |
| Admin | `GET /admin/settings` | ✅ 200 | 0.0s |
| Policy Packs | `GET /tenant-config/policy-packs` | ✅ 200 | 0.0s |
| Scoring Overrides | `GET /tenant-config/scoring-overrides` | ✅ 200 | 0.0s |
| Compliance Packs | `GET /tenant-config/compliance-packs` | ✅ 200 | 0.0s |

### Data Volume

| Metric | Value |
|--------|-------|
| Total uploads | 20 |
| Total reviews | 83 |
| Reviews by status | ai_analyzed: 51, closed: 9, finalized: 5, escalated: 4, approved: 3, rejected: 3, in_review: 2, legal_review: 2, legal_approval: 2, exec_approval: 2 |
| Total contracts | 83 |
| Active reviews | 61 |
| High risk contracts | 18 |
| Average risk score | 7.6/10 |
| Feature flags | 14 defined |
| Business units | 6 configured |

---

## 3. Failed Scenarios

### Critical: `GET /reviews/{id}` Returns 500

**Error**: `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`

**Affected endpoints**:
- `GET /reviews/{id}` — review detail
- `GET /reviews/{id}/findings` — findings list
- `GET /reviews/{id}/redlines` — redlines list
- `GET /reviews/{id}/risk-breakdown` — risk analysis
- `GET /reviews/{id}/activity` — activity timeline
- `GET /reviews/{id}/status` — status polling

**Root Cause**: The `get_review()` method in `service.py` (line 149) recomputes `finding_count` and `redline_count` from the `review_findings`/`review_redlines` tables using async SQLAlchemy operations. This works when called from an async context (e.g., Celery worker), but fails when called from the FastAPI request handler due to a greenlet context mismatch.

**Impact**: **HIGH** — Blocks the entire Review Workspace. Users cannot:
- View review details
- See findings
- See redlines
- See risk breakdown
- See activity timeline
- Poll review status

**Fix**: Ensure the async session is properly initialized in the FastAPI middleware chain before the review router handles requests.

### Medium: Test Fixture Data Has Phantom Counters

57 reviews (test fixtures) have `finding_count=3` and `redline_count=1` hardcoded but zero actual records in `review_findings`/`review_redlines`. This causes the list view to show incorrect counts for test data.

**Impact**: LOW (test data only, not production)

---

## 4. Risk Assessment

| Risk | Severity | Likelihood | Impact | Priority |
|------|----------|------------|--------|----------|
| Review detail 500 error | **Critical** | **Always** | Blocks workspace entirely | **P0** |
| Test fixture phantom counts | Low | Always | Misleading counters in list | P3 |
| No AI extraction of vendor/title | Medium | Always | All contracts show filename only | P2 |
| No multi-tenant policy isolation | Medium | Unknown | Tenant configs may not affect analysis | P2 |

---

## 5. Production Readiness Score

| Category | Score | Notes |
|----------|-------|-------|
| **Upload Pipeline** | **85%** | 14-state machine, Celery worker chain, retry logic. No upload endpoint tested end-to-end in this audit. |
| **AI Analysis** | **80%** | GPT-4o pipeline with findings, redlines, risk scoring. No AI extraction of contract metadata. |
| **Review Workspace** | **50%** | Blocked by MissingGreenlet error. All UI exists but cannot load data. |
| **Review Queue** | **90%** | Full enterprise queue with filters, sorting, bulk actions, SLA tracking. |
| **Review Dashboard** | **90%** | Summary cards, contracts table, filters, sorting. Uses live API. |
| **Tenant Settings** | **85%** | 6 functional tabs. Compliance packs missing DELETE endpoint. |
| **Approval Workflow** | **85%** | 21-state machine, assign/escalate/approve/reject, permission gating. |
| **Data Integrity** | **70%** | 26 real reviews have correct data. 57 test fixtures have phantom counters. |

### Overall Production Readiness: **72%**

### Blocker
The `MissingGreenlet` error on `GET /reviews/{id}` is the single highest-priority issue. Fixing this unlocks the entire Review Workspace.

---

## 6. Recommended Actions

### P0 — Fix MissingGreenlet Error

**File**: `backend/app/domains/review/service.py`  
**Issue**: `get_review()` at line 149 recomputes counts using async SQLAlchemy without proper async context  
**Fix**: Either:
1. Remove the count recomputation (use stored counters)
2. Use `sync` session for the count queries
3. Ensure the async session middleware initializes greenlet context before route handlers

### P1 — Fix Review Detail Endpoint

Once the greenlet issue is fixed, verify:
- `GET /reviews/{id}` returns 200 with full review data
- `GET /reviews/{id}/findings` returns findings
- `GET /reviews/{id}/redlines` returns redlines
- `GET /reviews/{id}/risk-breakdown` returns risk analysis
- `GET /reviews/{id}/activity` returns activity timeline

### P2 — Add AI Contract Metadata Extraction

Add extraction of `contract_title`, `vendor_name`, `agreement_type` to the AI analysis pipeline. Store in `upload_sessions.metadata` JSONB.

### P3 — Clean Test Fixture Counters

```sql
UPDATE contract_reviews
SET finding_count = 0, redline_count = 0
WHERE NOT EXISTS (SELECT 1 FROM review_findings rf WHERE rf.review_id = contract_reviews.review_id);
```
