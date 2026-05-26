# ContractRiskEdge — Production Implementation Blueprint

## V1 Execution Specification — Modular Monolith, AI-Native, Enterprise-Grade

**Classification:** Internal Engineering Blueprint  
**Version:** 1.0  
**Status:** Ready for Execution  
**Target:** Production Pilot Q3 2026

---

## Table of Contents

1. [V1 MVP Scope Freeze](#1-v1-mvp-scope-freeze)
2. [Modular Monolith Architecture](#2-modular-monolith-architecture)
3. [Physical Database Design](#3-physical-database-design)
4. [Backend Implementation Spec](#4-backend-implementation-spec)
5. [AI Runtime Implementation](#5-ai-runtime-implementation)
6. [Search + Vector Implementation](#6-search--vector-implementation)
7. [Frontend Engineering System](#7-frontend-engineering-system)
8. [Infrastructure + DevOps Blueprint](#8-infrastructure--devops-blueprint)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Engineering Governance Rules](#10-engineering-governance-rules)

---

## 1. V1 MVP Scope Freeze

### 1.1 MUST HAVE (P0 — Blocking for Pilot)

| Feature | Complexity | Business Impact | Risk | Rationale |
|---------|-----------|-----------------|------|-----------|
| Auth (email/password + OIDC) | Low | Critical | Low | No access without auth |
| Tenant isolation (RLS) | Medium | Critical | Medium | Multi-tenant requirement |
| RBAC (admin, analyst, viewer) | Low | Critical | Low | Enterprise requirement |
| Contract upload (PDF) | Medium | Critical | Medium | Core value proposition |
| OCR pipeline (PyMuPDF + Tesseract) | Medium | Critical | Medium | Document processing |
| Text chunking (semantic) | Medium | High | Medium | Foundation for search + AI |
| Embedding generation (OpenAI) | Low | Critical | Low | Vector search + RAG |
| Semantic search (pgvector) | Medium | High | Medium | Core search capability |
| AI risk analysis (single model) | Medium | Critical | Medium | Core AI value |
| Clause classification | Medium | High | Medium | Structured output |
| Workflow: single approval step | Medium | High | Medium | Basic workflow |
| Contract review UI | High | Critical | High | User-facing product |
| Audit logging (immutable) | Medium | Critical | Medium | Compliance requirement |
| Basic notifications (in-app) | Medium | Medium | Medium | User engagement |
| Admin: user management | Low | High | Low | Operational necessity |

### 1.2 SHOULD HAVE (P1 — Post-Pilot Enhancement)

| Feature | Complexity | Business Impact | Risk | Rationale |
|---------|-----------|-----------------|------|-----------|
| AI obligation extraction | Medium | High | Medium | Adds structured data |
| Redline suggestions | High | High | High | Complex AI output |
| Dashboard KPIs | Medium | Medium | Low | Visibility |
| Export (PDF/CSV) | Medium | Medium | Low | Data portability |
| Webhook integrations | Medium | Medium | Medium | Extensibility |
| Comment/annotation system | Medium | Medium | Low | Collaboration |
| Multi-step approval workflows | High | High | High | Complex workflow |
| Email notifications | Medium | Medium | Low | User engagement |
| Basic reporting | Medium | Medium | Low | Analytics |
| API key auth for integrations | Low | Medium | Low | Programmatic access |

### 1.3 DEFERRED (P2 — V2)

| Feature | Rationale |
|---------|-----------|
| Advanced AI agents (LangGraph) | Need production data first to train/validate |
| Multi-region active-active | Not needed until > 10k daily active users |
| Advanced benchmarking corpus | Requires cross-tenant data aggregation |
| Negotiation intelligence | Requires historical negotiation data |
| Graph neural networks | Research-phase technology for legal AI |
| Federated learning | Requires deployed on-prem customers |
| Sovereign cloud deployment | Customer-driven requirement, not yet |
| Advanced policy DSL (OPA) | Simple policy engine sufficient for V1 |
| Data mesh / data products | Premature before platform adoption |
| Autonomous AI actions | Regulatory risk without human oversight |

### 1.4 NOT IN V1

| Feature | Reason |
|---------|--------|
| Real-time collaborative editing | Massive complexity, low initial value |
| Native mobile apps | Web-first, mobile responsive sufficient |
| On-prem deployment | SaaS-only for V1 |
| Air-gapped deployment | Customer-driven, not yet required |
| Custom LLM fine-tuning | High cost, uncertain ROI at small scale |
| Blockchain-based audit trails | No customer demand, adds complexity |
| Natural language contract drafting | Legal risk, regulatory uncertainty |
| Multi-language OCR | English-only for V1 |
| Document generation | Out of scope for analysis platform |
| Advanced visual workflow builder | Low-code builder is V2+ feature |

### 1.5 Architecture Decisions for V1

```
1. Single PostgreSQL database (no read replicas)
2. pgvector for embeddings (no external vector DB)
3. OpenAI API for LLM (no self-hosted models)
4. Celery for background jobs (single queue)
5. Redis for caching + job broker + rate limiting
6. S3-compatible storage for documents
7. Next.js + Tailwind for frontend
8. Docker Compose for local development
9. Monolithic FastAPI process (no service split)
10. Single AI worker pool (no GPU orchestration)
```

---

## 2. Modular Monolith Architecture

### 2.1 High-Level Structure

```
api/
├── app/
│   ├── main.py                      # FastAPI app factory
│   ├── config.py                    # Pydantic settings
│   ├── dependencies.py              # FastAPI DI
│   ├── lifecycle.py                 # Startup/shutdown
│   │
│   ├── kernel/                      # SHARED KERNEL
│   │   ├── base/
│   │   │   ├── repository.py        # Abstract base repository
│   │   │   ├── service.py           # Abstract base service
│   │   │   ├── schema.py            # Base pydantic schema
│   │   │   └── model.py             # Base SQLAlchemy model
│   │   ├── database/
│   │   │   ├── session.py           # Async session factory
│   │   │   ├── unit_of_work.py      # UoW pattern
│   │   │   └── migrations/          # Alembic
│   │   ├── events/
│   │   │   ├── bus.py               # In-memory event bus
│   │   │   ├── dispatcher.py        # Event -> handler routing
│   │   │   └── handlers.py          # Global handler registration
│   │   ├── security/
│   │   │   ├── auth.py              # JWT validation
│   │   │   ├── rbac.py              # Role/permission checking
│   │   │   ├── tenant.py            # Tenant resolution
│   │   │   └── audit.py             # Audit logging
│   │   ├── middleware/
│   │   │   ├── request_id.py
│   │   │   ├── tenant_context.py
│   │   │   ├── auth_context.py
│   │   │   ├── logging_middleware.py
│   │   │   └── rate_limit.py
│   │   ├── pagination.py
│   │   ├── exceptions.py
│   │   ├── response.py              # Standard response envelope
│   │   └── utils/
│   │       ├── date_utils.py
│   │       ├── crypto_utils.py
│   │       └── validators.py
│   │
│   ├── domains/                     # DOMAIN MODULES
│   │   ├── auth/                    # Auth + users + tenants
│   │   ├── contracts/               # Contract CRUD + upload
│   │   ├── ingestion/               # OCR + chunking
│   │   ├── ai/                      # AI analysis + classification
│   │   ├── search/                  # Semantic + full-text search
│   │   ├── workflows/               # Workflow engine
│   │   ├── audit/                   # Audit logging
│   │   ├── notifications/           # In-app + email notifications
│   │   └── reporting/               # Basic reporting
│   │
│   └── integrations/                # External integrations
│       ├── storage/                 # S3-compatible storage
│       ├── llm/                     # OpenAI/Anthropic client
│       └── email/                   # SendGrid/SES client
│
├── workers/                         # BACKGROUND WORKERS
│   ├── celery_app.py                # Celery configuration
│   ├── ingestion_worker.py          # Document processing
│   ├── ai_worker.py                 # AI analysis
│   └── maintenance_worker.py        # Scheduled tasks
│
├── alembic/
├── tests/
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

### 2.2 Domain Module Template

Every domain module follows this exact structure:

```
domains/{domain}/
├── __init__.py              # Re-exports: router, schemas
├── schemas.py               # Pydantic request/response DTOs
├── models.py                # SQLAlchemy ORM models
├── repository.py            # Data access (extends BaseRepository)
├── service.py               # Business logic (extends BaseService)
├── router.py                # FastAPI routes
├── events.py                # Domain event definitions
├── exceptions.py            # Domain-specific exceptions
└── tests/
    ├── test_router.py
    ├── test_service.py
    └── test_repository.py
```

### 2.3 Dependency Rules

```
LAYER RULES (strict enforcement via CI/linters):

1. Router → Service → Repository
   (NEVER skip layers — no direct DB access from routers)

2. Domain modules CANNOT import from other domain modules directly
   (Cross-domain communication via Event Bus ONLY)

3. All domains CAN import from kernel/
   (kernel is the ONLY shared dependency)

4. Workers CAN import from domains/ (but NOT vice versa)

5. Tests CAN import from any domain + kernel

6. Circular dependencies = BUILD FAILURE
   (enforced via import-linter in CI)

7. Shared kernel has ZERO dependencies on any domain module
```

### 2.4 Internal Event Bus

```python
# kernel/events/bus.py

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

Handler = Callable[..., Awaitable[None]]

class EventBus:
    """In-memory domain event bus. Synchronous within process."""

    def __init__(self):
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def register(self, event_type: type, handler: Handler):
        self._handlers[event_type].append(handler)

    async def emit(self, event) -> None:
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return
        # Fire-and-forget — handlers run concurrently, errors logged
        results = await asyncio.gather(
            *[h(event) for h in handlers],
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    "Event handler failed: %s handling %s: %s",
                    handler.__name__, type(event).__name__, result,
                )

# ── Registration ──────────────────────────────────────────────────

# lifecycle.py
def register_domain_events(bus: EventBus, services: dict):
    """Wire domain events to handlers on startup."""
    # Auth events
    bus.register(UserCreated, services['notifications'].on_user_created)

    # Contract events
    bus.register(ContractUploaded, services['ingestion'].on_contract_uploaded)
    bus.register(ContractProcessed, services['ai'].on_contract_processed)

    # AI events
    bus.register(AIAnalysisCompleted, services['workflows'].on_analysis_completed)
    bus.register(RiskFindingCreated, services['notifications'].on_risk_finding)

    # Workflow events
    bus.register(WorkflowCompleted, services['notifications'].on_workflow_completed)
    bus.register(WorkflowEscalated, services['notifications'].on_escalation)
```

### 2.5 Anti-Corruption Rules

```
1. Domain services NEVER call other domain services directly
2. Domain services NEVER import models from other domains
3. Cross-domain data access goes through the Event Bus
4. For READ cross-domain data, use a lightweight query (not the domain model)
5. Each domain owns its tables exclusively
6. Foreign keys ONLY within a domain (cross-domain refs use entity_type + entity_id)
7. Migrations are per-domain (alembic version per domain folder)
```

### 2.6 Future Extraction Strategy

```
When a domain needs to become its own service:

1. Extract domain folder to new service repository
2. Add gRPC/REST client in kernel/
3. Replace Event Bus calls with network calls
4. Dual-write during migration
5. Verify parity, then remove old code

Extraction candidates (in order):
  AI Runtime      — Different scaling needs (GPU)
  Search Engine   — Read-heavy, different indexing
  Workflow Engine — Stateful, different persistence
  Integration Hub — External connectivity, security isolation
```

---

## 3. Physical Database Design

### 3.1 Production Schema Strategy

```sql
-- ── Naming Conventions ────────────────────────────────────────────
-- Tables:      snake_case, plural
-- Columns:     snake_case
-- PKs:         {table}_id  (UUID)
-- FKs:         {referenced_table}_id
-- Indexes:     idx_{table}_{columns}
-- Enums:       TEXT with CHECK constraint (no PG enum — easier migrations)
-- Timestamps:  created_at, updated_at (trigger auto-update)
-- Soft Delete: deleted_at TIMESTAMPTZ
-- Tenant:      tenant_id UUID NOT NULL (first column in all tenant tables)

-- ── Core Tables ───────────────────────────────────────────────────

-- tenants, users, roles: standard RBAC tables (see schema.sql)
-- contracts: already exists with HASH partitioning by tenant_id

-- ── Chunks Table (pgvector) ───────────────────────────────────────

CREATE TABLE chunks (
    chunk_id            UUID DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    chunk_index         INTEGER NOT NULL,
    text                TEXT NOT NULL,
    token_count         INTEGER NOT NULL CHECK (token_count >= 1),
    embedding           vector(1536),
    embedding_model     TEXT DEFAULT 'text-embedding-3-large',
    clause_ids          UUID[] DEFAULT '{}',
    page_numbers        INTEGER[] DEFAULT '{}',
    is_active           BOOLEAN DEFAULT TRUE,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (tenant_id, chunk_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
) PARTITION BY HASH (tenant_id);

-- 16 initial partitions
CREATE TABLE chunks_p0 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 0);
-- ... p1 through p15

-- Vector index (per partition — build after data loaded)
CREATE INDEX idx_chunks_p0_embedding ON chunks_p0
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- Repeat for each partition

-- ── Workflows Table ───────────────────────────────────────────────

CREATE TABLE workflows (
    workflow_id         UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    entity_type         TEXT NOT NULL,       -- 'contract', 'vendor'
    entity_id           UUID NOT NULL,
    workflow_type       TEXT NOT NULL,       -- 'legal_review', 'approval'
    status              TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'active', 'completed', 'cancelled', 'escalated'

    priority            TEXT NOT NULL DEFAULT 'normal',
    assigned_to         TEXT,                -- user_id
    sla_deadline        TIMESTAMPTZ,
    sla_breached        BOOLEAN DEFAULT FALSE,
    metadata            JSONB DEFAULT '{}',
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,

    PRIMARY KEY (tenant_id, workflow_id)
) PARTITION BY HASH (tenant_id);

CREATE INDEX idx_workflows_assignee
    ON workflows(tenant_id, assigned_to, status)
    WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_workflows_sla
    ON workflows(tenant_id, sla_deadline)
    WHERE status IN ('pending', 'active') AND sla_deadline IS NOT NULL;

-- ── Audit Logs (time-partitioned) ─────────────────────────────────

CREATE TABLE audit_logs (
    audit_id            UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    user_id             TEXT NOT NULL,
    action              TEXT NOT NULL,        -- 'contract.uploaded', 'workflow.approved'
    resource_type       TEXT NOT NULL,        -- 'contract', 'workflow'
    resource_id         TEXT NOT NULL,
    details             JSONB DEFAULT '{}',   -- before/after snapshots
    ip_address          TEXT,
    user_agent          TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (tenant_id, audit_id, created_at)
) PARTITION BY RANGE (created_at);

-- Monthly partitions, 7-year retention
CREATE TABLE audit_logs_2026_06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;
```

### 3.2 Index Strategy

```sql
-- ── Critical Indexes ──────────────────────────────────────────────

-- 1. Tenant isolation (every query starts with tenant_id)
CREATE INDEX idx_contracts_tenant_status ON contracts(tenant_id, status);
CREATE INDEX idx_chunks_tenant_contract ON chunks(tenant_id, contract_id);

-- 2. Common query patterns
CREATE INDEX idx_contracts_created ON contracts(tenant_id, created_at DESC);
CREATE INDEX idx_workflows_status ON workflows(tenant_id, status, created_at DESC);

-- 3. Full-text search
ALTER TABLE contracts ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(filename, ''))) STORED;
CREATE INDEX idx_contracts_search ON contracts USING GIN(search_vector);

-- 4. JSONB (only when needed — see JSONB governance)
CREATE INDEX idx_contracts_metadata ON contracts USING GIN(metadata jsonb_path_ops);

-- 5. Partial indexes for hot queries
CREATE INDEX idx_workflows_active_sla ON workflows(tenant_id, sla_deadline)
    WHERE status IN ('pending', 'active');
CREATE INDEX idx_audit_recent ON audit_logs(tenant_id, created_at DESC)
    WHERE created_at > NOW() - INTERVAL '30 days';
```

### 3.3 JSONB Governance

```sql
-- ── ALLOWED JSONB Use Cases ───────────────────────────────────────

-- 1. Extensible metadata (tenant-specific fields)
--    Schema: {"department": "...", "project_code": "..."}
--    Indexed ONLY if queried frequently

-- 2. AI analysis outputs (variable structure)
--    Schema: {"risk_score": 0.82, "findings": [...]}
--    NOT indexed — queried by analysis_id FK

-- 3. Audit details (variable structure)
--    Schema: {"before": {...}, "after": {...}}
--    NOT indexed — queried by audit_id

-- ── FORBIDDEN JSONB Patterns ──────────────────────────────────────

-- ❌ Queryable operational data
--    BAD:  WHERE metadata->>'status' = 'active'
--    GOOD: status TEXT NOT NULL

-- ❌ Filtered/sorted columns
--    BAD:  ORDER BY metadata->>'created_at'
--    GOOD: created_at TIMESTAMPTZ NOT NULL

-- ❌ Frequently updated fields
--    BAD:  UPDATE ... SET metadata = jsonb_set(metadata, '{status}', '"active"')
--    GOOD: UPDATE ... SET status = 'active'
```

### 3.4 Partitioning Strategy

| Table | Partition Key | Partitions | Retention | Row Estimate |
|-------|--------------|------------|-----------|-------------|
| contracts | HASH(tenant_id) | 16 | Permanent | 1M/year |
| chunks | HASH(tenant_id) | 16 | Permanent | 100M/year |
| workflows | HASH(tenant_id) | 16 | 90 days after completion | 5M/year |
| audit_logs | RANGE(created_at) | Monthly | 7 years | 50M/year |
| notifications | HASH(tenant_id) | 8 | 90 days | 10M/year |
| ai_analyses | HASH(tenant_id) | 8 | Permanent | 5M/year |

### 3.5 Archival Jobs

```python
# workers/maintenance_worker.py

@celery_app.task(name="archive_completed_workflows")
def archive_completed_workflows():
    """Move completed workflows older than 90 days to cold storage."""
    cutoff = datetime.utcnow() - timedelta(days=90)
    # Detach partition, export to Parquet in S3, drop partition
    ...

@celery_app.task(name="archive_old_audit_logs")
def archive_old_audit_logs():
    """Detach audit log partitions older than 7 years."""
    ...

@celery_app.task(name="vacuum_analyze_tables")
def vacuum_analyze_tables():
    """Weekly VACUUM ANALYZE on all tables."""
    ...
```

### 3.6 Backup Strategy

```
PostgreSQL:
  - Continuous WAL archiving to S3 (5-minute intervals)
  - Daily full snapshot (retained 30 days)
  - Weekly full snapshot (retained 12 months)
  - Monthly full snapshot (retained 7 years)

S3 Documents:
  - Cross-region replication (if multi-region enabled)
  - Versioning enabled (30-day retention)
  - Glacier transition after 90 days

Recovery:
  - Point-in-time recovery: 5-minute granularity, 30-day window
  - Full recovery: < 1 hour from daily snapshot
  - Disaster recovery: < 4 hours (provision new infra + restore)
```

---

## 4. Backend Implementation Spec

### 4.1 FastAPI Architecture

```python
# main.py — App Factory

from contextlib import asynccontextmanager
from fastapi import FastAPI
from kernel.database.session import create_session_factory
from kernel.events.bus import EventBus
from kernel.middleware import register_middleware
from kernel.exceptions import register_exception_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = create_session_factory(settings.DATABASE_URL)
    app.state.event_bus = EventBus()
    app.state.services = {}
    await register_domain_services(app.state)
    register_domain_events(app.state.event_bus, app.state.services)
    yield
    # Shutdown
    await app.state.db.close()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, title="ContractRiskEdge API", version="1.0.0")
    register_middleware(app)
    register_exception_handlers(app)
    register_routers(app)
    return app

app = create_app()
```

### 4.2 Dependency Injection

```python
# dependencies.py

from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db(request: Request) -> AsyncSession:
    """Yield session with automatic commit/rollback."""
    session = request.app.state.db()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

async def get_current_user(request: Request) -> UserContext:
    """From auth middleware."""
    return request.state.user

async def get_tenant_id(request: Request) -> str:
    return request.state.tenant_id

# Domain-specific DI
def get_contract_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> ContractService:
    return ContractService(
        repository=ContractRepository(db),
        event_bus=EventBus(),  # Singleton from app.state
        user=user,
        tenant_id=tenant_id,
    )
```

### 4.3 Service Template

```python
# domains/contracts/service.py

from dataclasses import dataclass, field

@dataclass
class ContractService:
    repository: ContractRepository
    event_bus: EventBus
    user: UserContext
    tenant_id: str

    async def create(self, data: ContractCreate) -> Contract:
        # 1. Validate
        if data.file_size > MAX_FILE_SIZE:
            raise ContractTooLargeError()

        # 2. Upload to S3
        file_path = await storage.upload(data.file, self.tenant_id)

        # 3. Persist (single transaction)
        contract = await self.repository.create(
            tenant_id=self.tenant_id,
            created_by=self.user.id,
            filename=data.filename,
            file_path=file_path,
            contract_type=data.contract_type,
        )

        # 4. Emit event (async, non-blocking)
        await self.event_bus.emit(
            ContractUploaded(contract_id=contract.id, tenant_id=self.tenant_id)
        )

        return contract

    async def get_by_id(self, contract_id: UUID) -> Contract:
        contract = await self.repository.get_by_id(contract_id, self.tenant_id)
        if not contract:
            raise ContractNotFoundError(contract_id)
        return contract

    async def list(self, filters: ContractFilters, page: int, page_size: int) -> tuple[list[Contract], int]:
        return await self.repository.list(self.tenant_id, filters, page, page_size)
```

### 4.4 Repository Template

```python
# kernel/base/repository.py

from dataclasses import dataclass
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class BaseRepository:
    session: AsyncSession

    async def execute(self, stmt):
        return await self.session.execute(stmt)

    async def scalar(self, stmt):
        result = await self.session.execute(stmt)
        return result.scalar()

    async def paginate(self, query, page: int, page_size: int):
        total = await self.scalar(select(func.count()).select_from(query.subquery()))
        result = await self.session.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

# domains/contracts/repository.py

@dataclass
class ContractRepository(BaseRepository):

    async def create(self, **kwargs) -> Contract:
        contract = Contract(**kwargs)
        self.session.add(contract)
        await self.session.flush()
        return contract

    async def get_by_id(self, contract_id: UUID, tenant_id: str) -> Contract | None:
        stmt = select(Contract).where(
            Contract.contract_id == contract_id,
            Contract.tenant_id == tenant_id,
            Contract.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, tenant_id: str, filters: ContractFilters, page: int, page_size: int):
        query = select(Contract).where(
            Contract.tenant_id == tenant_id,
            Contract.deleted_at.is_(None),
        )
        if filters.status:
            query = query.where(Contract.status == filters.status)
        if filters.contract_type:
            query = query.where(Contract.contract_type == filters.contract_type)

        query = query.order_by(Contract.created_at.desc())
        return await self.paginate(query, page, page_size)
```

### 4.5 Router Template

```python
# domains/contracts/router.py

from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/contracts", tags=["Contracts"])

@router.get("/", response_model=PaginatedResponse[ContractSummary])
async def list_contracts(
    filters: ContractFilters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ContractService = Depends(get_contract_service),
):
    items, total = await service.list(filters, page, page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)

@router.post("/", response_model=ContractDetail, status_code=status.HTTP_201_CREATED)
async def create_contract(
    body: ContractCreate,
    service: ContractService = Depends(get_contract_service),
):
    return await service.create(body)

@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    contract_id: UUID,
    service: ContractService = Depends(get_contract_service),
):
    return await service.get_by_id(contract_id)
```

### 4.6 Error Handling

```python
# kernel/exceptions.py

class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

class NotFoundError(AppError):
    status_code = 404
    code = "not_found"

class ValidationError(AppError):
    status_code = 422
    code = "validation_error"

class AuthorizationError(AppError):
    status_code = 403
    code = "forbidden"

class AuthenticationError(AppError):
    status_code = 401
    code = "unauthorized"

# ── Global handler ─────────────────────────────────────────────────

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": str(exc),
            "request_id": request.state.request_id,
        },
    )
```

### 4.7 Standard Response Envelope

```json
// Success (single)
{
    "data": { "id": "uuid", "name": "Contract A" },
    "request_id": "req_abc123"
}

// Success (list)
{
    "data": [ ... ],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total": 142,
        "total_pages": 8
    },
    "request_id": "req_abc123"
}

// Error
{
    "error": "not_found",
    "message": "Contract with id 'uuid' not found",
    "request_id": "req_abc123"
}
```

### 4.8 Worker Architecture

```python
# workers/celery_app.py

from celery import Celery

celery_app = Celery(
    "contractrisk",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_queues=[
        Queue("ingestion"),
        Queue("ai"),
        Queue("default"),
    ],
    task_routes={
        "ingestion.*": {"queue": "ingestion"},
        "ai.*": {"queue": "ai"},
    },
    beat_schedule={
        "vacuum-analyze-hourly": {
            "task": "maintenance.vacuum_analyze",
            "schedule": 3600.0,
        },
    },
)

# workers/ingestion_worker.py
@celery_app.task(bind=True, max_retries=3, acks_late=True)
def process_document(self, contract_id: str, tenant_id: str):
    """Full ingestion pipeline: extract -> chunk -> embed."""
    try:
        text = extract_text(contract_id, tenant_id)
        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)
        store_chunks(contract_id, tenant_id, chunks, embeddings)
        update_contract_status(contract_id, tenant_id, 'ready')
        event_bus.emit(ContractProcessed(contract_id=contract_id, tenant_id=tenant_id))
    except RetryableError as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

