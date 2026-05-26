"""Pytest configuration with async fixtures for database, auth, and tenant isolation testing."""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.kernel.database.session import TenantAwareSessionFactory
from app.kernel.security.auth import UserContext
from app.kernel.security.roles import Roles, resolve_permissions
from app.domains.ingestion.models import UploadSession, IngestionState
from app.domains.review.models import ContractReview, ReviewStatus
from app.domains.ai.models import AIExecutionRun, ExecutionStatus
from app.kernel.database.orm_registry import register_orm_models

# Register all ORM tables so SQLAlchemy can resolve FK relationships in tests.
register_orm_models()

# Stable UUIDs for Postgres FK columns (upload_sessions.tenant_id is UUID, not string slug).
TENANT_A_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
TENANT_B_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
TENANT_A_ID_STR = str(TENANT_A_ID)
TENANT_B_ID_STR = str(TENANT_B_ID)


@pytest_asyncio.fixture
async def ensure_test_tenants(tenant_a_session: AsyncSession) -> None:
    """Ensure FK target rows exist for upload/review fixtures."""
    for tenant_id, name in (
        (TENANT_A_ID, "Test Tenant A"),
        (TENANT_B_ID, "Test Tenant B"),
    ):
        await tenant_a_session.execute(
            sa_text("""
                INSERT INTO tenants (
                    tenant_id, name, plan, is_active, max_users, max_documents, features, settings
                )
                VALUES (
                    :tenant_id, :name, 'starter', true, 10, 1000,
                    ARRAY[]::text[], CAST(:settings AS jsonb)
                )
                ON CONFLICT (tenant_id) DO NOTHING
            """).bindparams(tenant_id=tenant_id, name=name, settings="{}")
        )
    await tenant_a_session.commit()


@pytest.fixture(autouse=True)
def disable_dev_auth_bypass(monkeypatch):
    """Tests assert real auth behavior; dev bypass would make test_no_auth pass incorrectly."""
    monkeypatch.setattr(settings, "dev_auth_bypass", False)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_factory() -> TenantAwareSessionFactory:
    """Create a tenant-aware session factory for testing."""
    factory = TenantAwareSessionFactory(
        database_url=settings.database_url,
        pool_size=2,
        max_overflow=1,
    )
    yield factory
    await factory.close()


@pytest_asyncio.fixture
async def tenant_a_session(db_factory: TenantAwareSessionFactory) -> AsyncSession:
    """Create a session scoped to Tenant A."""
    session = await db_factory.create_session(TENANT_A_ID_STR, "user-a", "admin")
    yield session
    await session.close()


@pytest_asyncio.fixture
async def tenant_b_session(db_factory: TenantAwareSessionFactory) -> AsyncSession:
    """Create a session scoped to Tenant B."""
    session = await db_factory.create_session(TENANT_B_ID_STR, "user-b", "viewer")
    yield session
    await session.close()


@pytest.fixture
def tenant_admin_user() -> UserContext:
    return UserContext(
        id="auth0|test-admin",
        email="admin@test.com",
        tenant_id=TENANT_A_ID_STR,
        role="tenant_admin",
        permissions=["contracts:read", "contracts:write", "contracts:delete", "workflows:approve", "ai:analyze", "audit:read"],
    )


@pytest.fixture
def viewer_user() -> UserContext:
    user = UserContext(
        id="auth0|test-viewer",
        email="viewer@test.com",
        tenant_id=TENANT_A_ID_STR,
        role="viewer",
        permissions=["contracts:read"],
    )
    # Resolve server-side permissions from role
    user.permissions = resolve_permissions(user)
    return user


@pytest.fixture
def other_tenant_user() -> UserContext:
    return UserContext(
        id="auth0|other-tenant",
        email="other@test.com",
        tenant_id=TENANT_B_ID_STR,
        role="viewer",
        permissions=["contracts:read"],
    )


# ── Integration Test Fixtures ──────────────────────────────────────


@pytest_asyncio.fixture
async def sample_upload(tenant_a_session: AsyncSession, ensure_test_tenants) -> UploadSession:
    """Create a sample upload session for testing."""
    upload_id = uuid.uuid4()
    await tenant_a_session.execute(
        sa_text("""
            INSERT INTO upload_sessions (
                upload_id, tenant_id, user_id, filename, content_type, file_size,
                ingestion_state, retry_count, metadata
            )
            VALUES (
                :upload_id, :tenant_id, :user_id, :filename, :content_type, :file_size,
                CAST(:state AS ingestion_state), :retry_count, CAST(:metadata AS jsonb)
            )
        """).bindparams(
            upload_id=upload_id, tenant_id=TENANT_A_ID,
            user_id="auth0|test-admin", filename="test-contract.pdf",
            content_type="application/pdf", file_size=1024, retry_count=0,
            state=IngestionState.UPLOADED.value, metadata="{}",
        )
    )
    await tenant_a_session.commit()
    # Fetch the created upload
    result = await tenant_a_session.execute(
        sa_text("SELECT * FROM upload_sessions WHERE upload_id = :upload_id").bindparams(upload_id=upload_id)
    )
    row = result.fetchone()
    upload = UploadSession(
        upload_id=row.upload_id, tenant_id=row.tenant_id, user_id=row.user_id,
        filename=row.filename, content_type=row.content_type, file_size=row.file_size,
        ingestion_state=IngestionState(row.ingestion_state),
    )
    return upload


