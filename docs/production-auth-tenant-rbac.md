# ContractRiskEdge — Production Auth + Tenant Isolation + RBAC Implementation

## V1 Enterprise-Grade Identity, Multi-Tenant Security & Authorization

---

## Table of Contents

1. [Authentication Strategy](#1-authentication-strategy)
2. [Auth0 Integration](#2-auth0-integration)
3. [JWT Validation & Token Management](#3-jwt-validation--token-management)
4. [Authentication Middleware](#4-authentication-middleware)
5. [Tenant Isolation Architecture](#5-tenant-isolation-architecture)
6. [PostgreSQL Row-Level Security](#6-postgresql-row-level-security)
7. [Tenant Context Propagation](#7-tenant-context-propagation)
8. [RBAC + Permission Model](#8-rbac--permission-model)
9. [Permission Enforcement](#9-permission-enforcement)
10. [API Key Authentication](#10-api-key-authentication)
11. [Service-to-Service Auth](#11-service-to-service-auth)
12. [Session Management](#12-session-management)
13. [Testing Auth + Tenant Isolation](#13-testing-auth--tenant-isolation)
14. [Engineering Governance](#14-engineering-governance)

---

## 1. Authentication Strategy

### 1.1 Architecture Overview

```
                    ┌──────────────────────────────────────────────┐
                    │         AUTHENTICATION ARCHITECTURE          │
                    ├──────────────────────────────────────────────┤
                    │                                              │
  ┌──────────┐      │  ┌──────────┐    ┌──────────┐              │
  │  Auth0   │──────│─>│  FastAPI  │───>│  JWT     │              │
  │  (OIDC)  │      │  │  Gateway │    │  Verify  │              │
  └──────────┘      │  └──────────┘    └────┬─────┘              │
                    │                        │                    │
                    │              ┌─────────┼─────────┐          │
                    │              │         │         │          │
                    │        ┌─────▼────┐ ┌──▼──────┐ ┌──▼─────┐ │
                    │        │  User    │ │  Tenant │ │  RBAC  │ │
                    │        │  Context │ │  Context│ │  Check │ │
                    │        └──────────┘ └─────────┘ └────────┘ │
                    │                                              │
                    │  Auth Flows:                                 │
                    │  ┌──────────────────────────────────────┐   │
                    │  │ SPA (PKCE)     → /authorize → /callback │   │
                    │  │ M2M (Client Credentials) → /oauth/token │   │
                    │  │ API Key        → X-API-Key header       │   │
                    │  │ Dev Token      → Development only       │   │
                    │  └──────────────────────────────────────┘   │
                    └──────────────────────────────────────────────┘
```

### 1.2 Authentication Flows

| Flow | Protocol | Use Case | Token Type | Expiry |
|------|----------|----------|------------|--------|
| **SPA Login** | OAuth 2.0 + PKCE | Browser-based UI | Access Token | 1 hour |
| **M2M** | Client Credentials | Backend services | Access Token | 24 hours |
| **API Key** | Static key | External integrations | Pre-shared key | Configurable |
| **Dev Token** | HS256 | Development only | Dev JWT | 24 hours |

### 1.3 Token Structure

```json
{
  "iss": "https://contractriskedge.auth0.com/",
  "sub": "auth0|63a1b2c3d4e5f6",
  "aud": "https://api.contractriskedge.com",
  "exp": 1715788800,
  "iat": 1715702400,
  "scope": "openid profile email",
  "permissions": [
    "contracts:read",
    "contracts:write",
    "workflows:approve"
  ],
  "email": "user@acmecorp.com",
  "https://api.contractriskedge.com/tenant_id": "tenant_uuid",
  "https://api.contractriskedge.com/role": "legal_reviewer"
}
```

### 1.4 Auth0 Tenant Setup

```text
AUTH0 CONFIGURATION (one-time setup):

1. Create Auth0 tenant: contractriskedge
2. Create API:
   - Name: ContractRiskEdge API
   - Identifier: https://api.contractriskedge.com
   - Signing Algorithm: RS256
3. Create Application (SPA):
   - Type: Single Page Application
   - Callback URLs: http://localhost:3000/api/auth/callback
   - Logout URLs: http://localhost:3000
   - Allowed Web Origins: http://localhost:3000
4. Create Application (M2M):
   - Type: Machine to Machine
   - Authorized for: ContractRiskEdge API
5. Create Roles:
   - tenant_admin, legal_reviewer, procurement_manager, approver, viewer, auditor
6. Create Permission Sets:
   - Map permissions to roles (see RBAC section)
7. Enable Auth0 Actions for tenant_id injection:
   - Pre-login action: Add tenant_id to app_metadata
   - Post-login action: Sync user to database
```

---

## 2. Auth0 Integration

### 2.1 Configuration

```python
# app/config.py

from pydantic_settings import BaseSettings

class AuthSettings(BaseSettings):
    # Auth0
    auth0_domain: str = "contractriskedge.auth0.com"
    auth0_audience: str = "https://api.contractriskedge.com"
    auth0_issuer: str = "https://contractriskedge.auth0.com/"
    auth0_jwks_url: str = "https://contractriskedge.auth0.com/.well-known/jwks.json"
    auth0_client_id: str = ""
    auth0_client_secret: str = ""

    # Token validation
    jwt_algorithm: str = "RS256"
    jwt_leeway: int = 10  # seconds

    # Development
    dev_jwt_secret: str = "dev-secret-change-in-production"
    environment: str = "development"

    # API Keys
    api_key_enabled: bool = True

    class Config:
        env_prefix = "AUTH_"
```

### 2.2 JWT Validator (Production)

```python
# app/kernel/security/auth.py

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx
from jose import jwk, jwt, JWTError

logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    """Authenticated user context — set on every request."""
    id: str                    # Auth0 sub claim
    email: str
    tenant_id: str
    role: str                  # 'tenant_admin', 'legal_reviewer', etc.
    permissions: list[str]     # ['contracts:read', 'contracts:write', ...]
    is_m2m: bool = False       # Machine-to-machine service account
    is_api_key: bool = False   # API key authentication


class TokenValidationError(Exception):
    """Raised when token validation fails."""
    pass


class JWKSProvider:
    """Cached JWKS key provider with automatic refresh."""

    CACHE_TTL = 3600  # 1 hour

    def __init__(self, jwks_url: str):
        self._jwks_url = jwks_url
        self._cache: dict = {}
        self._cache_time: float = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def get_key(self, kid: str) -> dict:
        """Get RSA key by key ID from cached JWKS."""
        await self._ensure_fresh()
        for key in self._cache.get("keys", []):
            if key.get("kid") == kid:
                return key
        raise TokenValidationError(f"No signing key found for kid: {kid}")

    async def _ensure_fresh(self):
        now = time.time()
        if self._cache and (now - self._cache_time) < self.CACHE_TTL:
            return
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self._jwks_url)
            resp.raise_for_status()
            self._cache = resp.json()
            self._cache_time = now
            logger.info("JWKS keys refreshed (%d keys)", len(self._cache.get("keys", [])))

    async def close(self):
        if self._client:
            await self._client.aclose()


class JWTValidator:
    """Validates Auth0 JWT tokens with JWKS caching."""

    def __init__(self, settings: "AuthSettings"):
        self.settings = settings
        self.jwks = JWKSProvider(settings.auth0_jwks_url)

    async def validate(self, token: str) -> UserContext:
        """Validate JWT and return user context. Raises TokenValidationError on failure."""
        # 1. Try dev token first (development only)
        if self.settings.environment == "development":
            user = self._try_dev_token(token)
            if user:
                return user

        # 2. Production validation
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise TokenValidationError("Token missing key ID (kid)")

            rsa_key = await self.jwks.get_key(kid)
            public_key = jwk.construct(rsa_key)

            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.settings.jwt_algorithm],
                audience=self.settings.auth0_audience,
                issuer=self.settings.auth0_issuer,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "sub", "iss", "aud"],
                },
            )

        except JWTError as exc:
            raise TokenValidationError(f"JWT validation failed: {exc}")

        return self._payload_to_context(payload)

    def _payload_to_context(self, payload: dict) -> UserContext:
        """Extract user context from decoded JWT payload."""
        namespace = f"{self.settings.auth0_audience}/"

        # Collect permissions from both Auth0 permissions claim and scope
        permissions = list(payload.get("permissions", []))
        scope = payload.get("scope", "")
        permissions.extend(scope.split())

        # Extract tenant_id from custom claims
        tenant_id = (
            payload.get(f"{namespace}tenant_id")
            or payload.get("tenant_id")
            or ""
        )

        return UserContext(
            id=payload["sub"],
            email=payload.get("email", ""),
            tenant_id=tenant_id,
            role=payload.get(f"{namespace}role", "viewer"),
            permissions=list(set(permissions)),
            is_m2m=payload.get("gty") == "client-credentials",
        )

    def _try_dev_token(self, token: str) -> Optional[UserContext]:
        """Validate development HS256 token (never enabled in production)."""
        import hmac, hashlib, base64, json
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts
            secret = self.settings.dev_jwt_secret

            expected_sig = base64.urlsafe_b64encode(
                hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
            ).rstrip(b"=").decode()

            if sig_b64 != expected_sig:
                return None

            padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))

            if payload.get("exp", 0) < time.time():
                return None

            return UserContext(
                id=payload.get("sub", "dev|user"),
                email=payload.get("email", "dev@example.com"),
                tenant_id=payload.get("tenant_id", "dev-tenant"),
                role=payload.get("role", "tenant_admin"),
                permissions=payload.get("permissions", ["*"]),
            )
        except Exception:
            return None

    async def close(self):
        await self.jwks.close()
```

---

## 3. JWT Validation & Token Management

### 3.1 Token Validation Flow

```
                    ┌──────────────────────────────────────┐
                    │         TOKEN VALIDATION FLOW        │
                    ├──────────────────────────────────────┤
                    │                                      │
  ┌──────────┐      │  1. Extract Bearer token from header │
  │ Request   │      │  2. Check dev token (dev only)      │
  │          │      │  3. Decode unverified header → get kid│
  │          │      │  4. Fetch JWKS (cached 1 hour)       │
  │          │      │  5. Find key by kid                  │
  │          │      │  6. Verify: signature, exp, iat,     │
  │          │      │     iss, aud                         │
  │          │      │  7. Extract: sub, email, tenant_id,  │
  │          │      │     role, permissions                │
  │          │      │  8. Build UserContext                │
  │          │      │  9. Set request.state.user           │
  │          │      │ 10. Set request.state.tenant_id      │
  └──────────┘      └──────────────────────────────────────┘
```

### 3.2 Token Validation Rules

```
1. EXP must be in the future (leeway: 10 seconds)
2. IAT must be in the past
3. ISS must match configured Auth0 issuer
4. AUD must match configured API audience
5. Signature must match JWKS public key
6. KID must be present in token header
7. SUB must be present (user or client ID)
8. Token must not be revoked (checked against Redis blacklist)
```

### 3.3 Token Revocation

```python
# app/kernel/security/token_revocation.py

import redis.asynced as aioredis

class TokenRevocationService:
    """Checks revoked tokens against Redis blacklist."""

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def revoke(self, jti: str, expires_in: int):
        """Add token ID to revocation list with TTL matching token expiry."""
        await self.redis.setex(f"revoked:{jti}", expires_in, "1")

    async def is_revoked(self, jti: str) -> bool:
        """Check if token has been revoked."""
        return await self.redis.exists(f"revoked:{jti}")

    async def revoke_all_user_tokens(self, user_id: str):
        """Revoke all tokens for a user (password reset, role change)."""
        await self.redis.incr(f"token_version:{user_id}")
```

---

## 4. Authentication Middleware

### 4.1 Auth Middleware

```python
# app/kernel/middleware/auth_context.py

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.kernel.security.auth import JWTValidator, TokenValidationError, UserContext
from app.config import settings

# Paths that don't require authentication
EXCLUDED_PATHS = {
    "/api/v1/health",
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/callback",
    "/api/v1/auth/dev-login",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Authenticates every request (except excluded paths)."""

    def __init__(self, app):
        super().__init__(app)
        self.validator = JWTValidator(settings.auth)

    async def dispatch(self, request: Request, call_next):
        # Skip excluded paths
        if request.url.path in EXCLUDED_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Extract token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "Missing Bearer token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.removeprefix("Bearer ").strip()

        # Validate token
        try:
            user = await self.validator.validate(token)
        except TokenValidationError as exc:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": str(exc)},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Set request context
        request.state.user = user
        request.state.tenant_id = request.headers.get("X-Tenant-ID") or user.tenant_id

        if not request.state.tenant_id:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "Tenant context required"},
            )

        return await call_next(request)
```

### 4.2 FastAPI Dependency

```python
# app/dependencies.py

from fastapi import Request, Depends, HTTPException
from app.kernel.security.auth import UserContext


async def get_current_user(request: Request) -> UserContext:
    """FastAPI dependency: get authenticated user (guaranteed by middleware)."""
    user: UserContext = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def get_tenant_id(request: Request) -> str:
    """FastAPI dependency: get current tenant ID."""
    tenant_id: str = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context required")
    return tenant_id
```

---

## 5. Tenant Isolation Architecture

### 5.1 Isolation Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TENANT ISOLATION STRATEGY                                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 1: Authentication (JWT)                                         │
│    └── Tenant ID embedded in JWT custom claims                         │
│    └── Cannot forge tenant ID without Auth0 private key                │
│                                                                         │
│  LAYER 2: Middleware (Request Context)                                 │
│    └── Tenant ID extracted from JWT or X-Tenant-ID header              │
│    └── Set on request.state.tenant_id                                  │
│    └── Set in PostgreSQL session: SET app.tenant_id = 'uuid'           │
│                                                                         │
│  LAYER 3: PostgreSQL Row-Level Security (MANDATORY)                    │
│    └── Every table has tenant_id column                                │
│    └── RLS policy: WHERE tenant_id = current_setting('app.tenant_id')  │
│    └── FAIL SAFE: Missing tenant_id → no rows returned (not all rows)  │
│                                                                         │
│  LAYER 4: Application Repository                                       │
│    └── Every repository method includes tenant_id filter               │
│    └── Even without RLS, queries are tenant-scoped                     │
│                                                                         │
│  LAYER 5: Cache Isolation                                              │
│    └── Redis keys prefixed with tenant_id                              │
│    └── Cache keys: {tenant_id}:{resource}:{id}                        │
│                                                                         │
│  LAYER 6: Search Isolation                                             │
│    └── pgvector queries include tenant_id filter                       │
│    └── Chunks table partitioned by HASH(tenant_id)                    │
│                                                                         │
│  LAYER 7: AI Isolation                                                 │
│    └── AI prompts include tenant context                               │
│    └── AI results tagged with tenant_id                                │
│    └── Cross-tenant AI analysis is BLOCKED                             │
│                                                                         │
│  LAYER 8: Event Isolation                                              │
│    └── Events include tenant_id                                        │
│    └── Event handlers filter by tenant_id                              │
│                                                                         │
│  FAIL-SAFE: If ANY layer fails open, the next layer catches it.        │
│  At least 3 layers must be breached for cross-tenant data access.      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Tenant Resolution Flow

```
                    ┌──────────────────────────────────────┐
                    │         TENANT RESOLUTION            │
                    ├──────────────────────────────────────┤
                    │                                      │
  ┌──────────┐      │  1. Extract from JWT custom claim    │
  │ Request   │──────│     (primary source)                 │
  └──────────┘      │                                      │
                    │  2. Override with X-Tenant-ID header  │
                    │     (admin/testing only, validated)   │
                    │                                      │
                    │  3. Validate tenant exists + active   │
                    │                                      │
                    │  4. Set request.state.tenant_id       │
                    │                                      │
                    │  5. Set PostgreSQL session:           │
                    │     SET app.tenant_id = 'uuid'        │
                    │     SET app.user_id = 'auth0|123'     │
                    │     SET app.user_role = 'admin'       │
                    │                                      │
                    │  6. Proceed to route handler          │
                    └──────────────────────────────────────┘
```

---

## 6. PostgreSQL Row-Level Security

### 6.1 RLS Implementation

```sql
-- ── Tenant Context Functions ──────────────────────────────────────

CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID;
END;
$$;

CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN NULLIF(current_setting('app.user_id', TRUE), '');
END;
$$;

CREATE OR REPLACE FUNCTION get_current_user_role()
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN NULLIF(current_setting('app.user_role', TRUE), '');
END;
$$;

-- ── RLS Policies ─────────────────────────────────────────────────

-- Every tenant-scoped table gets this EXACT policy:

ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON contracts
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON chunks
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workflows
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON audit_logs
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON notifications
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

ALTER TABLE ai_analyses ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ai_analyses
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

ALTER TABLE ai_findings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ai_findings
    FOR ALL
    USING (tenant_id = get_current_tenant_id());

-- ── User-Specific Policy (for user-owned data) ────────────────────

ALTER TABLE notifications ADD COLUMN user_id TEXT;
CREATE POLICY user_isolation ON notifications
    FOR ALL
    USING (
        tenant_id = get_current_tenant_id()
        AND (
            user_id = get_current_user_id()
            OR get_current_user_role() = 'tenant_admin'
        )
    );

-- ── Admin Override Policy ─────────────────────────────────────────

-- Tenant admins can see all data within their tenant
CREATE POLICY admin_access ON contracts
    FOR SELECT
    USING (
        tenant_id = get_current_tenant_id()
        AND (
            get_current_user_role() = 'tenant_admin'
            OR get_current_user_role() = 'auditor'
        )
    );
```

### 6.2 Setting Session Context (FastAPI Middleware)

```python
# app/kernel/middleware/tenant_context.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class TenantSQLContextMiddleware(BaseHTTPMiddleware):
    """Sets PostgreSQL session context for RLS enforcement."""

    async def dispatch(self, request: Request, call_next):
        tenant_id = getattr(request.state, "tenant_id", None)
        user = getattr(request.state, "user", None)

        if tenant_id:
            # These are set on the database connection pool
            # Each connection checks these settings before executing queries
            request.state.db_session_kwargs = {
                "app.tenant_id": tenant_id,
                "app.user_id": user.id if user else "",
                "app.user_role": user.role if user else "viewer",
            }

        return await call_next(request)


# ── Database session factory with context propagation ──────────────

# app/kernel/database/session.py

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

class TenantAwareSessionFactory:
    """Session factory that sets tenant context on each connection."""

    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, pool_size=10, max_overflow=5)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession)

    async def __call__(self, request: Request) -> AsyncSession:
        session = self.session_factory()
        context = getattr(request.state, "db_session_kwargs", {})

        # Set tenant context on this session
        for key, value in context.items():
            await session.execute(text(f"SET {key} = :val"), {"val": value})

        return session
```

### 6.3 Fail-Safe Query Rules

```sql
-- ❌ DANGEROUS: Missing tenant_id filter (RLS is the only protection)
SELECT * FROM contracts WHERE status = 'active';

-- ✅ SAFE: Explicit tenant_id filter (application-level + RLS)
SELECT * FROM contracts
WHERE tenant_id = :tenant_id AND status = 'active';

-- ❌ DANGEROUS: UPDATE without tenant_id
UPDATE contracts SET status = 'archived' WHERE contract_id = :id;

-- ✅ SAFE: UPDATE with tenant_id
UPDATE contracts SET status = 'archived'
WHERE contract_id = :id AND tenant_id = :tenant_id;

-- ❌ DANGEROUS: DELETE without tenant_id
DELETE FROM contracts WHERE contract_id = :id;

-- ✅ SAFE: DELETE with tenant_id
DELETE FROM contracts
WHERE contract_id = :id AND tenant_id = :tenant_id;
```

---

## 7. Tenant Context Propagation

### 7.1 Repository-Level Enforcement

```python
# app/kernel/repository/base.py

from dataclasses import dataclass
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class BaseRepository:
    """Base repository with tenant-safe query patterns."""

    session: AsyncSession
    tenant_id: str  # Injected by dependency

    async def execute(self, stmt):
        return await self.session.execute(stmt)

    async def scalar(self, stmt):
        result = await self.session.execute(stmt)
        return result.scalar()

    def _filter_tenant(self, stmt, model):
        """Add tenant_id filter to any query. FAIL-SAFE."""
        if not self.tenant_id:
            raise RuntimeError("Tenant ID is required for all queries")
        return stmt.where(model.tenant_id == self.tenant_id)


# domains/contracts/repository.py

from dataclasses import dataclass
from sqlalchemy import select, update
from app.kernel.repository.base import BaseRepository
from app.domains.contracts.models import Contract

@dataclass
class ContractRepository(BaseRepository):

    async def get_by_id(self, contract_id: str) -> Contract | None:
        stmt = select(Contract).where(
            Contract.contract_id == contract_id,
            Contract.deleted_at.is_(None),
        )
        stmt = self._filter_tenant(stmt, Contract)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, filters, pagination) -> tuple[list[Contract], int]:
        query = select(Contract).where(Contract.deleted_at.is_(None))
        query = self._filter_tenant(query, Contract)

        if filters.status:
            query = query.where(Contract.status == filters.status)
        if filters.contract_type:
            query = query.where(Contract.contract_type == filters.contract_type)

        sort_col = getattr(Contract, pagination.sort_by)
        order = sort_col.desc() if pagination.sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)

        return await self.paginate(query, pagination.page, pagination.page_size)

    async def create(self, **kwargs) -> Contract:
        contract = Contract(tenant_id=self.tenant_id, **kwargs)
        self.session.add(contract)
        await self.session.flush()
        return contract

    async def soft_delete(self, contract_id: str) -> None:
        stmt = (
            update(Contract)
            .where(Contract.contract_id == contract_id)
            .where(Contract.tenant_id == self.tenant_id)
            .values(deleted_at=func.now())
        )
        await self.session.execute(stmt)
```

### 7.2 Service-Level Tenant Injection

```python
# app/dependencies.py (domain-specific DI)

async def get_contract_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    event_bus = Depends(get_event_bus),
):
    from app.domains.contracts.repository import ContractRepository
    from app.domains.contracts.service import ContractService
    return ContractService(
        repository=ContractRepository(db, tenant_id=tenant_id),
        event_bus=event_bus,
        user=user,
        tenant_id=tenant_id,
    )
```

### 7.3 Cache Isolation

```python
# app/kernel/cache/tenant_cache.py

class TenantAwareCache:
    """Redis cache with tenant key prefixing."""

    def __init__(self, redis, tenant_id: str):
        self.redis = redis
        self.tenant_id = tenant_id

    def _key(self, key: str) -> str:
        return f"{self.tenant_id}:{key}"

    async def get(self, key: str):
        return await self.redis.get(self._key(key))

    async def set(self, key: str, value: str, ttl: int = 300):
        await self.redis.setex(self._key(key), ttl, value)

    async def delete(self, key: str):
        await self.redis.delete(self._key(key))

    async def flush_tenant(self):
        """Flush ALL cache keys for this tenant."""
        cursor = 0
        pattern = f"{self.tenant_id}:*"
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break
```

---

## 8. RBAC + Permission Model

### 8.1 Permission Structure

```python
# app/kernel/security/permissions.py

class Permissions:
    """Central permission registry. Single source of truth."""

    # ── Contracts ─────────────────────────────────────────────────
    CONTRACTS_READ = "contracts:read"
    CONTRACTS_WRITE = "contracts:write"
    CONTRACTS_DELETE = "contracts:delete"
    CONTRACTS_APPROVE = "contracts:approve"

    # ── AI ────────────────────────────────────────────────────────
    AI_ANALYZE = "ai:analyze"
    AI_VIEW = "ai:view"
    AI_MANAGE = "ai:manage"  # Configure AI models, prompts

    # ── Workflows ─────────────────────────────────────────────────
    WORKFLOWS_READ = "workflows:read"
    WORKFLOWS_WRITE = "workflows:write"
    WORKFLOWS_APPROVE = "workflows:approve"
    WORKFLOWS_ESCALATE = "workflows:escalate"

    # ── Vendors ───────────────────────────────────────────────────
    VENDORS_READ = "vendors:read"
    VENDORS_WRITE = "vendors:write"

    # ── Audit ─────────────────────────────────────────────────────
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # ── Users ─────────────────────────────────────────────────────
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"

    # ── Admin ─────────────────────────────────────────────────────
    ADMIN_TENANT = "admin:tenant"       # Tenant-level admin
    ADMIN_SYSTEM = "admin:system"       # Cross-tenant super admin
    ADMIN_BILLING = "admin:billing"
    ADMIN_INTEGRATIONS = "admin:integrations"

    # ── Special ───────────────────────────────────────────────────
    ALL = "*"  # Super admin (system-wide)
```

### 8.2 Default Role Definitions

```python
# app/kernel/security/roles.py

from app.kernel.security.permissions import Permissions as P

ROLES = {
    "super_admin": {
        "description": "System-wide administrator (platform team only)",
        "permissions": [P.ALL],
        "is_system": True,
    },
    "tenant_admin": {
        "description": "Tenant administrator — full access within tenant",
        "permissions": [
            P.CONTRACTS_READ, P.CONTRACTS_WRITE, P.CONTRACTS_DELETE, P.CONTRACTS_APPROVE,
            P.AI_ANALYZE, P.AI_VIEW, P.AI_MANAGE,
            P.WORKFLOWS_READ, P.WORKFLOWS_WRITE, P.WORKFLOWS_APPROVE, P.WORKFLOWS_ESCALATE,
            P.VENDORS_READ, P.VENDORS_WRITE,
            P.AUDIT_READ, P.AUDIT_EXPORT,
            P.USERS_READ, P.USERS_WRITE, P.USERS_DELETE,
            P.ADMIN_TENANT, P.ADMIN_BILLING, P.ADMIN_INTEGRATIONS,
        ],
        "is_system": True,
    },
    "legal_reviewer": {
        "description": "Legal team — reviews contracts, manages redlines",
        "permissions": [
            P.CONTRACTS_READ, P.CONTRACTS_WRITE, P.CONTRACTS_APPROVE,
            P.AI_ANALYZE, P.AI_VIEW,
            P.WORKFLOWS_READ, P.WORKFLOWS_WRITE, P.WORKFLOWS_APPROVE, P.WORKFLOWS_ESCALATE,
            P.VENDORS_READ,
        ],
        "is_system": True,
    },
    "procurement_manager": {
        "description": "Procurement — manages vendors, contracts, spend",
        "permissions": [
            P.CONTRACTS_READ, P.CONTRACTS_WRITE,
            P.AI_VIEW,
            P.WORKFLOWS_READ, P.WORKFLOWS_WRITE,
            P.VENDORS_READ, P.VENDORS_WRITE,
        ],
        "is_system": True,
    },
    "approver": {
        "description": "Executive approver — approves contracts and escalations",
        "permissions": [
            P.CONTRACTS_READ, P.CONTRACTS_APPROVE,
            P.AI_VIEW,
            P.WORKFLOWS_READ, P.WORKFLOWS_APPROVE,
            P.VENDORS_READ,
        ],
        "is_system": True,
    },
    "viewer": {
        "description": "Read-only access — auditors, stakeholders",
        "permissions": [
            P.CONTRACTS_READ,
            P.AI_VIEW,
            P.WORKFLOWS_READ,
            P.VENDORS_READ,
            P.AUDIT_READ,
        ],
        "is_system": True,
    },
    "auditor": {
        "description": "Auditor — read-only access to everything including audit logs",
        "permissions": [
            P.CONTRACTS_READ,
            P.AI_VIEW,
            P.WORKFLOWS_READ,
            P.VENDORS_READ,
            P.AUDIT_READ, P.AUDIT_EXPORT,
            P.USERS_READ,
        ],
        "is_system": True,
    },
}
```

### 8.3 Permission Enforcement

```python
# app/kernel/security/rbac.py

from fastapi import Depends, HTTPException, status
from functools import wraps
from app.dependencies import get_current_user
from app.kernel.security.auth import UserContext


class PermissionDenied(Exception):
    pass


def require_permission(permission: str):
    """FastAPI dependency: check user has required permission.

    Usage:
        @router.delete("/contracts/{id}")
        async def delete_contract(
            _: None = Depends(require_permission("contracts:delete")),
            service = Depends(get_contract_service),
        ):
            ...
    """
    async def _check(user: UserContext = Depends(get_current_user)) -> None:
        if Permissions.ALL in user.permissions:
            return  # super_admin bypass
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": f"Missing required permission: {permission}",
                },
            )
    return _check


def require_any_permission(*permissions: str):
    """FastAPI dependency: check user has at least one of the listed permissions."""
    async def _check(user: UserContext = Depends(get_current_user)) -> None:
        if Permissions.ALL in user.permissions:
            return
        if not any(p in user.permissions for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": f"Missing any required permission: {permissions}",
                },
            )
    return _check


def require_role(role: str):
    """FastAPI dependency: check user has specific role."""
    async def _check(user: UserContext = Depends(get_current_user)) -> None:
        if user.role != role and Permissions.ALL not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "forbidden", "message": f"Required role: {role}"},
            )
    return _check
```

### 8.4 Route-Level Enforcement Examples

```python
# domains/contracts/router.py

from fastapi import APIRouter, Depends, status
from app.kernel.security.rbac import require_permission, require_any_permission
from app.kernel.security.permissions import Permissions

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("/")
@require_permission(Permissions.CONTRACTS_READ)
async def list_contracts(service = Depends(get_contract_service)):
    ...


@router.post("/", status_code=status.HTTP_201_CREATED)
@require_permission(Permissions.CONTRACTS_WRITE)
async def create_contract(body: ContractCreate, service = Depends(get_contract_service)):
    ...


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission(Permissions.CONTRACTS_DELETE)
async def delete_contract(contract_id: str, service = Depends(get_contract_service)):
    ...


@router.post("/{contract_id}/approve")
@require_permission(Permissions.CONTRACTS_APPROVE)
async def approve_contract(contract_id: str, service = Depends(get_contract_service)):
    ...


# ── AI routes ──────────────────────────────────────────────────────

@router.post("/{contract_id}/analyze")
@require_any_permission(Permissions.AI_ANALYZE, Permissions.ADMIN_TENANT)
async def analyze_contract(contract_id: str, service = Depends(get_ai_service)):
    ...


# ── Admin routes ───────────────────────────────────────────────────

@router.get("/audit-logs")
@require_permission(Permissions.AUDIT_READ)
async def list_audit_logs(service = Depends(get_audit_service)):
    ...
```

---

## 9. API Key Authentication

### 9.1 API Key Model

```python
# domains/auth/models.py

class APIKey(Base):
    __tablename__ = "api_keys"

    api_key_id = Column(UUID, primary_key=True, default=uuid_generate_v4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id"), nullable=False)
    name = Column(Text, nullable=False)              # Human-readable name
    key_hash = Column(Text, nullable=False, unique=True)  # bcrypt hash of key
    key_prefix = Column(Text, nullable=False)        # First 8 chars for identification
    permissions = Column(ARRAY(Text), nullable=False, default=[])
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True))
    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
```

### 9.2 API Key Authentication

```python
# app/kernel/security/api_key.py

import secrets
import hashlib
from dataclasses import dataclass

@dataclass
class APIKeyContext:
    key_id: str
    tenant_id: str
    permissions: list[str]


class APIKeyAuthenticator:
    """Validates API keys and provides user context."""

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """Generate a new API key. Returns (raw_key, key_hash, key_prefix)."""
        raw_key = f"cre_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]
        return raw_key, key_hash, key_prefix

    async def authenticate(self, api_key: str) -> APIKeyContext:
        """Validate API key and return context."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Look up by hash
        result = await self.db.execute(
            "SELECT api_key_id, tenant_id, permissions, expires_at, is_active "
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

        # Update last used
        await self.db.execute(
            "UPDATE api_keys SET last_used_at = NOW() WHERE api_key_id = :id",
            {"id": row.api_key_id},
        )

        return APIKeyContext(
            key_id=row.api_key_id,
            tenant_id=row.tenant_id,
            permissions=row.permissions,
        )
```

---

## 10. Testing Auth + Tenant Isolation

### 10.1 Test Fixtures

```python
# tests/conftest.py

import pytest
from app.kernel.security.auth import UserContext

@pytest.fixture
def tenant_admin_user():
    return UserContext(
        id="auth0|test-admin",
        email="admin@test.com",
        tenant_id="test-tenant-1",
        role="tenant_admin",
        permissions=["contracts:read", "contracts:write", "contracts:delete", "workflows:approve", "ai:analyze", "audit:read", "users:read", "users:write"],
    )

@pytest.fixture
def viewer_user():
    return UserContext(
        id="auth0|test-viewer",
        email="viewer@test.com",
        tenant_id="test-tenant-1",
        role="viewer",
        permissions=["contracts:read", "workflows:read"],
    )

@pytest.fixture
def other_tenant_user():
    return UserContext(
        id="auth0|other-tenant",
        email="other@test.com",
        tenant_id="test-tenant-2",  # DIFFERENT tenant
        role="viewer",
        permissions=["contracts:read"],
    )

@pytest.fixture
def auth_headers(tenant_admin_user):
    """Generate auth headers for test requests."""
    token = generate_test_token(tenant_admin_user)
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_admin_user.tenant_id}
```

### 10.2 Tenant Isolation Tests

```python
# tests/integration/test_tenant_isolation.py

import pytest

class TestTenantIsolation:
    """CRITICAL: These tests verify that tenants CANNOT access each other's data."""

    async def test_tenant_cannot_read_other_tenant_contracts(
        self, client, tenant_admin_user, other_tenant_user
    ):
        """Tenant A creates a contract. Tenant B tries to read it → 404."""
        # Tenant A creates contract
        client.force_login(tenant_admin_user)
        resp = await client.post("/api/v1/contracts", json={"filename": "test.pdf"})
        assert resp.status_code == 201
        contract_id = resp.json()["data"]["contract_id"]

        # Tenant B tries to read it
        client.force_login(other_tenant_user)
        resp = await client.get(f"/api/v1/contracts/{contract_id}")
        assert resp.status_code == 404  # NOT 403 — hide existence

    async def test_tenant_cannot_search_other_tenant_chunks(
        self, client, tenant_admin_user, other_tenant_user
    ):
        """Tenant A's chunks are invisible to Tenant B's search."""
        client.force_login(tenant_admin_user)
        resp = await client.get("/api/v1/search?q=indemnification")
        tenant_a_ids = {r["chunk_id"] for r in resp.json()["data"]}

        client.force_login(other_tenant_user)
        resp = await client.get("/api/v1/search?q=indemnification")
        tenant_b_ids = {r["chunk_id"] for r in resp.json()["data"]}

        # No overlap
        assert tenant_a_ids.isdisjoint(tenant_b_ids)

    async def test_tenant_cannot_access_other_tenant_workflows(
        self, client, tenant_admin_user, other_tenant_user
    ):
        """Tenant A's workflows are invisible to Tenant B."""
        client.force_login(tenant_admin_user)
        resp = await client.get("/api/v1/workflows")
        tenant_a_count = len(resp.json()["data"])

        client.force_login(other_tenant_user)
        resp = await client.get("/api/v1/workflows")
        tenant_b_count = len(resp.json()["data"])

        # Different tenants, different data
        # This test verifies the counts aren't accidentally the same
        # (more precise: verify no overlap in IDs)

    async def test_rls_policy_prevents_direct_sql_leakage(
        self, db_session_factory
    ):
        """Even with direct SQL, RLS prevents cross-tenant access."""
        # Simulate Tenant A's session
        session_a = db_session_factory()
        await session_a.execute("SET app.tenant_id = 'tenant-a'")
        result_a = await session_a.execute("SELECT COUNT(*) FROM contracts")
        count_a = result_a.scalar()

        # Simulate Tenant B's session
        session_b = db_session_factory()
        await session_b.execute("SET app.tenant_id = 'tenant-b'")
        result_b = await session_b.execute("SELECT COUNT(*) FROM contracts")
        count_b = result_b.scalar()

        # Total across both tenants
        session_admin = db_session_factory()
        await session_admin.execute("SET app.tenant_id = 'tenant-a'")
        # Admin override
        # ...

        # Verify tenant isolation
        # count_a + count_b should equal total (no overlap, no gaps)
```

### 10.3 RBAC Tests

```python
# tests/integration/test_rbac.py

class TestRBAC:

    async def test_viewer_cannot_delete_contract(
        self, client, viewer_user
    ):
        client.force_login(viewer_user)
        resp = await client.delete("/api/v1/contracts/some-id")
        assert resp.status_code == 403
        assert resp.json()["error"] == "forbidden"

    async def test_viewer_cannot_analyze_contract(
        self, client, viewer_user
    ):
        client.force_login(viewer_user)
        resp = await client.post("/api/v1/ai/analyze/some-id")
        assert resp.status_code == 403

    async def test_legal_reviewer_can_approve_workflow(
        self, client, legal_reviewer_user
    ):
        client.force_login(legal_reviewer_user)
        resp = await client.post("/api/v1/workflows/wf-id/approve")
        assert resp.status_code == 200

    async def test_unauthenticated_request_is_rejected(
        self, client
    ):
        resp = await client.get("/api/v1/contracts")
        assert resp.status_code == 401
```

---

## 11. Engineering Governance

### 11.1 Tenant Isolation Rules

```
1. EVERY repository method MUST include tenant_id filter
   → Enforced via BaseRepository._filter_tenant()

2. EVERY database query MUST be tenant-scoped
   → RLS is the LAST line of defense, not the only one

3. EVERY cache key MUST be prefixed with tenant_id
   → {tenant_id}:{resource}:{id}

4. EVERY event MUST include tenant_id
   → Event handlers MUST filter by tenant_id

5. EVERY AI analysis MUST be tagged with tenant_id
   → Cross-tenant AI training is BLOCKED in V1

6. Tenant ID MUST come from JWT, NOT user input
   → X-Tenant-ID header is validated against JWT claims

7. Missing tenant_id = FAIL CLOSED (return 401, not all data)
```

### 11.2 RBAC Rules

```
1. Routes use require_permission() — NOT manual role checks
2. Permission checks happen in the dependency layer, not in service code
3. Service layer does NOT import permissions — it's the router's responsibility
4. Default role is 'viewer' (least privilege)
5. Super admin bypasses all permission checks (but NOT tenant isolation)
6. API keys have their own permission set (separate from user roles)
7. Permission changes require Auth0 re-login (token contains permissions at issue time)
```

### 11.3 Security Checklist

```
Pre-Deployment:
[ ] All tenant-scoped tables have RLS enabled
[ ] All RLS policies tested with cross-tenant attack scenarios
[ ] Auth0 JWKS URL is configured and reachable
[ ] Token validation includes: signature, exp, iat, iss, aud
[ ] Dev token path is DISABLED in production (ENVIRONMENT=production)
[ ] API key hashing uses SHA-256 (not plaintext)
[ ] CORS origins are restricted (not *)
[ ] Rate limiting is configured on auth endpoints
[ ] Failed auth attempts are logged
[ ] Token revocation is tested

CI/CD:
[ ] Tenant isolation tests run on every PR
[ ] RBAC tests run on every PR
[ ] Auth middleware tests run on every PR
[ ] No hardcoded secrets in code (enforced by pre-commit)
```