---

## 5. AI Runtime Implementation

### 5.1 Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │     AI RUNTIME (Modular Monolith)            │
                    ├──────────────────────────────────────────────┤
                    │                                              │
  ┌──────────┐      │  ┌──────────┐    ┌──────────┐              │
  │ Event    │──────│─>│Pipeline  │───>│ Executor │              │
  │ (internal)│     │  │Orchestr. │    │          │              │
  └──────────┘      │  └──────────┘    └────┬─────┘              │
                    │                        │                    │
                    │              ┌─────────┼─────────┐          │
                    │              │         │         │          │
                    │        ┌─────▼──┐ ┌────▼───┐ ┌──▼──────┐  │
                    │        │Prompt  │ │Model   │ │Output   │  │
                    │        │Builder │ │Router  │ │Validator│  │
                    │        └─────────┘ └─────────┘ └─────────┘  │
                    │                                              │
                    │  Execution: Celery worker (ai queue)         │
                    │  Cache: Redis (LLM response cache)           │
                    │  Storage: PostgreSQL (ai_analyses table)     │
                    └──────────────────────────────────────────────┘
```

### 5.2 Folder Structure

```
api/app/domains/ai/
├── __init__.py
├── schemas.py              # Pydantic: AnalysisRequest, AnalysisResult
├── models.py               # SQLAlchemy: AIAnalysis, AIFinding
├── repository.py           # CRUD for analyses + findings
├── service.py              # Orchestration: trigger analysis, store results
├── router.py               # API: POST /ai/analyze, GET /ai/analyses
│
├── pipeline/               # AI pipeline orchestration
│   ├── __init__.py
│   ├── orchestrator.py     # Pipeline step coordination
│   ├── risk_analysis.py    # Risk analysis step
│   ├── clause_classify.py  # Clause classification step
│   └── extract_obligations.py  # Obligation extraction step
│
├── llm/                    # LLM integration
│   ├── __init__.py
│   ├── client.py           # OpenAI/Anthropic client wrapper
│   ├── router.py           # Model selection (simple for V1)
│   ├── prompt_manager.py   # Prompt template loading
│   └── templates/          # Jinja2 prompt templates
│       ├── risk_analysis.j2
│       ├── clause_classify.j2
│       └── obligations.j2
│
├── chunking/               # Text chunking
│   ├── __init__.py
│   ├── semantic.py         # Semantic chunking (paragraph boundaries)
│   └── fixed_size.py       # Fixed-size fallback
│
├── embedding/              # Embedding generation
│   ├── __init__.py
│   └── embedder.py         # OpenAI embedding client
│
├── cache/                  # AI response cache
│   ├── __init__.py
│   └── llm_cache.py        # Redis semantic cache
│
├── exceptions.py
└── tests/
```

### 5.3 Pipeline Orchestrator

```python
# pipeline/orchestrator.py

