# ContractRiskEdge — Enterprise Service Architecture & Runtime Execution Model

## Fortune 500 AI-Native Contract Intelligence Operating System

---

## Table of Contents

1. [Service Topology Overview](#1-service-topology-overview)
2. [API Gateway & Edge Services](#2-api-gateway--edge-services)
3. [Core Microservices](#3-core-microservices)
4. [AI Execution Runtime](#4-ai-execution-runtime)
5. [Async Processing & Queue Architecture](#5-async-processing--queue-architecture)
6. [Worker Fleet](#6-worker-fleet)
7. [Orchestration Layer](#7-orchestration-layer)
8. [Integration Runtime](#8-integration-runtime)
9. [Event Bus & Webhook Architecture](#9-event-bus--webhook-architecture)
10. [Data Layer Topology](#10-data-layer-topology)
11. [Infrastructure Topology](#11-infrastructure-topology)
12. [Observability Stack](#12-observability-stack)
13. [Scaling Strategy](#13-scaling-strategy)
14. [Deployment Topology](#14-deployment-topology)
15. [Security Architecture](#15-security-architecture)
16. [Disaster Recovery & Resilience](#16-disaster-recovery--resilience)
17. [Runtime Execution Models](#17-runtime-execution-models)
18. [Service-Level Objectives](#18-service-level-objectives)

---

## 1. Service Topology Overview

### 1.1 High-Level Architecture

```
                                     ┌─────────────┐
                                     │   CDN       │
                                     │ (CloudFront)│
                                     └──────┬──────┘
                                            │
                                     ┌──────▼──────┐
                                     │  Load       │
                                     │  Balancer   │
                                     │ (ALB/NLB)   │
                                     └──────┬──────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
              ┌─────▼─────┐          ┌──────▼──────┐         ┌─────▼─────┐
              │  Next.js  │          │  FastAPI    │         │  FastAPI  │
              │  Frontend │          │  API Gateway│         │  Public   │
              │  (SSR)    │          │  (Internal) │         │  Webhooks │
              └─────┬─────┘          └──────┬──────┘         └─────┬─────┘
                    │                       │                       │
                    └───────┬───────────────┘                       │
                            │                                       │
                     ┌──────▼──────┐                        ┌──────▼──────┐
                     │  Service    │                        │  Event      │
                     │  Mesh      │                        │  Ingress    │
                     │ (Istio)    │                        │             │
                     └──────┬──────┘                        └─────────────┘
                            │
          ┌─────────────────┼─────────────────────────────────────┐
          │                 │                                     │
    ┌─────▼─────┐    ┌──────▼──────┐    ┌──────────────┐    ┌────▼─────┐
    │  Contract │    │   AI        │    │  Workflow    │    │Procure-  │
    │  Service  │    │  Service    │    │  Engine      │    │ment Intel│
    └─────┬─────┘    └──────┬──────┘    └──────┬───────┘    └────┬─────┘
          │                 │                  │                 │
    ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼───────┐   ┌─────▼─────┐
    │  Compliance│   │  Search     │    │  Notification│   │  Analytics│
    │  Service   │   │  Service    │    │  Service     │   │  Service  │
    └─────┬─────┘   └──────┬──────┘    └──────┬───────┘   └─────┬─────┘
          │                 │                  │                 │
          └─────────────────┼──────────────────┼─────────────────┘
                            │                  │
                     ┌──────▼──────┐    ┌──────▼──────┐
                     │  PostgreSQL │    │   Redis     │
                     │  (pgvector) │    │  (Cache,    │
                     │             │    │   Queue)    │
                     └─────────────┘    └─────────────┘
```

### 1.2 Service Inventory

| Service | Protocol | Language | Replicas | Criticality | Dependencies |
|---------|----------|----------|----------|-------------|--------------|
| **API Gateway** | HTTP/REST | Python/FastAPI | 3-6 | Critical | Auth0, Redis |
| **Frontend** | HTTP/SSR | TypeScript/Next.js | 2-4 | Critical | API Gateway |
| **Contract Service** | HTTP/REST | Python/FastAPI | 3-6 | Critical | PostgreSQL, S3 |
| **AI Service** | HTTP+gRPC | Python/FastAPI | 3-8 | Critical | PostgreSQL, Redis, LLM APIs |
| **Workflow Engine** | HTTP+gRPC | Python/FastAPI | 2-4 | Critical | PostgreSQL, Redis |
| **Procurement Intel** | HTTP/REST | Python/FastAPI | 2-3 | High | PostgreSQL |
| **Compliance Service** | HTTP/REST | Python/FastAPI | 2-3 | High | PostgreSQL |
| **Search Service** | HTTP/gRPC | Python/FastAPI | 2-4 | High | PostgreSQL, pgvector |
| **Notification Service** | HTTP+WS | Python/FastAPI | 2-3 | Medium | Redis, SES/SendGrid |
| **Analytics Service** | HTTP/REST | Python/FastAPI | 2-3 | Medium | PostgreSQL, Redshift |
| **Ingestion Worker** | Task Queue | Python/Celery | 3-8 | Critical | Redis, S3, OCR |
| **AI Worker** | Task Queue | Python/Celery | 3-10 | Critical | Redis, LLM APIs |
| **Webhook Dispatcher** | Task Queue | Python/Celery | 2-3 | Medium | Redis |
| **Batch Scheduler** | Cron/Event | Python | 1-2 | Low | Redis, PostgreSQL |
| **Event Bus** | Pub/Sub | Redis/NSQ | 2-3 | High | Redis/NSQ |

---

## 2. API Gateway & Edge Services

### 2.1 API Gateway Architecture

```
                         ┌──────────────────────┐
                         │   AWS ALB / NLB       │
                         │   TLS Termination     │
                         │   WebSocket Support   │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   FastAPI Gateway    │
                         │   (api/main.py)      │
                         ├──────────────────────┤
                         │ Middleware Stack:     │
                         │ 1. CORS               │
                         │ 2. Rate Limiting      │
                         │ 3. AuthN/AuthZ        │
                         │ 4. Request Logging    │
                         │ 5. Tenant Resolution  │
                         │ 6. Request ID         │
                         │ 7. Audit Logging      │
                         └──────────┬───────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
        ┌──────▼──────┐    ┌───────▼───────┐    ┌───────▼──────┐
        │ Internal    │    │  Public       │    │  Admin       │
        │ Routes      │    │  Webhooks     │    │  Routes      │
        │ /api/v1/*   │    │  /webhooks/*  │    │  /admin/*    │
        └─────────────┘    └───────────────┘    └──────────────┘
```

### 2.2 Middleware Pipeline

| Middleware | Order | Purpose | Configuration |
|-----------|-------|---------|---------------|
| **CORS** | 1 | Cross-origin requests | Whitelist origins from env |
| **Rate Limiter** | 2 | Request throttling | Redis-backed, per-tenant + per-user |
| **AuthN** | 3 | JWT verification | Auth0 JWKS, API key fallback |
| **AuthZ/RBAC** | 4 | Permission check | Role + permission lookup |
| **Tenant Resolution** | 5 | Tenant context | JWT claim + X-Tenant-ID header |
| **Request ID** | 6 | Distributed tracing | UUID v4, propagated to all services |
| **Logging** | 7 | Structured logging | JSON format, OpenTelemetry |
| **Audit** | 8 | Mutation audit | Async write to audit_logs |

### 2.3 Rate Limiting Strategy

```
┌────────────────────────────────────────────────────────────────┐
│  RATE LIMITING (Redis-based, sliding window)                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Per-Tenant:    1000 req/min (burst: 2000)                    │
│  Per-User:      100 req/min  (burst: 200)                     │
│  Per-Endpoint:  50 req/min  (AI endpoints)                    │
│  Per-IP:        500 req/min (unauthenticated)                 │
│                                                                │
│  AI Endpoints:  20 req/min  per tenant (cost control)         │
│  Webhook:       200 req/min per tenant                        │
│  Export:        10 req/min  per user                          │
│                                                                │
│  Response Headers: X-RateLimit-Remaining, X-RateLimit-Reset   │
│  Over-limit:    429 Too Many Requests + Retry-After header    │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Microservices

### 3.1 Service Boundary Definitions

#### Contract Service

```
Purpose:    Contract lifecycle management, CRUD, versioning, relationships
Language:   Python/FastAPI
Database:   PostgreSQL (contracts, contract_versions, contract_relationships)
Storage:    S3 (document files)
Cache:      Redis (contract metadata, active contracts list)
Queues:     Emits: contract.uploaded, contract.archived
            Consumes: ingestion.completed (status update)

Endpoints:
    POST   /api/v1/contracts              — Upload contract
    GET    /api/v1/contracts              — List contracts (filtered, paginated)
    GET    /api/v1/contracts/{id}         — Get contract detail
    PUT    /api/v1/contracts/{id}         — Update contract metadata
    DELETE /api/v1/contracts/{id}         — Soft delete contract
    POST   /api/v1/contracts/{id}/versions — Create new version
    GET    /api/v1/contracts/{id}/versions — List versions
    POST   /api/v1/contracts/{id}/relationships — Add relationship
    GET    /api/v1/contracts/{id}/graph   — Get relationship graph
```

#### AI Service

```
Purpose:    AI analysis, clause classification, risk scoring, RAG
Language:   Python/FastAPI + gRPC (internal)
Database:   PostgreSQL (ai_analyses, ai_outputs, chunks, citations)
Cache:      Redis (LLM response cache, model routing decisions)
Queues:     Emits: ai.analysis.completed, ai.finding.created
            Consumes: contract.processed (trigger analysis)

Endpoints:
    POST   /api/v1/ai/analyze/{contract_id}     — Trigger full analysis
    GET    /api/v1/ai/analyses/{contract_id}     — Get analyses for contract
    GET    /api/v1/ai/analyses/{id}              — Get analysis detail
    POST   /api/v1/ai/query                      — RAG query against corpus
    POST   /api/v1/ai/redline                    — Generate redline suggestion
    POST   /api/v1/ai/classify                   — Classify clause text
    POST   /api/v1/ai/compare                    — Compare two clauses
    GET    /api/v1/ai/embeddings/{chunk_id}      — Get chunk embedding

Internal gRPC:
    AnalyzeContract(ContractRequest) -> AnalysisResponse
    QueryCorpus(QueryRequest) -> QueryResponse
    GenerateEmbedding(TextRequest) -> EmbeddingResponse
```

#### Workflow Engine

```
Purpose:    Workflow orchestration, approvals, escalations, SLA tracking
Language:   Python/FastAPI
Database:   PostgreSQL (workflows, workflow_steps, approvals, escalations)
Cache:      Redis (active workflow state, SLA deadlines)
Queues:     Emits: workflow.created, workflow.escalated, workflow.sla.breached
            Consumes: ai.finding.created (trigger remediation workflow)

Endpoints:
    POST   /api/v1/workflows                   — Create workflow
    GET    /api/v1/workflows                   — List workflows
    GET    /api/v1/workflows/{id}              — Get workflow detail
    POST   /api/v1/workflows/{id}/approve      — Approve step
    POST   /api/v1/workflows/{id}/reject       — Reject step
    POST   /api/v1/workflows/{id}/escalate     — Escalate workflow
    GET    /api/v1/workflows/{id}/timeline     — Get activity timeline
    GET    /api/v1/sla                         — List SLA metrics
```

#### Procurement Intelligence Service

```
Purpose:    Vendor intelligence, spend analytics, supplier risk
Language:   Python/FastAPI
Database:   PostgreSQL (vendors, vendor_risks, spend_records)
Cache:      Redis (vendor risk scores, spend aggregates)
Queues:     Emits: vendor.risk.updated, vendor.sla.breached

Endpoints:
    GET    /api/v1/vendors                     — List vendors
    GET    /api/v1/vendors/{id}                — Get vendor detail
    POST   /api/v1/vendors                     — Create vendor
    PUT    /api/v1/vendors/{id}                — Update vendor
    GET    /api/v1/vendors/{id}/risks          — Get vendor risk history
    GET    /api/v1/vendors/{id}/spend          — Get spend analytics
    GET    /api/v1/spend/trends                — Spend trend data
    GET    /api/v1/spend/categories            — Category breakdown
```

#### Compliance Service

```
Purpose:    Compliance intelligence, obligation tracking, remediation
Language:   Python/FastAPI
Database:   PostgreSQL (compliance_requirements, compliance_findings, obligations, remediations)
Queues:     Emits: compliance.finding.created, compliance.obligation.due

Endpoints:
    GET    /api/v1/compliance/requirements     — List regulations
    GET    /api/v1/compliance/findings         — List findings
    POST   /api/v1/compliance/findings/{id}/remediate — Start remediation
    GET    /api/v1/obligations                 — List obligations
    PUT    /api/v1/obligations/{id}            — Update obligation status
    GET    /api/v1/compliance/score            — Get compliance score
```

#### Search Service

```
Purpose:    Semantic search, full-text search, saved searches
Language:   Python/FastAPI + gRPC
Database:   PostgreSQL (search_index, saved_searches) + pgvector
Cache:      Redis (popular search results, autocomplete)

Endpoints:
    GET    /api/v1/search?q=...                — Search all entities
    GET    /api/v1/search/contracts?q=...      — Search contracts only
    GET    /api/v1/search/clauses?q=...        — Search clauses only
    POST   /api/v1/search/saved                — Save search
    GET    /api/v1/search/saved                — List saved searches
    DELETE /api/v1/search/saved/{id}           — Delete saved search
```

#### Notification Service

```
Purpose:    User notifications, email, push, in-app alerts
Language:   Python/FastAPI + WebSocket
Database:   PostgreSQL (notifications)
Cache:      Redis (unread counts, real-time delivery)
Queues:     Consumes: all *.notification events

Endpoints:
    GET    /api/v1/notifications               — List notifications
    PUT    /api/v1/notifications/{id}/read     — Mark as read
    PUT    /api/v1/notifications/read-all      — Mark all as read
    GET    /api/v1/notifications/unread-count  — Get unread count
    WS     /api/v1/ws/notifications            — Real-time notification stream
```

#### Analytics Service

```
Purpose:    KPI aggregation, forecasting, report generation
Language:   Python/FastAPI
Database:   PostgreSQL (analytics_snapshots, kpi_definitions, forecasts)
Cache:      Redis (dashboard aggregates, materialized views)

Endpoints:
    GET    /api/v1/analytics/kpis              — List KPI definitions
    GET    /api/v1/analytics/dashboard         — Dashboard aggregates
    GET    /api/v1/analytics/trends/{kpi}      — KPI trend data
    GET    /api/v1/analytics/forecasts/{kpi}   — KPI forecast
    POST   /api/v1/analytics/reports           — Generate report
    GET    /api/v1/analytics/reports/{id}      — Get report
```

---

## 4. AI Execution Runtime

### 4.1 AI Pipeline Architecture

```
                    ┌─────────────────────────────────────┐
                    │         AI EXECUTION RUNTIME         │
                    ├─────────────────────────────────────┤
                    │                                     │
  ┌────────┐   ┌───▼────┐   ┌────────┐   ┌───────────┐   │
  │Trigger │──>│Router  │──>│Execute │──>│Post-      │   │
  │(Event  │   │(Model  │   │(LLM)   │   │Process    │   │
  │ /HTTP) │   │Selector│   │        │   │(Validate, │   │
  └────────┘   └───┬────┘   └────────┘   │Store,     │   │
                    │                     │Index)     │   │
                    │                     └─────┬─────┘   │
                    │                           │         │
                    │                     ┌─────▼─────┐   │
                    │                     │  Emit     │   │
                    │                     │  Event    │   │
                    │                     └───────────┘   │
                    └─────────────────────────────────────┘

Execution Paths:
    Synchronous (HTTP):  Request -> Route -> Execute -> Return
    Async (Queue):       Event -> Route -> Queue -> Worker -> Execute -> Store -> Emit
    Batch (Scheduled):   Schedule -> Queue -> Worker -> Execute -> Store -> Emit
```

### 4.2 Model Router (Cost-Optimized)

```
┌────────────────────────────────────────────────────────────────┐
│  MODEL ROUTER                                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Task Complexity -> Model Selection -> Cost Estimation         │
│                                                                │
│  SIMPLE:    gpt-4o-mini    ($0.15/M input tokens)              │
│  MEDIUM:    gpt-4o         ($2.50/M input tokens)              │
│  COMPLEX:   claude-3-opus  ($15.00/M input tokens)             │
│  CRITICAL:  claude-3-opus  ($15.00/M input tokens)             │
│                                                                │
│  Routing Strategies:                                           │
│    cost_optimized     — Cheapest adequate model                │
│    accuracy_optimized — Most capable model                     │
│    balanced           — Cost vs. accuracy tradeoff             │
│    tenant_config      — Per-tenant routing rules               │
│                                                                │
│  Cost Governance:                                              │
│    Daily budget caps per tenant                                │
│    Model usage quotas per tier                                 │
│    Off-peak scheduling for batch jobs                          │
│    Cache hits for repeated queries                             │
└────────────────────────────────────────────────────────────────┘
```

### 4.3 LLM Execution Patterns

```
┌────────────────────────────────────────────────────────────────┐
│  EXECUTION PATTERNS                                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. DIRECT (sync):    HTTP -> Model -> Response                │
│     Use: Chat, quick analysis, simple classification           │
│     Latency: 500ms - 5s                                        │
│                                                                │
│  2. STREAM (sync):    HTTP -> Model -> SSE Stream              │
│     Use: AI Copilot chat, redline generation                   │
│     Latency: First token < 500ms                               │
│                                                                │
│  3. ASYNC (queue):    Event -> Queue -> Worker -> Model        │
│     Use: Document analysis, batch classification               │
│     Latency: 10s - 5min                                        │
│                                                                │
│  4. BATCH (scheduled): Schedule -> Queue -> Worker -> Model    │
│     Use: Nightly re-analysis, corpus benchmarking              │
│     Latency: 1h - 12h                                          │
│                                                                │
│  5. RAG PIPELINE:     Query -> Embed -> Search -> Context ->   │
│                       Prompt -> Model -> Response + Citations  │
│     Use: Semantic search, Q&A, clause comparison               │
│     Latency: 2s - 10s                                          │
└────────────────────────────────────────────────────────────────┘
```

### 4.4 RAG Pipeline Runtime

```
                    ┌──────────────────────┐
                    │   User Query         │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Query Embedding    │
                    │   (text-embedding-3) │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Vector Search      │
                    │   pgvector (ivfflat) │
                    │   Top-K: 20          │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Context Assembly   │
                    │   Token budget: 8K   │
                    │   Re-rank: MMR       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Prompt Building    │
                    │   System + Context + │
                    │   User Query         │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   LLM Execution      │
                    │   (model per         │
                    │    complexity)       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Response +         │
                    │   Citations          │
                    └──────────────────────┘

RAG Configuration:
    Chunk size:      512 tokens (semantic)
    Overlap:         64 tokens
    Top-K:           20 chunks
    Re-rank:         MMR (lambda=0.7)
    Max context:     8,192 tokens
    Embedding model: text-embedding-3-large (1536d)
    Vector index:    ivfflat (lists=100)
    Similarity:      cosine distance
```

### 4.5 AI Worker Pool

```
┌────────────────────────────────────────────────────────────────┐
│  AI WORKER POOL (Celery)                                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Queues:                                                       │
│    ai_analysis      — Contract analysis, risk scoring          │
│    ai_redline       — Redline generation, clause comparison    │
│    ai_classify      — Clause classification, extraction        │
│    ai_rag           — RAG query processing                    │
│    ai_batch         — Batch/scheduled inference                │
│                                                                │
│  Concurrency: 4-8 workers per queue (configurable)             │
│  Retry:       3 retries, exponential backoff (60s, 120s, 240s) │
│  Timeout:     300s per task                                    │
│  Rate Limit:  Configurable per model per tenant                │
│                                                                │
│  Cost Tracking:                                                │
│    - Token usage per tenant per model                          │
│    - Cost per analysis (stored in ai_analyses.cost_usd)        │
│    - Daily budget enforcement                                  │
│    - Model quota enforcement                                   │
└────────────────────────────────────────────────────────────────┘
```

---

## 5. Async Processing & Queue Architecture

### 5.1 Queue Topology

```
                    ┌──────────────────────────────────────────┐
                    │            REDIS / RABBITMQ              │
                    │              (Message Broker)             │
                    └──────────────────────────────────────────┘
                               │              │
              ┌────────────────┼──────────────┼────────────────┐
              │                │              │                │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌────▼─────┐   ┌─────▼─────┐
        │ Ingestion │   │  AI       │   │ Workflow │   │ Webhook   │
        │ Queue     │   │  Queue    │   │ Queue    │   │ Queue     │
        ├───────────┤   ├───────────┤   ├──────────┤   ├───────────┤
        │ Priority: │   │ Priority: │   │ Priority: │   │ Priority: │
        │ FIFO      │   │ FIFO +    │   │ FIFO +    │   │ FIFO      │
        │           │   │ Urgency   │   │ SLA-based │   │           │
        │ Workers:  │   │ Workers:  │   │ Workers:  │   │ Workers:  │
        │ 3-8       │   │ 3-10      │   │ 2-4       │   │ 2-3       │
        └───────────┘   └───────────┘   └──────────┘   └───────────┘
```

### 5.2 Queue Definitions

| Queue Name | Routing Key | Workers | Priority | Max Retries | TTL | Description |
|-----------|-------------|---------|----------|-------------|-----|-------------|
| `ingestion` | `ingestion.#` | 3-8 | FIFO | 3 | 1h | Document ingestion pipeline |
| `extraction` | `extraction.#` | 3-6 | FIFO | 3 | 30m | Text extraction from documents |
| `ocr` | `ocr.#` | 2-4 | FIFO | 3 | 30m | OCR processing |
| `ai_analysis` | `ai.analysis.#` | 4-8 | Urgency | 3 | 10m | AI contract analysis |
| `ai_redline` | `ai.redline.#` | 2-4 | Urgency | 2 | 5m | Redline generation |
| `ai_classify` | `ai.classify.#` | 3-6 | FIFO | 3 | 10m | Clause classification |
| `ai_rag` | `ai.rag.#` | 2-4 | FIFO | 2 | 30s | RAG query processing |
| `ai_batch` | `ai.batch.#` | 1-3 | FIFO | 3 | 1h | Batch inference |
| `workflow` | `workflow.#` | 2-4 | SLA-based | 3 | 5m | Workflow orchestration |
| `notification` | `notification.#` | 2-3 | FIFO | 3 | 1m | Notification delivery |
| `webhook` | `webhook.#` | 2-3 | FIFO | 5 | 5m | Webhook dispatch |
| `analytics` | `analytics.#` | 1-2 | FIFO | 2 | 1h | Analytics aggregation |

### 5.3 Job Lifecycle

```
                    ┌──────────┐
                    │  PENDING │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
              ┌────>│ QUEUED   │
              │     └────┬─────┘
              │          │
              │     ┌────▼─────┐
              │     │PROCESSING│
              │     └────┬─────┘
              │          │
              │    ┌─────┴──────┐
              │    │            │
              │    ▼            ▼
              │ ┌────────┐ ┌────────┐
              │ │COMPLETED│ │ FAILED │
              │ └────────┘ └───┬────┘
              │                │
              │          ┌─────▼─────┐
              └──────────│ RETRY     │
                         │ (3 max)   │
                         └───────────┘
```

### 5.4 Queue Configuration

```python
# Celery Configuration
celery_app.conf.update(
    # Task Settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,              # Re-deliver on worker crash
    worker_prefetch_multiplier=1,     # One task per worker at a time
    task_reject_on_worker_lost=True,  # Reject unacknowledged tasks
    
    # Queue Definitions
    task_queues=[
        KombuQueue("ingestion", routing_key="ingestion.#"),
        KombuQueue("extraction", routing_key="extraction.#"),
        KombuQueue("ocr", routing_key="ocr.#"),
        KombuQueue("ai_analysis", routing_key="ai.analysis.#"),
        KombuQueue("ai_redline", routing_key="ai.redline.#"),
        KombuQueue("ai_classify", routing_key="ai.classify.#"),
        KombuQueue("ai_rag", routing_key="ai.rag.#"),
        KombuQueue("ai_batch", routing_key="ai.batch.#"),
        KombuQueue("workflow", routing_key="workflow.#"),
        KombuQueue("notification", routing_key="notification.#"),
        KombuQueue("webhook", routing_key="webhook.#"),
        KombuQueue("analytics", routing_key="analytics.#"),
    ],
    
    # Routing
    task_routes={
        "ingestion.tasks.*": {"queue": "ingestion"},
        "ai_service.tasks.*": {"queue": "ai_analysis"},
        "workflow.tasks.*": {"queue": "workflow"},
        "webhook.tasks.*": {"queue": "webhook"},
    },
    
    # Retry
    task_default_retry_delay=60,      # 60s initial retry delay
    task_max_retries=3,
    task_retry_backoff=True,
    task_retry_backoff_max=300,       # Max 5min backoff
    task_retry_jitter=True,           # Add jitter to prevent thundering herd
    
    # Visibility
    task_soft_time_limit=240,         # 4min soft limit
    task_time_limit=300,              # 5min hard limit
    result_expires=86400,             # Results expire after 24h
)
```

---

## 6. Worker Fleet

### 6.1 Worker Types

| Worker Type | Runtime | Queues | Concurrency | Scale Range | Resource Profile |
|------------|---------|--------|-------------|-------------|-----------------|
| **Ingestion Worker** | Celery | ingestion, extraction, ocr | 4-8 | 3-20 | CPU: 4-8 cores, RAM: 8-16GB |
| **AI Worker** | Celery | ai_analysis, ai_redline, ai_classify, ai_rag | 4-8 | 3-30 | CPU: 4-8 cores, RAM: 16-32GB, GPU: optional |
| **AI Batch Worker** | Celery | ai_batch | 2-4 | 1-10 | CPU: 8-16 cores, RAM: 32-64GB, GPU: preferred |
| **Workflow Worker** | Celery | workflow | 2-4 | 2-8 | CPU: 2-4 cores, RAM: 4-8GB |
| **Notification Worker** | Celery | notification | 2-4 | 2-6 | CPU: 2-4 cores, RAM: 4-8GB |
| **Webhook Worker** | Celery | webhook | 2-4 | 2-8 | CPU: 2-4 cores, RAM: 4-8GB |
| **Analytics Worker** | Celery | analytics | 1-2 | 1-4 | CPU: 4-8 cores, RAM: 8-16GB |

### 6.2 Worker Auto-Scaling

```
┌────────────────────────────────────────────────────────────────┐
│  AUTO-SCALING RULES (KEDA / AWS HPA)                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Ingestion Workers:                                            │
│    Scale on:  Queue depth > 50                                 │
│    Scale to:  max(3, min(20, queue_depth / 25))               │
│    Cooldown:  120s                                             │
│                                                                │
│  AI Workers:                                                   │
│    Scale on:  Queue depth > 20                                 │
│    Scale to:  max(3, min(30, queue_depth / 10))               │
│    Cooldown:  180s (avoid thrashing on burst)                  │
│                                                                │
│  Webhook Workers:                                              │
│    Scale on:  Queue depth > 100                                │
│    Scale to:  max(2, min(8, queue_depth / 50))                │
│    Cooldown:  60s                                              │
│                                                                │
│  Scale Down Rules:                                             │
│    Idle for:  300s                                             │
│    Min pods:  Configured per service                           │
│    Max pods:  Configured per service                           │
└────────────────────────────────────────────────────────────────┘
```

### 6.3 Worker Health & Reliability

```
Worker Health Checks:
    - Liveness:  HTTP /health (process alive)
    - Readiness: Queue connection OK, DB pool OK
    - Startup:   Dependencies initialized

Worker Reliability:
    - acks_late=True: Re-deliver on crash (at-least-once)
    - Prefetch=1:     One task at a time per worker
    - Retry:          3 attempts with exponential backoff
    - Dead Letter:    Failed tasks sent to DLQ for analysis
    - Rate Limiting:  Per-tenant rate limits enforced in worker

Worker Graceful Shutdown:
    1. SIGTERM -> Stop accepting new tasks
    2. Wait for in-flight tasks (max 30s)
    3. SIGKILL -> Force kill (tasks re-delivered)
```

---

## 7. Orchestration Layer

### 7.1 Orchestration Architecture

```
                    ┌──────────────────────────────────────┐
                    │        ORCHESTRATION LAYER           │
                    ├──────────────────────────────────────┤
                    │                                      │
  ┌────────┐   ┌───▼────┐   ┌────────┐   ┌───────────┐   │
  │Event   │──>│Pipeline│──>│Step    │──>│Compensate │   │
  │Trigger │   │Orch.   │   │Executor│   │(on fail)  │   │
  └────────┘   └───┬────┘   └────────┘   └───────────┘   │
                    │                                      │
            ┌───────▼───────┐                             │
            │  State Store  │                             │
            │  (PostgreSQL) │                             │
            └───────────────┘                             │
                    │                                      │
            ┌───────▼───────┐                             │
            │  Event Emitter│                             │
            └───────────────┘                             │
                    │                                      │
                    ▼                                      │
            ┌────────────────┐                             │
            │ Downstream     │                             │
            │ Consumers      │                             │
            └────────────────┘                             │
                    │                                      │
                    └──────────────────────────────────────┘
```

### 7.2 Pipeline Orchestrations

#### Document Ingestion Pipeline

```
Event: contract.uploaded

Step 1: Validate File        — Check format, size, checksum
Step 2: Extract Text         — PyMuPDF / Tika / OCR (Textract)
Step 3: Extract Metadata     — Title, parties, dates, values
Step 4: Classify Contract    — Contract type, risk category
Step 5: Segment Clauses      — Clause boundary detection
Step 6: Chunk Text           — Semantic chunking
Step 7: Generate Embeddings  — vector(1536) for each chunk
Step 8: Index for Search     — Full-text + vector index
Step 9: Trigger AI Analysis  — Emit contract.processed
Step 10: Emit Completion     — Emit ingestion.completed

Failure Compensation:
    Step 2 fail -> Try OCR fallback (Textract)
    Step 3 fail -> Continue with partial metadata
    Step 5 fail -> Fall back to fixed-size chunking
    Step 7 fail -> Retry embedding generation (3x)
    Any fail   -> Set contract status = 'error', emit ingestion.failed
```

#### AI Analysis Pipeline

```
Event: contract.processed

Step 1: Risk Analysis        — Full contract risk scoring
Step 2: Clause Classification — Classify each clause type
Step 3: Risk Findings        — Detect high-risk clauses
Step 4: Obligation Extraction — Extract obligations from clauses
Step 5: Benchmark Comparison — Compare clauses to market corpus
Step 6: Redline Suggestions  — Generate recommended changes
Step 7: Store Results        — Write to ai_analyses, ai_outputs
Step 8: Emit Completion      — Emit ai.analysis.completed

Parallel Execution:
    Steps 1-3: Sequential (risk depends on classification)
    Steps 4-6: Parallel (independent)
    Step 7:    After all parallel steps complete
```

#### Workflow Orchestration

```
Event: workflow.created

Step 1: Assign to User       — Auto-assign based on round-robin/load
Step 2: Notify Assignee      — Push notification + email
Step 3: SLA Timer Start      — Track deadline
Step 4: Await Action         — Approve / Reject / Escalate
    ├── Approve:  -> Step 5a: Complete step, advance to next
    ├── Reject:   -> Step 5b: Log rejection, notify creator
    └── Escalate: -> Step 5c: Escalate to level N, notify senior
Step 5: Check Completion     — All steps done?
    ├── Yes: -> Emit workflow.completed
    └── No:  -> Return to Step 1 for next step

SLA Monitoring:
    Every 5min: Check SLA deadlines
    At 80%:     Send "at risk" notification
    At 100%:    Send "breached" alert, trigger escalation
```

### 7.3 Saga Pattern for Distributed Transactions

```
┌────────────────────────────────────────────────────────────────┐
│  SAGA: Contract Upload + Analysis + Notification               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Step 1: Create Contract Record (Local TX)                     │
│    Compensation: DELETE contract record                        │
│                                                                │
│  Step 2: Upload File to S3 (Side Effect)                       │
│    Compensation: DELETE from S3                                │
│                                                                │
│  Step 3: Enqueue Ingestion Job (Local TX)                      │
│    Compensation: CANCEL ingestion job                          │
│                                                                │
│  Step 4: Wait for Ingestion Complete (Async)                   │
│    Compensation: Set contract status = 'error'                 │
│                                                                │
│  Step 5: Trigger AI Analysis (Async)                           │
│    Compensation: Log failure, no rollback needed               │
│                                                                │
│  Step 6: Send Notification (Async)                             │
│    Compensation: Log failure, no rollback needed               │
│                                                                │
│  Each step emits compensating action on failure.               │
│  Orchestrator tracks state in PostgreSQL.                      │
└────────────────────────────────────────────────────────────────┘
```

---

## 8. Integration Runtime

### 8.1 Integration Architecture

```
                    ┌──────────────────────────────────────┐
                    │       INTEGRATION RUNTIME            │
                    ├──────────────────────────────────────┤
                    │                                      │
  ┌────────────┐   ┌▼────────────┐   ┌──────────────────┐  │
  │ External   │──>│ Adapter     │──>│ Protocol         │  │
  │ System     │   │ Layer       │   │ Translation      │  │
  └────────────┘   └─────────────┘   └────────┬─────────┘  │
                                              │              │
  Supported Protocols:                        │              │
    - REST APIs                               │              │
    - GraphQL                                 │              │
    - Webhooks (inbound/outbound)             │              │
    - gRPC                                    │              │
    - Message Queues (RabbitMQ, SQS, Kafka)   │              │
    - SFTP / FTP                              │              │
    - Database Connectors                     │              │
    - LDAP / SAML / OIDC                      │              │
                                              │              │
  ┌───────────────────────────────────────────▼──────────┐   │
  │  Integration Patterns:                               │   │
  │  - Request/Reply (sync)                              │   │
  │  - Fire-and-Forget (async)                           │   │
  │  - Publish/Subscribe (event)                         │   │
  │  - Batch Sync (scheduled)                            │   │
  │  - Streaming (real-time)                             │   │
  └──────────────────────────────────────────────────────┘   │
                    │                                         │
                    └─────────────────────────────────────────┘
```

### 8.2 Webhook Architecture

```
                    ┌──────────────────────────────────────┐
                    │       WEBHOOK ENGINE                 │
                    ├──────────────────────────────────────┤
                    │                                      │
  Event Bus ───────>│  Webhook Matcher                     │
                    │  (matches event_type to registered   │
                    │   webhooks by tenant)                │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │  Webhook Dispatcher (Celery Worker)  │
                    │  - HTTP POST to registered URL      │
                    │  - Includes HMAC signature          │
                    │  - Retry: 5 attempts                │
                    │  - Backoff: 30s, 60s, 120s, 240s, 480s│
                    │  - Dead letter after 5 failures     │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │  Webhook Events                      │
                    ├──────────────────────────────────────┤
                    │  ingestion.completed                 │
                    │  ingestion.failed                    │
                    │  contract.analyzed                   │
                    │  workflow.completed                  │
                    │  workflow.escalated                  │
                    │  ai.finding.created                  │
                    │  compliance.finding.created          │
                    │  vendor.risk.updated                 │
                    │  obligation.due                      │
                    └──────────────────────────────────────┘
```

### 8.3 External Integrations

| Integration | Protocol | Sync/Async | Frequency | Purpose |
|------------|----------|------------|-----------|---------|
| Auth0 | REST/OIDC | Sync | On login | Authentication |
| OpenAI | REST | Sync+Async | Per analysis | LLM inference |
| Anthropic | REST | Sync+Async | Per analysis | LLM inference |
| AWS Textract | REST | Async | Per document | OCR processing |
| AWS S3 | REST | Sync | Per upload | Document storage |
| SendGrid/SES | REST | Async | Per notification | Email delivery |
| Slack | Webhook | Async | Per alert | Team notifications |
| Salesforce | REST | Async | On sync | CRM integration |
| SAP Ariba | REST | Async | On sync | Procurement integration |
| Workday | REST | Async | On sync | HR integration |
| DocuSign | REST | Async | Per contract | E-signature |
| SharePoint | REST | Async | On sync | Document sync |

---

## 9. Event Bus & Webhook Architecture

### 9.1 Event Bus Topology

```
                    ┌──────────────────────────────────────┐
                    │         EVENT BUS                    │
                    │    (Redis Pub/Sub + NSQ/Kafka)       │
                    ├──────────────────────────────────────┤
                    │                                      │
  ┌────────────┐   │  ┌────────────┐  ┌──────────────┐   │
  │ Producer   │──>│  │  Event     │──>│  Consumer    │   │
  │ (Service)  │   │  │  Channel   │  │  (Service)   │   │
  └────────────┘   │  └────────────┘  └──────────────┘   │
                   │                                      │
  Channels:         │  ┌──────────────────────────────┐   │
  contract.*        │  │  Event Envelope              │   │
  ingestion.*       │  │  {                           │   │
  ai.*              │  │    event_id,                 │   │
  workflow.*        │  │    event_type,               │   │
  vendor.*          │  │    source,                   │   │
  compliance.*      │  │    tenant_id,                │   │
  notification.*    │  │    timestamp,                │   │
  audit.*           │  │    correlation_id,           │   │
                    │  │    data: {...}               │   │
                    │  │  }                           │   │
                    │  └──────────────────────────────┘   │
                    └──────────────────────────────────────┘
```

### 9.2 Event Types & Consumers

| Event Type | Producer | Consumers | Delivery | Retention |
|-----------|----------|-----------|----------|-----------|
| `contract.uploaded` | API Gateway | Ingestion Worker | At-least-once | 7 days |
| `contract.processed` | Ingestion Worker | AI Service, Search Service | At-least-once | 7 days |
| `contract.analyzed` | AI Service | Workflow Engine, Notification | At-least-once | 7 days |
| `ingestion.completed` | Ingestion Worker | Webhook Dispatcher | At-least-once | 7 days |
| `ingestion.failed` | Ingestion Worker | Notification, Webhook | At-least-once | 7 days |
| `ai.analysis.completed` | AI Service | Analytics Service, Notification | At-least-once | 7 days |
| `ai.finding.created` | AI Service | Workflow Engine, Notification | At-least-once | 7 days |
| `workflow.created` | Workflow Engine | Notification | At-least-once | 7 days |
| `workflow.escalated` | Workflow Engine | Notification, Webhook | At-least-once | 30 days |
| `workflow.sla.breached` | Workflow Engine | Notification, Escalation | At-least-once | 30 days |
| `vendor.risk.updated` | Procurement Service | Notification, Webhook | At-least-once | 7 days |
| `compliance.finding.created` | Compliance Service | Workflow Engine, Notification | At-least-once | 30 days |
| `notification.sent` | Notification Service | Audit Logger | Best-effort | 90 days |

### 9.3 Event Delivery Guarantees

```
┌────────────────────────────────────────────────────────────────┐
│  EVENT DELIVERY STRATEGY                                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Critical Events (At-Least-Once):                              │
│    - contract.*, ingestion.*, ai.analysis.*, workflow.*        │
│    - Redis list (persistent queue) + consumer ACK              │
│    - Retry: 3 attempts, exponential backoff                    │
│    - DLQ: Failed events stored for manual replay               │
│                                                                │
│  Operational Events (Best-Effort):                             │
│    - audit.*, analytics.*, notification.*                      │
│    - Redis Pub/Sub (fire-and-forget)                           │
│    - No retry, no DLQ                                          │
│    - Acceptable to lose under load                             │
│                                                                │
│  Compliance Events (Exactly-Once semantics):                   │
│    - compliance.*, audit.* (critical audit trail)              │
│    - Database-logged before event emission                     │
│    - Idempotent consumers (event_id dedup)                     │
│    - Replayable from audit_logs table                          │
└────────────────────────────────────────────────────────────────┘
```

---

## 10. Data Layer Topology

### 10.1 Database Topology

```
                    ┌──────────────────────────────────────────┐
                    │         DATA LAYER                       │
                    ├──────────────────────────────────────────┤
                    │                                          │
  ┌──────────────┐  │  ┌──────────────┐  ┌──────────────────┐  │
  │  PostgreSQL  │  │  │  PostgreSQL  │  │  PostgreSQL      │  │
  │  Primary     │<──│──│  Replica 1  │  │  Replica 2       │  │
  │  (Read-Write)│  │  │  (Read-Only) │  │  (Read-Only)     │  │
  │              │  │  │              │  │                  │  │
  │  Tables:     │  │  │  Queries:    │  │  Queries:        │  │
  │  contracts   │  │  │  search      │  │  analytics       │  │
  │  chunks      │  │  │  listings    │  │  reporting       │  │
  │  clauses     │  │  │  vector      │  │  exports         │  │
  │  workflows   │  │  │  lookups     │  │  batch jobs      │  │
  │  audit_logs  │  │  │              │  │                  │  │
  └──────────────┘  │  └──────────────┘  └──────────────────┘  │
                    │                                          │
  ┌──────────────┐  │  ┌──────────────┐  ┌──────────────────┐  │
  │  Redis       │  │  │  Redis       │  │  S3-Compatible   │  │
  │  Primary     │  │  │  Replica     │  │  Object Store    │  │
  │              │  │  │              │  │                  │  │
  │  Cache:      │  │  │  Cache:      │  │  Buckets:        │  │
  │  session     │  │  │  read-through│  │  documents/      │  │
  │  rate limit  │  │  │  hot data    │  │  exports/        │  │
  │  queue       │  │  │              │  │  backups/        │  │
  └──────────────┘  │  └──────────────┘  │  archives/       │  │
                    │                    └──────────────────┘  │
                    └──────────────────────────────────────────┘
```

### 10.2 Connection Pool Configuration

```python
# PostgreSQL Connection Pool
engine = create_async_engine(
    database_url,
    pool_size=20,           # Connections per service instance
    max_overflow=10,        # Burst connections
    pool_pre_ping=True,     # Verify connection before use
    pool_recycle=3600,      # Recycle connections every hour
    pool_timeout=30,        # Wait 30s for connection
    echo=False,
)

# Redis Connection Pool
redis_client = aioredis.from_url(
    redis_url,
    max_connections=50,     # Max connections per service
    socket_connect_timeout=5,
    socket_keepalive=True,
    retry_on_timeout=True,
    health_check_interval=30,
)
```

### 10.3 Data Flow Patterns

```
┌────────────────────────────────────────────────────────────────┐
│  DATA FLOW: Upload -> Ingestion -> Analysis -> Storage         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. Client uploads PDF to API Gateway                          │
│  2. Gateway streams to S3 (multipart upload)                   │
│  3. Gateway creates contract record in PostgreSQL              │
│  4. Gateway emits contract.uploaded event                      │
│  5. Ingestion Worker picks up event from Redis queue           │
│  6. Worker downloads from S3, extracts text                    │
│  7. Worker writes extracted_pages, clauses, chunks to PG       │
│  8. Worker generates embeddings, writes to chunks.embedding    │
│  9. Worker updates contract status = 'ready'                   │
│  10. Worker emits ingestion.completed event                    │
│  11. AI Worker picks up event, triggers analysis               │
│  12. AI Worker writes findings to risk_findings table          │
│  13. AI Worker emits ai.analysis.completed event               │
│  14. Notification Worker sends "analysis complete" alert       │
│  15. Webhook Worker dispatches to external systems             │
└────────────────────────────────────────────────────────────────┘
```

---

## 11. Infrastructure Topology

### 11.1 Deployment Architecture (AWS)

```
                    ┌──────────────────────────────────────────┐
                    │         AWS CLOUD                        │
                    ├──────────────────────────────────────────┤
                    │                                          │
  ┌────────────────┐│  ┌────────────────────┐                  │
  │ Route 53       ││  │ CloudFront (CDN)   │                  │
  │ DNS            ││  │ Static assets,     │                  │
  └───────┬────────┘│  │ cached responses   │                  │
          │         │  └─────────┬──────────┘                  │
          │         │            │                             │
  ┌───────▼────────┐│  ┌────────▼─────────┐                  │
  │  WAF           ││  │  ALB (HTTPS)     │                  │
  │  Web ACL       ││  │  TLS termination │                  │
  └───────┬────────┘│  └────────┬─────────┘                  │
          │         │            │                             │
          └─────────┼────────────┼─────────────────────────────┘
                    │            │
          ┌─────────┴────────────┴─────────────────────────┐
          │            ECS / EKS (Fargate)                 │
          │                                                │
          │  ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
          │  │ Frontend │ │ API      │ │ AI Service   │   │
          │  │ (Next.js)│ │ Gateway  │ │ (FastAPI)    │   │
          │  │ 2-4 pods │ │ 3-6 pods │ │ 3-8 pods     │   │
          │  └──────────┘ └──────────┘ └──────────────┘   │
          │                                                │
          │  ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
          │  │ Contract │ │ Workflow │ │ Procurement  │   │
          │  │ Service  │ │ Engine   │ │ Intel        │   │
          │  │ 3-6 pods │ │ 2-4 pods │ │ 2-3 pods     │   │
          │  └──────────┘ └──────────┘ └──────────────┘   │
          │                                                │
          │  ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
          │  │ Celery   │ │ Celery  │ │ Celery       │   │
          │  │Ingestion │ │ AI      │ │ Webhook      │   │
          │  │ 3-8 pods │ │ 3-10    │ │ 2-3 pods     │   │
          │  └──────────┘ └──────────┘ └──────────────┘   │
          └────────────────────────────────────────────────┘
                    │
          ┌─────────┴─────────────────────────────────────────┐
          │              DATA LAYER                           │
          │                                                    │
          │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
          │  │ RDS      │  │ Elasti-  │  │ S3             │  │
          │  │PostgreSQL│  │ cache   │  │ Documents      │  │
          │  │ Multi-AZ │  │ Redis   │  │ + Backups      │  │
          │  │ pgvector │  │ Cluster │  │                │  │
          │  └──────────┘  └──────────┘  └────────────────┘  │
          └────────────────────────────────────────────────────┘
```

### 11.2 Container Configuration

```dockerfile
# Base image for all Python services
FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"
```

### 11.3 Docker Compose (Development)

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: contract_risk_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev_user -d contract_risk_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://dev_user:dev_password@postgres:5432/contract_risk_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
      ENVIRONMENT: development
      LOG_LEVEL: DEBUG
    volumes:
      - ./api:/app
      - uploads_data:/app/uploads
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }

  celery_worker:
    build: ./api
    environment:
      DATABASE_URL: postgresql+asyncpg://dev_user:dev_password@postgres:5432/contract_risk_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
      ENVIRONMENT: development
    volumes:
      - ./api:/app
      - uploads_data:/app/uploads
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: celery -A ingestion.tasks worker --loglevel=info --concurrency=4

  celery_beat:
    build: ./api
    environment:
      DATABASE_URL: postgresql+asyncpg://dev_user:dev_password@postgres:5432/contract_risk_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    volumes:
      - ./api:/app
    depends_on:
      redis: { condition: service_healthy }
    command: celery -A ingestion.tasks beat --loglevel=info

  flower:
    image: mher/flower:2.0
    ports:
      - "5555:5555"
    environment:
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      redis: { condition: service_healthy }

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - api
    command: npm run dev

volumes:
  postgres_data:
  redis_data:
  uploads_data:
```

---

## 12. Observability Stack

### 12.1 Observability Architecture

```
                    ┌──────────────────────────────────────────┐
                    │         OBSERVABILITY STACK              │
                    ├──────────────────────────────────────────┤
                    │                                          │
  ┌────────────┐    │  ┌────────────┐  ┌──────────────────┐   │
  │ Application│───>│  │ OpenTeleme-│──>│  AWS CloudWatch  │   │
  │ (Python)   │    │  │ try SDK   │  │  - Metrics        │   │
  │            │    │  │            │  │  - Logs           │   │
  │ Traces:    │    │  │ Traces:    │  │  - Alarms         │   │
  │ OTel SDK   │    │  │ OTLP       │  └──────────────────┘   │
  │ Metrics:   │    │  │ Metrics:   │                          │
  │ Prometheus │    │  │ OTLP       │  ┌──────────────────┐   │
  │ Logs:      │    │  │ Logs:      │──>│  Datadog /       │   │
  │ structlog  │    │  │ OTLP       │  │  Grafana Cloud   │   │
  └────────────┘    │  └────────────┘  │  - Dashboards     │   │
                    │                  │  - Alerts         │   │
  ┌────────────┐    │  ┌────────────┐  │  - SLO tracking  │   │
  │ Infra      │───>│  │ Container  │──>└──────────────────┘   │
  │ Metrics    │    │  │ Insights   │                          │
  │ (ECS/EKS)  │    │  │ (CW Agent) │  ┌──────────────────┐   │
  └────────────┘    │  └────────────┘  │  PagerDuty /      │   │
                    │                  │  OpsGenie         │   │
  ┌────────────┐    │  ┌────────────┐  │  - On-call        │   │
  │ LLM        │───>│  │ LangFuse   │──>│  - Escalation     │   │
  │ Observabil.│    │  │ / Helicone │  └──────────────────┘   │
  │ (cost,     │    │  │            │                          │
  │  latency,  │    │  │ LLM traces │  ┌──────────────────┐   │
  │  quality)  │    │  │ Cost       │  │  ELK / Grafana   │   │
  └────────────┘    │  │ Analytics  │──>│  Loki            │   │
                    │  └────────────┘  │  - Log aggregation│   │
                    │                  └──────────────────┘   │
                    └──────────────────────────────────────────┘
```

### 12.2 Metrics Collection

```python
# OpenTelemetry Metrics
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

# Key Metrics to Collect:
METRICS = {
    # API Metrics
    "api.request.duration": "Histogram",      # Request latency
    "api.request.count": "Counter",           # Request count
    "api.request.errors": "Counter",          # Error count
    "api.request.size": "Histogram",          # Request payload size
    
    # Business Metrics
    "contracts.uploaded": "Counter",          # Upload rate
    "contracts.processed": "Counter",         # Processing rate
    "contracts.analyzed": "Counter",          # Analysis rate
    "ai.analyses.completed": "Counter",       # AI completion rate
    "ai.analyses.failed": "Counter",          # AI failure rate
    
    # Queue Metrics
    "queue.depth": "Gauge",                   # Queue depth per queue
    "queue.latency": "Histogram",             # Time in queue
    "queue.processed": "Counter",             # Tasks processed
    
    # AI Metrics
    "ai.llm.latency": "Histogram",            # LLM response time
    "ai.llm.tokens": "Histogram",             # Token usage
    "ai.llm.cost": "Counter",                 # Cost per model
    "ai.vector.search.latency": "Histogram",  # Vector search time
    
    # Database Metrics
    "db.connection.pool.size": "Gauge",       # Active connections
    "db.query.latency": "Histogram",          # Query execution time
    "db.transactions": "Counter",             # Transaction rate
    
    # Business KPIs
    "kpi.contracts.total": "Gauge",           # Total contracts
    "kpi.risk.high": "Gauge",                 # High-risk contracts
    "kpi.compliance.score": "Gauge",          # Compliance score
    "kpi.sla.breaches": "Counter",            # SLA breach count
}
```

### 12.3 Structured Logging

```python
# structlog Configuration
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Log Format (JSON):
{
    "timestamp": "2026-05-15T10:30:00.123Z",
    "level": "INFO",
    "logger": "contract_service",
    "event": "contract.uploaded",
    "request_id": "req_abc123",
    "tenant_id": "tenant_uuid",
    "user_id": "user_123",
    "contract_id": "contract_uuid",
    "file_size": 2450000,
    "duration_ms": 234,
    "correlation_id": "corr_xyz789"
}
```

### 12.4 Distributed Tracing

```
┌────────────────────────────────────────────────────────────────┐
│  DISTRIBUTED TRACE: Contract Upload                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Span 1: POST /api/v1/contracts (API Gateway)                 │
│  ├── Span 1.1: AuthN/AuthZ (5ms)                             │
│  ├── Span 1.2: S3 Upload (120ms)                              │
│  ├── Span 1.3: DB Insert (15ms)                               │
│  └── Span 1.4: Event Emit (3ms)                               │
│                                                                │
│  Span 2: process_document (Ingestion Worker)                  │
│  ├── Span 2.1: S3 Download (80ms)                             │
│  ├── Span 2.2: Text Extraction (450ms)                        │
│  ├── Span 2.3: Clause Segmentation (120ms)                    │
│  ├── Span 2.4: Chunking (50ms)                                │
│  ├── Span 2.5: Embedding Generation (200ms)                   │
│  └── Span 2.6: DB Write (100ms)                               │
│                                                                │
│  Span 3: analyze_contract (AI Worker)                         │
│  ├── Span 3.1: Load Contract (10ms)                           │
│  ├── Span 3.2: LLM Risk Analysis (3,200ms)                    │
│  ├── Span 3.3: Clause Classification (1,800ms)                │
│  ├── Span 3.4: Obligation Extraction (2,100ms)                │
│  └── Span 3.5: Store Results (150ms)                          │
│                                                                │
│  Total Trace Duration: ~8.5s                                  │
│  Trace ID: trc_abc123def456                                   │
└────────────────────────────────────────────────────────────────┘
```

### 12.5 Alerting Rules

```
┌────────────────────────────────────────────────────────────────┐
│  ALERTING RULES                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Critical (PagerDuty, immediate):                              │
│    - API error rate > 5% (5 min window)                       │
│    - Queue depth > 1000 (any queue, 2 min)                    │
│    - Database connections > 80% of pool                       │
│    - LLM API failure rate > 10%                               │
│    - Ingestion pipeline failure rate > 5%                     │
│                                                                │
│  High (Slack, 5 min):                                         │
│    - API p99 latency > 5s                                     │
│    - AI analysis latency > 30s                                │
│    - Worker queue backlog > 500                                │
│    - Redis memory > 80%                                       │
│    - S3 upload errors > 2%                                    │
│                                                                │
│  Medium (Email, 15 min):                                      │
│    - API p95 latency > 2s                                     │
│    - Daily active users drop > 20%                            │
│    - Contract upload rate drop > 50%                          │
│    - Webhook delivery failure > 5%                            │
│                                                                │
│  Info (Dashboard):                                            │
│    - Any service restarted                                    │
│    - New tenant onboarded                                     │
│    - Daily cost report generated                              │
└────────────────────────────────────────────────────────────────┘
```

---

## 13. Scaling Strategy

### 13.1 Horizontal Scaling

```
┌────────────────────────────────────────────────────────────────┐
│  HORIZONTAL SCALING STRATEGY                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Stateless Services (HTTP):                                    │
│    - API Gateway, Contract Service, AI Service                 │
│    - Scale via ALB target group (add/remove instances)         │
│    - No session affinity required                              │
│    - All state in PostgreSQL/Redis                             │
│    - Scale trigger: CPU > 70% or req/sec > threshold          │
│                                                                │
│  Stateful Workers (Celery):                                    │
│    - Scale via queue depth (KEDA ScaledObject)                 │
│    - Each worker is stateless (reads from queue)               │
│    - Scale trigger: queue_depth > target                       │
│    - Cooldown: 120s to prevent thrashing                       │
│                                                                │
│  Database:                                                     │
│    - Read replicas for analytics queries                       │
│    - Connection pooling at service level                       │
│    - Partitioning for large tables (contracts, audit_logs)     │
│    - pgvector index for semantic search                        │
│                                                                │
│  Cache (Redis):                                                │
│    - Redis Cluster for horizontal scaling                      │
│    - Read replicas for cache-heavy workloads                   │
│    - Key prefix per service namespace                          │
└────────────────────────────────────────────────────────────────┘
```

### 13.2 Scaling Dimensions

| Dimension | Metric | Scale Action | Limit |
|-----------|--------|-------------|-------|
| **API Throughput** | Requests/sec per service | Add/remove service pods | 10k req/s per service |
| **Ingestion Throughput** | Documents/min | Add/remove ingestion workers | 100 docs/min per worker |
| **AI Throughput** | Analyses/min | Add/remove AI workers | 20 analyses/min per worker |
| **Search Throughput** | Queries/sec | Add/remove search pods, read replicas | 500 qps per replica |
| **Storage** | Total documents | Add partitions, archive cold data | 10M documents per cluster |
| **Vector Search** | Index size | Re-index with larger lists, scale replicas | 100M vectors per index |
| **Notification** | Messages/min | Add/remove notification workers | 10k/min per worker |
| **Webhook** | Webhooks/min | Add/remove webhook workers | 5k/min per worker |

### 13.3 Resource Sizing

```
┌────────────────────────────────────────────────────────────────┐
│  RESOURCE SIZING GUIDE                                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Development / Staging:                                       │
│    - Frontend:    1 pod (0.5 CPU, 1GB RAM)                    │
│    - API:         1 pod (1 CPU, 2GB RAM)                      │
│    - Workers:     1 pod each (1 CPU, 2GB RAM)                 │
│    - PostgreSQL:  db.t3.medium (2 CPU, 4GB RAM)               │
│    - Redis:       cache.t3.micro (0.5 CPU, 1GB RAM)           │
│                                                                │
│  Production (Small):                                          │
│    - Frontend:    2 pods (1 CPU, 2GB RAM)                     │
│    - API:         3 pods (2 CPU, 4GB RAM)                     │
│    - AI Workers:  3 pods (4 CPU, 8GB RAM)                     │
│    - Ingestion:   3 pods (4 CPU, 8GB RAM)                     │
│    - PostgreSQL:  db.r6g.large (2 CPU, 16GB RAM) + replica    │
│    - Redis:       cache.r6g.large (2 CPU, 13GB RAM)           │
│                                                                │
│  Production (Medium):                                         │
│    - Frontend:    4 pods (2 CPU, 4GB RAM)                     │
│    - API:         6 pods (4 CPU, 8GB RAM)                     │
│    - AI Workers:  8 pods (8 CPU, 16GB RAM)                    │
│    - Ingestion:   6 pods (8 CPU, 16GB RAM)                    │
│    - PostgreSQL:  db.r6g.xlarge (4 CPU, 32GB RAM) + 2 replicas│
│    - Redis:       cache.r6g.xlarge (4 CPU, 26GB RAM) cluster  │
│                                                                │
│  Production (Large / Enterprise):                             │
│    - Frontend:    8+ pods (4 CPU, 8GB RAM)                    │
│    - API:         12+ pods (8 CPU, 16GB RAM)                  │
│    - AI Workers:  20+ pods (8 CPU, 32GB RAM, GPU optional)   │
│    - Ingestion:   12+ pods (8 CPU, 16GB RAM)                  │
│    - PostgreSQL:  db.r6g.2xlarge (8 CPU, 64GB RAM) + 4 replicas│
│    - Redis:       cache.r6g.2xlarge (8 CPU, 52GB RAM) cluster │
└────────────────────────────────────────────────────────────────┘
```

---

## 14. Deployment Topology

### 14.1 Environment Strategy

```
┌────────────────────────────────────────────────────────────────┐
│  DEPLOYMENT ENVIRONMENTS                                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Development:                                                  │
│    - Purpose:    Local development, unit tests                 │
│    - Infra:      Docker Compose (single host)                  │
│    - Data:       Synthetic seed data                           │
│    - Deploy:     docker compose up                             │
│    - Access:     localhost:3000 (frontend), :8000 (API)        │
│                                                                │
│  Staging:                                                      │
│    - Purpose:    Integration tests, QA validation              │
│    - Infra:      ECS Fargate (minimal)                         │
│    - Data:       Anonymized production snapshot                │
│    - Deploy:     GitHub Actions -> ECR -> ECS                  │
│    - Access:     VPN-protected                                 │
│                                                                │
│  Production:                                                   │
│    - Purpose:    Customer-facing workloads                     │
│    - Infra:      ECS/EKS Fargate (HA, multi-AZ)                │
│    - Data:       Production data (RLS-protected)               │
│    - Deploy:     GitHub Actions -> ECR -> ECS (blue/green)     │
│    - Access:     CloudFront + WAF                              │
│                                                                │
│  DR (Disaster Recovery):                                       │
│    - Purpose:    Business continuity                           │
│    - Infra:      Standby in secondary region                   │
│    - Data:       Cross-region DB replica, S3 replication       │
│    - RTO:        15 minutes                                    │
│    - RPO:        5 minutes                                     │
└────────────────────────────────────────────────────────────────┘
```

### 14.2 CI/CD Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│  CI/CD PIPELINE (GitHub Actions)                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  On Push to main / release/*:                                 │
│                                                                │
│  Step 1: Lint & Type Check                                     │
│    - ruff check api/                                           │
│    - mypy api/                                                 │
│    - tsc --noEmit frontend/                                    │
│                                                                │
│  Step 2: Unit Tests                                            │
│    - pytest api/tests/ --cov --cov-report=xml                  │
│    - npm test frontend/                                        │
│    - Threshold: > 80% coverage                                 │
│                                                                │
│  Step 3: Build & Push Images                                   │
│    - docker build -t api:sha .                                 │
│    - docker push $ECR/api:sha                                  │
│    - docker push $ECR/frontend:sha                             │
│                                                                │
│  Step 4: Migrate Database                                      │
│    - alembic upgrade head                                      │
│    - (staging only, production uses manual approval)           │
│                                                                │
│  Step 5: Deploy to Staging                                     │
│    - Update ECS task definition                                │
│    - Deploy new task set                                       │
│    - Run smoke tests                                           │
│                                                                │
│  Step 6: Manual Approval Gate                                  │
│    - QA team validates staging                                 │
│    - Product owner approves                                    │
│                                                                │
│  Step 7: Deploy to Production                                  │
│    - Blue/green deployment                                     │
│    - Canary: 10% traffic for 5 min                             │
│    - Roll forward if healthy                                   │
│    - Auto-rollback if error rate > 1%                          │
│                                                                │
│  Step 8: Post-Deploy                                           │
│    - Run integration tests                                     │
│    - Update monitoring dashboards                              │
│    - Notify team via Slack                                     │
└────────────────────────────────────────────────────────────────┘
```

---

## 15. Security Architecture

### 15.1 Security Layers

```
┌────────────────────────────────────────────────────────────────┐
│  SECURITY ARCHITECTURE                                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Layer 1: Network Security                                     │
│    - VPC with private/public subnets                           │
│    - Security groups (least privilege)                         │
│    - WAF (SQL injection, XSS, rate limiting)                   │
│    - TLS 1.3 everywhere                                        │
│    - API Gateway as single entry point                         │
│                                                                │
│  Layer 2: Authentication                                       │
│    - Auth0 (OIDC/OAuth 2.0)                                    │
│    - JWT with RS256 signing                                    │
│    - API key authentication (service-to-service)               │
│    - MFA support                                               │
│    - Session management (Redis)                                │
│                                                                │
│  Layer 3: Authorization                                        │
│    - RBAC (role-based)                                         │
│    - Row-level security (PostgreSQL RLS)                       │
│    - Tenant isolation (tenant_id on every query)               │
│    - Permission checks at API middleware                       │
│                                                                │
│  Layer 4: Data Security                                        │
│    - Encryption at rest (RDS, S3, Redis)                       │
│    - Encryption in transit (TLS)                               │
│    - Tenant-level encryption keys (KMS)                        │
│    - PII masking in logs                                       │
│    - File scanning (malware detection on upload)               │
│                                                                │
│  Layer 5: AI Security                                          │
│    - Prompt injection detection                                │
│    - Output validation (PII leakage)                           │
│    - Rate limiting on AI endpoints                             │
│    - Cost governance (per-tenant budgets)                      │
│    - Model access controls                                     │
│                                                                │
│  Layer 6: Audit & Compliance                                   │
│    - Immutable audit logs                                      │
│    - All mutations logged                                      │
│    - AI analysis audit trail                                   │
│    - SOC 2 compliance ready                                    │
│    - GDPR data deletion workflows                              │
└────────────────────────────────────────────────────────────────┘
```

---

## 16. Disaster Recovery & Resilience

### 16.1 Resilience Patterns

```
┌────────────────────────────────────────────────────────────────┐
│  RESILIENCE PATTERNS                                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Circuit Breaker:                                              │
│    - External API calls (LLM, Auth0, S3)                      │
│    - Open after 5 consecutive failures                        │
│    - Half-open after 30s                                      │
│    - Fallback: cached response, degraded mode                  │
│                                                                │
│  Bulkhead:                                                     │
│    - Separate connection pools per service                    │
│    - Isolated thread pools for AI, DB, external calls         │
│    - Prevents cascade failure                                  │
│                                                                │
│  Retry with Backoff:                                           │
│    - 3 retries for transient failures                          │
│    - Exponential backoff (1s, 2s, 4s) + jitter                 │
│    - Idempotent operation keys                                 │
│                                                                │
│  Timeout:                                                      │
│    - API gateway: 30s                                          │
│    - Internal services: 10s                                    │
│    - LLM calls: 60s (sync), 300s (async)                      │
│    - Database: 5s                                              │
│                                                                │
│  Dead Letter Queue:                                            │
│    - Failed tasks stored for analysis                          │
│    - Manual replay capability                                  │
│    - Alert on DLQ accumulation                                 │
│                                                                │
│  Graceful Degradation:                                         │
│    - AI unavailable -> show cached analysis                    │
│    - Search unavailable -> basic text search                   │
│    - Notifications unavailable -> queue for later              │
└────────────────────────────────────────────────────────────────┘
```

### 16.2 Disaster Recovery Plan

```
┌────────────────────────────────────────────────────────────────┐
│  DISASTER RECOVERY PLAN                                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Scenario 1: Single AZ Failure                                 │
│    - Impact:   Partial capacity loss                           │
│    - Action:   ECS/Auto Scaling replaces instances             │
│    - RTO:      2 minutes                                       │
│    - RPO:      0 (no data loss)                                │
│                                                                │
│  Scenario 2: Entire Region Failure                             │
│    - Impact:   Full service outage                             │
│    - Action:   Route53 failover to DR region                   │
│    - RTO:      15 minutes                                      │
│    - RPO:      5 minutes (async DB replication)                │
│                                                                │
│  Scenario 3: Database Corruption                               │
│    - Impact:   Data integrity compromised                      │
│    - Action:   Point-in-time recovery (PITR)                   │
│    - RTO:      30 minutes                                      │
│    - RPO:      5 minutes                                       │
│                                                                │
│  Scenario 4: LLM API Outage                                    │
│    - Impact:   AI features unavailable                         │
│    - Action:   Fallback to cached results, queue for retry     │
│    - RTO:      Immediate (degraded mode)                       │
│    - RPO:      N/A                                             │
│                                                                │
│  Backup Schedule:                                              │
│    - PostgreSQL:  Continuous WAL archiving + daily snapshot    │
│    - S3:          Cross-region replication                     │
│    - Redis:       Periodic RDB snapshots to S3                 │
│    - Config:      Infrastructure as Code (Terraform)           │
└────────────────────────────────────────────────────────────────┘
```

---

## 17. Runtime Execution Models

### 17.1 Execution Model Matrix

| Model | Trigger | Latency | Resources | Use Case |
|-------|---------|---------|-----------|----------|
| **Synchronous HTTP** | User request | < 5s | CPU/Memory | CRUD, search, dashboard |
| **Streaming HTTP** | User request | < 500ms TTFT | CPU/Memory | AI chat, redline generation |
| **Async Queue** | Event | 10s - 5min | CPU/Memory/GPU | Document analysis, classification |
| **Batch Scheduled** | Cron | 1h - 12h | CPU/Memory/GPU | Nightly re-analysis, benchmarks |
| **Real-time WebSocket** | Connection | < 100ms | Memory | Notifications, activity feed |
| **Webhook** | Event | < 30s | CPU/Network | External system integration |
| **gRPC Internal** | Service call | < 500ms | CPU | Service-to-service AI calls |
| **Cron Job** | Time-based | N/A | CPU | Analytics aggregation, cleanup |

### 17.2 Request Flow: Synchronous

```
Client                    API Gateway              Service              Database
  │                          │                       │                    │
  │── POST /api/v1/contracts─>│                       │                    │
  │                          │── AuthN/AuthZ ────────>│                    │
  │                          │<── OK ────────────────│                    │
  │                          │── Validate Request ───>│                    │
  │                          │── Upload to S3 ───────>│                    │
  │                          │<── S3 URL ────────────│                    │
  │                          │── INSERT contract ────>│──── INSERT ──────>│
  │                          │<── contract_id ───────│<── OK ────────────│
  │                          │── Emit event ────────>│ (async to queue)   │
  │                          │                       │                    │
  │<── 201 Created ─────────│                       │                    │
  │    { contract_id }      │                       │                    │
```

### 17.3 Request Flow: Async (Document Ingestion)

```
Client         API Gateway        Redis Queue       Worker            DB/S3
  │                │                  │                │                │
  │── Upload ─────>│                  │                │                │
  │                │── Enqueue ──────>│                │                │
  │<── 202 Accepted│                  │                │                │
  │                │                  │── Dequeue ────>│                │
  │                │                  │                │── Download ───>│ S3
  │                │                  │                │<── File ──────│
  │                │                  │                │── Extract ────>│
  │                │                  │                │── Chunk ──────>│
  │                │                  │                │── Embed ──────>│
  │                │                  │                │── Write ──────>│ DB
  │                │                  │                │── Emit done ──>│ Redis
  │                │                  │<── Complete ───│                │
```

### 17.4 Request Flow: RAG Query

```
Client         API Gateway        AI Service        pgvector          LLM
  │                │                  │                │                │
  │── POST /ai/q──>│                  │                │                │
  │                │── Route ────────>│                │                │
  │                │                  │── Embed query ─>│                │
  │                │                  │<── vector ─────│                │
  │                │                  │── Search ─────>│                │
  │                │                  │<── chunks ────│                │
  │                │                  │── Build prompt │                │
  │                │                  │── LLM call ───────────────────>│
  │                │                  │<── response ───────────────────│
  │                │                  │── Format + cite                │
  │<── 200 OK ─────│<── response ────│                                │
```

---

## 18. Service-Level Objectives

### 18.1 SLO Definitions

| Service | Metric | Target | Measurement | Burn Rate |
|---------|--------|--------|-------------|-----------|
| **API Gateway** | Availability | 99.99% | Request success rate | 5% error in 5min |
| **API Gateway** | Latency p99 | < 500ms | Response time | > 2s for 5min |
| **Contract Service** | Availability | 99.99% | Request success rate | 5% error in 5min |
| **Contract Service** | Latency p95 | < 200ms | Response time | > 1s for 5min |
| **AI Service** | Availability | 99.9% | Analysis completion | 10% failure in 5min |
| **AI Service** | Latency p95 | < 30s | Analysis time | > 60s for 10min |
| **AI Service** | Accuracy | > 85% | Human validation | < 80% for 1 day |
| **Ingestion Pipeline** | Availability | 99.9% | Job completion rate | 5% failure in 5min |
| **Ingestion Pipeline** | Throughput | 100 docs/min | Documents processed | < 50/min for 10min |
| **Ingestion Pipeline** | Latency p95 | < 5min | Document to ready | > 15min for 30min |
| **Search Service** | Availability | 99.99% | Query success rate | 2% error in 5min |
| **Search Service** | Latency p99 | < 2s | Query response time | > 5s for 5min |
| **Workflow Engine** | Availability | 99.99% | Step completion | 2% failure in 5min |
| **Notification Service** | Delivery | 99.9% | Notification delivered | 2% failure in 5min |
| **Webhook** | Delivery | 99.5% | Webhook delivered | 5% failure in 10min |

### 18.2 Error Budgets

```
┌────────────────────────────────────────────────────────────────┐
│  ERROR BUDGETS (Monthly)                                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  API Gateway (99.99%):   4.32 minutes of downtime/month        │
│  AI Service (99.9%):    43.2 minutes of downtime/month         │
│  Ingestion (99.9%):     43.2 minutes of downtime/month         │
│  Search (99.99%):        4.32 minutes of downtime/month        │
│                                                                │
│  Budget Consumption:                                           │
│    < 50%:  Deploy freely                                       │
│    50-80%: Slow deploys, require manual approval               │
│    80-100%: Freeze deploys, focus on reliability               │
│    > 100%: Incident review required                            │
└────────────────────────────────────────────────────────────────┘
```

---

## Appendix A: Port Mapping

| Service | Port | Protocol | Internal/External |
|---------|------|----------|-------------------|
| Frontend (Next.js) | 3000 | HTTP | External |
| API Gateway | 8000 | HTTP | External |
| PostgreSQL | 5432 | PostgreSQL | Internal |
| Redis | 6379 | Redis | Internal |
| Celery Flower | 5555 | HTTP | Internal (admin) |
| gRPC (AI Service) | 50051 | gRPC | Internal |
| WebSocket | 8001 | WS | External |
| Metrics | 9090 | HTTP | Internal |
| Health | 8000/health | HTTP | Internal (ALB) |

## Appendix B: Environment Variables

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=info
API_VERSION=v1

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/contract_risk
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=50

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CELERY_WORKER_CONCURRENCY=4

# Auth
AUTH0_DOMAIN=tenant.auth0.com
AUTH0_AUDIENCE=https://api.contractriskanalyzer.com
AUTH0_ISSUER=https://tenant.auth0.com/

# AWS
AWS_REGION=us-east-1
S3_DOCUMENTS_BUCKET=contractrisk-documents-prod
S3_EXPORTS_BUCKET=contractrisk-exports-prod
S3_BACKUPS_BUCKET=contractrisk-backups-prod

# AI / LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=1536
DEFAULT_LLM_MODEL=gpt-4o

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4318
OTEL_SERVICE_NAME=contract-risk-analyzer
DD_API_KEY=...
DD_SITE=datadoghq.com

# Security
ENCRYPTION_KEY_ID=alias/contractrisk-tenant-key
JWT_SECRET=...
CORS_ORIGINS=https://app.contractriskanalyzer.com
```

## Appendix C: Service Dependencies Graph

```
                     ┌─────────────┐
                     │   Auth0     │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  Frontend   │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │API Gateway  │
                     └──┬───┬───┬──┘
                        │   │   │
          ┌─────────────┘   │   └─────────────┐
          │                 │                 │
    ┌─────▼─────┐    ┌─────▼─────┐    ┌──────▼──────┐
    │  Contract │    │  AI       │    │  Workflow   │
    │  Service  │    │  Service  │    │  Engine     │
    └──┬───┬────┘    └──┬───┬────┘    └──┬───┬──────┘
       │   │            │   │           │   │
       │   └──┐         │   └──┐        │   └──┐
       │      │         │      │        │      │
    ┌──▼──┐ ┌─▼──┐  ┌──▼──┐ ┌─▼──┐  ┌──▼──┐ ┌─▼──┐
    │Post-│ │ S3 │  │Post-│ │LLM │  │Post-│ │Redis│
    │greSQL│ │    │  │greSQL│ │API │  │greSQL│ │    │
    └─────┘ └────┘  └─────┘ └────┘  └─────┘ └────┘

    Key:
    ──>  HTTP/REST
    ──>  gRPC
    ──>  Async Event
    ──>  Database
```
