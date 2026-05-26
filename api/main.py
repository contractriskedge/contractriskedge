"""FastAPI application entry point for the AI Contract Risk Analyzer.

Configures the ASGI application with all routers, middleware,
exception handlers, and lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.logging import LoggingMiddleware

logger = logging.getLogger(__name__)

PROJECT_NAME = "AI Contract Risk Analyzer"
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# ── Application State ────────────────────────────────────────────────────────


class AppState:
    """Holds shared application state and service instances."""

    def __init__(self) -> None:
        self.startup_time: float = 0.0
        self.db_pool: object = None
        self.redis_client: object = None
        self.ingestion_queue: object = None
        self.db_repo: object = None


state = AppState()


# ── Lifespan Handler ─────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events.

    Initializes database connections, Redis, and other services
    on startup. Performs graceful cleanup on shutdown.
    """
    # Startup
    state.startup_time = time.time()
    app.state.startup_time = state.startup_time
    app.state.db_repo = None
    app.state.db_pool = None
    app.state.redis_client = None
    app.state.ingestion_queue = None
    logger.info(
        "Starting %s (environment: %s)",
        PROJECT_NAME,
        os.getenv("ENVIRONMENT", "development"),
    )

    # Initialize database pool (non-blocking - runs in background task)
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev",
    )
    
    async def _init_db():
        """Initialize database pool in background."""
        nonlocal database_url
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine
            from models.database import DatabaseRepository

            is_sqlite = database_url.startswith("sqlite")
            if is_sqlite:
                engine = create_async_engine(
                    database_url,
                    echo=os.getenv("LOG_LEVEL", "INFO") == "DEBUG",
                )
            else:
                engine = create_async_engine(
                    database_url,
                    pool_size=5,
                    max_overflow=2,
                    pool_pre_ping=False,
                    pool_timeout=3,
                    echo=os.getenv("LOG_LEVEL", "INFO") == "DEBUG",
                )
            state.db_pool = engine
            
            # Verify connection with timeout
            conn = await asyncio.wait_for(engine.connect(), timeout=5.0)
            await conn.execute(text("SELECT 1"))
            await conn.close()
            state.db_repo = DatabaseRepository(engine)
            app.state.db_repo = state.db_repo
            logger.info("Database pool initialized and verified")
        except asyncio.TimeoutError:
            logger.warning("Database connection timed out after 5s")
            if state.db_pool:
                await state.db_pool.dispose()
            state.db_pool = None
        except OSError as exc:
            logger.warning("Database connection failed (OS error): %s", exc)
            if state.db_pool:
                await state.db_pool.dispose()
            state.db_pool = None
        except Exception as exc:
            logger.warning("Database pool initialization failed: %s", exc, exc_info=True)
            if state.db_pool:
                await state.db_pool.dispose()
            state.db_pool = None

    # Initialize Redis (non-blocking)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    async def _init_redis():
        """Initialize Redis connection in background."""
        nonlocal redis_url
        try:
            import redis.asyncio as aioredis

            state.redis_client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3,
            )
            await asyncio.wait_for(state.redis_client.ping(), timeout=3.0)
            logger.info("Redis connection established")
        except asyncio.TimeoutError:
            logger.warning("Redis connection timed out")
            state.redis_client = None
        except Exception as exc:
            logger.warning("Redis connection failed: %s", exc)
            state.redis_client = None

    # Initialize ingestion queue
    async def _init_queue():
        """Initialize ingestion queue in background."""
        nonlocal redis_url
        from ingestion.queue import IngestionQueue
        state.ingestion_queue = IngestionQueue(redis_url=redis_url)

    # Run all initializations concurrently with a timeout
    # Note: Package imports on external volumes can be slow (5-10s each)
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                _init_db(),
                _init_redis(),
                _init_queue(),
                return_exceptions=True,
            ),
            timeout=30.0,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Service init %d failed: %s", i, result)
    except asyncio.TimeoutError:
        logger.warning("Some services failed to initialize within 30s timeout")

    # Seed sample data for development
    try:
        from routers.redlines import seed_sample_suggestions
        seeded = seed_sample_suggestions()
        if seeded:
            logger.info("Seeded %d sample redline suggestions", seeded)
    except Exception as exc:
        logger.warning("Failed to seed sample data: %s", exc)

    # ── Initialize Continuous Monitoring Services (Sprint 11) ──────────────
    try:
        from continuous_monitoring.event_bus import ObligationEventBus
        from continuous_monitoring.renewal_monitor import RenewalMonitor
        from continuous_monitoring.sla_tracker import SLATracker
        from continuous_monitoring.insurance_monitor import InsuranceMonitor
        from continuous_monitoring.compliance_monitor import ComplianceMonitor
        from continuous_monitoring.litigation_monitor import LitigationMonitor
        from continuous_monitoring.renewal_forecast import RenewalForecastEngine

        event_bus = ObligationEventBus(db_pool=state.db_pool)
        app.state.obligation_event_bus = event_bus

        app.state.renewal_monitor = RenewalMonitor(event_bus, db_pool=state.db_pool)
        app.state.sla_tracker = SLATracker(event_bus, db_pool=state.db_pool)
        app.state.insurance_monitor = InsuranceMonitor(event_bus, db_pool=state.db_pool)
        app.state.compliance_monitor = ComplianceMonitor(event_bus, db_pool=state.db_pool)
        app.state.litigation_monitor = LitigationMonitor(event_bus, db_pool=state.db_pool)
        app.state.renewal_forecast_engine = RenewalForecastEngine(event_bus, db_pool=state.db_pool)

        logger.info("Continuous monitoring services initialized")
    except Exception as exc:
        logger.warning("Failed to initialize continuous monitoring: %s", exc)

    # ── Initialize Sprint 12 Services (Semantic Search & Cost Gov.) ────────
    try:
        from continuous_monitoring.semantic_search import SemanticSearchEngine
        from continuous_monitoring.search_index import SearchIndexPipeline
        from continuous_monitoring.cost_governance import CostGovernance
        from continuous_monitoring.model_router import ModelRouter
        from continuous_monitoring.batch_scheduler import BatchScheduler

        app.state.semantic_search_engine = SemanticSearchEngine(
            db_repo=state.db_repo,
        )
        app.state.search_index_pipeline = SearchIndexPipeline(
            db_repo=state.db_repo,
        )
        app.state.cost_governance = CostGovernance(db_pool=state.db_pool)
        app.state.model_router = ModelRouter()
        app.state.batch_scheduler = BatchScheduler()

        logger.info("Semantic search & cost governance services initialized")
    except Exception as exc:
        logger.warning("Failed to initialize Sprint 12 services: %s", exc)

    # ── Initialize Sprint 13 Services (Benchmark Phase 2 & Procurement) ────
    try:
        from continuous_monitoring.benchmark_corpus import BenchmarkCorpusPipeline
        from continuous_monitoring.industry_segmentation import IndustrySegmentationPhase2
        from continuous_monitoring.benchmark_confidence import BenchmarkConfidenceScorer
        from continuous_monitoring.procurement_integration import ProcurementIntegration
        from continuous_monitoring.vendor_onboarding import VendorOnboardingWorkflow
        from continuous_monitoring.supplier_concentration import SupplierConcentrationAnalyzer

        # Use existing benchmarking modules if available
        anonymizer = getattr(state, 'anonymizer', None)
        quality_filter = getattr(state, 'quality_filter', None)
        corpus_ingestion = getattr(state, 'corpus_ingestion', None)

        app.state.benchmark_corpus_pipeline = BenchmarkCorpusPipeline(
            anonymizer=anonymizer,
            quality_filter=quality_filter,
            corpus_ingestion=corpus_ingestion,
            db_pool=state.db_pool,
        )
        app.state.industry_segmentation = IndustrySegmentationPhase2(db_pool=state.db_pool)
        app.state.benchmark_confidence_scorer = BenchmarkConfidenceScorer()
        app.state.procurement_integration = ProcurementIntegration(db_pool=state.db_pool)
        app.state.vendor_onboarding_workflow = VendorOnboardingWorkflow(db_pool=state.db_pool)
        app.state.supplier_concentration_analyzer = SupplierConcentrationAnalyzer(db_pool=state.db_pool)

        logger.info("Benchmark Phase 2 & Procurement services initialized")
    except Exception as exc:
        logger.warning("Failed to initialize Sprint 13 services: %s", exc)

    yield

    # Shutdown
    logger.info("Shutting down %s", PROJECT_NAME)

    if state.db_pool is not None:
        await state.db_pool.dispose()
        logger.info("Database pool disposed")

    if state.redis_client is not None:
        try:
            await state.redis_client.close()
        except Exception:
            pass
        logger.info("Redis connection closed")

    if state.ingestion_queue is not None:
        await state.ingestion_queue.close()
        logger.info("Ingestion queue closed")


