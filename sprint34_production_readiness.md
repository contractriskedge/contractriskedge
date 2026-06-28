# Sprint 34 — Production Readiness

**Theme:** Make the platform deployable, not more feature-rich.
**Duration:** 4 weeks
**Backend:** Frozen except for bug fixes.
**After this:** Sprint 35 (Contract Authoring Studio) → Sprint 36 (Enterprise Integrations)

---

## Guiding Principle

No new business features. No new workflow capabilities. No new AI models.

This sprint is about **trust, security, performance, and operability**. Every item here either prevents a production incident, enables a recovery, or gives an administrator confidence that the platform is healthy.

---

## Week 1 — Security & Tenant Validation (Highest Priority)

Don't start with performance. Start with things that can break customer trust.

### 1.1 Tenant Isolation Verification

Every data access path must be verified. Try accessing Tenant A data from Tenant B — expected result is `403` or `0 records`.

| Entity | Query scoped by tenant_id? | Cross-tenant test |
|---|---|---|
| Contract | Verify | A→B = 0 records |
| Template | Verify | A→B = 0 records |
| Clause | Verify | A→B = 0 records |
| Review | Verify | A→B = 0 records |
| Finding | Verify | A→B = 0 records |
| Workflow Pack | Verify | A→B = 0 records |
| Workflow Instance | Verify | A→B = 0 records |
| Obligation | Verify | A→B = 0 records |
| Signature Envelope | Verify | A→B = 0 records |
| Dashboard Data | Verify | A→B = 0 records |
| Search Results | Verify | A→B = 0 records |
| Export | Verify | A→B = 0 records |
| Audit Events | Verify | A→B = 0 records |
| Notifications | Verify | A→B = 0 records |
| File Storage | Verify | A→B cannot access |

**Automated test:** One script that creates data in Tenant A, attempts access from Tenant B, asserts denial for every entity type.

### 1.2 RBAC Audit

Review every endpoint against the role-permission matrix:

| Role | Can read | Can write | Can delete | Can admin |
|---|---|---|---|---|
| Viewer | Own tenant | No | No | No |
| Reviewer | Own tenant | Reviews | No | No |
| Legal | Own tenant | Contracts | No | No |
| Admin | Own tenant | Yes | Yes | No |
| Workflow Admin | Own tenant | Workflows | Workflows | No |
| Tenant Admin | Own tenant | Yes | Yes | Yes |

Verify no endpoint allows privilege escalation.

### 1.3 Security Review

- [ ] **File upload validation** — type, size, content inspection
- [ ] **File download authorization** — tenant + permission check
- [ ] **SQL injection** — all queries use parameterized statements
- [ ] **XSS prevention** — all user content escaped in UI
- [ ] **JWT validation** — expiry, signature, issuer
- [ ] **Rate limiting** — configured per endpoint group
- [ ] **CSRF protection** — state-changing requests
- [ ] **Secrets management** — no credentials in code

---

## Week 2 — Performance Baselines

### Targets

| Operation | P95 Target | Baseline |
|---|---|---|
| API read endpoints | < 500ms | Measure |
| API write endpoints | < 2s | Measure |
| Dashboard load | < 2s | Measure |
| Search | < 500ms | Measure |
| Workflow validation | < 100ms | 0.005ms |
| JSON Logic evaluation | < 10ms | 0.001ms |
| Simulation | < 1s | 0.001ms |
| Page load (Next.js) | < 2s | Measure |

### Load Test Scenarios

1. **Dashboard** — 50 concurrent users, mixed read/write
2. **Search** — 50 concurrent users, varied queries
3. **Workflow** — 25 concurrent simulations, 25 concurrent validations
4. **AI Review** — 10 concurrent analysis requests
5. **Audit** — 50 concurrent audit log queries

### Deliverable

Performance report:

```
| Operation          | P50    | P95    | P99    | Target |
|--------------------|--------|--------|--------|--------|
| Dashboard          | 120ms  | 180ms  | 350ms  | 500ms  |
| Search             | 180ms  | 240ms  | 410ms  | 500ms  |
| Workflow Validate  | 3ms    | 5ms    | 30ms   | 100ms  |
| Simulation         | 0.5ms  | 1ms    | 2ms    | 1s     |
| Audit Query        | 80ms   | 160ms  | 290ms  | 500ms  |
```

This becomes the production baseline for regression detection.

---

## Week 3 — Operations

### 3.1 System Health Dashboard

A single page administrators open first to understand platform status.

```
┌─────────────────────────────────────────────────────────────┐
│  Platform Health                                  [Live]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🟢 API           🟢 Database      🟢 Search       🟢 Cache │
│     12ms avg        4ms avg         240ms avg       1ms avg │
│                                                             │
│  🟢 Scheduler    🟢 Workflow     🟢 AI Review    🟢 Email  │
│     0 pending       0 failed        0 queued        0 stuck │
│                                                             │
│  🟢 DocuSign     🟢 Storage      🟢 Notifications 🟢 Queue │
│     Connected       72% used        0 pending        0 depth│
│                                                             │
│  ── Recent Alerts ────────────────────────────────────────  │
│  None — all systems operational                             │
└─────────────────────────────────────────────────────────────┘
```

**Backend:** `GET /health` returning all subsystem status with latency.
**Frontend:** Auto-refreshing dashboard with color-coded indicators.

### 3.2 Observability

- [ ] **Prometheus metrics endpoint** (`/metrics`)
  - `http_requests_total{method, path, status}`
  - `http_request_duration_seconds{method, path}`
  - `db_query_duration_seconds{query_name}`
  - `db_connection_pool_size`
  - `cache_hit_ratio`
  - `queue_depth{queue_name}`