@pytest_asyncio.fixture
async def completed_upload(tenant_a_session: AsyncSession, ensure_test_tenants) -> UploadSession:
    """Create an upload that has completed ingestion."""
    import uuid
    upload_id = uuid.uuid4()
    await tenant_a_session.execute(
        sa_text("""
            INSERT INTO upload_sessions (
                upload_id, tenant_id, user_id, filename, content_type, file_size,
                ingestion_state, retry_count, storage_key, server_checksum_sha256, metadata
            )
            VALUES (
                :upload_id, :tenant_id, :user_id, :filename, :content_type, :file_size,
                CAST(:state AS ingestion_state), :retry_count, :storage_key, :checksum,
                CAST(:metadata AS jsonb)
            )
        """).bindparams(
            upload_id=upload_id, tenant_id=TENANT_A_ID,
            user_id="auth0|test-admin", filename="completed-contract.pdf",
            content_type="application/pdf", file_size=2048, retry_count=0,
            state=IngestionState.REVIEW_READY.value,
            storage_key="test/key.pdf", checksum="abc123", metadata="{}",
        )
    )
    await tenant_a_session.commit()
    result = await tenant_a_session.execute(
        sa_text("SELECT * FROM upload_sessions WHERE upload_id = :upload_id").bindparams(upload_id=upload_id)
    )
    row = result.fetchone()
    upload = UploadSession(
        upload_id=row.upload_id, tenant_id=row.tenant_id, user_id=row.user_id,
        filename=row.filename, content_type=row.content_type, file_size=row.file_size,
        ingestion_state=IngestionState(row.ingestion_state),
        storage_key=row.storage_key,
    )
    return upload


@pytest_asyncio.fixture
async def sample_review(tenant_a_session: AsyncSession, completed_upload: UploadSession) -> ContractReview:
    """Create a sample review for testing."""
    import uuid
    review_id = uuid.uuid4()
    await tenant_a_session.execute(
        sa_text("""
            INSERT INTO contract_reviews (
                review_id, upload_id, tenant_id, status, created_by, priority,
                finding_count, redline_count, comment_count, escalation_count,
                sla_breached, metadata
            )
            VALUES (
                :review_id, :upload_id, :tenant_id, CAST(:status AS review_status),
                :created_by, :priority, :finding_count, :redline_count,
                :comment_count, :escalation_count, :sla_breached, CAST(:metadata AS jsonb)
            )
        """).bindparams(
            review_id=review_id, upload_id=completed_upload.upload_id,
            tenant_id=TENANT_A_ID,
            status=ReviewStatus.AI_ANALYZED.value,
            created_by="auth0|test-admin", priority="normal",
            finding_count=3, redline_count=1,
            comment_count=0, escalation_count=0, sla_breached=False, metadata="{}",
        )
    )
    await tenant_a_session.commit()
    result = await tenant_a_session.execute(
        sa_text("SELECT * FROM contract_reviews WHERE review_id = :review_id").bindparams(review_id=review_id)
    )
    row = result.fetchone()
    review = ContractReview(
        review_id=row.review_id, upload_id=row.upload_id, tenant_id=row.tenant_id,
        status=ReviewStatus(row.status), created_by=row.created_by,
        priority=row.priority, finding_count=row.finding_count,
        redline_count=row.redline_count,
    )
    return review


@pytest_asyncio.fixture
async def sample_ai_run(tenant_a_session: AsyncSession, completed_upload: UploadSession) -> AIExecutionRun:
    """Create a sample AI execution run for testing."""
    import uuid
    run_id = uuid.uuid4()
    await tenant_a_session.execute(
        sa_text("""
            INSERT INTO ai_execution_runs (run_id, upload_id, tenant_id, analysis_type, status, model, provider, total_tokens, cost_usd, findings_count, redlines_count)
            VALUES (:run_id, :upload_id, :tenant_id, :analysis_type, CAST(:status AS ai_exec_status), :model, :provider, :total_tokens, :cost_usd, :findings_count, :redlines_count)
        """).bindparams(
            run_id=run_id, upload_id=completed_upload.upload_id,
            tenant_id=TENANT_A_ID,
            analysis_type="full",
            status=ExecutionStatus.COMPLETED.value, model="gpt-4o",
            provider="openai", total_tokens=1500, cost_usd=0.03,
            findings_count=3, redlines_count=1,
        )
    )
    await tenant_a_session.commit()
    result = await tenant_a_session.execute(
        sa_text("SELECT * FROM ai_execution_runs WHERE run_id = :run_id").bindparams(run_id=run_id)
    )
    row = result.fetchone()
    run = AIExecutionRun(
        run_id=row.run_id, upload_id=row.upload_id, tenant_id=row.tenant_id,
        analysis_type=row.analysis_type, status=ExecutionStatus(row.status),
        model=row.model, provider=row.provider, total_tokens=row.total_tokens,
        cost_usd=row.cost_usd, findings_count=row.findings_count,
        redlines_count=row.redlines_count,
    )
    return run


@pytest.fixture
def legal_reviewer_user() -> UserContext:
    """User with legal_reviewer role."""
    user = UserContext(
        id="auth0|legal-reviewer",
        email="legal@test.com",
        tenant_id=TENANT_A_ID_STR,
        role=Roles.LEGAL_REVIEWER,
        permissions=[],
    )
    user.permissions = resolve_permissions(user)
    return user


@pytest.fixture
def auditor_user() -> UserContext:
    """User with auditor role."""
    user = UserContext(
        id="auth0|auditor",
        email="auditor@test.com",
        tenant_id=TENANT_A_ID_STR,
        role=Roles.AUDITOR,
        permissions=[],
    )
    user.permissions = resolve_permissions(user)
    return user


@pytest.fixture
def rbac_admin_user() -> UserContext:
    """User with tenant_admin role (full permissions)."""
    user = UserContext(
        id="auth0|rbac-admin",
        email="rbac-admin@test.com",
        tenant_id=TENANT_A_ID_STR,
        role=Roles.ADMIN,
        permissions=[],
    )
    user.permissions = resolve_permissions(user)
    return user
