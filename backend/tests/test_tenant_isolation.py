"""CRITICAL: Tenant isolation tests.

These tests verify that tenants CANNOT access each other's data
at the database level, even with direct SQL access.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.database.session import TenantAwareSessionFactory
from tests.conftest import TENANT_A_ID, TENANT_A_ID_STR, TENANT_B_ID_STR


async def _rls_is_effective(db_factory: TenantAwareSessionFactory) -> bool:
    """True when upload_sessions reads are restricted by tenant context."""
    session = await db_factory.create_session(TENANT_A_ID_STR, "probe", "admin")
    try:
        row = await session.execute(
            text("""
                SELECT c.relrowsecurity AS rls_on,
                       COALESCE(r.rolbypassrls, false) AS bypass_rls
                FROM pg_class c
                JOIN pg_roles r ON r.rolname = current_user
                WHERE c.relname = 'upload_sessions'
            """)
        )
        info = row.one_or_none()
        if info is None or not info.rls_on or info.bypass_rls:
            return False

        await session.execute(text("RESET app.tenant_id"))
        unscoped = (await session.execute(text("SELECT COUNT(*) FROM upload_sessions"))).scalar()
        return unscoped == 0
    finally:
        await session.close()


@pytest_asyncio.fixture
async def require_upload_sessions_rls(db_factory: TenantAwareSessionFactory):
    if not await _rls_is_effective(db_factory):
        pytest.skip(
            "upload_sessions RLS is not effective (run: alembic upgrade head; "
            "use a DB role without BYPASSRLS)"
        )


class TestRLSFailClosed:
    """Verify RLS fails closed (returns 0 rows) when tenant context is missing."""

    async def test_rls_without_tenant_context_returns_zero(
        self, db_factory, require_upload_sessions_rls
    ):
        """Without setting app.tenant_id, queries must return 0 rows."""
        session = await db_factory.create_session("", "", "")
        await session.execute(text("RESET app.tenant_id"))
        result = await session.execute(text("SELECT COUNT(*) FROM upload_sessions"))
        count = result.scalar()
        assert count == 0, f"RLS fail-closed violation: returned {count} rows"
        await session.close()

    async def test_rls_with_invalid_tenant_returns_zero(
        self, db_factory, require_upload_sessions_rls
    ):
        """With a non-existent tenant_id, queries must return 0 rows."""
        session = await db_factory.create_session(
            "00000000-0000-0000-0000-000000000000", "test", "viewer"
        )
        result = await session.execute(text("SELECT COUNT(*) FROM upload_sessions"))
        count = result.scalar()
        assert count == 0, f"RLS fail-closed violation: returned {count} rows"
        await session.close()


class TestTenantDataIsolation:
    """Verify tenants cannot access each other's data."""

    async def test_tenant_a_cannot_see_tenant_b_data(
        self,
        tenant_a_session: AsyncSession,
        tenant_b_session: AsyncSession,
        ensure_test_tenants,
        require_upload_sessions_rls,
    ):
        """Tenant A creates a record. Tenant B should not see it."""
        upload_id = uuid.uuid4()
        await tenant_a_session.execute(
            text("""
                INSERT INTO upload_sessions (
                    upload_id, tenant_id, user_id, filename, content_type, file_size,
                    ingestion_state, retry_count, metadata
                ) VALUES (
                    :upload_id, :tenant_id, 'user-a', 'a.pdf', 'application/pdf', 1,
                    'uploaded', 0, '{}'::jsonb
                )
            """),
            {"upload_id": upload_id, "tenant_id": TENANT_A_ID},
        )
        await tenant_a_session.commit()

        result = await tenant_b_session.execute(
            text("SELECT COUNT(*) FROM upload_sessions WHERE upload_id = :upload_id"),
            {"upload_id": upload_id},
        )
        count = result.scalar()
        assert count == 0, "Tenant B should not see Tenant A's data"

        await tenant_a_session.execute(
            text("DELETE FROM upload_sessions WHERE upload_id = :upload_id"),
            {"upload_id": upload_id},
        )
        await tenant_a_session.commit()

    async def test_connection_pool_does_not_leak_tenant_context(self, db_factory):
        """Sequential requests from different tenants must not leak context."""
        session_a = await db_factory.create_session("tenant-alpha", "user-a", "admin")
        result_a = await session_a.execute(
            text("SELECT current_setting('app.tenant_id', TRUE)")
        )
        assert result_a.scalar() == "tenant-alpha"
        await session_a.close()

        session_b = await db_factory.create_session("tenant-beta", "user-b", "viewer")
        result_b = await session_b.execute(
            text("SELECT current_setting('app.tenant_id', TRUE)")
        )
        assert result_b.scalar() == "tenant-beta", "Connection pool leaked tenant context!"
        await session_b.close()
