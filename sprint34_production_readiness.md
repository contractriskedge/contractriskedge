# Sprint 34 — Production Readiness

**Theme:** Make the platform deployable, not more feature-rich.
**Duration:** 3 weeks
**Backend:** Frozen except for bug fixes.
**After this:** Sprint 35 (Contract Authoring Studio) → Sprint 36 (Enterprise Integrations)

---

## Guiding Principle

No new business features. No new workflow capabilities. No new AI models.

This sprint is about **trust, performance, and operability**. Every item here either prevents a production incident, enables a recovery, or gives an administrator confidence that the platform is healthy.

---

## Deliverable 1: Multi-Tenant Verification (Highest Priority)

### Scope
Every data access path must be verified for tenant isolation.

### Checklist

- [ ] **All API endpoints** — verify `tenant_id` is extracted from auth context, not from request body
- [ ] **All repository queries** — verify every `SELECT` includes `WHERE tenant_id = :tenant_id`
- [ ] **All cache keys** — verify tenant ID is part of every cache key
- [ ] **All search indexes** — verify search results are filtered by tenant
- [ ] **All exports** — verify exported data is scoped to tenant
- [ ] **All notifications** — verify notifications are sent only to users in the same tenant
- [ ] **All webhooks** — verify webhook payloads are tenant-scoped
- [ ] **All audit events** — verify audit queries filter by tenant
- [ ] **All workflow instances** — verify cross-tenant workflow access is impossible
- [ ] **All file storage paths** — verify object storage keys include tenant ID

### Test

Write an automated test that:
1. Creates data in Tenant A
2. Attempts to access it from Tenant B
3. Asserts the access is denied (empty result, 403, or equivalent)

Run this for every major entity type.

---

## Deliverable 2: Performance Baselines & Targets

### Targets

| Operation | P95 Target | Current Baseline |
|---|---|---|
| API read endpoints | < 500ms | TBD |
| API write endpoints | < 2s | TBD |
| Workflow validation | < 100ms | 0.005ms |
| JSON Logic evaluation | < 10ms | 0.001ms |
| Simulation | < 1s | 0.001ms |
| Search | < 500ms | TBD |
| Dashboard load | < 2s | TBD |
| Page load (Next.js) | < 2s | TBD |

### Implementation

1. Run load tests for each operation with 10, 50, 100 concurrent users
2. Record P50, P95, P99 for each
3. Identify top 3 bottlenecks
4. Optimize or document as known limitations

### Tools

- `locust` or `k6` for load testing
- Existing `test_concurrent_load_benchmark.py` for workflow-specific tests
- Application Performance Monitoring (APM) for production tracking

---

## Deliverable 3: Security Audit

### Scope

- [ ] **RBAC enforcement** — verify every endpoint checks permissions before executing
- [ ] **Authentication** — verify JWT validation, expiry, and refresh flows
- [ ] **Authorization** — verify users cannot escalate privileges
- [ ] **Input validation** — verify all user inputs are validated (type, length, range, format)
- [ ] **SQL injection** — verify all queries use parameterized statements (SQLAlchemy ORM handles this, but raw SQL in migrations should be reviewed)
- [ ] **XSS prevention** — verify all user-generated content is escaped in UI
- [ ] **CSRF protection** — verify state-changing requests require CSRF tokens
- [ ] **Rate limiting** — verify API rate limits are configured
- [ ] **File upload** — verify file type, size, and content validation
- [ ] **File download** — verify download authorization checks tenant and permissions
- [ ] **Audit integrity** — verify audit logs are append-only (no deletion or modification)
- [ ] **Secrets management** — verify API keys, database credentials, and signing secrets are not in code

---

## Deliverable 4: Observability

### Metrics to expose

```
Endpoint: /metrics (Prometheus format)

- http_requests_total{method, path, status}
- http_request_duration_seconds{method, path}
- db_query_duration_seconds{query_name}
- db_connection_pool_size
- cache_hit_ratio
- queue_depth{queue_name}
- workflow_instances_total{status}
- workflow_execution_duration_seconds{workflow_type}
- ai_analysis_duration_seconds
- signature_envelope_status{provider, status}
```

### Health checks