- [ ] **Structured JSON logging** — not plain text
- [ ] **Correlation ID** on every request (tracing header)
- [ ] **Slow query log** — queries exceeding 500ms
- [ ] **Health check endpoint** — `GET /health` with DB, cache, queue, storage checks
- [ ] **Error rate alerting** — threshold-based alerts

---

## Week 4 — Deployment

### 4.1 Docker Compose

- `docker-compose.yml` for development
- `docker-compose.prod.yml` for production (with secrets, volumes)
- Services: API, Worker, Frontend, Database, Cache, Queue

### 4.2 Backup & Restore + Disaster Recovery Validation

- [ ] Automated daily database backup (pg_dump + WAL archiving)
- [ ] Object storage backup (contracts, documents)
- [ ] Configuration backup (workflow packs, templates, clauses)
- [ ] Documented restore procedure
- [ ] RTO (Recovery Time Objective) and RPO (Recovery Point Objective) defined

**Disaster Recovery Validation — must be tested, not just documented:**

```
1. Take full backup
2. Delete database
3. Restore from backup
4. Run full acceptance test suite
5. Verify all 35+ tests pass
6. Record RTO and RPO
```

**Deliverable:**

```
Recovery Time (RTO):    < 10 min
Recovery Point (RPO):   < 5 min
Acceptance Tests:       35/35 Passed
```

### 4.3 Production Configuration Validator

Before the application starts, verify every required dependency:

```python
# On startup, check:
✅ DATABASE_URL — connection successful
✅ REDIS_URL — cache connected
✅ STORAGE_BUCKET — bucket accessible
✅ AI_PROVIDER — model loaded and responsive
✅ SMTP_HOST — email configured
✅ DOCUSIGN_CLIENT_ID — API credentials valid
✅ JWT_SECRET — signing key present
✅ All required env vars — present and non-empty
✅ Disk space — sufficient (> 10% free)
✅ TLS certificates — valid (if HTTPS enabled)
```

If any check fails, the service logs a clear error and exits immediately:

```
Startup Failed
Reason: Missing DOCUSIGN_CLIENT_ID
Expected: Set DOCUSIGN_CLIENT_ID environment variable
```

### 4.4 OpenAPI Documentation

- [ ] All endpoints documented (FastAPI auto-generation)
- [ ] Request/response schemas accurate
- [ ] Error responses follow consistent format
- [ ] Authentication documented (Bearer JWT)
- [ ] Rate limits documented
- [ ] Pagination documented

### 4.5 API Compatibility Tests

Automated API regression tests that run after every build. Every major module must have at least one test:

```
✅ GET    /api/v1/contracts
✅ POST   /api/v1/templates
✅ POST   /api/v1/contracts/generate
✅ POST   /api/v1/reviews
✅ POST   /api/v1/reviews/{id}/approve
✅ POST   /api/v1/signatures/send
✅ POST   /api/v1/obligations
✅ GET    /api/v1/search
✅ GET    /api/v1/dashboard
✅ GET    /api/v1/workflow-packs
✅ POST   /api/v1/workflow-packs/{id}/validate
✅ POST   /api/v1/workflow-packs/{id}/simulate
✅ POST   /api/v1/workflow-packs/{id}/publish
✅ GET    /api/v1/workflow-instances
✅ GET    /api/v1/workflow-analytics
✅ GET    /api/v1/workflow-audit
```

**Implementation:** One pytest file (`test_api_compatibility.py`) that calls every endpoint and asserts `2xx` response.

### 4.6 Demo Seed Data

Create a realistic demo tenant:

- **100+ contracts** across NDA, MSA, SOW, License, DPA
- **30 templates** with clause placeholders
- **200 clauses** in the Clause Library
- **50 obligations** with due dates
- **20 workflow packs** (5 active, 15 templates)
- **500 AI findings** across contracts
- **Completed signatures** via DocuSign mock
- **Upcoming renewals** for the next 6 months
- **Dashboard data** populated with realistic metrics
- **Search index** populated

**Implementation:** `seed_demo.py` — idempotent, runs in < 60 seconds.

---

## Deliverable: Readiness Report

At the end of Sprint 34, produce this report:

```
# Sprint 34 — Enterprise Readiness Report

| Area              | Status | Notes |
|-------------------|--------|-------|
| Tenant Isolation  | ✅     | 15/15 entities verified, cross-tenant attacks tested |
| Security Audit    | ✅     | 12/12 checks passed |
| RBAC              | ✅     | 6 roles verified, privilege escalation tested |
| Performance       | ✅     | All P95 targets met, baselines recorded |
| Health Checks     | ✅     | 10 subsystems monitored |
| Monitoring        | ✅     | Prometheus metrics + structured logging + alerts |
| Backup            | ✅     | Automated daily, RTO < 10min, RPO < 5min |
| Restore           | ✅     | Tested: delete → restore → 35/35 tests pass |
| API Compatibility | ✅     | 16 endpoint regression tests pass |
| Config Validation | ✅     | 10 startup checks, fails fast on missing config |
| API Docs          | ✅     | OpenAPI complete |
| Demo Environment  | ✅     | 100+ contracts, 20 workflows, realistic data |
| Integration Tests | ✅     | Full lifecycle validated |
```

This becomes the **go/no-go checklist** before customer pilots.

---

## What NOT to build

| Feature | Why not | When |
|---|---|---|
| Contract Authoring Studio | New feature | Sprint 35 |
| Enterprise Integrations | New feature | Sprint 36 |
| AI Copilot | New feature | Sprint 37 |
| Administration Center | New feature | Sprint 38 |
| New workflow capabilities | Engine is feature-complete | Post-Sprint 38 review |
