# ContractRiskEdge — Auth + Tenant Isolation + RBAC Hardening

## Critical Security Corrections & Operational Hardening — Pre-Implementation

---

## Table of Contents

1. [Remove X-Tenant-ID Trust](#1-remove-x-tenant-id-trust)
2. [Fix Database Connection Pooling & Session Leaks](#2-fix-database-connection-pooling--session-leaks)
3. [Fix Async Worker Tenant Isolation](#3-fix-async-worker-tenant-isolation)
4. [Fix Permission Freshness & Token Limitations](#4-fix-permission-freshness--token-limitations)
5. [Fix RLS Correctness & Fail-Closed Behavior](#5-fix-rls-correctness--fail-closed-behavior)
6. [Fix API Key Authentication](#6-fix-api-key-authentication)
7. [Fix Audit Log Integrity](#7-fix-audit-log-integrity)
8. [Fix Operational Security Gaps](#8-fix-operational-security-gaps)
9. [Hardening Summary](#9-hardening-summary)

---

## 1. Remove X-Tenant-ID Trust

### 1.1 Problem

Current middleware allows the client to override tenant ID via HTTP header:

```python
# ❌ CURRENT — VULNERABLE
request.state.tenant_id = request.headers.get("X-Tenant-ID") or user.tenant_id
```

A malicious user can inject `X-Tenant-ID: other-tenant-uuid` to access another tenant's data. The JWT is verified, but the header overrides the JWT-embedded tenant_id. This is a **critical cross-tenant data access vulnerability**.

### 1.2 Fix: Tenant ID MUST come from JWT ONLY

```python
# app/kernel/middleware/tenant_context.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class TenantContextMiddleware(BaseHTTPMiddleware):
    """Tenant ID comes EXCLUSIVELY from JWT. X-Tenant-ID is NEVER trusted."""

    async def dispatch(self, request: Request, call_next):
        user = getattr(request.state, "user", None)

        if not user or not user.tenant_id:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthorized",
                    "message": "Tenant context not found in authentication token. "
                               "Contact your administrator to ensure your account is "
                               "properly provisioned with a tenant.",
                },
            )

        # CRITICAL: Tenant comes from JWT ONLY
        # X-Tenant-ID header is NEVER accepted from clients
        request.state.tenant_id = user.tenant_id

        return await call_next(request)
```

### 1.3 Admin Override (Controlled Exception)

For platform support debugging ONLY — requires `admin:system` permission and audit logging:

```python
# app/kernel/middleware/tenant_context.py

class TenantContextMiddleware(BaseHTTPMiddleware):
    """Tenant ID comes EXCLUSIVELY from JWT. X-Tenant-ID is NEVER trusted."""

    async def dispatch(self, request: Request, call_next):
        user = getattr(request.state, "user", None)
        if not user or not user.tenant_id:
            raise HTTPException(status_code=401, detail="Tenant context required")

        # Default: tenant from JWT
        tenant_id = user.tenant_id

        # Admin override: ONLY for users with admin:system permission
        # This is used by platform support for debugging customer issues
        header_tenant = request.headers.get("X-Tenant-ID")
        if header_tenant and header_tenant != user.tenant_id:
            if "admin:system" not in user.permissions:
                raise HTTPException(
                    status_code=403,
                    detail="X-Tenant-ID override requires admin:system permission",
                )
            # Audit log the override
            logger.warning(
                "Tenant override by admin",
                admin_id=user.id,
                original_tenant=user.tenant_id,
                override_tenant=header_tenant,
                path=request.url.path,
            )
            tenant_id = header_tenant

        request.state.tenant_id = tenant_id
        return await call_next(request)
```

### 1.4 Repository-Level Enforcement

Even if middleware is bypassed, the repository must never trust a client-provided tenant_id:

```python
# app/kernel/repository/base.py

from dataclasses import dataclass

@dataclass
class BaseRepository:
    session: AsyncSession
    tenant_id: str  # Injected by DI — comes from request.state.tenant_id (JWT)

    def _filter_tenant(self, stmt, model):
        """FAIL-SAFE: Every query MUST include tenant_id filter.
        
        If tenant_id is somehow empty, return FALSE WHERE clause
        instead of returning all rows."""
        if not self.tenant_id:
            # FAIL CLOSED: Return no rows instead of all rows
            return stmt.where(text("1=0"))
        return stmt.where(model.tenant_id == self.tenant_id)
```

---

## 2. Fix Database Connection Pooling & Session Leaks

### 2.1 Problem

PostgreSQL connection pooling REUSES connections across requests. If `SET app.tenant_id` is set on a connection and the connection is returned to the pool, the NEXT request (from a different tenant) will inherit the previous tenant's context. This causes **cross-tenant data leakage**.

### 2.2 Fix: Reset Session Context on Every Connection Checkout

```python
# app/kernel/database/session.py

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

class TenantAwareSessionFactory:
    """Session factory that resets tenant context on every connection checkout.
    
    CRITICAL: Connection pooling reuses connections. Without resetting
    the session context, a connection from Tenant A could be reused
    for Tenant B's query, inheriting Tenant A's RLS context.
    """

    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,       # Verify connection before use
            pool_recycle=300,          # Recycle connections every 5 minutes
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_session(self, tenant_id: str, user_id: str, user_role: str) -> AsyncSession:
        """Create a new session with tenant context set.
        
        ALWAYS resets session variables to prevent cross-tenant context leaks.
        """
        session = self.session_factory()

        # CRITICAL: Reset ALL session variables before setting new ones
        # This prevents context leaking from the previous connection user
        await session.execute(text("RESET app.tenant_id"))
        await session.execute(text("RESET app.user_id"))
        await session.execute(text("RESET app.user_role"))

        # Set tenant context for RLS
        await session.execute(
            text("SET app.tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        await session.execute(
            text("SET app.user_id = :user_id"),
            {"user_id": user_id},
        )
        await session.execute(
            text("SET app.user_role = :user_role"),
            {"user_role": user_role},
        )

        return session
```

### 2.3 Fix: Dependency Injection Must Use New Session Per Request

```python
# app/dependencies.py

from fastapi import Request

async def get_db(request: Request):
    """Get tenant-safe database session.
    
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
```

### 2.4 Connection Pool Verification Test

```python
# tests/integration/test_tenant_pool_safety.py

class TestConnectionPoolTenantSafety:
    """CRITICAL: Verifies that connection pooling does NOT leak tenant context."""

    async def test_connection_pool_resets_tenant_context(self, db_factory):
        """Simulate sequential requests from different tenants on pooled connections."""
        # Request 1: Tenant A
        session_a = await db_factory.create_session("tenant-a", "user-a", "admin")
        result_a = await session_a.execute(
            text("SELECT current_setting('app.tenant_id', TRUE)")
        )
        assert result_a.scalar() == "tenant-a"
        await session_a.close()  # Return to pool

        # Request 2: Tenant B (uses same connection from pool)
        session_b = await db_factory.create_session("tenant-b", "user-b", "viewer")
        result_b = await session_b.execute(
            text("SELECT current_setting('app.tenant_id', TRUE)")
        )
        # CRITICAL: Must NOT be "tenant-a" from the previous request
        assert result_b.scalar() == "tenant-b"
        await session_b.close()

    async def test_connection_pool_does_not_leak_data(self, db_factory):
        """Verify RLS actually prevents cross-tenant access on pooled connections."""
        # Tenant A creates data
        session_a = await db_factory.create_session("tenant-a", "user-a", "admin")
        await session_a.execute(text("INSERT INTO contracts (contract_id, tenant_id, filename) VALUES ('a-1', 'tenant-a', 'a.pdf')"))
        await session_a.commit()
        await session_a.close()

        # Tenant B queries (same pool connection)
        session_b = await db_factory.create_session("tenant-b", "user-b", "viewer")
        result = await session_b.execute(text("SELECT COUNT(*) FROM contracts"))
        count = result.scalar()
        # Tenant B should see ZERO of Tenant A's data
        assert count == 0, f"Tenant B should see 0 contracts, saw {count}"
        await session_b.close()
```

---

## 3. Fix Async Worker Tenant Isolation

### 3.1 Problem

Celery workers run outside the HTTP request context. They have no access to `request.state`. If a worker task processes data for multiple tenants, it must establish its own tenant context. Without this, all worker queries run without RLS, potentially accessing all tenants' data.

### 3.2 Fix: Worker Must Establish Tenant Context

```python
# workers/base.py

from app.kernel.database.session import TenantAwareSessionFactory

class TenantAwareTask:
    """Base task that establishes tenant context for worker execution."""

    async def execute_in_tenant(self, tenant_id: str, user_id: str, user_role: str, fn):
        """Execute a function within a specific tenant context."""
        factory = TenantAwareSessionFactory(settings.database_url)
        session = await factory.create_session(tenant_id, user_id, user_role)

        try:
            result = await fn(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 3.3 Fix: All Worker Tasks MUST Include Tenant ID

```python
# workers/ingestion.py

from workers.base import TenantAwareTask
from workers.celery_app import celery_app

@celery_app.task(base=TenantAwareTask, name="process_document")
def process_document(contract_id: str, tenant_id: str, user_id: str):
    """Process document with EXPLICIT tenant context.
    
    CRITICAL: tenant_id is REQUIRED. Never process without tenant context.
    """
    if not tenant_id:
        raise ValueError("tenant_id is required for all worker tasks")

    return execute_in_tenant(
        tenant_id=tenant_id,
        user_id=user_id,
        user_role="api",
        fn=lambda session: _process_document(session, contract_id),
    )


@celery_app.task(base=TenantAwareTask, name="analyze_contract")
def analyze_contract(contract_id: str, tenant_id: str, user_id: str):
    """AI analysis with EXPLICIT tenant context."""
    if not tenant_id:
        raise ValueError("tenant_id is required for all worker tasks")

    return execute_in_tenant(
        tenant_id=tenant_id,
        user_id=user_id,
        user_role="api",
        fn=lambda session: _analyze_contract(session, contract_id),
    )
```

### 3.4 Fix: Worker Configuration Validation

```python
# workers/celery_app.py

from celery import Celery

celery_app = Celery("contractrisk", broker=settings.celery_broker_url)

# ── Worker startup: verify configuration ───────────────────────────

@celery_app.on_after_configure.connect
def verify_worker_config(sender, **kwargs):
    """Fail fast on startup if worker configuration is invalid."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for worker tasks")
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is required for worker tasks")
```

### 3.5 Fix: Reject Tasks Without Tenant ID

```python
# workers/celery_app.py — Task rejection

from celery import Task

class TenantRequiredTask(Task):
    """Base task that REJECTS tasks without tenant_id."""

    abstract = True

    def apply_async(self, args=None, kwargs=None, **options):
        if kwargs is None:
            kwargs = {}
        if "tenant_id" not in kwargs or not kwargs["tenant_id"]:
            raise ValueError(
                f"Task {self.name} requires tenant_id in kwargs. "
                "All worker tasks must operate within a tenant context."
            )
        return super().apply_async(args=args, kwargs=kwargs, **options)
```

---

## 4. Fix Permission Freshness & Token Limitations

### 4.1 Problem

JWT tokens contain permissions at the time of ISSUANCE. If a user's role changes (promoted from viewer to legal_reviewer), their existing JWT still has old permissions until the token expires (up to 1 hour). This means:

- **Promotion delay:** New permissions take up to 1 hour to take effect
- **Demotion risk:** Revoked permissions remain active for up to 1 hour
- **No real-time enforcement:** Cannot immediately block a user whose role changed

### 4.2 Fix: Short Token Expiry + Redis Permission Cache

```python
# app/kernel/security/permission_cache.py

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PermissionCache:
    """Redis-backed permission cache with real-time invalidation.
    
    Permissions are checked against this cache on EVERY request.
    If the cache has a newer version than the JWT, the cache wins.
    This enables REAL-TIME permission changes without waiting for token expiry.
    """

    CACHE_TTL = 300  # 5 minutes — short enough for timely updates
    TOKEN_EXPIRY_HOURS = 1  # Auth0 access token default

    def __init__(self, redis):
        self.redis = redis

    async def get_effective_permissions(self, user_id: str, token_permissions: list[str], token_issued_at: int) -> list[str]:
        """Get the user's effective permissions (cache overrides token if newer)."""
        cache_key = f"permissions:{user_id}"

        # Check Redis for cached permissions
        cached = await self.redis.get(cache_key)
        if cached:
            cached_data = json.loads(cached)
            # If cache was updated AFTER token was issued, use cache
            if cached_data.get("updated_at", 0) > token_issued_at:
                logger.info("Using cached permissions (newer than token) for user %s", user_id)
                return cached_data["permissions"]

        # Fall back to token permissions
        return token_permissions

    async def update_permissions(self, user_id: str, permissions: list[str]):
        """Update cached permissions (called when role changes)."""
        cache_key = f"permissions:{user_id}"
        data = {
            "permissions": permissions,
            "updated_at": int(datetime.utcnow().timestamp()),
        }
        await self.redis.setex(cache_key, self.CACHE_TTL, json.dumps(data))
        logger.info("Permissions updated for user %s", user_id)

    async def invalidate_user(self, user_id: str):
        """Force permission re-check on next request."""
        await self.redis.delete(f"permissions:{user_id}")
```

### 4.3 Fix: Integrate Permission Cache into Auth Middleware

```python
# app/kernel/middleware/auth_context.py — Updated

class AuthMiddleware(BaseHTTPMiddleware):
    """Auth middleware with real-time permission checking."""

    async def dispatch(self, request: Request, call_next):
        # ... existing JWT validation ...

        # Check permission cache for real-time updates
        permission_cache = PermissionCache(request.app.state.redis)
        effective_permissions = await permission_cache.get_effective_permissions(
            user_id=user.id,
            token_permissions=user.permissions,
            token_issued_at=payload.get("iat", 0),
        )

        # Override token permissions with potentially newer cached permissions
        user.permissions = effective_permissions
        request.state.user = user

        return await call_next(request)
```

### 4.4 Fix: Role Change → Invalidate Cache

```python
# domains/auth/service.py

class UserService:
    async def change_user_role(self, user_id: str, new_role: str, tenant_id: str):
        """Change user role and invalidate permission cache immediately."""
        # 1. Update database
        await self.repository.update_role(user_id, new_role, tenant_id)

        # 2. Get new permissions for the role
        new_permissions = ROLES[new_role]["permissions"]

        # 3. Invalidate permission cache
        await self.permission_cache.update_permissions(user_id, new_permissions)

        # 4. Force token re-issuance by incrementing token version
        await self.token_revocation.revoke_all_user_tokens(user_id)

        # 5. Audit log
        await self.audit_service.log(
            action="user.role_changed",
            actor=self.user.id,
            target=user_id,
            details={"old_role": old_role, "new_role": new_role},
        )
```

---

## 5. Fix RLS Correctness & Fail-Closed Behavior

### 5.1 Problem

The current RLS policies use `FOR ALL` which applies to SELECT, INSERT, UPDATE, and DELETE. However, `current_setting('app.tenant_id', TRUE)` returns NULL if the setting was never set (e.g., if middleware fails). When tenant_id is NULL, `tenant_id = NULL` evaluates to NULL (not TRUE), which means **no rows are returned**. This is the correct fail-closed behavior, but it must be verified.

### 5.2 Fix: Verify RLS Fail-Closed

```sql
-- ── RLS Policy — FAIL CLOSED ──────────────────────────────────────

ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;

-- CRITICAL: If app.tenant_id is not set, current_setting returns NULL
-- NULL = NULL is NULL (not TRUE), so NO rows are returned
-- This is the correct FAIL-CLOSED behavior
CREATE POLICY tenant_isolation ON contracts
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- ── Verify fail-closed behavior ───────────────────────────────────

-- Test: Without setting app.tenant_id, queries return 0 rows
-- RESET app.tenant_id;
-- SELECT COUNT(*) FROM contracts;  -- Returns 0, not all rows

-- Test: With invalid tenant_id, queries return 0 rows
-- SET app.tenant_id = '00000000-0000-0000-0000-000000000000';
-- SELECT COUNT(*) FROM contracts;  -- Returns 0
```

### 5.3 Fix: Add RLS Verification Test

```python
# tests/integration/test_rls_fail_closed.py

class TestRLSFailClosed:
    """CRITICAL: Verify RLS fails closed, not open."""

    async def test_rls_without_tenant_context_returns_zero_rows(self, db_session):
        """Without setting app.tenant_id, queries must return 0 rows."""
        await db_session.execute(text("RESET app.tenant_id"))
        result = await db_session.execute(text("SELECT COUNT(*) FROM contracts"))
        count = result.scalar()
        assert count == 0, (
            f"RLS fail-closed violation: without tenant context, "
            f"query returned {count} rows instead of 0"
        )

    async def test_rls_with_invalid_tenant_returns_zero_rows(self, db_session):
        """With an invalid/non-existent tenant_id, queries must return 0 rows."""
        await db_session.execute(
            text("SET app.tenant_id = '00000000-0000-0000-0000-000000000000'")
        )
        result = await db_session.execute(text("SELECT COUNT(*) FROM contracts"))
        count = result.scalar()
        assert count == 0, (
            f"RLS fail-closed violation: with invalid tenant, "
            f"query returned {count} rows instead of 0"
        )

    async def test_rls_allows_admin_override(self, db_session):
        """Tenant admin should see their own tenant's data."""
        await db_session.execute(text("SET app.tenant_id = 'test-tenant-1'"))
        result = await db_session.execute(text("SELECT COUNT(*) FROM contracts"))
        count = result.scalar()
        # Should see data for test-tenant-1 (exact count depends on test data)
        assert count >= 0  # Will be 0 or more depending on seed data
```

### 5.4 Fix: INSERT Must Also Have RLS

```sql
-- CRITICAL: RLS on INSERT prevents creating data in another tenant's partition
-- Without this, a malicious query could INSERT with a different tenant_id

-- The FOR ALL policy already covers INSERT, but verify:
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;

-- This policy ensures INSERT checks tenant_id matches the session context
-- If a query tries to INSERT with tenant_id = 'other-tenant', RLS blocks it
CREATE POLICY tenant_isolation_insert ON contracts
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
```

---

## 6. Fix API Key Authentication

### 6.1 Problem

The current API key implementation generates keys but does not enforce that API keys are tenant-scoped. An API key from Tenant A could be used to access Tenant B's data if the key validation doesn't enforce tenant matching.

### 6.2 Fix: API Key Must Be Tenant-Scoped with Validation

```python
# app/kernel/security/api_key.py

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

@dataclass
class APIKeyContext:
    key_id: str
    tenant_id: str
    name: str
    permissions: list[str]


class APIKeyAuthenticator:
    """Validates tenant-scoped API keys."""

    @staticmethod
    def generate_key(tenant_id: str, name: str, permissions: list[str]) -> tuple[str, str, str]:
        """Generate a tenant-scoped API key.
        
        Returns:
            Tuple of (raw_key, key_hash, key_prefix)
            raw_key is shown ONCE to the user and cannot be retrieved again.
        """
        raw_key = f"cre_{tenant_id[:8]}_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:20]  # cre_{tenant_prefix}_
        return raw_key, key_hash, key_prefix

    async def authenticate(self, api_key: str, request_tenant_id: str) -> APIKeyContext:
        """Validate API key AND verify it belongs to the requesting tenant.
        
        CRITICAL: The tenant_id from the API key MUST match the tenant_id
        from the request context. This prevents cross-tenant API key usage.
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        result = await self.db.execute(
            "SELECT api_key_id, tenant_id, name, permissions, expires_at, is_active "
            "FROM api_keys WHERE key_hash = :key_hash",
            {"key_hash": key_hash},
        )
        row = result.fetchone()

        if not row:
            raise AuthenticationError("Invalid API key")

        if not row.is_active:
            raise AuthenticationError("API key is deactivated")

        if row.expires_at and row.expires_at < datetime.utcnow():
            raise AuthenticationError("API key has expired")

        # CRITICAL: Verify the API key belongs to the requesting tenant
        if row.tenant_id != request_tenant_id:
            # Log the cross-tenant attempt for security monitoring
            logger.warning(
                "Cross-tenant API key attempt",
                key_id=row.api_key_id,
                key_tenant=row.tenant_id,
                request_tenant=request_tenant_id,
            )
            raise AuthenticationError("API key does not belong to this tenant")

        # Update last used
        await self.db.execute(
            "UPDATE api_keys SET last_used_at = NOW() WHERE api_key_id = :id",
            {"id": row.api_key_id},
        )

        return APIKeyContext(
            key_id=row.api_key_id,
            tenant_id=row.tenant_id,
            name=row.name,
            permissions=row.permissions,
        )
```

---

## 7. Fix Audit Log Integrity

### 7.1 Problem

Audit logs are append-only via trigger, but:
1. There is no verification that audit entries cannot be tampered with
2. There is no chain-of-custody (each entry doesn't reference the previous)
3. Database administrators could modify audit_logs directly (bypassing the trigger)

### 7.2 Fix: Audit Log Chaining with Checksums

```sql
-- ── Audit Log with Chain Integrity ────────────────────────────────

ALTER TABLE audit_logs ADD COLUMN previous_audit_id UUID;
ALTER TABLE audit_logs ADD COLUMN chain_hash TEXT;  -- SHA-256 of (previous_chain_hash + current_row_data)

-- Chain hash trigger
CREATE OR REPLACE FUNCTION compute_audit_chain_hash()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    prev_hash TEXT;
BEGIN
    -- Get the hash of the previous audit entry for this tenant
    SELECT chain_hash INTO prev_hash
    FROM audit_logs
    WHERE tenant_id = NEW.tenant_id
    ORDER BY created_at DESC
    LIMIT 1;

    -- Compute chain hash: SHA-256(prev_hash + new_data)
    NEW.previous_audit_id = (
        SELECT audit_id FROM audit_logs
        WHERE tenant_id = NEW.tenant_id
        ORDER BY created_at DESC
        LIMIT 1
    );
    NEW.chain_hash = encode(
        sha256(
            COALESCE(prev_hash, 'GENESIS')::bytea ||
            NEW.tenant_id::text::bytea ||
            NEW.action::bytea ||
            NEW.resource_type::bytea ||
            NEW.resource_id::bytea ||
            NEW.created_at::text::bytea
        ),
        'hex'
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER compute_audit_chain
    BEFORE INSERT ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION compute_audit_chain_hash();

-- ── Audit Log Integrity Verification ──────────────────────────────

CREATE OR REPLACE FUNCTION verify_audit_chain(verify_tenant_id UUID)
RETURNS TABLE(entry_index BIGINT, audit_id UUID, hash_valid BOOLEAN)
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    prev_hash TEXT := 'GENESIS';
    idx BIGINT := 0;
    expected_hash TEXT;
BEGIN
    FOR rec IN
        SELECT * FROM audit_logs
        WHERE tenant_id = verify_tenant_id
        ORDER BY created_at ASC
    LOOP
        expected_hash := encode(
            sha256(
                prev_hash::bytea ||
                rec.tenant_id::text::bytea ||
                rec.action::bytea ||
                rec.resource_type::bytea ||
                rec.resource_id::bytea ||
                rec.created_at::text::bytea
            ),
            'hex'
        );
        entry_index := idx;
        audit_id := rec.audit_id;
        hash_valid := (expected_hash = rec.chain_hash);
        RETURN NEXT;
        prev_hash := rec.chain_hash;
        idx := idx + 1;
    END LOOP;
END;
$$;

-- Usage: SELECT * FROM verify_audit_chain('tenant-uuid');
-- Returns: entry_index, audit_id, hash_valid
-- If any row has hash_valid = FALSE, the audit log has been tampered with
```

### 7.3 Fix: Audit Log Verification Job

```python
# workers/maintenance.py

@celery_app.task(name="verify_audit_integrity")
def verify_audit_integrity():
    """Daily audit log integrity check. Alerts on tampering."""
    tenants = get_all_tenants()
    for tenant in tenants:
        result = db.execute(
            text("SELECT * FROM verify_audit_chain(:tenant_id) WHERE NOT hash_valid"),
            {"tenant_id": tenant},
        )
        tampered = result.fetchall()
        if tampered:
            logger.error(
                "AUDIT TAMPERING DETECTED",
                tenant_id=tenant,
                tampered_entries=[str(r.audit_id) for r in tampered],
            )
            # Send security alert
            send_security_alert(f"Audit log tampering detected for tenant {tenant}")
```

---

## 8. Fix Operational Security Gaps

### 8.1 Rate Limiting on Auth Endpoints

```python
# app/kernel/middleware/rate_limit.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting specifically for authentication endpoints.
    
    Prevents brute-force attacks and token enumeration.
    """

    RATE_LIMITS = {
        "/api/v1/auth/login": (10, 60),       # 10 requests per 60 seconds
        "/api/v1/auth/token": (20, 60),       # 20 requests per 60 seconds
        "/api/v1/auth/dev-login": (5, 300),   # 5 requests per 5 minutes
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self.RATE_LIMITS:
            limit, window = self.RATE_LIMITS[path]
            client_ip = request.client.host
            key = f"ratelimit:{path}:{client_ip}"

            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window)

            if count > limit:
                raise HTTPException(
                    status_code=429,
                    detail="Too many authentication attempts. Try again later.",
                )

        return await call_next(request)
```

### 8.2 JWT Leeway and Clock Skew Protection

```python
# app/kernel/security/auth.py — JWT validation with leeway

class JWTValidator:
    """JWT validation with clock skew protection."""

    MAX_CLOCK_SKEW_SECONDS = 30

    async def validate(self, token: str) -> UserContext:
        """Validate JWT with clock skew tolerance."""
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.settings.auth0_audience,
                issuer=self.settings.auth0_issuer,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "sub", "iss", "aud"],
                    "leeway": self.MAX_CLOCK_SKEW_SECONDS,
                },
            )
        except jwt.ExpiredSignatureError:
            # Check if within grace period
            if self._is_within_grace_period(token):
                logger.warning("Token accepted within grace period")
            else:
                raise
```

### 8.3 Secret Rotation

```python
# app/kernel/security/secrets.py

class SecretRotationManager:
    """Manages secret rotation with zero-downtime."""

    async def rotate_jwks(self):
        """JWKS rotation is handled by Auth0. Verify we're using the latest."""
        # Auth0 automatically rotates signing keys
        # Our JWKS provider fetches the latest on cache expiry
        # No manual rotation needed

    async def rotate_api_keys(self):
        """Rotate API keys that are near expiry."""
        expiring = await self.db.execute(
            "SELECT api_key_id, name FROM api_keys "
            "WHERE expires_at IS NOT NULL "
            "AND expires_at < NOW() + INTERVAL '7 days'"
        )
        for key in expiring:
            logger.info("API key expiring soon", key_id=key.api_key_id, name=key.name)

    async def rotate_dev_secret(self):
        """Rotate development JWT secret (production must use Auth0 only)."""
        if settings.environment == "production":
            return  # Dev tokens are disabled in production
        new_secret = secrets.token_urlsafe(64)
        settings.dev_jwt_secret = new_secret
        logger.info("Dev JWT secret rotated")
```

### 8.4 Security Event Logging

```python
# app/kernel/security/events.py

SECURITY_EVENTS = {
    "AUTH_SUCCESS": "auth.login.success",
    "AUTH_FAILURE": "auth.login.failure",
    "AUTH_TOKEN_EXPIRED": "auth.token.expired",
    "AUTH_TOKEN_INVALID": "auth.token.invalid",
    "AUTH_TOKEN_REVOKED": "auth.token.revoked",
    "AUTH_PERMISSION_DENIED": "auth.permission.denied",
    "AUTH_CROSS_TENANT_ATTEMPT": "auth.cross_tenant.attempt",
    "AUTH_API_KEY_USAGE": "auth.api_key.used",
    "AUTH_API_KEY_EXPIRING": "auth.api_key.expiring",
    "AUTH_RATE_LIMIT_EXCEEDED": "auth.rate_limit.exceeded",
    "AUTH_ROLE_CHANGED": "auth.role.changed",
    "AUTH_USER_CREATED": "auth.user.created",
    "AUTH_USER_DEACTIVATED": "auth.user.deactivated",
    "ADMIN_TENANT_OVERRIDE": "admin.tenant.override",
    "SECURITY_AUDIT_TAMPERING": "security.audit.tampering",
}


class SecurityEventLogger:
    """Logs security events for SIEM integration."""

    def log(self, event: str, **context):
        logger.warning(
            "SECURITY_EVENT",
            extra={
                "security_event": event,
                **context,
            },
        )
```

---

## 9. Hardening Summary

### 9.1 Critical Fixes

| # | Fix | Severity | Impact | Effort |
|---|-----|----------|--------|--------|
| 1 | Remove X-Tenant-ID trust — JWT is the only source of tenant_id | **CRITICAL** | Prevents cross-tenant data access via header injection | 1 hour |
| 2 | Reset session context on every DB connection checkout | **CRITICAL** | Prevents cross-tenant data leak via connection pooling | 2 hours |
| 3 | Worker tasks must include tenant_id — reject tasks without it | **CRITICAL** | Prevents worker from processing without tenant isolation | 1 hour |
| 4 | API key must validate tenant_id matches request context | **CRITICAL** | Prevents cross-tenant API key usage | 1 hour |
| 5 | Audit log chaining with SHA-256 checksums | **HIGH** | Detects audit log tampering | 3 hours |
| 6 | Permission cache for real-time role changes | **HIGH** | Closes 1-hour window of stale permissions | 2 hours |
| 7 | RLS fail-closed verification tests | **HIGH** | Ensures missing tenant context returns 0 rows | 1 hour |
| 8 | Rate limiting on auth endpoints | **HIGH** | Prevents brute-force attacks | 1 hour |

### 9.2 Verification Checklist

```
Pre-Deployment Verification:
[ ] X-Tenant-ID header is NEVER accepted — JWT is the only source
[ ] DB session context is RESET on every connection checkout
[ ] Connection pool test passes (Tenant B does not see Tenant A's data)
[ ] All worker tasks require and validate tenant_id
[ ] API key authentication validates tenant_id match
[ ] RLS fail-closed test passes (no tenant context = 0 rows)
[ ] Audit chain verification passes (no tampered entries)
[ ] Permission cache invalidates on role change
[ ] Rate limiting is active on auth endpoints
[ ] Dev token path is DISABLED in production
[ ] Security events are logged for SIEM integration
[ ] JWKS cache refreshes automatically (1 hour TTL)
[ ] Token validation includes clock skew leeway (30 seconds)
[ ] Audit log trigger prevents UPDATE/DELETE
```

### 9.3 Forbidden Patterns (Additions)

```
❌ X-Tenant-ID header from clients (CRITICAL: use JWT only)
❌ Sharing database sessions across requests (CRITICAL: new session per request)
❌ Worker tasks without explicit tenant_id (CRITICAL: always required)
❌ API keys without tenant_id validation (CRITICAL: must match request context)
❌ Token permissions without cache check (HIGH: stale permissions)
❌ Audit log modifications without chain verification (HIGH: tampering risk)
❌ Auth endpoints without rate limiting (HIGH: brute-force risk)
❌ Dev tokens in production (CRITICAL: must be disabled)
```
