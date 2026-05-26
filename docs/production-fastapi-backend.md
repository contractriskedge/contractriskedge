# ContractRiskEdge — Production FastAPI Backend Implementation Blueprint

## V1 Modular Monolith — AI-Native Contract Intelligence Platform

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [FastAPI Application Design](#2-fastapi-application-design)
3. [API Layer Design](#3-api-layer-design)
4. [Service Layer Design](#4-service-layer-design)
5. [Repository Layer Design](#5-repository-layer-design)
6. [Domain Event System](#6-domain-event-system)
7. [Background Job Architecture](#7-background-job-architecture)
8. [Auth + Tenant Enforcement](#8-auth--tenant-enforcement)
9. [Validation + Error Handling](#9-validation--error-handling)
10. [AI Runtime Integration](#10-ai-runtime-integration)
11. [Search Integration](#11-search-integration)
12. [Observability](#12-observability)
13. [Testing Strategy](#13-testing-strategy)
14. [Engineering Governance](#14-engineering-governance)

---

## 1. Project Structure

### 1.1 Complete Folder Layout

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app factory
│   ├── config.py                        # Pydantic Settings
│   ├── dependencies.py                  # FastAPI dependency injection
│   ├── lifecycle.py                     # Startup/shutdown event handlers
│   │
│   ├── kernel/                          # SHARED KERNEL — no domain imports
│   │   ├── __init__.py
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── session.py               # AsyncSession factory
│   │   │   ├── unit_of_work.py          # UoW context manager
│   │   │   └── base.py                  # DeclarativeBase
│   │   │
│   │   ├── repository/
│   │   │   ├── __init__.py
│   │   │   └── base.py                  # Abstract BaseRepository
│   │   │
│   │   ├── service/
│   │   │   ├── __init__.py
│   │   │   └── base.py                  # Abstract BaseService
│   │   │
│   │   ├── events/
│   │   │   ├── __init__.py
│   │   │   ├── bus.py                   # In-memory EventBus
│   │   │   ├── dispatcher.py            # Handler registration
│   │   │   └── interface.py             # DomainEvent base class
│   │   │
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── request_id.py            # X-Request-ID
│   │   │   ├── tenant_context.py        # Tenant resolution
│   │   │   ├── auth_context.py          # JWT → UserContext
│   │   │   ├── audit_middleware.py      # Request audit logging
│   │   │   └── logging_middleware.py    # Structured request logging
│   │   │
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                  # JWT verification
│   │   │   ├── rbac.py                  # Permission checking
│   │   │   └── encryption.py            # Field-level encryption
│   │   │
│   │   ├── telemetry/
│   │   │   ├── __init__.py
│   │   │   ├── tracer.py                # OpenTelemetry setup
│   │   │   ├── metrics.py               # Prometheus metrics
│   │   │   └── logger.py                # structlog configuration
│   │   │
│   │   ├── web/
│   │   │   ├── __init__.py
│   │   │   ├── pagination.py            # PaginationParams, PaginatedResponse
│   │   │   ├── response.py              # ApiResponse envelope
│   │   │   ├── exceptions.py            # AppError hierarchy
│   │   │   └── error_handlers.py        # FastAPI exception handlers
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── dates.py                 # Date/time utilities
│   │       └── validators.py            # Shared validators
│   │
│   ├── domains/                         # DOMAIN MODULES
│   │   ├── auth/                        # Auth, users, tenants
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # LoginRequest, UserResponse
│   │   │   ├── models.py                # User, Tenant ORM models
│   │   │   ├── repository.py            # UserRepository, TenantRepository
│   │   │   ├── service.py               # AuthService, UserService
│   │   │   ├── router.py                # /auth, /users, /tenants
│   │   │   ├── events.py                # UserCreated, UserInvited
│   │   │   ├── exceptions.py            # UserNotFoundError
│   │   │   └── tests/
│   │   │       ├── test_router.py
│   │   │       ├── test_service.py
│   │   │       └── test_repository.py
│   │   │
│   │   ├── contracts/                   # Contract CRUD + upload
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # ContractCreate, ContractResponse
│   │   │   ├── models.py                # Contract ORM model
│   │   │   ├── repository.py            # ContractRepository
│   │   │   ├── service.py               # ContractService
│   │   │   ├── router.py                # /contracts
│   │   │   ├── events.py                # ContractUploaded
│   │   │   ├── exceptions.py
│   │   │   └── tests/
│   │   │
│   │   ├── ingestion/                   # OCR + chunking + embedding
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py                # IngestionJob, DocumentPage
│   │   │   ├── repository.py
│   │   │   ├── service.py               # IngestionService
│   │   │   ├── router.py                # /ingestion (admin)
│   │   │   ├── ocr/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── extractor.py         # PyMuPDF + Tesseract
│   │   │   │   └── quality.py           # OCR quality scoring
│   │   │   ├── chunking/
│   │   │   │   ├── __init__.py
│   │   │   │   └── semantic.py          # Semantic chunker
│   │   │   ├── embedding/
│   │   │   │   ├── __init__.py
│   │   │   │   └── embedder.py          # OpenAI embedding client
│   │   │   ├── events.py
│   │   │   ├── exceptions.py
│   │   │   └── tests/
│   │   │
│   │   ├── search/                      # Semantic + full-text search
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # SearchRequest, SearchResponse
│   │   │   ├── service.py               # SearchService (hybrid)
│   │   │   ├── router.py                # /search
│   │   │   ├── engine/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── hybrid.py            # BM25 + vector fusion
│   │   │   │   ├── vector.py            # pgvector queries
│   │   │   │   └── fulltext.py          # PostgreSQL FTS
│   │   │   ├── events.py
│   │   │   └── tests/
│   │   │
│   │   ├── ai/                          # AI analysis pipeline
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # AnalysisRequest, AnalysisResponse
│   │   │   ├── models.py                # AIAnalysis, AIFinding
│   │   │   ├── repository.py
│   │   │   ├── service.py               # AIService
│   │   │   ├── router.py                # /ai
│   │   │   ├── pipeline/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py      # Multi-step pipeline
│   │   │   │   ├── risk_analysis.py     # Risk scoring step
│   │   │   │   └── classify.py          # Clause classification step
│   │   │   ├── llm/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── interface.py         # LLMProvider ABC
│   │   │   │   ├── openai_provider.py   # OpenAI implementation
│   │   │   │   ├── anthropic_provider.py
│   │   │   │   ├── router.py            # ModelRouter with fallback
│   │   │   │   └── prompt_manager.py    # Jinja2 prompt templates
│   │   │   ├── cache/
│   │   │   │   ├── __init__.py
│   │   │   │   └── llm_cache.py         # Redis semantic cache
│   │   │   ├── events.py
│   │   │   ├── exceptions.py
│   │   │   └── tests/
│   │   │
│   │   ├── workflows/                   # Workflow engine
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py                # Workflow, WorkflowStep, Approval
│   │   │   ├── repository.py
│   │   │   ├── service.py               # WorkflowService
│   │   │   ├── router.py                # /workflows
│   │   │   ├── events.py
│   │   │   ├── exceptions.py
│   │   │   └── tests/
│   │   │
│   │   ├── notifications/              # In-app + email
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py                # Notification
│   │   │   ├── repository.py
│   │   │   ├── service.py               # NotificationService
│   │   │   ├── router.py                # /notifications
│   │   │   └── tests/
│   │   │
│   │   ├── comments/                    # Comments + annotations
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py                # Comment
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   ├── router.py                # /comments
│   │   │   └── tests/
│   │   │
│   │   ├── audit/                       # Audit logging
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py                # AuditLog (append-only)
│   │   │   ├── repository.py
│   │   │   ├── service.py               # AuditService
│   │   │   ├── router.py                # /audit (admin)
│   │   │   └── tests/
│   │   │
│   │   └── reporting/                   # Basic reporting
│   │       ├── __init__.py
│   │       ├── schemas.py
│   │       ├── service.py               # ReportingService
│   │       ├── router.py                # /reports
│   │       └── tests/
│   │
│   └── integrations/                    # External integrations
│       ├── __init__.py
│       ├── storage/
│       │   ├── __init__.py
│       │   └── s3.py                    # S3-compatible storage
│       ├── llm/
│       │   ├── __init__.py
│       │   └── client.py                # Shared HTTP client
│       └── email/
│           ├── __init__.py
│           └── sendgrid.py              # Email sending
│
├── workers/                             # BACKGROUND WORKERS
│   ├── __init__.py
│   ├── celery_app.py                    # Celery application
│   ├── celery_config.py                 # Beat schedule, queues
│   ├── ingestion.py                     # Document processing tasks
│   ├── ai_worker.py                     # AI analysis tasks
│   ├── notifications.py                 # Email/push tasks
│   └── maintenance.py                   # Scheduled maintenance
│
├── alembic/
│   ├── env.py
│   ├── versions/
│   │   ├── 001_create_tenants_users.py
│   │   ├── 002_create_contracts.py
│   │   └── ...
│   └── script.py.mako
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Global fixtures
│   ├── factories/                       # Test data factories
│   │   ├── __init__.py
│   │   ├── contract_factory.py
│   │   └── user_factory.py
│   ├── unit/                            # Unit tests (service layer)
│   ├── integration/                     # Integration tests (API + DB)
│   └── e2e/                             # End-to-end tests
│
├── app/__init__.py
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── pytest.ini
```

### 1.2 Import Rules

```
LAYER RULES (enforced via import-linter in CI):

1. kernel/ → NO imports from domains/ or workers/
2. domains/{x}/ → CAN import from kernel/ ONLY
3. domains/{x}/ → CANNOT import from domains/{y}/ (cross-domain via EventBus)
4. workers/ → CAN import from domains/ and kernel/
5. integrations/ → CAN import from kernel/ ONLY
6. tests/ → CAN import from anything
7. Circular imports → BUILD FAILURE

FOLDER IMPORT RULES (within a domain):
  router.py → service.py ONLY
  service.py → repository.py, events/, integrations/ ONLY
  repository.py → models.py ONLY
  models.py → NO domain imports (SQLAlchemy + kernel only)
```

---

## 2. FastAPI Application Design

### 2.1 App Factory

```python
# app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.lifecycle import register_domain_services, register_event_handlers
from app.kernel.database.session import create_session_factory
from app.kernel.events.bus import EventBus
from app.kernel.middleware.request_id import RequestIDMiddleware
from app.kernel.middleware.tenant_context import TenantContextMiddleware
from app.kernel.middleware.auth_context import AuthContextMiddleware
from app.kernel.middleware.logging_middleware import LoggingMiddleware
from app.kernel.middleware.audit_middleware import AuditMiddleware
from app.kernel.web.exceptions import register_exception_handlers
from app.kernel.telemetry.tracer import setup_tracing
from app.kernel.telemetry.logger import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ────────────────────────────────────────────────────
    setup_logging()
    setup_tracing(app)

    # Database
    app.state.db_factory = create_session_factory(settings.database_url)
    app.state.event_bus = EventBus()

    # Domain services
    app.state.services = await register_domain_services(app.state)

    # Event handlers
    register_event_handlers(app.state.event_bus, app.state.services)

    yield

    # ── SHUTDOWN ───────────────────────────────────────────────────
    await app.state.db_factory.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ContractRiskEdge API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    # Middleware order matters (first = outermost)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(AuthContextMiddleware)
    app.add_middleware(AuditMiddleware)

    register_exception_handlers(app)
    _register_routers(app)

    return app


def _register_routers(app: FastAPI):
    """Auto-discover and register all domain routers."""
    from app.domains.auth.router import router as auth_router
    from app.domains.contracts.router import router as contracts_router
    from app.domains.ingestion.router import router as ingestion_router
    from app.domains.search.router import router as search_router
    from app.domains.ai.router import router as ai_router
    from app.domains.workflows.router import router as workflows_router
    from app.domains.notifications.router import router as notifications_router
    from app.domains.comments.router import router as comments_router
    from app.domains.audit.router import router as audit_router
    from app.domains.reporting.router import router as reporting_router

    prefix = "/api/v1"
    app.include_router(auth_router, prefix=prefix)
    app.include_router(contracts_router, prefix=prefix)
    app.include_router(ingestion_router, prefix=prefix)
    app.include_router(search_router, prefix=prefix)
    app.include_router(ai_router, prefix=prefix)
    app.include_router(workflows_router, prefix=prefix)
    app.include_router(notifications_router, prefix=prefix)
    app.include_router(comments_router, prefix=prefix)
    app.include_router(audit_router, prefix=prefix)
    app.include_router(reporting_router, prefix=prefix)


app = create_app()
```

### 2.2 Configuration

```python
# app/config.py

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev"
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_recycle: int = 3600

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth0
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_issuer: str = ""
    auth0_jwks_url: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_organization: str = ""
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 1536

    # S3
    s3_bucket: str = "contractrisk-documents"
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]

    # Sentry
    sentry_dsn: str = ""

    # OpenTelemetry
    otel_endpoint: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### 2.3 Dependency Injection

```python
# app/dependencies.py

from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.database.session import get_session
from app.kernel.security.auth import UserContext


async def get_db(request: Request) -> AsyncSession:
    """Yield session with automatic commit/rollback."""
    async with request.app.state.db_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(request: Request) -> UserContext:
    """From auth middleware — guaranteed to exist on authenticated routes."""
    return request.state.user


async def get_tenant_id(request: Request) -> str:
    return request.state.tenant_id


async def get_event_bus(request: Request):
    return request.app.state.event_bus


# ── Domain-specific DI ─────────────────────────────────────────────

async def get_contract_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    event_bus = Depends(get_event_bus),
):
    from app.domains.contracts.repository import ContractRepository
    from app.domains.contracts.service import ContractService
    return ContractService(
        repository=ContractRepository(db),
        event_bus=event_bus,
        user=user,
        tenant_id=tenant_id,
    )


async def get_workflow_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    event_bus = Depends(get_event_bus),
):
    from app.domains.workflows.repository import WorkflowRepository
    from app.domains.workflows.service import WorkflowService
    return WorkflowService(
        repository=WorkflowRepository(db),
        event_bus=event_bus,
        user=user,
        tenant_id=tenant_id,
    )
```

### 2.4 Database Session

```python
# app/kernel/database/session.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session(db_factory) -> AsyncSession:
    async with db_factory() as session:
        yield session
```

### 2.5 Middleware Chain

```python
# Middleware execution order (outermost → innermost):

# 1. CORSMiddleware           — CORS headers (always first)
# 2. RequestIDMiddleware      — Assign X-Request-ID
# 3. LoggingMiddleware        — Log request/response
# 4. TenantContextMiddleware  — Resolve tenant_id → request.state.tenant_id
# 5. AuthContextMiddleware    — Verify JWT → request.state.user
# 6. AuditMiddleware          — Log mutations to audit_logs

# Each middleware:
#   - Processes request before handler
#   - Sets request.state attributes
#   - Processes response after handler
#   - Handles errors gracefully (500 → error response)
```

---

## 3. API Layer Design

### 3.1 Router Template

```python
# domains/contracts/router.py

from fastapi import APIRouter, Depends, Query, status

from app.kernel.web.pagination import PaginatedResponse, PaginationParams
from app.dependencies import get_contract_service
from app.domains.contracts.schemas import ContractCreate, ContractResponse, ContractFilters

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("/", response_model=PaginatedResponse[ContractResponse])
async def list_contracts(
    filters: ContractFilters = Depends(),
    pagination: PaginationParams = Depends(),
    service = Depends(get_contract_service),
):
    """List contracts with filtering, sorting, and pagination."""
    items, total = await service.list(filters, pagination)
    return PaginatedResponse(items=items, total=total, pagination=pagination)


@router.post("/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    body: ContractCreate,
    service = Depends(get_contract_service),
):
    """Upload and create a new contract."""
    return await service.create(body)


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    service = Depends(get_contract_service),
):
    """Get contract by ID with full details."""
    return await service.get_by_id(contract_id)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: str,
    service = Depends(get_contract_service),
):
    """Soft-delete a contract."""
    await service.delete(contract_id)
```

### 3.2 Response Envelope

```python
# app/kernel/web/response.py

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""
    data: T
    request_id: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: Optional[str] = None
    details: Optional[dict] = None
```

### 3.3 Pagination

```python
# app/kernel/web/pagination.py

from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationMeta
    request_id: Optional[str] = None
```

### 3.4 API Standards

```
ENDPOINT NAMING:
  GET    /{resource}           → List resources
  POST   /{resource}           → Create resource
  GET    /{resource}/{id}      → Get resource
  PUT    /{resource}/{id}      → Full update
  PATCH  /{resource}/{id}      → Partial update
  DELETE /{resource}/{id}      → Delete resource

STATUS CODES:
  200 OK          — Successful GET, PUT, PATCH
  201 Created     — Successful POST
  204 No Content  — Successful DELETE
  400 Bad Request — Validation error
  401 Unauthorized— Missing/invalid auth
  403 Forbidden   — Insufficient permissions
  404 Not Found   — Resource not found
  409 Conflict    — Duplicate/state conflict
  422 Unprocessable — Validation error
  429 Too Many Requests — Rate limit
  500 Server Error— Unhandled error

FILTERING:
  ?status=active&contract_type=msa
  ?tags=tech,cloud

SORTING:
  ?sort_by=created_at&sort_order=desc

PAGINATION:
  ?page=1&page_size=20
```

---

## 4. Service Layer Design

### 4.1 Service Template

```python
# domains/contracts/service.py

from dataclasses import dataclass, field
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

@dataclass
class ContractService:
    repository: "ContractRepository"
    event_bus: EventBus
    user: UserContext
    tenant_id: str

    async def create(self, data: "ContractCreate") -> "ContractResponse":
        # 1. Validate business rules
        if data.file_size > 100_000_000:  # 100MB
            raise ContractTooLargeError()

        # 2. Upload file to S3
        file_path = await self._upload_to_s3(data)

        # 3. Persist
        contract = await self.repository.create(
            tenant_id=self.tenant_id,
            created_by=self.user.id,
            filename=data.filename,
            content_type=data.content_type,
            file_size=data.file_size,
            file_path=file_path,
            contract_type=data.contract_type,
            metadata=data.metadata,
        )

        # 4. Emit domain event (async, non-blocking)
        await self.event_bus.emit(
            ContractUploaded(
                contract_id=contract.contract_id,
                tenant_id=self.tenant_id,
                file_path=file_path,
            )
        )

        return ContractResponse.from_orm(contract)

    async def get_by_id(self, contract_id: str) -> "ContractResponse":
        contract = await self.repository.get_by_id(contract_id, self.tenant_id)
        if not contract:
            raise ContractNotFoundError(contract_id)
        return ContractResponse.from_orm(contract)

    async def list(self, filters, pagination) -> tuple[list, int]:
        return await self.repository.list(self.tenant_id, filters, pagination)

    async def delete(self, contract_id: str) -> None:
        contract = await self.repository.get_by_id(contract_id, self.tenant_id)
        if not contract:
            raise ContractNotFoundError(contract_id)
        await self.repository.soft_delete(contract_id, self.tenant_id)

    async def _upload_to_s3(self, data) -> str:
        from app.integrations.storage.s3 import s3_client
        return await s3_client.upload(
            bucket=settings.s3_bucket,
            key=f"{self.tenant_id}/{data.filename}",
            body=data.file,
        )
```

### 4.2 Transaction Boundaries

```python
# Rule: One service method = one transaction
# The session is managed by the dependency injection (get_db)
# commit happens automatically on success
# rollback happens automatically on exception

# For multi-repository operations, use the repository directly:

async def create_with_relationships(self, data):
    # Single transaction across multiple repositories
    contract = await self.repository.create(...)
    await self.related_repo.create(contract_id=contract.contract_id, ...)
    # commit happens when the service method returns successfully
    return contract
```

---

## 5. Repository Layer Design

### 5.1 Base Repository

```python
# app/kernel/repository/base.py

from dataclasses import dataclass
from typing import Any
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class BaseRepository:
    """Abstract base repository with common query patterns."""

    session: AsyncSession

    async def execute(self, stmt):
        return await self.session.execute(stmt)

    async def scalar(self, stmt):
        result = await self.session.execute(stmt)
        return result.scalar()

    async def paginate(self, query, page: int, page_size: int):
        """Offset-based pagination with total count."""
        total = await self.scalar(select(func.count()).select_from(query.subquery()))
        result = await self.session.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

    async def paginate_keyset(self, query, cursor: Any, limit: int):
        """Keyset pagination for large datasets."""
        result = await self.session.execute(query.limit(limit))
        items = result.scalars().all()
        next_cursor = items[-1].created_at.isoformat() if items else None
        return items, next_cursor
```

### 5.2 Domain Repository

```python
# domains/contracts/repository.py

from dataclasses import dataclass
from sqlalchemy import select, update, delete
from app.kernel.repository.base import BaseRepository
from app.domains.contracts.models import Contract

@dataclass
class ContractRepository(BaseRepository):

    async def create(self, **kwargs) -> Contract:
        contract = Contract(**kwargs)
        self.session.add(contract)
        await self.session.flush()
        return contract

    async def get_by_id(self, contract_id: str, tenant_id: str) -> Contract | None:
        stmt = select(Contract).where(
            Contract.contract_id == contract_id,
            Contract.tenant_id == tenant_id,
            Contract.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, tenant_id: str, filters, pagination) -> tuple[list[Contract], int]:
        query = select(Contract).where(
            Contract.tenant_id == tenant_id,
            Contract.deleted_at.is_(None),
        )
        if filters.status:
            query = query.where(Contract.status == filters.status)
        if filters.contract_type:
            query = query.where(Contract.contract_type == filters.contract_type)

        sort_col = getattr(Contract, pagination.sort_by)
        order = sort_col.desc() if pagination.sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)

        return await self.paginate(query, pagination.page, pagination.page_size)

    async def soft_delete(self, contract_id: str, tenant_id: str) -> None:
        stmt = update(Contract).where(
            Contract.contract_id == contract_id,
            Contract.tenant_id == tenant_id,
        ).values(deleted_at=func.now())
        await self.session.execute(stmt)

    async def update_status(self, contract_id: str, tenant_id: str, status: str) -> None:
        stmt = update(Contract).where(
            Contract.contract_id == contract_id,
            Contract.tenant_id == tenant_id,
        ).values(status=status)
        await self.session.execute(stmt)
```

### 5.3 N+1 Prevention

```python
# ❌ N+1: Loading chunks for each contract in a loop
contracts = await contract_repo.list(...)
for contract in contracts:
    chunks = await chunk_repo.get_by_contract(contract.contract_id)  # N queries

# ✅ Eager loading: Single query with JOIN
stmt = select(Contract).options(selectinload(Contract.chunks)).where(...)
```

---

## 6. Domain Event System

### 6.1 Event Base Class

```python
# app/kernel/events/interface.py

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    tenant_id: str = ""
    correlation_id: str = ""
    actor_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__
```

### 6.2 Event Definitions

```python
# domains/contracts/events.py

from app.kernel.events.interface import DomainEvent

class ContractUploaded(DomainEvent):
    event_type: str = "contract.uploaded"

class ContractProcessed(DomainEvent):
    event_type: str = "contract.processed"

class ContractDeleted(DomainEvent):
    event_type: str = "contract.deleted"


# domains/workflows/events.py

class WorkflowCreated(DomainEvent):
    event_type: str = "workflow.created"

class WorkflowApproved(DomainEvent):
    event_type: str = "workflow.approved"

class WorkflowEscalated(DomainEvent):
    event_type: str = "workflow.escalated"


# domains/ai/events.py

class AIAnalysisCompleted(DomainEvent):
    event_type: str = "ai.analysis.completed"

class RiskFindingCreated(DomainEvent):
    event_type: str = "ai.finding.created"
```

### 6.3 Event Bus

```python
# app/kernel/events/bus.py

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

Handler = Callable[..., Awaitable[None]]

class EventBus:
    """In-memory event bus. Synchronous within the process."""

    def __init__(self):
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def register(self, event_type: type, handler: Handler):
        self._handlers[event_type].append(handler)

    async def emit(self, event) -> None:
        """Emit event to all registered handlers. Fire-and-forget."""
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return
        results = await asyncio.gather(
            *[h(event) for h in handlers],
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    "Event handler %s failed for %s: %s",
                    handler.__name__, type(event).__name__, result,
                )
```

### 6.4 Handler Registration

```python
# app/lifecycle.py

from app.kernel.events.bus import EventBus

def register_event_handlers(bus: EventBus, services: dict):
    """Wire domain events to handlers on startup."""

    # Contract → Ingestion
    bus.register(ContractUploaded, services["ingestion"].on_contract_uploaded)

    # Ingestion → AI
    bus.register(ContractProcessed, services["ai"].on_contract_processed)

    # AI → Workflows + Notifications
    bus.register(AIAnalysisCompleted, services["workflows"].on_analysis_completed)
    bus.register(RiskFindingCreated, services["notifications"].on_risk_finding)

    # Workflows → Notifications
    bus.register(WorkflowApproved, services["notifications"].on_workflow_approved)
    bus.register(WorkflowEscalated, services["notifications"].on_escalation)
```

---

## 7. Background Job Architecture

### 7.1 Celery Configuration

```python
# workers/celery_app.py

from celery import Celery
from kombu import Queue

celery_app = Celery(
    "contractrisk",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_queues=[
        Queue("ingestion"),
        Queue("ai"),
        Queue("notifications"),
        Queue("default"),
    ],
    task_routes={
        "workers.ingestion.*": {"queue": "ingestion"},
        "workers.ai_worker.*": {"queue": "ai"},
        "workers.notifications.*": {"queue": "notifications"},
    },
    beat_schedule={
        "vacuum-analyze-hourly": {
            "task": "workers.maintenance.vacuum_analyze",
            "schedule": 3600.0,
        },
        "cleanup-expired-notifications": {
            "task": "workers.maintenance.cleanup_notifications",
            "schedule": 86400.0,
        },
    },
)
```

### 7.2 Task Template

```python
# workers/ingestion.py

from celery import Task
from workers.celery_app import celery_app

class IngestionTask(Task):
    """Base task for ingestion jobs with retry and logging."""
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


@celery_app.task(base=IngestionTask, name="process_document")
def process_document(contract_id: str, tenant_id: str):
    """Full ingestion pipeline: extract → chunk → embed."""
    logger.info("Processing document", contract_id=contract_id)

    # 1. Extract text (PyMuPDF → Tesseract fallback)
    text = extract_text(contract_id, tenant_id)

    # 2. Chunk text
    chunks = chunk_text(text)

    # 3. Generate embeddings
    embeddings = generate_embeddings(chunks)

    # 4. Store
    store_chunks(contract_id, tenant_id, chunks, embeddings)

    # 5. Update contract status
    update_contract_status(contract_id, tenant_id, "ready")

    # 6. Emit event (via Redis pub/sub or direct DB)
    emit_event("contract.processed", contract_id=contract_id, tenant_id=tenant_id)
```

### 7.3 Queue Ownership

```
QUEUE OWNERSHIP RULES:
  ingestion queue  → ONLY ingestion tasks
  ai queue         → ONLY AI analysis tasks
  notifications    → ONLY notification delivery tasks
  default          → Everything else (maintenance, etc.)

TASK NAMING:
  workers.ingestion.process_document
  workers.ai_worker.analyze_contract
  workers.notifications.send_email
  workers.maintenance.vacuum_analyze
```

---

## 8. Auth + Tenant Enforcement

### 8.1 JWT Verification

```python
# app/kernel/security/auth.py

from dataclasses import dataclass
from jose import jwt, JWTError
from app.config import settings

@dataclass
class UserContext:
    id: str
    email: str
    tenant_id: str
    role: str
    permissions: list[str]


async def verify_token(token: str) -> UserContext:
    """Verify JWT and return user context."""
    try:
        payload = jwt.decode(
            token,
            settings.auth0_jwks_url,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=settings.auth0_issuer,
        )
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}")

    return UserContext(
        id=payload["sub"],
        email=payload.get("email", ""),
        tenant_id=payload.get(f"{settings.auth0_audience}/tenant_id", ""),
        role=payload.get(f"{settings.auth0_audience}/role", "viewer"),
        permissions=payload.get("permissions", []),
    )
```

### 8.2 Auth Middleware

```python
# app/kernel/middleware/auth_context.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.kernel.security.auth import verify_token

EXCLUDED_PATHS = {"/api/v1/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"}

class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authorization header")

        token = auth_header.split(" ")[1]
        request.state.user = await verify_token(token)

        return await call_next(request)
```

### 8.3 Tenant Middleware

```python
# app/kernel/middleware/tenant_context.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Tenant comes from JWT or X-Tenant-ID header
        tenant_id = (
            getattr(request.state, "user", None)
            and request.state.user.tenant_id
            or request.headers.get("X-Tenant-ID")
        )

        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant context required")

        request.state.tenant_id = tenant_id

        # Set PostgreSQL session context for RLS
        # This is done in the database session factory

        return await call_next(request)
```

### 8.4 RBAC Enforcement

```python
# app/kernel/security/rbac.py

from functools import wraps
from fastapi import HTTPException

def require_permission(resource: str, action: str):
    """Decorator to enforce RBAC on endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next(
                (a for a in args if hasattr(a, "state")),
                kwargs.get("request"),
            )
            if not request:
                raise HTTPException(status_code=500, detail="Request context not found")

            user = request.state.user
            permission = f"{resource}:{action}"

            if user.role == "admin":
                return await func(*args, **kwargs)

            if permission not in user.permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}",
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage:
# @router.delete("/{contract_id}")
# @require_permission("contract", "delete")
# async def delete_contract(...):
```

---

## 9. Validation + Error Handling

### 9.1 Exception Hierarchy

```python
# app/kernel/web/exceptions.py

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

# Domain-specific
class ContractNotFoundError(NotFoundError):
    pass

class ContractTooLargeError(ValidationError):
    pass
```

### 9.2 Error Handler

```python
# app/kernel/web/error_handlers.py

from fastapi import Request
from fastapi.responses import JSONResponse
from app.kernel.web.exceptions import AppError

def register_exception_handlers(app):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None),
            },
        )
```

---

## 10. AI Runtime Integration

### 10.1 Provider Interface

```python
# domains/ai/llm/interface.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMRequest:
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.1
    max_tokens: int = 4096
    response_format: dict | None = None

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float

class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...
```

### 10.2 AI Service

```python
# domains/ai/service.py

from dataclasses import dataclass
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

@dataclass
class AIService:
    repository: "AIRepository"
    pipeline: "AnalysisPipeline"
    event_bus: EventBus
    user: UserContext
    tenant_id: str

    async def analyze_contract(self, contract_id: str) -> "AnalysisResponse":
        # 1. Get contract + chunks
        chunks = await self.repository.get_chunks(contract_id, self.tenant_id)
        if not chunks:
            raise NoChunksError(contract_id)

        # 2. Run pipeline (async, in worker)
        from workers.ai_worker import analyze_contract_task
        analyze_contract_task.delay(contract_id, self.tenant_id)

        # 3. Return pending analysis
        return AnalysisResponse(analysis_id="pending", status="processing")

    async def store_results(self, contract_id: str, results: dict) -> "AnalysisResponse":
        analysis = await self.repository.create_analysis(
            contract_id=contract_id,
            tenant_id=self.tenant_id,
            risk_score=results["risk_score"],
            findings=results["findings"],
            model_used=results["model"],
            tokens=results["total_tokens"],
            cost=results["cost"],
        )

        await self.event_bus.emit(
            AIAnalysisCompleted(
                contract_id=contract_id,
                tenant_id=self.tenant_id,
                analysis_id=analysis.analysis_id,
            )
        )

        return AnalysisResponse.from_orm(analysis)
```

---

## 11. Search Integration

### 11.1 Search Service

```python
# domains/search/service.py

from dataclasses import dataclass
from app.domains.search.engine.hybrid import HybridSearchEngine

@dataclass
class SearchService:
    engine: HybridSearchEngine

    async def search(self, request: "SearchRequest") -> "SearchResponse":
        results, total = await self.engine.search(
            query=request.query,
            tenant_id=request.tenant_id,
            filters=request.filters,
            page=request.page,
            page_size=request.page_size,
        )

        # Log search query for analytics
        await self._log_query(request, total)

        return SearchResponse(
            results=results,
            total=total,
            page=request.page,
            page_size=request.page_size,
        )

    async def _log_query(self, request, total):
        from app.domains.search.models import SearchQuery
        # Async log to search_queries table
```

### 11.2 Hybrid Search Engine

```python
# domains/search/engine/hybrid.py

from dataclasses import dataclass
from sqlalchemy import text

@dataclass
class HybridSearchEngine:
    """BM25 + Vector fusion via Reciprocal Rank Fusion."""

    K: int = 60
    VECTOR_WEIGHT: float = 0.7
    BM25_WEIGHT: float = 0.3

    async def search(self, query, tenant_id, filters, page, page_size):
        # 1. Embed query
        query_vector = await self._embed(query)

        # 2. Vector search (pgvector)
        vector_results = await self._vector_search(query_vector, tenant_id, filters)

        # 3. BM25 search (PostgreSQL FTS)
        bm25_results = await self._bm25_search(query, tenant_id, filters)

        # 4. RRF fusion
        fused = self._rrf(vector_results, bm25_results)

        # 5. Paginate
        start = (page - 1) * page_size
        return fused[start:start + page_size], len(fused)

    async def _vector_search(self, query_vector, tenant_id, filters):
        sql = """
            SELECT chunk_id, contract_id, text,
                   1 - (embedding <=> :query) AS score
            FROM chunks
            WHERE tenant_id = :tenant_id
              AND embedding IS NOT NULL
              AND is_active = TRUE
            ORDER BY embedding <=> :query
            LIMIT 50
        """
        result = await self.session.execute(text(sql), {
            "query": query_vector, "tenant_id": tenant_id,
        })
        return result.fetchall()

    async def _bm25_search(self, query, tenant_id, filters):
        sql = """
            SELECT chunk_id, contract_id, text,
                   ts_rank(search_vector, plainto_tsquery('english', :query)) AS score
            FROM chunks
            WHERE tenant_id = :tenant_id
              AND search_vector @@ plainto_tsquery('english', :query)
              AND is_active = TRUE
            ORDER BY score DESC
            LIMIT 50
        """
        result = await self.session.execute(text(sql), {
            "query": query, "tenant_id": tenant_id,
        })
        return result.fetchall()

    def _rrf(self, vector_results, bm25_results):
        scores = {}
        for rank, row in enumerate(vector_results):
            scores[row.chunk_id] = self.VECTOR_WEIGHT / (self.K + rank)
        for rank, row in enumerate(bm25_results):
            scores[row.chunk_id] = scores.get(row.chunk_id, 0) + self.BM25_WEIGHT / (self.K + rank)
        return sorted(
            [{"chunk_id": k, "score": v} for k, v in scores.items()],
            key=lambda x: x["score"], reverse=True,
        )
```

---

## 12. Observability

### 12.1 Structured Logging

```python
# app/kernel/telemetry/logger.py

import structlog

def setup_logging():
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
# logger.info("contract.uploaded", contract_id=id, tenant_id=tid, file_size=fs)
```

### 12.2 Request ID Middleware

```python
# app/kernel/middleware/request_id.py

from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

---

## 13. Testing Strategy

### 13.1 Test Structure

```
tests/
├── conftest.py              # Global fixtures (db session, client, auth)
├── factories/               # Test data factories
│   ├── contract_factory.py
│   └── user_factory.py
├── unit/                    # Service layer tests (mocked DB)
│   ├── test_contract_service.py
│   └── test_workflow_service.py
├── integration/             # API + DB tests (real DB)
│   ├── test_contracts_api.py
│   └── test_workflows_api.py
└── e2e/                     # End-to-end (upload → process → analyze → review)
    └── test_full_workflow.py
```

### 13.2 Conftest

```python
# tests/conftest.py

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    """Test database session with transaction rollback."""
    engine = create_async_engine("postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev_test")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def test_user():
    return UserContext(id="test-user", email="test@test.com", tenant_id="test-tenant", role="admin", permissions=[])

@pytest.fixture
def contract_service(db_session, test_user):
    return ContractService(
        repository=ContractRepository(db_session),
        event_bus=MockEventBus(),
        user=test_user,
        tenant_id="test-tenant",
    )
```

---

## 14. Engineering Governance

### 14.1 Forbidden Patterns

```
❌ Circular imports between domain modules
   → Enforced via import-linter in CI

❌ Direct DB access from routers
   → Router → Service → Repository only

❌ Synchronous blocking calls in async endpoints
   → Use asyncio.to_thread() or worker tasks

❌ Hardcoded secrets in code
   → Use config.py + .env + secret store

❌ N+1 queries in REST endpoints
   → Use selectinload or JOIN

❌ SELECT * in production queries
   → Always specify columns

❌ Unbounded pagination
   → Always set LIMIT

❌ Business logic in routers
   → Routers only validate + format responses

❌ Framework imports in service layer
   → No FastAPI, no Celery in service layer

❌ JSONB for queryable fields
   → Use dedicated columns with indexes
```

### 14.2 Domain Module Rules

```
1. Every domain has: schemas.py, models.py, repository.py, service.py, router.py
2. schemas.py exports: Create*, Update*, Response*, Filter* Pydantic models
3. models.py exports: SQLAlchemy ORM model
4. repository.py exports: Repository class (extends BaseRepository)
5. service.py exports: Service class (stateless, @dataclass)
6. router.py exports: APIRouter instance
7. events.py exports: DomainEvent subclasses
8. exceptions.py exports: Domain-specific exceptions
```

### 14.3 Async Safety Rules

```
1. ALL database operations use async (await)
2. ALL external API calls use async (httpx, aiohttp)
3. CPU-bound operations run in executor (asyncio.to_thread)
4. No blocking calls in the main thread
5. Database sessions are NOT shared across tasks
6. Event handlers run concurrently (asyncio.gather)
7. Background tasks use Celery (not asyncio.create_task)
```

### 14.4 Code Review Checklist

```
[ ] No circular imports
[ ] No direct DB access from router
[ ] No business logic in router
[ ] No sync blocking calls
[ ] All queries include tenant_id filter
[ ] Migrations have downgrade script
[ ] New endpoints have OpenAPI docs
[ ] Error handling covers all failure modes
[ ] Audit logging for all mutations
[ ] Tests for all new endpoints
[ ] Test coverage > 80% for new code
[ ] No secrets in code or config
```