# ── Application Factory ──────────────────────────────────────────────────────

app = FastAPI(
    title=PROJECT_NAME,
    description="Production-grade platform for AI-powered contract risk analysis, "
    "clause extraction, and compliance benchmarking.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    redirect_slashes=False,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8000",
    ).split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Tenant-ID",
        "X-API-Key",
    ],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)

# ── Custom Middleware ────────────────────────────────────────────────────────

app.add_middleware(
    AuthMiddleware,
    exclude_paths={
        f"{API_PREFIX}/docs",
        f"{API_PREFIX}/redoc",
        f"{API_PREFIX}/openapi.json",
        f"{API_PREFIX}/health",
        "/health",
        "/ready",
        f"{API_PREFIX}/auth/token",
        f"{API_PREFIX}/auth/dev-login",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    },
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)


# ── Exception Handlers ───────────────────────────────────────────────────────


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation errors with consistent response format."""
    logger.warning("Validation error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": str(exc),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with a generic error response."""
    logger.error(
        "Unhandled exception on %s: %s",
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ── Health Check ─────────────────────────────────────────────────────────────


@app.get(f"{API_PREFIX}/health")
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for load balancers and monitoring.

    Returns:
        Dict with service status and uptime information.
    """
    uptime = time.time() - state.startup_time
    
    # Check database connectivity
    db_status = "disconnected"
    if state.db_repo is not None:
        try:
            db_ok = await state.db_repo.health_check()
            db_status = "connected" if db_ok else "disconnected"
        except Exception:
            db_status = "disconnected"
    
    return {
        "status": "healthy",
        "service": PROJECT_NAME,
        "version": "1.0.0",
        "uptime_seconds": round(uptime, 2),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database": db_status,
        "redis": "connected" if state.redis_client is not None else "disconnected",
    }


@app.get("/ready")
async def readiness_check() -> dict:
    """Readiness probe at root path (matches common K8s / load balancer expectations)."""
    db_ok = False
    if state.db_repo is not None:
        try:
            db_ok = await state.db_repo.health_check()
        except Exception:
            db_ok = False
    return {
        "status": "ready" if db_ok else "not_ready",
        "database": {"connected": db_ok},
    }


# ── Router Registration ──────────────────────────────────────────────────────

from routers.ingest import router as ingest_router
from routers.contracts import router as contracts_router
from routers.risks import router as risks_router
from routers.redlines import router as redlines_router
from routers.benchmarks import router as benchmarks_router
from routers.audit import router as audit_router
from routers.webhooks import router as webhooks_router
from routers.evaluation import router as evaluation_router
from routers.auth import router as auth_router
from routers.export import router as export_router
from routers.playbooks import router as playbooks_router
from routers.rag import router as rag_router
from routers.monitoring import router as monitoring_router
from routers.users import router as users_router
from routers.relationships import router as relationships_router
from routers.continuous_monitoring import router as continuous_monitoring_router

app.include_router(ingest_router, prefix=API_PREFIX)
app.include_router(contracts_router, prefix=API_PREFIX)
app.include_router(risks_router, prefix=API_PREFIX)
app.include_router(redlines_router, prefix=API_PREFIX)
app.include_router(benchmarks_router, prefix=API_PREFIX)
app.include_router(audit_router, prefix=API_PREFIX)
app.include_router(webhooks_router, prefix=API_PREFIX)
app.include_router(evaluation_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(export_router, prefix=API_PREFIX)
app.include_router(playbooks_router, prefix=API_PREFIX)
app.include_router(rag_router, prefix=API_PREFIX)
app.include_router(monitoring_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(relationships_router, prefix=API_PREFIX)
app.include_router(continuous_monitoring_router, prefix=API_PREFIX)


# ── Root Redirect ────────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict:
    """Root endpoint redirecting to API documentation."""
    return {
        "service": PROJECT_NAME,
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
    }


# ── Direct Execution ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
