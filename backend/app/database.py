"""Compatibility module — provides database session factory for legacy imports.

Integration workers and services import get_async_session from app.database.
This module bridges to the kernel's TenantAwareSessionFactory.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.kernel.database.session import TenantAwareSessionFactory

logger = logging.getLogger(__name__)

# Global factory instance (initialized by app lifespan)
_factory: TenantAwareSessionFactory | None = None


def get_factory() -> TenantAwareSessionFactory:
    """Return the global TenantAwareSessionFactory instance."""
    global _factory
    if _factory is None:
        _factory = TenantAwareSessionFactory(
            database_url=settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle,
            statement_timeout_ms=settings.db_statement_timeout_ms,
            lock_timeout_ms=settings.db_lock_timeout_ms,
            idle_transaction_timeout_s=settings.db_idle_transaction_timeout_s,
            slow_query_threshold_ms=settings.db_slow_query_threshold_ms,
        )
    return _factory


@asynccontextmanager
async def get_async_session(
    tenant_id: str = "system",
    user_id: str = "system",
    user_role: str = "admin",
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a tenant-safe database session.

    Legacy compatibility wrapper used by integration workers.
    New code should use request.app.state.db_factory.create_session() directly.
    """
    factory = get_factory()
    session = await factory.create_session(
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
    )
    try:
        yield session
    finally:
        await session.close()
