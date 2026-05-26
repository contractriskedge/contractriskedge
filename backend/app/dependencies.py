"""FastAPI dependency injection for database, auth, tenant context, event bus, and embedding service."""

from __future__ import annotations

from fastapi import Request, Depends, HTTPException

from app.config import settings
from app.kernel.database.session import TenantAwareSessionFactory
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext
from app.domains.vectors.services.embedding_service import EmbeddingService


async def get_db(request: Request):
    """Create a tenant-safe database session for this request.

    CRITICAL: Creates a NEW session with RESET context for every request.
    Never reuses a session across requests.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    user = getattr(request.state, "user", None)

    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context required")

    factory: TenantAwareSessionFactory = request.app.state.db_factory
    session = await factory.create_session(
        tenant_id=tenant_id,
        user_id=user.id if user else "",
        user_role=user.role if user else "viewer",
    )

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_current_user(request: Request) -> UserContext:
    """Get the authenticated user from request state (set by auth middleware)."""
    user: UserContext = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def get_tenant_id(request: Request) -> str:
    """Get the current tenant ID from request state."""
    tenant_id: str = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context required")
    return tenant_id


async def get_event_bus(request: Request) -> EventBus:
    """Get the application-wide event bus from app state."""
    event_bus: EventBus = getattr(request.app.state, "event_bus", None)
    if not event_bus:
        raise HTTPException(status_code=500, detail="Event bus not available")
    return event_bus


# ── Embedding Service ────────────────────────────────────────────────


async def get_embedding_service(request: Request) -> EmbeddingService:
    """Provide a singleton ``EmbeddingService`` via application state.

    The service is lazily initialized on first request and cached in
    ``request.app.state`` for the lifetime of the application.

    Configuration is sourced from environment variables:
        - ``OPENAI_API_KEY``
        - ``DEFAULT_EMBEDDING_MODEL`` (default: ``text-embedding-3-small``)
    """
    service: EmbeddingService | None = getattr(
        request.app.state, "embedding_service", None
    )
    if service is not None:
        return service

    service = EmbeddingService(
        api_key=settings.openai_api_key or None,
        model=settings.default_embedding_model,
    )
    request.app.state.embedding_service = service
    return service
