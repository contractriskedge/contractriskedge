# ContractRiskEdge — Enterprise Implementation Blueprint & Engineering Execution Plan

## Fortune 500 AI-Native Contract Intelligence Operating System

---

## Table of Contents

1. [Repository Architecture](#1-repository-architecture)
2. [Backend Implementation Blueprint](#2-backend-implementation-blueprint)
3. [Frontend Implementation Blueprint](#3-frontend-implementation-blueprint)
4. [Database Implementation Strategy](#4-database-implementation-strategy)
5. [AI Implementation Strategy](#5-ai-implementation-strategy)
6. [Search Implementation Strategy](#6-search-implementation-strategy)
7. [Worker & Job Execution Strategy](#7-worker--job-execution-strategy)
8. [API Implementation Standards](#8-api-implementation-standards)
9. [Event System Implementation](#9-event-system-implementation)
10. [Security Implementation](#10-security-implementation)
11. [Observability Implementation](#11-observability-implementation)
12. [Testing Strategy](#12-testing-strategy)
13. [CI/CD Implementation](#13-cicd-implementation)
14. [Developer Experience](#14-developer-experience)
15. [Engineering Governance](#15-engineering-governance)
16. [Implementation Roadmap](#16-implementation-roadmap)

---

## 1. Repository Architecture

### 1.1 Monorepo Structure

```
contractriskedge/
├── .github/
│   ├── workflows/
│   │   ├── ci-backend.yml
│   │   ├── ci-frontend.yml
│   │   ├── ci-ai.yml
│   │   ├── deploy-staging.yml
│   │   ├── deploy-production.yml
│   │   └── lint.yml
│   ├── CODEOWNERS
│   └── pull_request_template.md
│
├── api/                              # MODULAR MONOLITH — Core Business
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory
│   │   ├── config.py                 # Pydantic settings
│   │   ├── dependencies.py           # FastAPI dependency injection
│   │   ├── lifecycle.py              # Startup/shutdown events
│   │   │
│   │   ├── common/                   # Shared across all domains
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Base model, repository, service
│   │   │   ├── pagination.py
│   │   │   ├── response.py           # Standard response envelope
│   │   │   ├── exceptions.py         # Domain exceptions hierarchy
│   │   │   ├── error_handlers.py     # FastAPI exception handlers
│   │   │   ├── middleware/
│   │   │   │   ├── auth.py
│   │   │   │   ├── tenant.py
│   │   │   │   ├── audit.py
│   │   │   │   ├── rate_limit.py
│   │   │   │   ├── request_id.py
│   │   │   │   └── logging.py
│   │   │   ├── database/
│   │   │   │   ├── session.py        # Async session factory
│   │   │   │   ├── repositories.py   # Base repository
│   │   │   │   ├── uow.py            # Unit of work pattern
│   │   │   │   └── migrations/       # Alembic
│   │   │   ├── events/
│   │   │   │   ├── bus.py            # Internal event bus
│   │   │   │   ├── dispatcher.py
│   │   │   │   └── handlers.py
│   │   │   ├── security/
│   │   │   │   ├── auth.py           # JWT validation
│   │   │   │   ├── rbac.py           # Permission checking
│   │   │   │   └── encryption.py
│   │   │   ├── logging/
│   │   │   │   ├── logger.py         # structlog config
│   │   │   │   └── correlation.py
│   │   │   ├── telemetry/
│   │   │   │   ├── tracer.py         # OpenTelemetry
│   │   │   │   ├── metrics.py
│   │   │   │   └── instruments.py
│   │   │   └── utils/
│   │   │       ├── date_utils.py
│   │   │       ├── string_utils.py
│   │   │       └── validators.py
│   │   │
│   │   ├── domains/                   # DOMAIN-DRIVEN MODULES
│   │   │   ├── contracts/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── schemas.py         # Pydantic request/response
│   │   │   │   ├── models.py          # SQLAlchemy models
│   │   │   │   ├── repository.py      # Data access
│   │   │   │   ├── service.py         # Business logic
│   │   │   │   ├── router.py          # FastAPI routes
│   │   │   │   ├── events.py          # Domain events
│   │   │   │   ├── exceptions.py
│   │   │   │   └── tests/
│   │   │   │       ├── test_router.py
│   │   │   │       ├── test_service.py
│   │   │   │       └── test_repository.py
│   │   │   │
│   │   │   ├── clauses/               # Same structure
│   │   │   ├── vendors/
│   │   │   ├── workflows/
│   │   │   ├── compliance/
│   │   │   ├── obligations/
│   │   │   ├── negotiations/
│   │   │   ├── redlines/
│   │   │   ├── renewals/
│   │   │   ├── playbooks/
│   │   │   ├── benchmarks/
│   │   │   ├── notifications/
│   │   │   ├── analytics/
│   │   │   ├── audit/
│   │   │   └── teams/
│   │   │
│   │   └── integrations/              # External integrations
│   │       ├── auth0/
│   │       ├── s3/
│   │       ├── ocr/
│   │       └── webhooks/
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   ├── versions/
│   │   └── script.py.mako
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── factories/                 # Test factories (factory_boy)
│   │   ├── fixtures/                  # JSON fixtures
│   │   ├── integration/
│   │   └── e2e/
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── pytest.ini
│
├── ai-runtime/                        # SEPARATE AI RUNTIME
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # gRPC + HTTP server
│   │   ├── config.py
│   │   │
│   │   ├── agents/                    # LangGraph agents
│   │   │   ├── base.py
│   │   │   ├── risk_agent.py
│   │   │   ├── clause_agent.py
│   │   │   ├── obligation_agent.py
│   │   │   ├── redline_agent.py
│   │   │   ├── negotiation_agent.py
│   │   │   └── compliance_agent.py
│   │   │
│   │   ├── pipelines/                 # RAG pipelines
│   │   │   ├── rag_pipeline.py
│   │   │   ├── chunking.py
│   │   │   ├── embedding.py
│   │   │   └── reranking.py
│   │   │
│   │   ├── models/                    # AI model management
│   │   │   ├── router.py              # Model router
│   │   │   ├── registry.py
│   │   │   └── fallback.py
│   │   │
│   │   ├── prompts/                   # Prompt management
│   │   │   ├── manager.py
│   │   │   ├── registry.py
│   │   │   ├── templates/
│   │   │   └── versions/
│   │   │
│   │   ├── tools/                     # AI tool calling
│   │   │   ├── registry.py
│   │   │   ├── contract_tools.py
│   │   │   ├── search_tools.py
│   │   │   ├── workflow_tools.py
│   │   │   └── vendor_tools.py
│   │   │
│   │   ├── evaluation/                # AI eval framework
│   │   │   ├── runner.py
│   │   │   ├── metrics.py
│   │   │   ├── datasets/
│   │   │   └── reports/
│   │   │
│   │   ├── telemetry/
│   │   │   ├── tracer.py
│   │   │   ├── cost_tracker.py
│   │   │   └── token_counter.py
│   │   │
│   │   └── cache/
│   │       ├── llm_cache.py
│   │       └── embedding_cache.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── worker-runtime/                     # SEPARATE WORKER RUNTIME
│   ├── app/
│   │   ├── __init__.py
│   │   ├── celery_app.py              # Celery application
│   │   ├── config.py
│   │   │
│   │   ├── tasks/                     # Task definitions
│   │   │   ├── ingestion/
│   │   │   │   ├── process_document.py
│   │   │   │   ├── extract_text.py
│   │   │   │   └── ocr_fallback.py
│   │   │   ├── ai/
│   │   │   │   ├── analyze_contract.py
│   │   │   │   ├── classify_clauses.py
│   │   │   │   └── redline_generation.py
│   │   │   ├── workflow/
│   │   │   │   ├── execute_step.py
│   │   │   │   └── sla_check.py
│   │   │   ├── notification/
│   │   │   │   ├── send_email.py
│   │   │   │   └── send_webhook.py
│   │   │   ├── analytics/
│   │   │   │   ├── aggregate_kpis.py
│   │   │   │   └── generate_report.py
│   │   │   └── maintenance/
│   │   │       ├── reindex_search.py
│   │   │       └── archive_old_data.py
│   │   │
│   │   ├── beat_schedule.py            # Celery Beat schedule
│   │   └── signals.py                  # Celery signal handlers
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── search-runtime/                     # SEPARATE SEARCH RUNTIME
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI search service
│   │   ├── config.py
│   │   │
│   │   ├── engine/
│   │   │   ├── hybrid.py              # BM25 + vector fusion
│   │   │   ├── vector.py              # pgvector queries
│   │   │   ├── fulltext.py            # PostgreSQL FTS
│   │   │   └── reranker.py            # Cross-encoder reranking
│   │   │
│   │   ├── indexing/
│   │   │   ├── indexer.py
│   │   │   ├── chunker.py
│   │   │   └── embedder.py
│   │   │
│   │   ├── routes/
│   │   │   ├── search.py
│   │   │   ├── suggest.py
│   │   │   └── saved.py
│   │   │
│   │   └── cache/
│   │       └── search_cache.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── packages/                           # SHARED PACKAGES
│   ├── shared-sdk/                     # Internal Python SDK
│   │   ├── src/
│   │   │   ├── sdk/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py          # HTTP client for internal services
│   │   │   │   ├── schemas/           # Shared Pydantic models
│   │   │   │   ├── events/            # Event type definitions
│   │   │   │   ├── exceptions/
│   │   │   │   └── types/             # Shared enums, type aliases
│   │   │   └── ...
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── shared-types/                   # Shared TypeScript types
│       ├── src/
│       │   ├── types/
│       │   ├── schemas/
│       │   └── constants/
│       ├── package.json
│       └── tsconfig.json
│
├── frontend/                           # Next.js APPLICATION
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   └── tsconfig.json
│
├── infra/                              # INFRASTRUCTURE
│   ├── terraform/
│   │   ├── modules/
│   │   ├── environments/
│   │   └── main.tf
│   ├── kubernetes/
│   │   ├── api-deployment.yaml
│   │   ├── ai-deployment.yaml
│   │   ├── worker-deployment.yaml
│   │   ├── search-deployment.yaml
│   │   └── frontend-deployment.yaml
│   ├── docker-compose.yml
│   └── monitoring/
│       ├── grafana-dashboards/
│       └── prometheus-rules.yml
│
├── docs/                               # DOCUMENTATION
│   ├── architecture/
│   ├── api/
│   ├── adr/
│   ├── runbooks/
│   └── onboarding/
│
├── scripts/                            # DEVELOPMENT SCRIPTS
│   ├── setup.sh
│   ├── seed.sh
│   ├── migrate.sh
│   └── dev.sh
│
├── .github/
├── .env.example
├── .pre-commit-config.yaml
├── .editorconfig
├── .gitignore
├── Makefile
├── README.md
└── CONTRIBUTING.md
```

### 1.2 Runtime Separation Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ContractRiskEdge Platform                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  MODULAR MONOLITH (api/)                                        │   │
│  │  ──────────────────────                                         │   │
│  │  • contracts  • clauses   • vendors    • workflows              │   │
│  │  • compliance • obligations • renewals • negotiations           │   │
│  │  • redlines   • playbooks  • benchmarks • notifications         │   │
│  │  • analytics  • audit     • teams      • webhooks               │   │
│  │                                                                 │   │
│  │  Single FastAPI process. Domain modules communicate via         │   │
│  │  in-memory event bus. Shared database. Shared middleware.       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  AI RUNTIME          │  │  WORKER RUNTIME  │  │  SEARCH RUNTIME  │  │
│  │  ───────────         │  │  ─────────────── │  │  ─────────────── │  │
│  │  Separate process    │  │  Celery workers  │  │  Separate process│  │
│  │  gRPC + HTTP         │  │  Queue consumer  │  │  Read-heavy API  │  │
│  │  LangGraph agents    │  │  Batch processor │  │  Hybrid search   │  │
│  │  LLM orchestration   │  │  Cron scheduler │  │  Vector + FTS    │  │
│  │  Prompt management   │  │  Webhook sender  │  │  Re-ranking      │  │
│  │  Model routing       │  │  Email sender    │  │  Search cache    │  │
│  └──────────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                         │
│  Communication: HTTP/gRPC (sync) + Redis Pub/Sub (async)               │
│  Database: Shared PostgreSQL (modular monolith owns schema)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Dependency Rules

```
api/ (modular monolith):
    └── depends on: packages/shared-sdk, PostgreSQL, Redis
    └── no dependency on: ai-runtime, worker-runtime, search-runtime

ai-runtime:
    └── depends on: packages/shared-sdk, PostgreSQL (read-only), Redis
    └── no dependency on: api/ domains directly

worker-runtime:
    └── depends on: packages/shared-sdk, PostgreSQL, Redis
    └── no dependency on: api/ domains directly

search-runtime:
    └── depends on: packages/shared-sdk, PostgreSQL (read-only), Redis
    └── no dependency on: api/ domains directly

frontend:
    └── depends on: packages/shared-types, api/ (HTTP)
    └── no dependency on: ai-runtime, worker-runtime, search-runtime directly
```

---

## 2. Backend Implementation Blueprint

### 2.1 Modular Monolith Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  api/app/main.py — FastAPI Application Factory                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  def create_app() -> FastAPI:                                          │
│      app = FastAPI(lifespan=lifespan)                                  │
│      add_middleware(app)                                                │
│      register_exception_handlers(app)                                  │
│      register_routers(app)  # Auto-discover domains/*/router.py        │
│      return app                                                        │
│                                                                         │
│  Router auto-discovery:                                                 │
│      for domain in scan_domains("app/domains"):                        │
│          app.include_router(domain.router, prefix="/api/v1")           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Domain Module Template

Every domain module follows this exact structure:

```
domains/{domain}/
├── __init__.py          # Re-exports: router, schemas, models
├── schemas.py           # Pydantic: request/response DTOs
├── models.py            # SQLAlchemy: ORM models
├── repository.py        # Data access: CRUD + queries
├── service.py           # Business logic: orchestration
├── router.py            # FastAPI: route definitions
├── events.py            # Domain events (pydantic models)
├── exceptions.py        # Domain-specific exceptions
└── tests/
    ├── test_router.py
    ├── test_service.py
    └── test_repository.py
```

### 2.3 Router/Service/Repository Pattern

```
                    ┌─────────────┐
                    │   Router    │  ← FastAPI routes, validation, auth
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Service   │  ← Business logic, orchestration, events
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Repository  │  ← Data access, queries, raw SQL
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Database   │  ← PostgreSQL
                    └─────────────┘
```

**Rules:**
- Router NEVER contains business logic — only validation + response formatting
- Service NEVER contains SQL — only business rules + event emission
- Repository NEVER raises HTTP exceptions — only domain exceptions
- Dependencies flow: Router → Service → Repository
- Services are stateless — all state in DB or passed as arguments

### 2.4 Dependency Injection Strategy

```python
# app/dependencies.py

from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db(request: Request) -> AsyncSession:
    """Yield a database session with automatic rollback on error."""
    async with request.app.state.db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_user(request: Request) -> UserContext:
    """Extract authenticated user from request state (set by auth middleware)."""
    return request.state.user

async def get_tenant_id(request: Request) -> str:
    """Extract tenant ID from request state."""
    return request.state.tenant_id

# Domain-specific dependencies
def get_contract_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> ContractService:
    return ContractService(
        repository=ContractRepository(db),
        event_bus=EventBus(),
        user=user,
        tenant_id=tenant_id,
    )
```

### 2.5 Router Pattern

```python
# domains/contracts/router.py

from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/contracts", tags=["Contracts"])

@router.get("/", response_model=PaginatedResponse[ContractSummary])
async def list_contracts(
    filters: ContractFilters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ContractService = Depends(get_contract_service),
):
    """List contracts with filtering, sorting, and pagination."""
    return await service.list(filters, page=page, page_size=page_size)

@router.post("/", response_model=ContractDetail, status_code=status.HTTP_201_CREATED)
async def create_contract(
    body: ContractCreate,
    service: ContractService = Depends(get_contract_service),
):
    """Upload and create a new contract."""
    return await service.create(body)

@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    contract_id: UUID,
    service: ContractService = Depends(get_contract_service),
):
    """Get contract by ID with full details."""
    return await service.get_by_id(contract_id)
```

### 2.6 Service Pattern

```python
# domains/contracts/service.py

from dataclasses import dataclass

@dataclass
class ContractService:
    repository: ContractRepository
    event_bus: EventBus
    user: UserContext
    tenant_id: str

    async def create(self, data: ContractCreate) -> ContractDetail:
        # 1. Validate business rules
        self._validate_upload(data)

        # 2. Upload file to S3
        file_path = await self._upload_to_s3(data.file)

        # 3. Persist
        contract = await self.repository.create(
            tenant_id=self.tenant_id,
            created_by=self.user.id,
            filename=data.filename,
            file_path=file_path,
            contract_type=data.contract_type,
            metadata=data.metadata,
        )

        # 4. Emit domain event
        await self.event_bus.emit(
            ContractUploaded(
                contract_id=contract.id,
                tenant_id=self.tenant_id,
                file_path=file_path,
            )
        )

        return ContractDetail.from_orm(contract)

    def _validate_upload(self, data: ContractCreate) -> None:
        if data.file_size > MAX_FILE_SIZE:
            raise ContractTooLargeError(data.file_size)
        if data.content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedFileTypeError(data.content_type)
```

### 2.7 Repository Pattern

```python
# domains/contracts/repository.py

from dataclasses import dataclass

@dataclass
class ContractRepository:
    session: AsyncSession

    async def create(self, *, tenant_id: str, created_by: str, **kwargs) -> ContractModel:
        contract = ContractModel(
            tenant_id=tenant_id,
            user_id=created_by,
            **kwargs
        )
        self.session.add(contract)
        await self.session.flush()
        return contract

    async def get_by_id(self, contract_id: UUID, tenant_id: str) -> ContractModel | None:
        stmt = select(ContractModel).where(
            ContractModel.contract_id == contract_id,
            ContractModel.tenant_id == tenant_id,
            ContractModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str,
        filters: ContractFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ContractModel], int]:
        query = select(ContractModel).where(ContractModel.tenant_id == tenant_id)

        if filters.status:
            query = query.where(ContractModel.status == filters.status)
        if filters.contract_type:
            query = query.where(ContractModel.contract_type == filters.contract_type)

        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        result = await self.session.execute(
            query.order_by(ContractModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total
```

### 2.8 Event Bus (In-Memory)

```python
# app/common/events/bus.py

import asyncio
from collections import defaultdict
from typing import Callable, Coroutine

Handler = Callable[..., Coroutine]

class EventBus:
    """In-memory event bus for domain events within the modular monolith."""

    def __init__(self):
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def register(self, event_type: type, handler: Handler):
        self._handlers[event_type].append(handler)

    async def emit(self, event):
        """Emit event to all registered handlers (async, non-blocking)."""
        handlers = self._handlers.get(type(event), [])
        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Event handler failed: {result}")

# ── Event Handler Registration ──────────────────────────────────────────

# app/lifecycle.py

def register_event_handlers(event_bus: EventBus, services: dict):
    """Wire domain events to handlers on startup."""
    event_bus.register(ContractUploaded, services["ingestion"].on_contract_uploaded)
    event_bus.register(ContractProcessed, services["ai"].on_contract_processed)
    event_bus.register(AIAnalysisCompleted, services["workflow"].on_analysis_completed)
    event_bus.register(WorkflowEscalated, services["notification"].on_escalation)
```

### 2.9 Middleware Stack

```python
# app/common/middleware/stack.py

MIDDLEWARE_ORDER = [
    "RequestIDMiddleware",      # 1. Assign request ID
    "CORSMiddleware",           # 2. CORS headers
    "LoggingMiddleware",        # 3. Request/response logging
    "RateLimitMiddleware",      # 4. Rate limiting
    "AuthMiddleware",           # 5. JWT validation
    "TenantMiddleware",         # 6. Tenant resolution
    "AuditMiddleware",          # 7. Audit logging (mutations only)
]

# Each middleware:
# 1. Processes request before handler
# 2. Sets request.state attributes
# 3. Processes response after handler
# 4. Handles errors gracefully
```

### 2.10 Exception Hierarchy

```python
# app/common/exceptions.py

class AppError(Exception):
    """Base application error."""
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

class ConflictError(AppError):
    status_code = 409
    code = "conflict"

class RateLimitError(AppError):
    status_code = 429
    code = "rate_limit_exceeded"

# Domain-specific:
class ContractNotFoundError(NotFoundError): ...
class ContractTooLargeError(ValidationError): ...
class VendorNotCompliantError(ConflictError): ...

# Error handler:
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

---

## 3. Frontend Implementation Blueprint

### 3.1 Next.js App Router Structure

```
frontend/
├── app/
│   ├── layout.tsx                    # Root layout (providers, fonts)
│   ├── page.tsx                      # Login / Landing
│   │
│   ├── (dashboard)/                  # Route group — authenticated
│   │   ├── layout.tsx                # DashboardLayout (sidebar, topnav)
│   │   ├── page.tsx                  # Redirect to /portfolio
│   │   │
│   │   ├── portfolio/
│   │   │   └── page.tsx
│   │   ├── cfo/
│   │   │   └── page.tsx
│   │   ├── legal-review/
│   │   │   └── page.tsx
│   │   ├── procurement/
│   │   │   └── page.tsx
│   │   ├── contracts/
│   │   │   ├── page.tsx              # Contracts list
│   │   │   └── [id]/
│   │   │       └── page.tsx          # Contract detail workspace
│   │   ├── vendors/
│   │   │   ├── page.tsx
│   │   │   └── [id]/
│   │   │       └── page.tsx
│   │   ├── workflows/
│   │   │   └── page.tsx
│   │   ├── compliance/
│   │   │   └── page.tsx
│   │   ├── obligations/
│   │   │   └── page.tsx
│   │   ├── negotiations/
│   │   │   └── page.tsx
│   │   ├── clause-library/
│   │   │   └── page.tsx
│   │   ├── benchmarks/
│   │   │   └── page.tsx
│   │   ├── analytics/
│   │   │   └── page.tsx
│   │   ├── search/
│   │   │   └── page.tsx
│   │   ├── settings/
│   │   │   └── page.tsx
│   │   └── admin/
│   │       └── page.tsx
│   │
│   ├── api/                          # API routes (Next.js API handlers)
│   │   └── auth/
│   │       └── [...auth0]/route.ts
│   │
│   └── error.tsx                     # Global error boundary
│
├── components/
│   ├── ui/                           # Design system (shadcn/ui)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── table.tsx
│   │   ├── dialog.tsx
│   │   ├── drawer.tsx
│   │   ├── badge.tsx
│   │   ├── kpi-card.tsx
│   │   ├── data-table.tsx
│   │   ├── filter-bar.tsx
│   │   ├── search-bar.tsx
│   │   └── ...
│   │
│   ├── layout/                       # Layout components
│   │   ├── sidebar.tsx
│   │   ├── topnav.tsx
│   │   ├── breadcrumbs.tsx
│   │   └── workspace-layout.tsx      # 3-panel layout wrapper
│   │
│   ├── dashboard/                    # Feature-based modules
│   │   ├── portfolio/
│   │   ├── cfo/
│   │   ├── legal-review/
│   │   ├── procurement/
│   │   ├── contracts/
│   │   ├── vendors/
│   │   ├── workflows/
│   │   ├── compliance/
│   │   ├── obligations/
│   │   ├── negotiations/
│   │   ├── clause-library/
│   │   ├── benchmarks/
│   │   ├── analytics/
│   │   ├── search/
│   │   └── admin/
│   │
│   ├── ai-copilot/                   # Global AI Copilot
│   │   ├── copilot.tsx
│   │   ├── chat.tsx
│   │   ├── insights-panel.tsx
│   │   └── action-executor.tsx
│   │
│   └── shared/                       # Shared business components
│       ├── entity-drawer.tsx
│       ├── activity-feed.tsx
│       ├── comment-thread.tsx
│       ├── notification-bell.tsx
│       └── ...
│
├── lib/
│   ├── api/                          # API client layer
│   │   ├── client.ts                 # Axios/fetch wrapper
│   │   ├── contracts.ts              # Contract API functions
│   │   ├── vendors.ts
│   │   ├── workflows.ts
│   │   ├── ai.ts
│   │   └── ...
│   │
│   ├── hooks/                        # React hooks
│   │   ├── use-contracts.ts          # React Query hooks
│   │   ├── use-vendors.ts
│   │   ├── use-workflows.ts
│   │   ├── use-ai-copilot.ts
│   │   ├── use-notifications.ts
│   │   ├── use-websocket.ts
│   │   └── use-debounce.ts
│   │
│   ├── stores/                       # Zustand stores
│   │   ├── ui-store.ts               # Sidebar, theme, layout state
│   │   ├── workspace-store.ts        # Active workspace state
│   │   └── copilot-store.ts          # AI Copilot state
│   │
│   ├── utils/
│   │   ├── cn.ts                     # clsx + tailwind-merge
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   │
│   └── websocket/
│       └── client.ts
│
├── public/
├── styles/
│   └── globals.css
│
├── __tests__/
│   ├── components/
│   ├── hooks/
│   └── e2e/
│
├── Dockerfile
├── next.config.js
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

### 3.2 Component Hierarchy

```
Page (Route)
└── DashboardLayout
    ├── Sidebar
    ├── TopNav
    │   ├── SearchBar (global Cmd+K)
    │   ├── NotificationBell
    │   └── UserMenu
    └── WorkspaceLayout (3-panel | full | drawer)
        ├── KPIRow (horizontal scroll)
        ├── FilterBar (horizontal dropdowns)
        ├── LeftPanel (240-320px, collapsible)
        │   ├── Queue / List / Nav
        │   └── AI Insights (optional)
        ├── CenterPanel (flex-1)
        │   ├── Content / Table / Chart / Graph
        │   └── Toolbar (contextual actions)
        └── RightPanel (320-420px, collapsible)
            ├── Detail / AI Copilot / Activity
            └── Drawer (slide-over, multi-tab)
```

### 3.3 State Management Strategy

```typescript
// lib/stores/ui-store.ts — Zustand (Global UI State)
interface UIStore {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  fontSize: number;
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

// React Query (Server State)
// lib/hooks/use-contracts.ts
function useContracts(filters: ContractFilters) {
  return useQuery({
    queryKey: ['contracts', filters],
    queryFn: () => contractsApi.list(filters),
    staleTime: 30_000,        // 30s before refetch
    gcTime: 5 * 60_000,       // 5min in cache
    keepPreviousData: true,   // Smooth pagination
  });
}

// WebSocket (Real-time State)
// lib/hooks/use-notifications.ts
function useNotifications() {
  const queryClient = useQueryClient();
  const socket = useWebSocket('/ws/notifications');

  useEffect(() => {
    socket.on('notification', (data) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      // Show toast
      toast(data.title);
    });
  }, []);
}
```

### 3.4 AI Streaming UX Pattern

```typescript
// lib/hooks/use-ai-copilot.ts
function useAICopilot() {
  const [messages, setMessages] = useState<Message[]>([]);

  const sendMessage = useCallback(async (content: string) => {
    // 1. Add user message immediately (optimistic)
    setMessages(prev => [...prev, { role: 'user', content }]);

    // 2. Add placeholder for AI response
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);

    // 3. Stream response
    const response = await fetch('/api/v1/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message: content }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        updated[updated.length - 1] = {
          ...last,
          content: last.content + chunk,
        };
        return updated;
      });
    }

    // 4. Mark streaming complete
    setMessages(prev => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      updated[updated.length - 1] = { ...last, streaming: false };
      return updated;
    });
  }, []);

  return { messages, sendMessage };
}
```

---

## 4. Database Implementation Strategy

### 4.1 Schema Organization

```sql
-- ── Naming Conventions ──────────────────────────────────────────────
-- Tables:      snake_case, plural (contracts, audit_logs)
-- Columns:     snake_case (contract_id, created_at)
-- PKs:         <table>_id (contract_id)
-- FKs:         <referenced_table>_id (tenant_id, contract_id)
-- Indexes:     idx_<table>_<columns> (idx_contracts_tenant_status)
-- Enums:       snake_case values ('pending', 'in_progress')
-- JSONB:       snake_case keys
-- Soft Delete: deleted_at TIMESTAMPTZ NULLABLE
-- Timestamps:  created_at, updated_at (trigger auto-update)
-- Audit:       All tables have tenant_id for RLS

-- ── All tables must include: ─────────────────────────────────────────
tenant_id    UUID NOT NULL REFERENCES tenants(tenant_id)
created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
deleted_at   TIMESTAMPTZ NULLABLE  -- Soft delete
```

### 4.2 Migration Workflow

```bash
# Create migration
alembic revision --autogenerate -m "add vendor_risks table"

# Review migration (ALWAYS review auto-generated migrations)
code alembic/versions/abc123_add_vendor_risks.py

# Apply migration (local dev)
alembic upgrade head

# Rollback
alembic downgrade -1

# Apply to production
# CI/CD runs: alembic upgrade head (with manual approval gate)
```

### 4.3 RLS Implementation

```sql
-- ── Row-Level Security ──────────────────────────────────────────────

-- 1. Enable RLS on all tenant-scoped tables
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;

-- 2. Create tenant isolation policy
CREATE POLICY tenant_isolation ON contracts
    USING (tenant_id = get_current_tenant_id());

-- 3. Create user-scoped policy (for user-owned data)
CREATE POLICY user_isolation ON notifications
    USING (
        tenant_id = get_current_tenant_id()
        AND user_id = get_current_user_id()
    );

-- 4. Create role-based policy
CREATE POLICY role_based_access ON contracts
    USING (
        tenant_id = get_current_tenant_id()
        AND (
            get_current_user_role() = 'admin'
            OR get_current_user_role() = 'analyst'
            OR (get_current_user_role() = 'viewer' AND status != 'error')
        )
    );
```

### 4.4 Indexing Standards

```sql
-- ── Standard Indexes ────────────────────────────────────────────────

-- 1. Foreign key indexes (every FK gets an index)
CREATE INDEX idx_contracts_tenant ON contracts(tenant_id);
CREATE INDEX idx_clauses_contract ON clauses(contract_id);

-- 2. Filtered indexes (for common query patterns)
CREATE INDEX idx_contracts_active ON contracts(tenant_id, status)
    WHERE deleted_at IS NULL AND status != 'archived';

-- 3. Composite indexes (for sort + filter combinations)
CREATE INDEX idx_contracts_tenant_created ON contracts(tenant_id, created_at DESC)
    WHERE deleted_at IS NULL;

-- 4. Partial indexes (for sparse data)
CREATE INDEX idx_contracts_high_risk ON contracts(tenant_id, risk_score)
    WHERE risk_score >= 0.7 AND deleted_at IS NULL;

-- 5. GIN indexes (for JSONB and arrays)
CREATE INDEX idx_contracts_tags ON contracts USING GIN(tags);
CREATE INDEX idx_contracts_metadata ON contracts USING GIN(metadata jsonb_path_ops);

-- 6. Full-text search indexes
CREATE INDEX idx_contracts_search ON contracts USING GIN(search_vector);
CREATE INDEX idx_clauses_search ON clauses USING GIN(to_tsvector('english', text));

-- 7. Vector indexes
CREATE INDEX idx_chunks_embedding ON chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 4.5 Partitioning Strategy

```sql
-- ── Partitioned Tables ──────────────────────────────────────────────

-- 1. Contracts: Hash-partitioned by tenant_id
CREATE TABLE contracts (
    contract_id UUID, tenant_id UUID, ...
    PRIMARY KEY (tenant_id, contract_id)
) PARTITION BY HASH (tenant_id);
-- 4-16 partitions (scale with tenant count)

-- 2. Audit logs: Range-partitioned by created_at
CREATE TABLE audit_logs (
    audit_id UUID, tenant_id UUID, created_at TIMESTAMPTZ, ...
) PARTITION BY RANGE (created_at);
-- Monthly partitions, 7-year retention

-- 3. Analytics snapshots: Range-partitioned by period_start
CREATE TABLE analytics_snapshots (
    snapshot_id UUID, tenant_id UUID, period_start DATE, ...
) PARTITION BY RANGE (period_start);
-- Monthly partitions, tiered retention
```

### 4.6 Archival Strategy

```sql
-- ── Data Lifecycle ──────────────────────────────────────────────────

-- Hot (current):        Active contracts, open workflows, recent notifications
-- Warm (< 1 year):     Completed workflows, older contracts
-- Cold (< 3 years):    Archived contracts, old audit logs
-- Glacier (> 7 years): All data → Parquet in S3, metadata-only in DB

-- Archival job (Celery Beat, daily):
-- 1. Detach old partitions
ALTER TABLE audit_logs DETACH PARTITION audit_logs_2025_05;

-- 2. Export to Parquet
COPY (SELECT * FROM audit_logs_2025_05) TO 's3://archive/audit_logs/2025_05.parquet';

-- 3. Drop partition
DROP TABLE audit_logs_2025_05;

-- 4. Update metadata table
INSERT INTO archived_partitions (table_name, partition_name, archived_at, s3_path)
VALUES ('audit_logs', 'audit_logs_2025_05', NOW(), 's3://archive/audit_logs/2025_05.parquet');
```

---

## 5. AI Implementation Strategy

### 5.1 LangGraph Agent Architecture

```python
# ai-runtime/app/agents/risk_agent.py

from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

class RiskAnalysisState(TypedDict):
    contract_id: str
    contract_text: str
    clauses: list[ClauseData]
    risk_score: float | None
    findings: list[RiskFinding]
    recommendations: list[str]
    citations: list[Citation]

# ── Define Agent Nodes ───────────────────────────────────────────────

async def load_contract(state: RiskAnalysisState) -> dict:
    """Load contract text and clauses from database."""
    contract = await contract_service.get_with_clauses(state["contract_id"])
    return {
        "contract_text": contract.full_text,
        "clauses": contract.clauses,
    }

async def classify_clauses(state: RiskAnalysisState) -> dict:
    """Classify each clause by type and risk category."""
    classified = await clause_classifier.classify_batch(state["clauses"])
    return {"clauses": classified}

async def assess_risk(state: RiskAnalysisState) -> dict:
    """Assess overall contract risk using LLM."""
    result = await llm.call(
        prompt=Prompts.RISK_ASSESSMENT,
        variables={
            "contract_text": state["contract_text"],
            "clauses": state["clauses"],
        },
    )
    return {
        "risk_score": result.risk_score,
        "findings": result.findings,
    }

async def generate_recommendations(state: RiskAnalysisState) -> dict:
    """Generate remediation recommendations."""
    result = await llm.call(
        prompt=Prompts.RISK_RECOMMENDATIONS,
        variables={"findings": state["findings"]},
    )
    return {"recommendations": result.recommendations}

async def add_citations(state: RiskAnalysisState) -> dict:
    """Cite source clauses for each finding."""
    citations = await citation_engine.cite_findings(
        findings=state["findings"],
        clauses=state["clauses"],
    )
    return {"citations": citations}

# ── Build Graph ──────────────────────────────────────────────────────

workflow = StateGraph(RiskAnalysisState)

workflow.add_node("load_contract", load_contract)
workflow.add_node("classify_clauses", classify_clauses)
workflow.add_node("assess_risk", assess_risk)
workflow.add_node("generate_recommendations", generate_recommendations)
workflow.add_node("add_citations", add_citations)

workflow.set_entry_point("load_contract")
workflow.add_edge("load_contract", "classify_clauses")
workflow.add_edge("classify_clauses", "assess_risk")
workflow.add_edge("assess_risk", "generate_recommendations")
workflow.add_edge("generate_recommendations", "add_citations")
workflow.add_edge("add_citations", END)

risk_agent = workflow.compile()
```

### 5.2 Prompt Management

```python
# ai-runtime/app/prompts/manager.py

from pydantic import BaseModel
from jinja2 import Template

class PromptTemplate(BaseModel):
    id: str
    version: str
    template: str
    variables: list[str]
    model: str  # Default model for this prompt
    temperature: float = 0.1
    max_tokens: int = 4096

class PromptManager:
    """Versioned prompt registry with template rendering."""

    def __init__(self):
        self._templates: dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate):
        self._templates[template.id] = template

    def render(self, prompt_id: str, version: str, **variables) -> str:
        template = self._templates[prompt_id]
        assert template.version == version
        jinja = Template(template.template)
        return jinja.render(**variables)

    def get_config(self, prompt_id: str) -> PromptTemplate:
        return self._templates[prompt_id]

# ── Prompt Registry ──────────────────────────────────────────────────

PROMPTS = PromptManager()
PROMPTS.register(PromptTemplate(
    id="risk_assessment",
    version="1.0",
    template="""
You are a senior contract risk analyst. Analyze the following contract
and identify all high-risk clauses.

Contract: {{ contract_name }}
Type: {{ contract_type }}

Clauses:
{% for clause in clauses %}
[{{ clause.section_number }}] {{ clause.heading }}
{{ clause.text }}
{% endfor %}

For each high-risk clause, provide:
1. Risk score (0-10)
2. Risk category
3. Explanation
4. Recommended action

Respond in JSON format.
    """,
    variables=["contract_name", "contract_type", "clauses"],
    model="gpt-4o",
    temperature=0.1,
))
```

### 5.3 Tool Calling Architecture

```python
# ai-runtime/app/tools/registry.py

from dataclasses import dataclass
from typing import Any, Callable, Awaitable

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema
    handler: Callable[..., Awaitable[Any]]

class ToolRegistry:
    """Registry of tools available to AI agents."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    async def execute(self, name: str, **kwargs) -> Any:
        tool = self._tools[name]
        return await tool.handler(**kwargs)

# ── Tool Definitions ─────────────────────────────────────────────────

TOOLS = ToolRegistry()
TOOLS.register(Tool(
    name="search_contracts",
    description="Search contracts by query, filters, and pagination",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "draft", "archived"]},
            "limit": {"type": "integer", "default": 10},
        },
    },
    handler=search_service.search_contracts,
))
TOOLS.register(Tool(
    name="get_contract_detail",
    description="Get full contract detail with clauses",
    parameters={
        "type": "object",
        "properties": {
            "contract_id": {"type": "string"},
        },
        "required": ["contract_id"],
    },
    handler=contract_service.get_contract_detail,
))
```

### 5.4 RAG Pipeline Implementation

```python
# ai-runtime/app/pipelines/rag_pipeline.py

@dataclass
class RAGPipeline:
    embedder: EmbeddingService
    vector_db: VectorDatabase
    reranker: Reranker
    llm: LLMService
    prompt_manager: PromptManager

    async def query(
        self,
        query: str,
        tenant_id: str,
        filters: dict | None = None,
        top_k: int = 20,
    ) -> RAGResponse:
        # 1. Embed query
        query_vector = await self.embedder.embed(query)

        # 2. Retrieve candidates (vector search)
        candidates = await self.vector_db.search(
            query_vector=query_vector,
            tenant_id=tenant_id,
            filters=filters,
            top_k=top_k,
        )

        # 3. Re-rank with cross-encoder
        reranked = await self.reranker.rerank(
            query=query,
            documents=[c.text for c in candidates],
            scores=[c.score for c in candidates],
        )

        # 4. Build context (token budget: 8K)
        context = self._build_context(reranked, max_tokens=8_000)

        # 5. Generate response with citations
        response = await self.llm.call(
            prompt=self.prompt_manager.render(
                "rag_answer",
                version="1.0",
                query=query,
                context=context,
            ),
        )

        # 6. Format citations
        citations = self._extract_citations(response, reranked)

        return RAGResponse(
            answer=response.answer,
            citations=citations,
            confidence=response.confidence,
        )

    def _build_context(
        self, documents: list[ScoredDocument], max_tokens: int
    ) -> str:
        """Build context string respecting token budget."""
        parts = []
        tokens = 0
        for doc in documents:
            doc_tokens = estimate_tokens(doc.text)
            if tokens + doc_tokens > max_tokens:
                break
            parts.append(f"[Source {doc.index}] {doc.text}")
            tokens += doc_tokens
        return "\n\n".join(parts)
```

### 5.5 AI Cache Strategy

```python
# ai-runtime/app/cache/llm_cache.py

class LLMCache:
    """Semantic cache for LLM responses using embedding similarity."""

    def __init__(self, redis, embedder, similarity_threshold=0.95):
        self.redis = redis
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold

    async def get(self, prompt: str, model: str) -> str | None:
        """Get cached response if semantically similar query exists."""
        query_vector = await self.embedder.embed(prompt)
        # Search for similar cached queries
        cached = await self.redis.ft_search(
            index="llm_cache",
            query=f"@model:{model}",
            vector=("embedding", query_vector),
            top_k=1,
        )
        if cached and cached[0].score >= self.similarity_threshold:
            return cached[0].response
        return None

    async def set(self, prompt: str, response: str, model: str, ttl: int = 3600):
        """Cache LLM response."""
        embedding = await self.embedder.embed(prompt)
        await self.redis.ft_add(
            "llm_cache",
            {
                "prompt": prompt,
                "response": response,
                "model": model,
                "embedding": embedding,
            },
            ttl=ttl,
        )
```

---

## 6. Search Implementation Strategy

### 6.1 Hybrid Search Architecture

```python
# search-runtime/app/engine/hybrid.py

@dataclass
class HybridSearchEngine:
    """BM25 + Vector fusion search with configurable weights."""

    vector_weight: float = 0.7
    keyword_weight: float = 0.3

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResults:
        # 1. Parallel execution
        vector_results, keyword_results = await asyncio.gather(
            self._vector_search(query, tenant_id, filters),
            self._keyword_search(query, tenant_id, filters),
        )

        # 2. Reciprocal Rank Fusion (RRF)
        fused = self._rrf_fusion(
            vector_results, self.vector_weight,
            keyword_results, self.keyword_weight,
        )

        # 3. Paginate
        total = len(fused)
        paginated = fused[(page - 1) * page_size : page * page_size]

        return SearchResults(
            results=paginated,
            total=total,
            page=page,
            page_size=page_size,
        )

    def _rrf_fusion(
        self,
        vector_results: list[ScoredResult],
        vector_weight: float,
        keyword_results: list[ScoredResult],
        keyword_weight: float,
    ) -> list[ScoredResult]:
        """Reciprocal Rank Fusion with configurable weights."""
        scores: dict[str, float] = {}
        for rank, result in enumerate(vector_results):
            scores[result.id] = vector_weight / (60 + rank)
        for rank, result in enumerate(keyword_results):
            scores[result.id] = scores.get(result.id, 0) + keyword_weight / (60 + rank)
        return sorted(
            [ScoredResult(id=k, score=v) for k, v in scores.items()],
            key=lambda x: x.score,
            reverse=True,
        )
```

### 6.2 Re-ranking Pipeline

```python
# search-runtime/app/engine/reranker.py

class CrossEncoderReranker:
    """Cross-encoder re-ranker for precision improvement."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = load_model(model_name)

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 10,
    ) -> list[ScoredDocument]:
        """Re-rank documents using cross-encoder."""
        pairs = [(query, doc) for doc in documents]
        scores = self.model.predict(pairs)

        scored = [
            ScoredDocument(text=doc, score=float(score))
            for doc, score in zip(documents, scores)
        ]
        scored.sort(key=lambda x: x.score, reverse=True)

        return scored[:top_k]
```

### 6.3 Embedding Lifecycle

```python
# search-runtime/app/indexing/embedder.py

class EmbeddingManager:
    """Manages embedding generation, updates, and re-indexing."""

    async def generate_embeddings(self, contract_id: str, tenant_id: str):
        """Generate embeddings for all chunks in a contract."""
        chunks = await chunk_repo.get_by_contract(contract_id, tenant_id)
        texts = [chunk.text for chunk in chunks]

        # Batch embed (max 20 at a time)
        for batch in batched(texts, 20):
            embeddings = await self.embedder.embed_batch(batch)
            for chunk, embedding in zip(batch, embeddings):
                await chunk_repo.update_embedding(chunk.id, embedding)

    async def reindex_tenant(self, tenant_id: str):
        """Full re-index for a tenant (scheduled job)."""
        contracts = await contract_repo.get_all(tenant_id)
        for contract in contracts:
            await self.generate_embeddings(contract.id, tenant_id)

    async def incremental_update(self, contract_id: str, tenant_id: str):
        """Update embeddings for a single contract (triggered on version change)."""
        await self.generate_embeddings(contract_id, tenant_id)
```

---

## 7. Worker & Job Execution Strategy

### 7.1 Celery Architecture

```python
# worker-runtime/app/celery_app.py

from celery import Celery
from kombu import Queue, Exchange

celery_app = Celery(
    "contractrisk_worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_queues=[
        Queue("ingestion", Exchange("ingestion"), routing_key="ingestion.#"),
        Queue("ai", Exchange("ai"), routing_key="ai.#"),
        Queue("workflow", Exchange("workflow"), routing_key="workflow.#"),
        Queue("notification", Exchange("notification"), routing_key="notification.#"),
        Queue("analytics", Exchange("analytics"), routing_key="analytics.#"),
        Queue("maintenance", Exchange("maintenance"), routing_key="maintenance.#"),
        Queue("default", Exchange("default"), routing_key="default"),
    ],
    task_routes={
        "tasks.ingestion.*": {"queue": "ingestion"},
        "tasks.ai.*": {"queue": "ai"},
        "tasks.workflow.*": {"queue": "workflow"},
        "tasks.notification.*": {"queue": "notification"},
        "tasks.analytics.*": {"queue": "analytics"},
        "tasks.maintenance.*": {"queue": "maintenance"},
    },
    task_default_queue="default",
)
```

### 7.2 Task Patterns

```python
# worker-runtime/app/tasks/ingestion/process_document.py

@celery_app.task(
    bind=True,
    name="process_document",
    max_retries=3,
    acks_late=True,
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    soft_time_limit=240,
    time_limit=300,
)
def process_document(self, job_id: str, document_path: str, options: dict | None = None):
    """Process a document through the full ingestion pipeline."""
    logger.info(f"Processing document", job_id=job_id, path=document_path)

    try:
        # 1. Extract text
        text = extract_text(document_path)

        # 2. Extract metadata
        metadata = extract_metadata(text)

        # 3. Segment clauses
        clauses = segment_clauses(text)

        # 4. Chunk text
        chunks = chunk_text(text, clauses)

        # 5. Store results
        store_results(job_id, text, metadata, clauses, chunks)

        # 6. Update job status
        update_job_status(job_id, "completed")

        logger.info(f"Document processed successfully", job_id=job_id)

    except RetryableError as exc:
        logger.warning(f"Retryable error processing document", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)

    except FatalError as exc:
        logger.error(f"Fatal error processing document", job_id=job_id, error=str(exc))
        update_job_status(job_id, "failed", error=str(exc))
```

### 7.3 Chained Tasks

```python
# worker-runtime/app/tasks/ai/analyze_contract.py

@celery_app.task(name="analyze_contract")
def analyze_contract(contract_id: str):
    """Start contract analysis pipeline (chain of tasks)."""
    chain = (
        classify_clauses.s(contract_id) |
        assess_risk.s() |
        extract_obligations.s() |
        generate_redlines.s() |
        store_analysis_results.s(contract_id)
    )
    chain()

@celery_app.task(name="classify_clauses")
def classify_clauses(contract_id: str) -> dict:
    clauses = get_clauses(contract_id)
    classified = ai_service.classify_clauses(clauses)
    return {"contract_id": contract_id, "classified_clauses": classified}

@celery_app.task(name="assess_risk")
def assess_risk(previous_result: dict) -> dict:
    risk = ai_service.assess_risk(previous_result["classified_clauses"])
    return {**previous_result, "risk_assessment": risk}
```

### 7.4 Beat Schedule

```python
# worker-runtime/app/beat_schedule.py

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # ── Every 5 minutes ─────────────────────────────────────
    "check_sla_deadlines": {
        "task": "tasks.workflow.check_sla_deadlines",
        "schedule": 300.0,  # 5 min
    },
    "check_renewal_approaching": {
        "task": "tasks.workflow.check_renewals",
        "schedule": 300.0,
    },

    # ── Every hour ───────────────────────────────────────────
    "aggregate_kpis": {
        "task": "tasks.analytics.aggregate_kpis",
        "schedule": 3600.0,
    },
    "process_notification_queue": {
        "task": "tasks.notification.process_queue",
        "schedule": 3600.0,
    },

    # ── Daily (off-peak) ─────────────────────────────────────
    "nightly_re_analysis": {
        "task": "tasks.ai.nightly_re_analysis",
        "schedule": crontab(hour=2, minute=0),
    },
    "reindex_search": {
        "task": "tasks.maintenance.reindex_search",
        "schedule": crontab(hour=3, minute=0),
    },
    "archive_old_data": {
        "task": "tasks.maintenance.archive_old_data",
        "schedule": crontab(hour=4, minute=0),
    },
    "generate_daily_report": {
        "task": "tasks.analytics.generate_daily_report",
        "schedule": crontab(hour=6, minute=0),
    },

    # ── Weekly ───────────────────────────────────────────────
    "weekly_benchmark_update": {
        "task": "tasks.ai.weekly_benchmark_update",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
    },
}
```

---

## 8. API Implementation Standards

### 8.1 Response Envelope

```python
# Standard response format for all endpoints

# Success:
{
    "data": { ... },         # Single object
    # OR
    "data": [ ... ],         # Array
    # OR (paginated)
    "data": [ ... ],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total": 142,
        "total_pages": 8,
    }
}

# Error:
{
    "error": "validation_error",
    "message": "Contract name is required",
    "request_id": "req_abc123",
    "details": {
        "field": "name",
        "reason": "required"
    }
}

# Pagination query params:
#   ?page=1&page_size=20&sort_by=created_at&sort_order=desc

# Filtering:
#   ?status=active&contract_type=msa
#   ?tags=tech,cloud
#   ?created_at.gte=2026-01-01&created_at.lte=2026-05-15

# Sorting:
#   ?sort_by=risk_score&sort_order=desc
```

### 8.2 Pagination Implementation

```python
# app/common/pagination.py

from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: Literal["asc", "desc"] = Field(default="desc")

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

# Usage in repository:
async def list(self, tenant_id: str, pagination: PaginationParams, filters: dict) -> tuple[list, int]:
    query = select(Model).where(Model.tenant_id == tenant_id)

    # Apply filters
    for field, value in filters.items():
        if value is not None:
            query = query.where(getattr(Model, field) == value)

    # Get total
    total = await self.session.scalar(select(func.count()).select_from(query.subquery()))

    # Apply sorting
    sort_col = getattr(Model, pagination.sort_by)
    query = query.order_by(sort_col.desc() if pagination.sort_order == "desc" else sort_col.asc())

    # Apply pagination
    query = query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size)

    result = await self.session.execute(query)
    return result.scalars().all(), total
```

### 8.3 API Versioning

```python
# Strategy: URL prefix versioning
# /api/v1/contracts
# /api/v2/contracts (future)

# Current: v1 is the only version
# Deprecation: v1 endpoints return Deprecation header 6 months before removal
# Sunset: v1 removed after 12 months deprecation period

# In router registration:
app.include_router(v1_router, prefix="/api/v1")
# When v2 is needed:
# app.include_router(v2_router, prefix="/api/v2")
```

---

## 9. Event System Implementation

### 9.1 Event Schema

```python
# packages/shared-sdk/src/sdk/events/base.py

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4

class DomainEvent(BaseModel):
    """Base class for all domain events."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    event_version: str = "1.0"
    source: str
    tenant_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None
    actor_id: str | None = None
    data: dict

# ── Event Definitions ────────────────────────────────────────────────

class ContractUploaded(DomainEvent):
    event_type: str = "contract.uploaded"
    source: str = "contract-service"

class ContractProcessed(DomainEvent):
    event_type: str = "contract.processed"
    source: str = "ingestion-worker"

class AIAnalysisCompleted(DomainEvent):
    event_type: str = "ai.analysis.completed"
    source: str = "ai-runtime"

class WorkflowEscalated(DomainEvent):
    event_type: str = "workflow.escalated"
    source: str = "workflow-engine"
```

### 9.2 Idempotency Handling

```python
# worker-runtime/app/tasks/base.py

class IdempotentTask(Task):
    """Base task with idempotency protection."""

    abstract = True

    def apply_async(self, args=None, kwargs=None, task_id=None, **options):
        """Generate deterministic task_id from event_id for dedup."""
        if kwargs and "event" in kwargs:
            task_id = f"{self.name}:{kwargs['event'].event_id}"
        return super().apply_async(args=args, kwargs=kwargs, task_id=task_id, **options)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Store result for idempotency check."""
        if status == "SUCCESS":
            redis_client.setex(f"task:result:{task_id}", 86400, json.dumps(retval))

# Usage:
@celery_app.task(base=IdempotentTask, name="process_contract_uploaded")
def process_contract_uploaded(event: ContractUploaded):
    # Check if already processed
    existing = redis_client.get(f"task:result:process_contract_uploaded:{event.event_id}")
    if existing:
        return json.loads(existing)
    # ... process ...
```

### 9.3 Event Replay

```python
# worker-runtime/app/tasks/maintenance/replay_events.py

@celery_app.task(name="replay_events")
def replay_events(event_type: str, start_date: str, end_date: str):
    """Replay events from audit_logs for recovery."""
    events = audit_repo.get_events_by_type(event_type, start_date, end_date)
    for event in events:
        # Re-publish event with original correlation_id
        event_bus.publish(event)
```

---

## 10. Security Implementation

### 10.1 Auth Implementation

```python
# api/app/common/security/auth.py

from fastapi import Request, HTTPException
from jose import jwt, JWTError

async def verify_jwt(request: Request) -> UserContext:
    """Verify JWT token and return user context."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            request.app.state.jwks_client,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=settings.AUTH0_ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    return UserContext(
        id=payload["sub"],
        email=payload.get("email"),
        tenant_id=payload.get(f"{settings.AUTH0_AUDIENCE}/tenant_id"),
        role=payload.get(f"{settings.AUTH0_AUDIENCE}/role", "viewer"),
        permissions=payload.get("permissions", []),
    )
```

### 10.2 RBAC Enforcement

```python
# api/app/common/security/rbac.py

from functools import wraps

def require_permission(resource: str, action: str):
    """Decorator to enforce RBAC on endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or next(
                (a for a in args if isinstance(a, Request)), None
            )
            user: UserContext = request.state.user

            if not user.has_permission(f"{resource}:{action}"):
                raise AuthorizationError(
                    f"User lacks {action} permission on {resource}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage:
@router.delete("/{contract_id}")
@require_permission("contract", "delete")
async def delete_contract(contract_id: UUID, service: ContractService = Depends(...)):
    ...
```

### 10.3 Tenant Isolation Enforcement

```python
# api/app/common/middleware/tenant.py

class TenantMiddleware:
    """Resolve and validate tenant context for every request."""

    async def __call__(self, request: Request, call_next):
        # 1. Extract tenant from JWT or header
        tenant_id = (
            request.state.user.tenant_id
            or request.headers.get("X-Tenant-ID")
        )

        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant context required")

        # 2. Set tenant context for this request
        request.state.tenant_id = tenant_id

        # 3. Set PostgreSQL session context (for RLS)
        async with request.app.state.db_session_factory() as session:
            await session.execute(
                text(f"SET app.tenant_id = '{tenant_id}'")
            )
            await session.execute(
                text(f"SET app.user_id = '{request.state.user.id}'")
            )
            await session.execute(
                text(f"SET app.user_role = '{request.state.user.role}'")
            )

        # 4. Proceed
        response = await call_next(request)
        return response
```

---

## 11. Observability Implementation

### 11.1 Structured Logging

```python
# api/app/common/logging/logger.py

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
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage:
logger.info("contract.uploaded",
    contract_id=contract.id,
    tenant_id=tenant_id,
    file_size=file_size,
    duration_ms=duration,
)
```

### 11.2 Distributed Tracing

```python
# api/app/common/telemetry/tracer.py

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(app: FastAPI, engine: AsyncEngine):
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

# Manual tracing in services:
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

async def analyze_contract(contract_id: str):
    with tracer.start_as_current_span("analyze_contract") as span:
        span.set_attribute("contract_id", contract_id)
        span.add_event("analysis.started")

        result = await ai_service.analyze(contract_id)

        span.set_attribute("risk_score", result.risk_score)
        span.set_attribute("findings_count", len(result.findings))
        span.add_event("analysis.completed")

        return result
```

### 11.3 Metrics Instrumentation

```python
# api/app/common/telemetry/metrics.py

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

meter = metrics.get_meter(__name__)

# Define metrics
request_count = meter.create_counter(
    name="api.request.count",
    description="Total request count",
    unit="1",
)

request_duration = meter.create_histogram(
    name="api.request.duration",
    description="Request duration in seconds",
    unit="s",
)

active_contracts = meter.create_up_down_counter(
    name="contracts.active",
    description="Number of active contracts",
    unit="1",
)

# Usage in middleware:
async def logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    request_count.add(1, {
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
    })
    request_duration.record(duration, {
        "method": request.method,
        "path": request.url.path,
    })

    return response
```

---

## 12. Testing Strategy

### 12.1 Testing Pyramid

```
                    ┌──────────┐
                    │   E2E    │  ← 5%  (Cypress, Playwright)
                    │  Tests   │
                    └────┬─────┘
                    ┌────┴─────┐
                    │Integration│  ← 20% (pytest, API tests)
                    │  Tests    │
                    └────┬─────┘
                    ┌────┴─────┐
                    │  Unit    │  ← 75% (pytest, vitest)
                    │  Tests   │
                    └──────────┘
```

### 12.2 Backend Testing

```python
# api/tests/conftest.py

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    """Create a test database session with transaction rollback."""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost:5432/test")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def contract_repo(db_session):
    return ContractRepository(db_session)

@pytest.fixture
def contract_service(contract_repo):
    return ContractService(
        repository=contract_repo,
        event_bus=MockEventBus(),
        user=UserContext(id="test-user", tenant_id="test-tenant"),
        tenant_id="test-tenant",
    )

# api/tests/domains/contracts/test_service.py

class TestContractService:
    async def test_create_contract_success(self, contract_service):
        data = ContractCreate(filename="test.pdf", content_type="application/pdf", file_size=1000)
        result = await contract_service.create(data)
        assert result.filename == "test.pdf"
        assert result.status == "pending"

    async def test_create_contract_too_large(self, contract_service):
        data = ContractCreate(filename="large.pdf", content_type="application/pdf", file_size=100_000_000)
        with pytest.raises(ContractTooLargeError):
            await contract_service.create(data)

    async def test_list_contracts_pagination(self, contract_service):
        # Create 25 contracts
        for i in range(25):
            await contract_service.create(ContractCreate(filename=f"doc_{i}.pdf", ...))
        
        result, total = await contract_service.list(ContractFilters(), page=1, page_size=10)
        assert len(result) == 10
        assert total == 25
```

### 12.3 AI Evaluation Testing

```python
# ai-runtime/app/evaluation/runner.py

class AIEvaluationRunner:
    """Evaluate AI model outputs against ground truth datasets."""

    def __init__(self):
        self.metrics = {
            "accuracy": AccuracyMetric(),
            "precision": PrecisionMetric(),
            "recall": RecallMetric(),
            "f1": F1Metric(),
            "hallucination_rate": HallucinationMetric(),
            "citation_accuracy": CitationAccuracyMetric(),
        }

    async def evaluate(self, dataset: EvalDataset, agent) -> EvalReport:
        results = []
        for example in dataset:
            output = await agent.run(example.input)
            results.append(self._score(example, output))

        return EvalReport(
            dataset=dataset.name,
            metrics={name: metric.compute(results) for name, metric in self.metrics.items()},
            examples=results,
        )

# ── Test Dataset ─────────────────────────────────────────────────────

EVAL_DATASETS = {
    "risk_classification": EvalDataset(
        name="Risk Classification",
        examples=[
            EvalExample(
                input={"clause_text": "Party A shall indemnify Party B..."},
                expected={"risk_score": 0.8, "category": "indemnification"},
            ),
            # ... 100+ examples
        ],
    ),
}
```

### 12.4 Frontend Testing

```typescript
// frontend/__tests__/components/ContractTable.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { ContractTable } from '@/components/dashboard/contracts/ContractTable';

describe('ContractTable', () => {
  const mockContracts = [
    { id: '1', name: 'Contract A', riskScore: 8.2, status: 'active' },
    { id: '2', name: 'Contract B', riskScore: 3.5, status: 'draft' },
  ];

  it('renders all contracts', () => {
    render(<ContractTable contracts={mockContracts} onSelect={jest.fn()} />);
    expect(screen.getByText('Contract A')).toBeInTheDocument();
    expect(screen.getByText('Contract B')).toBeInTheDocument();
  });

  it('calls onSelect when row clicked', () => {
    const onSelect = jest.fn();
    render(<ContractTable contracts={mockContracts} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('Contract A'));
    expect(onSelect).toHaveBeenCalledWith(mockContracts[0]);
  });

  it('sorts by risk score', () => {
    render(<ContractTable contracts={mockContracts} onSelect={jest.fn()} />);
    fireEvent.click(screen.getByText('Risk'));
    const rows = screen.getAllByRole('row');
    // First row should be highest risk after sort
    expect(rows[1]).toHaveTextContent('8.2');
  });
});
```

### 12.5 Load Testing

```yaml
# k6-load-test.js

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 200 },   // Ramp up to 200 users
    { duration: '5m', target: 200 },   // Stay at 200 users
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95) < 2000'],  // 95% of requests under 2s
    http_req_failed: ['rate < 0.01'],      // Less than 1% failure rate
  },
};

export default function () {
  const params = {
    headers: {
      'Authorization': `Bearer ${__ENV.TEST_TOKEN}`,
      'X-Tenant-ID': 'test-tenant',
    },
  };

  // Test contract listing
  const listRes = http.get('http://api:8000/api/v1/contracts?page=1&page_size=20', params);
  check(listRes, { 'contract list status 200': (r) => r.status === 200 });

  // Test search
  const searchRes = http.get('http://api:8000/api/v1/search?q=indemnification&limit=10', params);
  check(searchRes, { 'search status 200': (r) => r.status === 200 });

  sleep(1);
}
```

---

## 13. CI/CD Implementation

### 13.1 GitHub Actions Workflow

```yaml
# .github/workflows/ci-backend.yml

name: CI - Backend
on:
  push:
    branches: [main, develop, 'release/*']
    paths: ['api/**', 'packages/shared-sdk/**']
  pull_request:
    branches: [main, develop]

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
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r api/requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov
      - run: pytest api/tests/ --cov=api/app --cov-report=xml --cov-report=term
      - uses: codecov/codecov-action@v4
        with: { file: ./coverage.xml }

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ secrets.ECR_REGISTRY }}
          username: ${{ secrets.AWS_ACCESS_KEY_ID }}
          password: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      - run: |
          docker build -t $ECR_REGISTRY/api:$GITHUB_SHA ./api
          docker push $ECR_REGISTRY/api:$GITHUB_SHA
```

### 13.2 Deployment Workflow

```yaml
# .github/workflows/deploy-production.yml

name: Deploy - Production
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Release version'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Run database migrations
        run: |
          aws ecs run-task --cluster production \
            --task-definition migrate \
            --overrides '{"command": ["alembic", "upgrade", "head"]}'

      - name: Deploy API (blue/green)
        run: |
          aws ecs update-service --cluster production \
            --service api --task-definition api:${{ github.sha }} \
            --deployment-controller type=CODE_DEPLOY

      - name: Deploy AI Runtime
        run: |
          aws ecs update-service --cluster production \
            --service ai-runtime --task-definition ai-runtime:${{ github.sha }}

      - name: Deploy Workers
        run: |
          aws ecs update-service --cluster production \
            --service celery-worker --task-definition worker:${{ github.sha }}

      - name: Deploy Search Runtime
        run: |
          aws ecs update-service --cluster production \
            --service search-runtime --task-definition search:${{ github.sha }}

      - name: Deploy Frontend
        run: |
          aws ecs update-service --cluster production \
            --service frontend --task-definition frontend:${{ github.sha }}

      - name: Smoke Tests
        run: |
          sleep 30
          curl -f https://api.contractriskanalyzer.com/api/v1/health
          curl -f https://app.contractriskanalyzer.com

      - name: Notify
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Production deployed: ${{ github.sha }}\"}" \
            ${{ secrets.SLACK_WEBHOOK }}
```

### 13.3 Rollback Strategy

```yaml
# Rollback procedure (manual)

# 1. Revert to previous task definition
aws ecs update-service --cluster production \
  --service api \
  --task-definition api:previous_version

# 2. Revert database migration
aws ecs run-task --cluster production \
  --task-definition migrate \
  --overrides '{"command": ["alembic", "downgrade", "-1"]}'

# 3. Verify health
curl -f https://api.contractriskanalyzer.com/api/v1/health

# 4. Notify
slack-notify "Rollback completed to previous version"
```

---

## 14. Developer Experience

### 14.1 Local Development Setup

```bash
# scripts/setup.sh

#!/bin/bash
set -e

echo "🚀 Setting up ContractRiskEdge development environment..."

# 1. Check prerequisites
command -v python3 || { echo "Python 3.12+ required"; exit 1; }
command -v node || { echo "Node.js 18+ required"; exit 1; }
command -v docker || { echo "Docker required"; exit 1; }

# 2. Clone and install
git clone git@github.com:org/contractriskedge.git
cd contractriskedge

# 3. Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
pip install -r ai-runtime/requirements.txt
pip install -r worker-runtime/requirements.txt

# 4. Install frontend
cd frontend
npm install
cd ..

# 5. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 6. Start infrastructure
docker compose up -d postgres redis

# 7. Run migrations
cd api
alembic upgrade head
cd ..

# 8. Seed development data
python scripts/seed.py

# 9. Start development servers
echo "✅ Setup complete!"
echo "   API:        http://localhost:8000"
echo "   Frontend:   http://localhost:3000"
echo "   Docs:       http://localhost:8000/api/v1/docs"
```

### 14.2 Docker Dev Environment

```yaml
# docker-compose.yml (development)

services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck: { test: ["CMD-SHELL", "pg_isready"], interval: 10s, timeout: 5s, retries: 5 }

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck: { test: ["CMD", "redis-cli", "ping"], interval: 10s, timeout: 5s, retries: 5 }

  api:  # Hot reload
    build: ./api
    ports: ["8000:8000"]
    volumes: [./api:/app]  # Mount for hot reload
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: postgresql+asyncpg://dev:dev@postgres:5432/contract_risk_dev
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: development
    depends_on: [postgres, redis]

  ai-runtime:  # Hot reload
    build: ./ai-runtime
    ports: ["8001:8001"]
    volumes: [./ai-runtime:/app]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
    environment:
      DATABASE_URL: postgresql+asyncpg://dev:dev@postgres:5432/contract_risk_dev
      REDIS_URL: redis://redis:6379/0
    depends_on: [postgres, redis]

  worker:  # Auto-reload on code changes
    build: ./worker-runtime
    volumes: [./worker-runtime:/app, ./api:/app/api]
    command: watchfiles "celery -A app.celery_app worker --loglevel=info" /app
    environment:
      DATABASE_URL: postgresql+asyncpg://dev:dev@postgres:5432/contract_risk_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
    depends_on: [postgres, redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    volumes: [./frontend:/app, /app/node_modules]
    command: npm run dev
    depends_on: [api]

volumes:
  postgres_data:
```

### 14.3 Makefile

```makefile
# Makefile

.PHONY: help setup dev test lint migrate seed clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup:  ## Full development setup
	@bash scripts/setup.sh

dev:  ## Start development environment
	docker compose up -d
	@echo "API: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"

dev-logs:  ## View development logs
	docker compose logs -f

test:  ## Run all tests
	pytest api/tests/ -v --cov=api/app
	cd frontend && npm test

test-api:  ## Run API tests only
	pytest api/tests/ -v

test-ai:  ## Run AI evaluation tests
	pytest ai-runtime/tests/ -v

lint:  ## Run linters
	ruff check api/ ai-runtime/ worker-runtime/
	mypy api/ --strict
	cd frontend && npm run lint

migrate:  ## Run database migrations
	cd api && alembic upgrade head

migrate-rollback:  ## Rollback last migration
	cd api && alembic downgrade -1

seed:  ## Seed development data
	python scripts/seed.py

clean:  ## Clean up
	docker compose down -v
	rm -rf .venv
	rm -rf frontend/node_modules
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

db-shell:  ## Open database shell
	docker compose exec postgres psql -U dev -d contract_risk_dev

redis-cli:  ## Open Redis CLI
	docker compose exec redis redis-cli
```

---

## 15. Engineering Governance

### 15.1 Coding Standards

```yaml
# .editorconfig
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_size = 4
max_line_length = 100

[*.{ts,tsx,js,jsx}]
indent_size = 2
max_line_length = 100

[*.{yml,yaml,json}]
indent_size = 2

[Makefile]
indent_style = tab
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--strict]

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.2.0
    hooks:
      - id: prettier
        types_or: [typescript, tsx, javascript, jsx, json, yaml, css]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: [--maxkb=500]
```

### 15.2 Branching Strategy

```
main
  ├── Production-ready code
  ├── Protected branch — no direct commits
  └── Merged from: release/*, hotfix/*

develop
  ├── Integration branch
  ├── Protected branch — no direct commits
  └── Merged from: feature/*

feature/*
  ├── Branch from: develop
  ├── Naming: feature/CONT-123-description
  └── Merge to: develop (squash merge)

release/*
  ├── Branch from: develop
  ├── Naming: release/v1.2.3
  ├── Only bug fixes, no new features
  └── Merge to: main + develop

hotfix/*
  ├── Branch from: main
  ├── Naming: hotfix/CONT-456-critical-fix
  └── Merge to: main + develop
```

### 15.3 PR Review Process

```markdown
# Pull Request Template

## Description
<!-- Brief description of changes -->

## Type of Change
- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Documentation
- [ ] Infrastructure

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guide
- [ ] No new lint errors
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Migration added (if schema change)
- [ ] ADR created (if architectural decision)

## Screenshots
<!-- If UI changes -->

## Related Issues
Closes #123
```

### 15.4 ADR Workflow

```markdown
# docs/adr/ADR-001-modular-monolith-architecture.md

# ADR-001: Modular Monolith Architecture

## Status
Accepted

## Context
We need to balance development velocity with future scalability.
Premature microservices would slow development.

## Decision
Use a modular monolith for core business domains with separate
runtimes for AI, workers, and search.

## Consequences
Positive:
- Faster development (no service boundaries)
- Simpler deployment (single API service)
- Easier refactoring (in-process calls)
- Shared database schema

Negative:
- Cannot scale domains independently
- Must enforce module boundaries via code review
- Future split requires extraction effort

## Alternatives Considered
1. Full microservices — rejected (too slow, premature)
2. Single monolith — rejected (AI/worker/search have different scaling needs)
```

### 15.5 Dependency Governance

```toml
# api/pyproject.toml

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "ARG", "PTH", "RUF"]
ignore = ["E501"]  # Handled by formatter

[tool.mypy]
strict = true
python_version = "3.12"
disallow_untyped_defs = true
disallow_any_unimported = true
no_implicit_optional = true
warn_return_any = true
warn_unused_ignores = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 15.6 Release Strategy

```
Versioning: SemVer (MAJOR.MINOR.PATCH)
    MAJOR: Breaking API changes
    MINOR: New features, backward compatible
    PATCH: Bug fixes, backward compatible

Release Cadence:
    Major: Every 6 months
    Minor: Every 2-4 weeks
    Patch: As needed (hotfix)

Release Process:
    1. Create release branch: release/v1.2.3
    2. Run full test suite
    3. Deploy to staging
    4. QA validation (2-5 days)
    5. Product owner approval
    6. Deploy to production (blue/green)
    7. Tag release: v1.2.3
    8. Merge to main + develop
    9. Update changelog
```

---

## 16. Implementation Roadmap

### 16.1 Phase 1: Foundation (Weeks 1-4)

```
Week 1-2: Repository & Infrastructure
  [ ] Initialize monorepo structure
  [ ] Set up Docker dev environment
  [ ] Configure CI/CD pipelines
  [ ] Set up PostgreSQL with pgvector
  [ ] Configure Alembic migrations
  [ ] Implement shared SDK package

Week 3-4: Core API Framework
  [ ] Implement FastAPI app factory
  [ ] Build middleware stack (auth, tenant, logging, audit)
  [ ] Implement exception handling
  [ ] Build pagination system
  [ ] Implement response envelope
  [ ] Create domain module template
  [ ] Implement in-memory event bus
```

### 16.2 Phase 2: Core Domains (Weeks 5-10)

```
Week 5-6: Contract Domain
  [ ] Contract CRUD endpoints
  [ ] Contract version management
  [ ] Contract relationships (MSA/SOW/Amendment)
  [ ] File upload to S3
  [ ] Contract search (basic)

Week 7-8: Ingestion Pipeline
  [ ] Document ingestion worker
  [ ] Text extraction (PyMuPDF/Tika)
  [ ] OCR fallback (Textract)
  [ ] Clause segmentation
  [ ] Chunking service

Week 9-10: AI Runtime
  [ ] AI runtime service setup
  [ ] LangGraph agent framework
  [ ] Risk analysis agent
  [ ] Clause classification agent
  [ ] Prompt management system
```

### 16.3 Phase 3: Intelligence (Weeks 11-16)

```
Week 11-12: AI Pipeline
  [ ] RAG pipeline implementation
  [ ] Embedding generation
  [ ] Vector search (pgvector)
  [ ] Model router with cost governance
  [ ] LLM caching

Week 13-14: Search Runtime
  [ ] Hybrid search (BM25 + vector)
  [ ] Cross-encoder re-ranking
  [ ] Saved searches
  [ ] Search indexing worker

Week 15-16: Workflow Engine
  [ ] Workflow CRUD
  [ ] Approval chains
  [ ] Escalation management
  [ ] SLA tracking
  [ ] Workflow worker
```

### 16.4 Phase 4: Enterprise Features (Weeks 17-24)

```
Week 17-18: Procurement & Vendors
  [ ] Vendor management
  [ ] Vendor risk scoring
  [ ] Spend analytics
  [ ] Procurement workflows

Week 19-20: Compliance & Obligations
  [ ] Compliance requirements
  [ ] Obligation extraction
  [ ] Remediation workflows
  [ ] Audit center

Week 21-22: Frontend Workspaces
  [ ] 3-panel workspace pattern
  [ ] Legal review workspace
  [ ] Vendor 360 workspace
  [ ] Contract detail workspace
  [ ] Global AI Copilot

Week 23-24: Analytics & Reporting
  [ ] KPI aggregation
  [ ] Analytics snapshots
  [ ] Executive dashboards
  [ ] Report generation
  [ ] Forecasting
```

### 16.5 Phase 5: Scale & Optimize (Weeks 25-32)

```
Week 25-26: Performance
  [ ] Query optimization
  [ ] Indexing review
  [ ] Caching strategy
  [ ] Connection pooling tuning
  [ ] Load testing

Week 27-28: Observability
  [ ] Distributed tracing
  [ ] Structured logging
  [ ] Metrics instrumentation
  [ ] AI telemetry
  [ ] Grafana dashboards
  [ ] Alerting rules

Week 29-30: Security & Compliance
  [ ] Security audit
  [ ] Penetration testing
  [ ] DLP implementation
  [ ] SOC 2 readiness
  [ ] GDPR compliance

Week 31-32: Production Readiness
  [ ] Blue/green deployment
  [ ] Disaster recovery testing
  [ ] Runbook creation
  [ ] Team training
  [ ] Production launch
```

### 16.6 Scalability Migration Roadmap

```
Phase 1 (Months 1-6): Modular Monolith
  - Single API service with domain modules
  - Separate AI, Worker, Search runtimes
  - Shared PostgreSQL database
  - Vertical scaling

Phase 2 (Months 7-12): Read Replicas
  - Add PostgreSQL read replicas
  - Split read/write paths in repository layer
  - Search runtime scales independently
  - AI runtime scales independently

Phase 3 (Months 13-18): Domain Extraction
  - Extract high-traffic domains (contracts, search)
  - Deploy as independent services
  - Event-driven communication
  - Independent scaling per domain

Phase 4 (Months 19-24): Full Microservices
  - All domains extractable as needed
  - Service mesh (Istio)
  - Database per service (if needed)
  - Global event bus (Kafka)
```

### 16.7 Technical Debt Prevention

```
1. Architecture Decision Records (ADRs)
   - Every architectural decision documented
   - Reviewed by architecture team
   - Stored in docs/adr/

2. Automated Quality Gates
   - CI: lint, type check, test, coverage > 80%
   - PR: required reviews, no failing tests
   - Release: staging validation, smoke tests

3. Code Health Metrics
   - Cyclomatic complexity < 10
   - Test coverage > 80%
   - No TODOs in production code
   - No deprecated dependencies

4. Regular Refactoring
   - Dedicated refactoring sprints every quarter
   - Boy scout rule: leave code cleaner than found
   - Dependency upgrade automation (Dependabot)

5. Monitoring Debt
   - Service-level objectives for all services
   - Error budgets tracked monthly
   - Debt prioritized when error budget consumed

6. Knowledge Sharing
   - Weekly tech talks
   - Pair programming for complex features
   - Onboarding documentation
   - Runbooks for operations
```
