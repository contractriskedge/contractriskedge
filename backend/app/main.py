"""FastAPI application factory with full middleware stack and lifecycle management."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

from app.config import settings
from app.kernel.dev_context import ensure_dev_tenant
from app.kernel.database.session import TenantAwareSessionFactory
from app.kernel.events.bus import EventBus
from app.kernel.middleware.request_id import RequestIDMiddleware
from app.kernel.middleware.tenant_context import TenantContextMiddleware
from app.kernel.middleware.auth_context import AuthContextMiddleware
from app.kernel.middleware.logging_middleware import LoggingMiddleware
from app.kernel.middleware.deadline import RequestDeadlineMiddleware
from app.kernel.middleware.request_size import RequestBodySizeMiddleware
from app.kernel.telemetry.logger import setup_logging
from app.kernel.telemetry.tracer import setup_tracing
from app.kernel.web.exceptions import AppError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # ── STARTUP ────────────────────────────────────────────────────
    app.state.startup_time = time.time()
    app.state.environment = settings.environment
    app.state.db_ready = False

    setup_logging(settings.environment, settings.log_level)
    setup_tracing(app)

    # Initialize Sentry if DSN configured
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=0.25 if settings.environment == "production" else 1.0,
                profiles_sample_rate=0.1,
                send_default_pii=False,
            )
            logger.info("Sentry initialized", extra={"environment": settings.environment})
        except Exception as exc:
            logger.warning("Sentry initialization failed: %s", exc)

    # Initialize database with timeout protections
    app.state.db_factory = TenantAwareSessionFactory(
        database_url=settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        statement_timeout_ms=settings.db_statement_timeout_ms,
        lock_timeout_ms=settings.db_lock_timeout_ms,
        idle_transaction_timeout_s=settings.db_idle_transaction_timeout_s,
        slow_query_threshold_ms=settings.db_slow_query_threshold_ms,
    )

    # Verify database connection
    try:
        session = await app.state.db_factory.create_session(
            tenant_id="system",
            user_id="system",
            user_role="admin",
        )
        await session.execute(text("SELECT 1"))
        await session.close()
        app.state.db_ready = True
        logger.info("Database connection verified")
        if settings.environment == "development":
            await ensure_dev_tenant(app.state.db_factory)
    except Exception as exc:
        logger.warning("Database connection failed: %s", exc)

    # Initialize in-memory event bus
    app.state.event_bus = EventBus()
    logger.info("Event bus initialized")

    try:
        from app.integrations.storage.s3 import storage_service

        await storage_service.warm_up()
    except Exception as exc:
        logger.warning("Storage warm-up failed (uploads need MinIO): %s", exc)

    # Recover stuck uploads on startup (production-grade resilience)
    try:
        from app.domains.ingestion.recovery import recover_stuck_uploads_on_startup
        recovered = await recover_stuck_uploads_on_startup(app.state.db_factory)
        if recovered:
            logger.info("Recovered %d stuck upload(s) during startup", len(recovered))
    except Exception as exc:
        logger.warning("Startup upload recovery failed (non-fatal): %s", exc)

    logger.info(
        "Application started",
        extra={"environment": settings.environment, "version": "1.0.0"},
    )
    yield

    # ── SHUTDOWN ───────────────────────────────────────────────────
    await app.state.db_factory.close()
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ContractRiskEdge API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        debug=True,
    )

    # ── Middleware (Starlette: last added = outermost on the request) ─
    # Auth must run before Tenant so request.state.user is set first.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestDeadlineMiddleware, timeout_seconds=settings.request_timeout_seconds)
    app.add_middleware(RequestBodySizeMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(AuthContextMiddleware)

    class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            try:
                return await call_next(request)
            except BaseException as exc:
                import traceback

                root = exc
                if isinstance(exc, BaseExceptionGroup):
                    root = exc.exceptions[0] if exc.exceptions else exc

                if isinstance(root, AppError):
                    body = root.to_dict()
                    return JSONResponse(status_code=root.status_code, content=body)

                print("\n" + "=" * 80)
                print("UNHANDLED REQUEST EXCEPTION")
                print(f"PATH: {request.method} {request.url.path}")
                print("=" * 80)
                traceback.print_exc()
                print("=" * 80 + "\n")
                raise root from exc

    app.add_middleware(ExceptionLoggingMiddleware)

    # ── Metrics middleware (records HTTP metrics for Prometheus) ──
    from app.kernel.telemetry.metrics import MetricsMiddleware

    app.add_middleware(BaseHTTPMiddleware, dispatch=MetricsMiddleware().__call__)

    # ── Exception handlers ─────────────────────────────────────────
    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    from app.domains.ingestion.security import FileValidationError

    @app.exception_handler(FileValidationError)
    async def file_validation_error_handler(request, exc: FileValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request, exc: Exception):
        import traceback

        if isinstance(exc, BaseExceptionGroup) and exc.exceptions:
            exc = exc.exceptions[0]

        traceback.print_exc()
        logger.exception("Unhandled exception")

        error_code = exc.__class__.__name__
        # Map common exceptions to user-safe messages
        user_message = str(exc)
        if isinstance(exc, (AttributeError, KeyError, TypeError, ValueError)):
            user_message = "An unexpected error occurred. Our team has been notified."

        return JSONResponse(
            status_code=500,
            content={
                "error": error_code,
                "message": user_message,
                "request_id": getattr(request.state, "request_id", None),
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

    # ── Register routers ──────────────────────────────────────────
    # Register ORM models with SQLAlchemy metadata
    from app.kernel.database.orm_registry import register_orm_models

    register_orm_models()
    from app.domains.health.router import router as health_router
    from app.domains.ingestion.router import router as ingestion_router
    from app.domains.search.router import router as search_router
    from app.domains.ai.router import router as ai_router
    from app.domains.review.router import router as review_router
    from app.domains.notify.router import router as notify_router
    from app.domains.playbook.router import router as playbook_router
    from app.domains.analytics.router import router as analytics_router
    from app.domains.audit.router import router as audit_router
    from app.domains.exports.router import router as exports_router
    from app.domains.workspace.router import router as workspace_router
    from app.domains.admin.router import router as admin_router
    from app.domains.cases.router import router as cases_router
    from app.kernel.events.router import router as events_router

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(health_router)  # /health, /ready for probes and local checks
    if settings.environment == "development":
        from app.domains.health.dev_auth import router as dev_auth_router

        app.include_router(dev_auth_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(ai_router, prefix="/api/v1")
    app.include_router(review_router, prefix="/api/v1")
    app.include_router(notify_router, prefix="/api/v1")
    app.include_router(playbook_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(exports_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(cases_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")

    # ── Prometheus metrics endpoint (no prefix, no auth) ──
    from app.kernel.telemetry.metrics import metrics_endpoint

    @app.get("/metrics")
    async def metrics(request: Request):
        return await metrics_endpoint(request)

    return app


app = create_app()
