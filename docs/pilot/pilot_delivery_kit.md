# ContractRiskEdge — Pilot Delivery Kit

## Table of Contents

1. [Deployment Guide](#1-deployment-guide)
2. [Architecture Overview](#2-architecture-overview)
3. [Security Overview](#3-security-overview)
4. [Onboarding Guide](#4-onboarding-guide)
5. [Admin Guide](#5-admin-guide)
6. [Incident Guide](#6-incident-guide)
7. [SLA Expectations](#7-sla-expectations)
8. [Pilot Success Criteria](#8-pilot-success-criteria)

---

## 1. Deployment Guide

### Prerequisites

| Dependency | Minimum Version | Required |
|-----------|----------------|----------|
| Docker | 24.0+ | Yes |
| Docker Compose | 2.20+ | Yes |
| Python | 3.12+ | For seed scripts |
| PostgreSQL 16 + pgvector | 16+ | Managed or self-hosted |
| Redis | 7+ | Managed or self-hosted |
| Auth0 tenant | — | Yes |
| OpenAI API key | — | Yes |
| S3-compatible storage | — | Yes (MinIO for dev) |

### Quick Start (Docker Compose)

```bash
# 1. Clone and configure
git clone <repo-url>
cd contractrisk-edge
cp .env.example .env
# Edit .env with your secrets (see Environment Variables below)

# 2. Start infrastructure
docker compose up -d postgres redis minio

# 3. Run database migrations
cd backend
alembic upgrade head

# 4. Seed demo data
python -m app.scripts.seed_demo_tenant --reset

# 5. Start full stack
docker compose up -d
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string (asyncpg) |
| `REDIS_URL` | Yes | Redis connection string |
| `AUTH0_DOMAIN` | Yes | Auth0 tenant domain |
| `AUTH0_AUDIENCE` | Yes | Auth0 API identifier |
| `AUTH0_ISSUER` | Yes | Auth0 issuer URL |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `SECRET_KEY` | Yes | Application secret (min 32 chars) |
| `S3_ENDPOINT_URL` | No | S3-compatible storage endpoint |
| `S3_ACCESS_KEY_ID` | No | S3 access key |
| `S3_SECRET_ACCESS_KEY` | No | S3 secret key |
| `SENTRY_DSN` | No | Sentry error tracking DSN |
| `OTEL_ENABLED` | No | Enable OpenTelemetry (default: true) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | OTel collector endpoint |

### Verification

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs

# Metrics
curl http://localhost:8000/metrics

# Frontend
open http://localhost:3000
```

---

## 2. Architecture Overview

### System Context

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────▶│   FastAPI    │────▶│  PostgreSQL │
│  (Next.js)  │     │   Backend    │     │  + pgvector │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │                     │
       │                    │                     │
       ▼                    ▼                     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Auth0     │     │   Celery     │     │    Redis    │
│  (JWT)      │     │   Workers    │     │  (Queue)    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   OpenAI     │     │  S3/MinIO   │
                    │   (AI/LLM)   │     │  (Storage)  │
                    └──────────────┘     └─────────────┘
```

### Key Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Gateway** | FastAPI | REST API, WebSocket, auth, rate limiting |
| **Workers** | Celery | Async ingestion, AI analysis, notifications |
| **Database** | PostgreSQL 16 + pgvector | Relational data + vector embeddings |
| **Queue** | Redis | Celery broker + result backend |
| **Storage** | S3/MinIO | Document storage |
| **Auth** | Auth0 | JWT-based authentication + RBAC |
| **AI** | OpenAI GPT-4o | Contract analysis, copilot, briefings |
| **Frontend** | Next.js 14 | Enterprise UI with SSR |
| **Observability** | OpenTelemetry + Grafana | Metrics, traces, dashboards |

### Data Flow

```
Upload → Validate → OCR → Extract → Chunk → Embed → Analyze → Review → Export
```

---

## 3. Security Overview

### Authentication
- JWT-based (RS256) via Auth0
- MFA supported (tenant-configurable)
- Token expiry: configurable (default 24h)
- Session management: stateless JWT

### Authorization
- Role-Based Access Control (RBAC)
- Granular permissions per endpoint
- Route-level permission validation
- Default-deny for unauthenticated requests

### Data Protection
- Encryption in transit: TLS 1.3
- Encryption at rest: storage-provider dependent
- Tenant isolation: row-level security
- Audit trail: immutable append-only logs
- Credential encryption: AES-256 for integration secrets

### AI Security
- Prompt injection guardrails
- Structured output validation
- Per-tenant rate limiting
- Token accounting and cost tracking
- Execution tracing for replay

### Network Security
- CORS: whitelist-based
- Rate limiting: per-IP and per-tenant
- Request size limits
- SQL injection protection (parameterized queries)
- WebSocket authentication on connect

---

## 4. Onboarding Guide

### First Login
1. Navigate to the platform URL
2. Click "Log in" — redirected to Auth0
3. Authenticate with your enterprise credentials
4. Accept terms of service

### First Contract Upload
1. Navigate to "Upload" from the sidebar
2. Drag and drop a PDF contract (or click to browse)
3. Set metadata (vendor, type, business unit)
4. Click "Upload" — processing begins automatically
5. Monitor progress in the upload queue

### First Review
1. When AI analysis completes, navigate to "Reviews"
2. Select the contract from the queue
3. Review AI-generated findings and redlines
4. Accept, modify, or reject each suggestion
5. Add comments for collaboration
6. Approve or escalate the review

### First Executive Insight
1. Navigate to "Executive" from the sidebar
2. View portfolio risk summary
3. Review SLA heatmap
4. Check operational alerts
5. Generate AI briefing

### First Alert Simulation
1. Navigate to "Executive" → "Alert Center"
2. Alerts appear automatically based on operational data
3. Acknowledge, escalate, or resolve alerts
4. View alert details for affected entities

---

## 5. Admin Guide

### User Management
- Add users via Auth0 dashboard
- Assign roles: viewer, reviewer, legal_reviewer, auditor, admin, executive
- Permissions are enforced at the API layer

### Tenant Configuration
- Each tenant is isolated at the database level
- Configure tenant settings via `/admin` console
- Set feature flags, rate limits, workspace limits

### Monitoring
- **Health**: `GET /health`
- **Metrics**: `GET /metrics`
- **Grafana**: Operational dashboards at `http://<host>:3001`
- **Flower**: Celery monitoring at `http://<host>:5555`

### Backup
- Database: `pg_dump` or managed DB snapshot
- Storage: S3 bucket replication
- Configuration: Environment variables + Auth0 tenant

---

## 6. Incident Guide

See [Operational Runbooks](./runbooks.md) for detailed incident response procedures.

### Quick Reference

| Incident | Severity | First Action |
|----------|----------|-------------|
| AI provider down | Critical | Enable fallback mode |
| Database slow | High | Check slow queries |
| WebSocket disconnected | High | Restart events router |
| Queue backlog | Medium | Scale workers |
| Deployment failed | Variable | Rollback to last stable |

---

## 7. SLA Expectations

| Metric | Target | Measurement |
|--------|--------|-------------|
| API availability | 99.9% | Uptime monitoring |
| API response time (P95) | < 500ms | Prometheus |
| AI analysis time | < 5 min per contract | Execution tracking |
| Ingestion time | < 2 min per document | Pipeline tracking |
| Dashboard load time | < 2s | Frontend telemetry |
| Alert delivery | < 30s | Real-time feed |
| Support response | < 4 hours business hours | Ticketing system |

---

## 8. Pilot Success Criteria

### Must-Have
- [ ] User can upload a contract and receive AI analysis
- [ ] User can review findings and approve/reject redlines
- [ ] Executive dashboard shows real operational data
- [ ] Alerts are generated for SLA breaches and anomalies
- [ ] AI briefing can be generated for any time period
- [ ] Search returns relevant contract clauses
- [ ] Audit trail captures all review actions

### Should-Have
- [ ] Multi-user collaboration on reviews
- [ ] Custom playbook integration
- [ ] Benchmark comparison against industry data
- [ ] Export review reports
- [ ] WebSocket real-time updates

### Nice-to-Have
- [ ] Integration with enterprise SSO
- [ ] Custom workflow automation
- [ ] Marketplace pack installation
- [ ] Federation coordination

### Exit Criteria
- [ ] 10+ successful end-to-end reviews completed
- [ ] Executive team has reviewed dashboards
- [ ] Security review completed with no critical findings
- [ ] Load testing shows acceptable performance
- [ ] Deployment process is reproducible
- [ ] Onboarding takes < 15 minutes for new users
- [ ] Operational runbooks are validated