import asyncio
from dataclasses import dataclass

@dataclass
class AnalysisPipeline:
    """Orchestrates multi-step AI analysis for a contract."""

    llm_client: LLMClient
    prompt_manager: PromptManager
    embedder: Embedder
    cache: LLMCache
    repository: AIAnalysisRepository

    async def run(self, contract_id: UUID, tenant_id: str) -> AIAnalysis:
        # 1. Load contract text + chunks
        chunks = await self.repository.get_chunks(contract_id, tenant_id)
        full_text = " ".join(c.text for c in chunks)

        # 2. Run parallel analysis steps
        risk_task = self._analyze_risk(full_text, contract_id, tenant_id)
        classify_task = self._classify_clauses(chunks, contract_id, tenant_id)
        oblig_task = self._extract_obligations(full_text, contract_id, tenant_id)

        risk_result, classify_result, oblig_result = await asyncio.gather(
            risk_task, classify_task, oblig_task,
        )

        # 3. Store results
        analysis = await self.repository.create_analysis(
            contract_id=contract_id,
            tenant_id=tenant_id,
            risk_score=risk_result.risk_score,
            findings=risk_result.findings + classify_result.findings,
            obligations=oblig_result.obligations,
            model_used="gpt-4o",
            tokens_used=risk_result.tokens + classify_result.tokens + oblig_result.tokens,
        )

        return analysis

    async def _analyze_risk(self, text: str, contract_id: UUID, tenant_id: str) -> RiskResult:
        # Check cache
        cache_key = f"risk:{contract_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return RiskResult(**cached)

        # Build prompt
        prompt = self.prompt_manager.render("risk_analysis", contract_text=text)

        # Execute LLM
        response = await self.llm_client.call(prompt, model="gpt-4o", response_format={"type": "json_object"})

        # Validate output
        result = RiskResult.model_validate_json(response)

        # Cache
        await self.cache.set(cache_key, result.model_dump_json(), ttl=3600)

        return result
