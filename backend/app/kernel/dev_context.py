"""Development-only tenant/user identities for local auth bypass."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.tenants.models import Tenant
from app.kernel.database.session import TenantAwareSessionFactory

logger = logging.getLogger(__name__)

# Stable UUID for local dev (override via DEV_TENANT_ID env)
DEFAULT_DEV_TENANT_UUID = uuid.UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_DEV_USER_ID = "dev-user"
DEFAULT_DEV_TENANT_NAME = "Development Tenant"


def dev_tenant_id() -> str:
    """Canonical dev tenant id string (valid UUID for Postgres)."""
    return settings.dev_tenant_id


def dev_user_id() -> str:
    return settings.dev_user_id


async def ensure_dev_tenant(db_factory: TenantAwareSessionFactory) -> None:
    """Ensure the development tenant row exists (FK target for uploads)."""
    tenant_uuid = uuid.UUID(dev_tenant_id())
    session: AsyncSession = await db_factory.create_session(
        tenant_id=str(tenant_uuid),
        user_id=dev_user_id(),
        user_role="admin",
    )
    try:
        existing = await session.get(Tenant, tenant_uuid)
        if existing is None:
            session.add(Tenant(tenant_id=tenant_uuid, name=DEFAULT_DEV_TENANT_NAME))
            await session.commit()
            logger.info("Created development tenant %s", tenant_uuid)
    except Exception as exc:
        await session.rollback()
        logger.warning("Could not ensure development tenant: %s", exc)
    finally:
        await session.close()