```
GET /health

{
  "status": "healthy",
  "version": "2.0.0",
  "checks": {
    "database": { "status": "healthy", "latency_ms": 2 },
    "cache": { "status": "healthy", "latency_ms": 1 },
    "queue": { "status": "healthy", "depth": 0 },
    "storage": { "status": "healthy" },
    "ai_service": { "status": "healthy" },
    "signature_provider": { "status": "healthy", "provider": "docusign" }
  },
  "uptime_seconds": 86400
}
```

### Logging

- Structured JSON logging (not plain text)
- Correlation ID on every request
- Log levels: DEBUG, INFO, WARN, ERROR
- Slow query log (> 500ms queries)
- Error rate alerting

---

## Deliverable 5: System Health Dashboard

A single page administrators open first to understand platform status.

```
┌─────────────────────────────────────────────────────────────┐
│  System Health                                  [Last: 2m] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Contracts │  │ AI Queue │  │ Workflow │  │ Notific- │   │
│  │ 66        │  │ Healthy  │  │ Healthy  │  │ ations   │   │
│  │ ▲ 3 today │  │ 0 pending│  │ 0 failed │  │ Healthy  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ DocuSign │  │ Storage  │  │ Search   │  │ Database │   │
│  │ Connected│  │ 72% used │  │ Healthy  │  │ Healthy  │   │
│  │ 12 envs  │  │ 1.2TB/2TB│  │ 1.2s avg│  │ 4ms avg  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                             │
│  ── Recent Alerts ────────────────────────────────────────  │
│  None — all systems operational                             │
└─────────────────────────────────────────────────────────────┘
```

### Components

- Backend: `GET /health` endpoint returning all subsystem status
- Frontend: `SystemHealthDashboard` component with auto-refresh
- Color-coded: green (healthy), yellow (degraded), red (down)

---

## Deliverable 6: Backup & Restore

### Database

- [ ] Automated daily backup script
- [ ] Point-in-time recovery (WAL archiving for PostgreSQL)
- [ ] Documented restore procedure
- [ ] Tested restore to a separate environment

### Object Storage

- [ ] Backup of uploaded contracts and documents
- [ ] Cross-region replication (if applicable)
- [ ] Retention policy configuration

### Configuration

- [ ] Backup of workflow packs, templates, clause library
- [ ] Export/import format already exists (JSON/YAML)

### Documentation

- [ ] Disaster recovery runbook
- [ ] RTO (Recovery Time Objective) and RPO (Recovery Point Objective) defined

---

## Deliverable 7: OpenAPI Documentation

- [ ] All endpoints documented via FastAPI's automatic OpenAPI generation
- [ ] Request/response schemas accurate
- [ ] Error responses follow consistent format
- [ ] Authentication documented (Bearer JWT)
- [ ] Rate limits documented
- [ ] Pagination documented

---

## Deliverable 8: Seed Data & Demo Environment

Create a realistic demo tenant with:

- **20+ vendors** with varied profiles
- **100+ contracts** across different types (NDA, MSA, SOW, License, DPA)
- **5 workflow packs** (NDA Review, Procurement, Legal Review, High Value, Renewal)
- **Obligations** attached to contracts
- **Negotiations** with redlines and comments
- **AI findings** with suggested clauses
- **Completed signatures** via DocuSign mock
- **Renewals** scheduled for upcoming months
- **Dashboard data** populated with realistic metrics
- **Search index** populated

### Implementation

- Create a `seed_demo.py` script that populates all data
- Script should be idempotent (safe to run multiple times)
- Script should run in < 60 seconds

---

## What NOT to build in Sprint 34

| Feature | Why not | When |
|---|---|---|
| Contract Authoring Studio | New feature, not hardening | Sprint 35 |
| Enterprise Integrations | New feature, not hardening | Sprint 36 |
| AI Copilot | New feature, not hardening | Sprint 37 |
| Administration Center | New feature, not hardening | Sprint 38 |
| New workflow capabilities | Engine is feature-complete | Post-Sprint 38 review |

---

## Implementation Order

| Week | Focus |
|---|---|
| Week 1 | Multi-tenant verification + Performance baselines |
| Week 1 | Security audit |
| Week 2 | Observability (metrics, health checks, logging) |
| Week 2 | System Health Dashboard |
| Week 3 | Backup/Restore + OpenAPI documentation |
| Week 3 | Seed data + Demo environment + Enterprise Readiness Review |