```

### 5.4 LLM Client

```python
# llm/client.py

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMClient:
    """OpenAI client with retry, timeout, and cost tracking."""

    def __init__(self, api_key: str, default_model: str = "gpt-4o"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.default_model = default_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def call(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> str:
        start = time.time()
        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        latency_ms = int((time.time() - start) * 1000)

        # Track cost (approximate)
        cost = self._estimate_cost(
            model or self.default_model,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )

        logger.info("LLM call", model=model, latency_ms=latency_ms, cost=cost, tokens=response.usage.total_tokens)

        return response.choices[0].message.content

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = {
            "gpt-4o": {"input": 0.0000025, "output": 0.00001},
            "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
        }
        rate = rates.get(model, rates["gpt-4o"])
        return (prompt_tokens * rate["input"]) + (completion_tokens * rate["output"])
```

### 5.5 Prompt Templates

```jinja
{# llm/templates/risk_analysis.j2 #}
You are a senior contract risk analyst. Analyze the following contract text
and identify all high-risk clauses.

Contract Text:
{{ contract_text }}

For each high-risk clause, respond in JSON format:
{
    "risk_score": <0.0-1.0>,
    "findings": [
        {
            "clause_type": "indemnification|liability|termination|data_privacy|compliance",
            "severity": "critical|high|medium|low",
            "title": "Short title",
            "description": "Detailed explanation",
            "recommendation": "Suggested remediation"
        }
    ]
}

Focus on: uncapped liability, missing DPA, auto-renewal, limitation of liability,
indemnification, termination for convenience, governing law, non-compete.
```

### 5.6 AI Execution Flow (V1)

```
1. Contract processed -> emit ContractProcessed event
2. AI worker picks up event from 'ai' queue
3. Worker loads contract chunks from DB
4. Pipeline orchestrator runs 3 parallel steps:
   a. Risk analysis (LLM call #1)
   b. Clause classification (LLM call #2)
   c. Obligation extraction (LLM call #3)
5. Each step checks cache before LLM call
6. Results validated against JSON schema
7. Results stored in ai_analyses table
8. Findings stored in risk_findings table
9. Emit AIAnalysisCompleted event
10. Workflow engine picks up event, updates workflow status
11. Notification sent to assigned reviewer
```

---

## 6. Search + Vector Implementation

### 6.1 Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │     SEARCH ENGINE (Modular Monolith)         │
                    ├──────────────────────────────────────────────┤
                    │                                              │
  ┌──────────┐      │  ┌──────────┐    ┌──────────┐              │
  │ Query    │──────│─>│  Parser  │───>│  Hybrid  │              │
  │          │      │  │          │    │  Search  │              │
  └──────────┘      │  └──────────┘    └────┬─────┘              │
                    │                        │                    │
                    │              ┌─────────┼─────────┐          │
                    │              │         │         │          │
                    │        ┌─────▼──┐ ┌────▼───┐ ┌──▼──────┐  │
                    │        │Vector  │ │BM25    │ │Metadata │  │
                    │        │Search  │ │Search  │ │Filter   │  │
                    │        │(pgvec) │ │(tsvec) │ │         │  │
                    │        └────┬───┘ └────┬───┘ └────┬─────┘  │
                    │             │          │          │        │
                    │        ┌────▼──────────▼──────────▼────┐   │
                    │        │      Reciprocal Rank Fusion   │   │
                    │        │  (RRF: k=60, vector=0.7,      │   │
                    │        │         bm25=0.3)             │   │
                    │        └──────────────┬───────────────┘   │
                    │                       │                   │
                    │        ┌──────────────▼───────────────┐   │
                    │        │      Result Enrichment       │   │
                    │        │  (highlighting, summaries)   │   │
                    │        └──────────────────────────────┘   │
                    └──────────────────────────────────────────────┘
```

### 6.2 Hybrid Search Implementation

```python
# domains/search/engine/hybrid.py

from dataclasses import dataclass
import math

@dataclass
class HybridSearchEngine:
    """BM25 + Vector fusion with Reciprocal Rank Fusion."""

    K: int = 60  # RRF constant
    VECTOR_WEIGHT: float = 0.7
    BM25_WEIGHT: float = 0.3

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResults:
        # 1. Embed query for vector search
        query_vector = await embedder.embed(query)

        # 2. Run vector search
        vector_results = await self._vector_search(
            query_vector, tenant_id, filters, limit=50
        )

        # 3. Run BM25 search
        bm25_results = await self._bm25_search(
            query, tenant_id, filters, limit=50
        )

        # 4. Fuse with RRF
        fused = self._rrf_fusion(vector_results, bm25_results)

        # 5. Paginate
        total = len(fused)
        start = (page - 1) * page_size
        paginated = fused[start:start + page_size]

        return SearchResults(
            results=paginated,
            total=total,
            page=page,
            page_size=page_size,
        )

    def _rrf_fusion(self, vector: list, bm25: list) -> list:
        scores: dict[str, float] = {}
        for rank, doc in enumerate(vector):
            scores[doc.id] = self.VECTOR_WEIGHT / (self.K + rank)
        for rank, doc in enumerate(bm25):
            scores[doc.id] = scores.get(doc.id, 0) + self.BM25_WEIGHT / (self.K + rank)
        return sorted(
            [ScoredResult(id=k, score=v) for k, v in scores.items()],
            key=lambda x: x.score, reverse=True,
        )

    async def _vector_search(self, query_vector, tenant_id, filters, limit):
        # pgvector: cosine distance
        sql = """
            SELECT chunk_id, contract_id, text, 1 - (embedding <=> :query) AS score
            FROM chunks
            WHERE tenant_id = :tenant_id
              AND embedding IS NOT NULL
              AND is_active = TRUE
            ORDER BY embedding <=> :query
            LIMIT :limit
        """
        rows = await self.db.fetch_all(sql, {
            "query": query_vector, "tenant_id": tenant_id, "limit": limit,
        })
        return [VectorResult(id=r["chunk_id"], text=r["text"], score=r["score"]) for r in rows]

    async def _bm25_search(self, query, tenant_id, filters, limit):
        # PostgreSQL full-text search
        sql = """
            SELECT chunk_id, contract_id, text,
                   ts_rank(to_tsvector('english', text), plainto_tsquery('english', :query)) AS score
            FROM chunks
            WHERE tenant_id = :tenant_id
              AND to_tsvector('english', text) @@ plainto_tsquery('english', :query)
              AND is_active = TRUE
            ORDER BY score DESC
            LIMIT :limit
        """
        rows = await self.db.fetch_all(sql, {
            "query": query, "tenant_id": tenant_id, "limit": limit,
        })
        return [BM25Result(id=r["chunk_id"], text=r["text"], score=r["score"]) for r in rows]
```

### 6.3 Chunking Strategy

```python
# domains/ai/chunking/semantic.py

class SemanticChunker:
    """Chunk text at semantic boundaries (paragraphs, sections)."""

    MAX_CHUNK_SIZE = 512    # tokens
    MIN_CHUNK_SIZE = 128    # tokens
    OVERLAP_SIZE = 64       # tokens

    def chunk(self, text: str) -> list[Chunk]:
        # 1. Split by paragraphs
        paragraphs = text.split('\n\n')

        chunks = []
        current = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            if current_tokens + para_tokens > self.MAX_CHUNK_SIZE and current:
                # Save current chunk
                chunk_text = '\n\n'.join(current)
                chunks.append(Chunk(
                    text=chunk_text,
                    token_count=current_tokens,
                    start_char=len(''.join(current)),
                ))
                # Start new chunk with overlap
                overlap = self._get_overlap(current, self.OVERLAP_SIZE)
                current = [overlap] if overlap else []
                current_tokens = self._count_tokens(overlap) if overlap else 0

            current.append(para)
            current_tokens += para_tokens

        # Last chunk
        if current:
            chunks.append(Chunk(
                text='\n\n'.join(current),
                token_count=current_tokens,
            ))

        return chunks

    def _count_tokens(self, text: str) -> int:
        # Approximate: 4 chars per token
        return len(text) // 4
```

### 6.4 Embedding Generation

```python
# domains/ai/embedding/embedder.py

class Embedder:
    """OpenAI embedding client with batching and caching."""

    MODEL = "text-embedding-3-large"
    DIMENSION = 1536
    BATCH_SIZE = 20

    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.cache = RedisCache()

    async def embed(self, text: str) -> list[float]:
        # Check cache
        cache_key = f"embed:{hashlib.sha256(text.encode()).hexdigest()}"
        cached = await self.cache.get(cache_key)
        if cached:
            return json.loads(cached)

        response = await self.client.embeddings.create(
            model=self.MODEL,
            input=text,
            dimensions=self.DIMENSION,
        )
        embedding = response.data[0].embedding

        await self.cache.set(cache_key, json.dumps(embedding), ttl=86400)
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results = []
        for batch in self._batched(texts, self.BATCH_SIZE):
            response = await self.client.embeddings.create(
                model=self.MODEL,
                input=batch,
                dimensions=self.DIMENSION,
            )
            results.extend([r.embedding for r in response.data])
        return results
```

### 6.5 Vector Index Maintenance

```python
# workers/maintenance_worker.py

@celery_app.task(name="reindex_tenant_vectors")
def reindex_tenant_vectors(tenant_id: str):
    """Rebuild ivfflat index for a tenant's chunk partition."""
    # Determine partition for this tenant
    partition = get_tenant_partition(tenant_id)
    sql = f"""
        REINDEX INDEX idx_{partition}_embedding;
        ANALYZE {partition};
    """
    db.execute(sql)

@celery_app.task(name="vacuum_chunks")
def vacuum_chunks():
    """Weekly VACUUM on chunks table to reclaim space."""
    db.execute("VACUUM ANALYZE chunks;")
```

### 6.6 Search Performance Targets

```
p50 latency:  < 200ms  (simple keyword search)
p95 latency:  < 500ms  (hybrid search)
p99 latency:  < 2s     (hybrid search with large result sets)
Recall@10:    > 0.85   (fraction of relevant results in top 10)
Index freshness: < 5min (time from chunk creation to searchable)
```

---

## 7. Frontend Engineering System

### 7.1 Folder Structure

```
frontend/
├── app/
│   ├── layout.tsx                    # Root layout (providers, fonts)
│   ├── page.tsx                      # Login / redirect
│   ├── (dashboard)/                  # Authenticated routes
│   │   ├── layout.tsx                # DashboardLayout (sidebar + topnav)
│   │   ├── page.tsx                  # Redirect to /portfolio
│   │   ├── portfolio/page.tsx
│   │   ├── contracts/page.tsx
│   │   ├── contracts/[id]/page.tsx
│   │   ├── review/page.tsx
│   │   ├── workflows/page.tsx
│   │   ├── search/page.tsx
│   │   ├── settings/page.tsx
│   │   └── admin/page.tsx
│   └── api/auth/[...auth0]/route.ts  # Auth callback
│
├── components/
│   ├── ui/                           # Design system (shadcn/ui)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── table.tsx
│   │   ├── dialog.tsx
│   │   ├── badge.tsx
│   │   ├── kpi-card.tsx
│   │   ├── data-table.tsx
│   │   ├── filter-bar.tsx
│   │   └── search-bar.tsx
│   │
│   ├── layout/                       # Layout components
│   │   ├── sidebar.tsx
│   │   ├── topnav.tsx
│   │   └── workspace-layout.tsx
│   │
│   ├── features/                     # Feature modules
│   │   ├── contracts/
│   │   │   ├── contract-table.tsx
│   │   │   ├── contract-detail.tsx
│   │   │   ├── contract-upload.tsx
│   │   │   └── hooks/use-contracts.ts
│   │   ├── review/
│   │   │   ├── review-queue.tsx
│   │   │   ├── clause-viewer.tsx
│   │   │   ├── ai-findings.tsx
│   │   │   └── hooks/use-review.ts
│   │   ├── workflows/
│   │   │   ├── workflow-list.tsx
│   │   │   ├── approval-dialog.tsx
│   │   │   └── hooks/use-workflows.ts
│   │   ├── search/
│   │   │   ├── search-results.tsx
│   │   │   ├── search-filters.tsx
│   │   │   └── hooks/use-search.ts
│   │   └── admin/
│   │       ├── user-table.tsx
│   │       └── tenant-settings.tsx
│   │
│   └── shared/                       # Shared components
│       ├── loading-skeleton.tsx
│       ├── error-boundary.tsx
│       ├── empty-state.tsx
│       └── confirm-dialog.tsx
│
├── lib/
│   ├── api/                          # API client
│   │   ├── client.ts                 # Axios instance with auth
│   │   ├── contracts.ts
│   │   ├── workflows.ts
│   │   ├── search.ts
│   │   └── ai.ts
│   ├── hooks/                        # React Query hooks
│   │   ├── use-contracts.ts
│   │   ├── use-workflows.ts
│   │   ├── use-search.ts
│   │   └── use-notifications.ts
│   ├── stores/                       # Zustand stores
│   │   ├── ui-store.ts               # Sidebar, theme
│   │   └── auth-store.ts             # User, token
│   └── utils/
│       ├── cn.ts                     # clsx + tailwind-merge
│       ├── formatters.ts
│       └── validators.ts
│
├── __tests__/
├── Dockerfile
├── next.config.js
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

### 7.2 API Client

```typescript
// lib/api/client.ts

import axios, { AxiosError } from 'axios';
import { useAuthStore } from '@/stores/auth-store';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach auth token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### 7.3 React Query Hooks

```typescript
// lib/hooks/use-contracts.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api/client';

interface ContractFilters {
  status?: string;
  contract_type?: string;
  page?: number;
  page_size?: number;
}

export function useContracts(filters: ContractFilters) {
  return useQuery({
    queryKey: ['contracts', filters],
    queryFn: () => apiClient.get('/contracts', { params: filters }).then(r => r.data),
    staleTime: 30_000,
    keepPreviousData: true,
  });
}

export function useContract(contractId: string) {
  return useQuery({
    queryKey: ['contract', contractId],
    queryFn: () => apiClient.get(`/contracts/${contractId}`).then(r => r.data),
    enabled: !!contractId,
  });
}

export function useUploadContract() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post('/contracts', formData).then(r => r.data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
    },
  });
}
```

### 7.4 AI Streaming UX

```typescript
// components/features/review/ai-findings.tsx

import { useState } from 'react';

export function AIAnalysisStream({ contractId }: { contractId: string }) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'streaming' | 'complete'>('idle');
  const [findings, setFindings] = useState<Finding[]>([]);

  const startAnalysis = async () => {
    setStatus('loading');

    const response = await fetch(`/api/v1/ai/analyze/${contractId}`, {
      method: 'POST',
    });

    if (!response.body) return;

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    setStatus('streaming');

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      // Parse SSE event
      const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
      for (const line of lines) {
        const data = JSON.parse(line.slice(6));
        if (data.type === 'finding') {
          setFindings(prev => [...prev, data.payload]);
        }
      }
    }

    setStatus('complete');
  };

  return (
    <div>
      <button onClick={startAnalysis} disabled={status === 'loading' || status === 'streaming'}>
        {status === 'idle' && 'Run AI Analysis'}
        {status === 'loading' && 'Starting...'}
        {status === 'streaming' && `Analyzing... ${findings.length} findings`}
        {status === 'complete' && 'Re-analyze'}
      </button>
      {findings.map(f => (
        <FindingCard key={f.id} finding={f} />
      ))}
    </div>
  );
}
```

### 7.5 State Management

```typescript
// lib/stores/ui-store.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      theme: 'light',
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'ui-storage' }
  )
);
```

---

## 8. Infrastructure + DevOps Blueprint

### 8.1 Docker Compose (Development)

```yaml
# docker-compose.yml

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: contract_risk_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: ./api
    ports: ["8000:8000"]
    volumes: [./api:/app]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: postgresql+asyncpg://dev_user:dev_password@postgres:5432/contract_risk_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ENVIRONMENT: development
    depends_on: [postgres, redis]

  worker:
    build: ./api
    volumes: [./api:/app]
    command: celery -A workers.celery_app worker --loglevel=info --concurrency=2
    environment:
      DATABASE_URL: postgresql+asyncpg://dev_user:dev_password@postgres:5432/contract_risk_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on: [postgres, redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    volumes: [./frontend:/app, /app/node_modules]
    command: npm run dev
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1
    depends_on: [api]

volumes:
  postgres_data:
  redis_data:
```

### 8.2 Production Kubernetes Manifests

```yaml
# k8s/api-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: contractrisk
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: ${ECR_REGISTRY}/api:${IMAGE_TAG}
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: url
            - name: REDIS_URL
              value: redis://redis:6379/0
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: openai
                  key: api-key
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

### 8.3 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml

name: CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install ruff mypy
      - run: ruff check api/
      - run: mypy api/ --strict

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r api/requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov
      - run: pytest api/tests/ --cov=api/app --cov-report=xml
      - uses: codecov/codecov-action@v4

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - run: |
          docker build -t api:${{ github.sha }} ./api
          docker tag api:${{ github.sha }} ${{ secrets.ECR }}/api:${{ github.sha }}
          docker push ${{ secrets.ECR }}/api:${{ github.sha }}
```

### 8.4 Observability Stack

```yaml
# docker-compose.observability.yml (development)

services:
  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]
    volumes: [./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml]

  grafana:
    image: grafana/grafana
    ports: ["3001:3000"]
    volumes: [grafana_data:/var/lib/grafana]

  tempo:
    image: grafana/tempo
    ports: ["4317:4317"]  # OTLP gRPC
    command: ["-config.file=/etc/tempo.yaml"]

  loki:
    image: grafana/loki
    ports: ["3100:3100"]
    command: ["-config.file=/etc/loki/local-config.yaml"]
```

### 8.5 Environment Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ENVIRONMENT STRATEGY                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  local:          Docker Compose, hot reload, seed data                  │
│                  Developer machine                                      │
│                                                                         │
│  dev:            Single replica, shared DB, automatic deploys           │
│                  GitHub Actions on push to develop                      │
│                                                                         │
│  staging:        2 replicas, staging DB, manual deploys                 │
│                  QA validation, integration tests                        │
│                                                                         │
│  prod:           3+ replicas, production DB, blue/green deploys        │
│                  Manual approval gate, canary 10% → 100%               │
│                                                                         │
│  DR:             Standby region, read replica, cold standby             │
│                  Activated on failover (RTO: 15min, RPO: 5min)          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Roadmap

### 9.1 Month 1-2: Foundation

```
Sprint 1-2: Project Setup + Auth + Tenant
  [ ] Initialize monorepo structure
  [ ] Docker Compose dev environment
  [ ] CI/CD pipeline (lint → test → build)
  [ ] PostgreSQL schema + Alembic migrations
  [ ] Auth module (JWT + OIDC)
  [ ] Tenant isolation (RLS)
  [ ] RBAC (admin, analyst, viewer)
  [ ] User management API

Sprint 3-4: Contract Upload + Ingestion
  [ ] Contract upload API (S3)
  [ ] Contract CRUD
  [ ] OCR pipeline (PyMuPDF)
  [ ] Text extraction
  [ ] Semantic chunking
  [ ] Embedding generation (OpenAI)
  [ ] Celery worker setup
  [ ] Audit logging

Milestone: User can upload a PDF and see it processed into chunks
```

### 9.2 Month 3-4: AI + Search

```
Sprint 5-6: AI Analysis
  [ ] AI pipeline orchestrator
  [ ] Risk analysis prompt + LLM integration
  [ ] Clause classification
  [ ] Obligation extraction
  [ ] AI findings storage
  [ ] AI response cache (Redis)
  [ ] Retry + error handling

Sprint 7-8: Search + Vector
  [ ] pgvector index setup
  [ ] Hybrid search (BM25 + vector)
  [ ] Search API
  [ ] Metadata filtering
  [ ] Search UI
  [ ] Vector maintenance jobs

Milestone: User can search contracts and get AI risk analysis
```

### 9.3 Month 5-6: Workflows + UI

```
Sprint 9-10: Workflow Engine
  [ ] Workflow CRUD
  [ ] Single-step approval workflow
  [ ] SLA tracking
  [ ] Escalation
  [ ] Workflow API
  [ ] Notification system (in-app)

Sprint 11-12: Frontend + Integration
  [ ] Contract review UI
  [ ] AI findings display
  [ ] Workflow approval UI
  [ ] Dashboard KPIs
  [ ] Admin UI (user management)
  [ ] Export (PDF)

Milestone: Complete V1 pilot — end-to-end contract review workflow
```

### 9.4 Month 6-12: Hardening + Scale

```
Sprint 13-16: Production Hardening
  [ ] Load testing + optimization
  [ ] Index tuning
  [ ] Query optimization
  [ ] Caching strategy
  [ ] Error budget monitoring
  [ ] Production monitoring (Grafana dashboards)
  [ ] Alerting (PagerDuty)
  [ ] Security audit
  [ ] Penetration testing

Sprint 17-20: Post-Pilot Features
  [ ] Multi-step workflows
  [ ] Redline suggestions
  [ ] Email notifications
  [ ] Webhook integrations
  [ ] API key auth
  [ ] Comment/annotation system
  [ ] Reporting

Sprint 21-24: Scale Readiness
  [ ] Read replica setup
  [ ] Connection pooling tuning
  [ ] Archival jobs
  [ ] Backup/restore testing
  [ ] DR drill
  [ ] Runbook creation
  [ ] Team training
```

### 9.5 Team Structure Assumptions

```
V1 Team (Months 1-6):
  2-3 Backend engineers (Python/FastAPI)
  1-2 Frontend engineers (React/TypeScript)
  1 DevOps/Infrastructure engineer
  1 AI/ML engineer
  1 Product manager
  ────────────────────────────
  6-8 total

Post-V1 Team (Months 6-12):
  3-4 Backend engineers
  2-3 Frontend engineers
  1 DevOps engineer
  1 AI engineer
  1 QA engineer
  1 Product manager
  ────────────────────────────
  9-12 total
```

### 9.6 Critical Path Analysis

```
CRITICAL PATH (longest dependent chain):

Auth + Tenant → Contract Upload → OCR Pipeline → Chunking
    → Embedding → Vector Index → Search API
    → AI Analysis → Findings → Workflow → Notifications → UI

PARALLELIZABLE:
  - Frontend development (can start with mock API)
  - Audit logging (independent of most features)
  - Infrastructure setup (independent of application code)

RISK AREAS:
  1. OCR quality on scanned PDFs (fallback: Tesseract)
  2. OpenAI API latency/cost (mitigation: caching, batching)
  3. pgvector index build time (mitigation: background job)
  4. Embedding dimension cost (mitigation: use text-embedding-3-small for dev)
```

---

## 10. Engineering Governance Rules

### 10.1 Architecture Review Rules

```
1. ANY new table requires architecture review
2. ANY new external API integration requires security review
3. ANY new AI prompt requires safety review
4. ANY schema change requires migration plan
5. ANY breaking API change requires deprecation notice
6. ANY new dependency requires license compliance check
7. ANY new background job requires idempotency design
8. ANY new event type requires schema definition
```

### 10.2 Migration Governance

```
1. All migrations MUST be reversible (upgrade + downgrade)
2. Migrations MUST NOT lock tables for more than 5 seconds
3. Large table migrations use expand/contract pattern:
   a. Add new column (NULLABLE)
   b. Backfill in background job
   c. Make NOT NULL
   d. Drop old column (separate deployment)
4. Migration review checklist:
   [ ] Rollback script exists
   [ ] No long-running locks
   [ ] Index created (if needed)
   [ ] RLS policy updated (if tenant table)
   [ ] Audit logging updated (if entity table)
```

### 10.3 Code Review Standards

```
1. Every PR requires:
   [ ] At least 1 approval from domain expert
   [ ] All CI checks passing
   [ ] Test coverage > 80% for new code
   [ ] No lint errors (ruff strict)
   [ ] No type errors (mypy strict)
   [ ] Migration reviewed (if schema change)

2. PR size limit: 400 lines (exceptions for generated code)
3. PR response time: < 4 hours during business hours
4. No direct pushes to main/develop (branch + PR only)
```

### 10.4 Forbidden Patterns

```
❌ Circular imports between domain modules
❌ Direct DB access from routers (bypassing service layer)
❌ JSONB for queryable or sortable fields
❌ Synchronous blocking calls in async endpoints
❌ Hardcoded secrets in code or config files
❌ N+1 queries in REST endpoints
❌ SELECT * in production queries
❌ Unbounded pagination (no limit)
❌ Storing raw passwords (hash + salt required)
❌ Client-side only auth checks (server-side enforcement required)
```

### 10.5 AI Safety Requirements

```
1. Every prompt template is version-controlled
2. Every LLM output is validated against JSON schema
3. Every AI action is logged (who requested, what model, what cost)
4. Human approval required for: contract approval, financial decisions
5. AI confidence scores displayed alongside all AI outputs
6. Hallucination disclaimer shown for all AI-generated content
7. Rate limiting on AI endpoints (per tenant, per user)
8. Timeout handling (max 60s for sync, 300s for async)
9. Fallback model configured for each AI operation
10. PII detection on AI inputs and outputs
```

### 10.6 Observability Requirements

```
1. EVERY request has a correlation_id (propagated across services)
2. EVERY external API call is traced (OpenTelemetry span)
3. EVERY database query is logged (slow query threshold: 500ms)
4. EVERY AI call is logged (model, tokens, latency, cost)
5. EVERY error has a stack trace and request context
6. Metrics exported for: request rate, latency, error rate, queue depth
7. Dashboards for: API health, worker health, AI cost, search latency
8. Alerts for: error rate > 5%, latency p99 > 5s, queue depth > 1000
```

### 10.7 Testing Requirements

```
Coverage targets:
  Unit tests:       > 80% (service layer, business logic)
  Integration:      > 60% (API endpoints, database)
  E2E:              Critical paths only (upload → process → review → approve)

Required tests by layer:
  Router:     Status codes, response format, auth enforcement, validation errors
  Service:    Business logic, event emission, error conditions, edge cases
  Repository: CRUD operations, filtering, pagination, tenant isolation
  Worker:     Task execution, retry logic, error handling
  AI:         Prompt rendering, output validation, cache behavior
```

### 10.8 Performance Requirements

```
API:
  p50 latency:  < 200ms  (CRUD endpoints)
  p95 latency:  < 1s     (search endpoints)
  p99 latency:  < 5s     (any endpoint)
  Throughput:   > 100 req/s per instance

Search:
  p50 latency:  < 200ms  (keyword)
  p95 latency:  < 500ms  (hybrid)
  Recall@10:    > 0.85

AI:
  p95 latency:  < 30s    (full analysis)
  p95 latency:  < 5s     (single classification)
  Cost:         < $0.10  (per analysis)
  Cache hit:    > 20%    (after warmup)

Database:
  Connection pool: 20 per instance
  Max connections: 200 (RDS)
  Slow query:      > 500ms (logged)
  Dead connection: < 5s (detected)
```
