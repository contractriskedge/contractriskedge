"""Auth0 JWT authentication middleware for FastAPI.

Provides JWT token validation against Auth0 with RS256 verification,
caching of JWKS keys, and tenant isolation via the X-Tenant-ID header.
Includes permission-based access control via the require_permission dependency.
"""

from __future__ import annotations

import json
import logging
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Union

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def _canonical_request_path(path: str) -> str:
    """Normalize URL path for auth exemption checks (handles trailing slashes)."""
    stripped = path.rstrip("/")
    return stripped if stripped else "/"


def _decode_dev_token(token: str) -> Optional[TokenPayload]:
    """Decode a development JWT token.

    Tries to decode the token as a dev token (HS256 with dev secret).
    Returns None if it's not a valid dev token.

    Args:
        token: The JWT token string.

    Returns:
        TokenPayload if valid dev token, None otherwise.
    """
    import base64
    import hashlib
    import hmac

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature with dev secret
        secret = os.getenv("DEV_JWT_SECRET", "dev-secret-change-in-production")
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(
                secret.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256,
            ).digest()
        ).rstrip(b"=").decode()

        if signature_b64 != expected_sig:
            return None

        # Decode payload
        # Add padding
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload_dict = json.loads(base64.urlsafe_b64decode(padded))

        # Check expiration
        if payload_dict.get("exp", 0) < time.time():
            return None

        return TokenPayload(
            sub=payload_dict.get("sub", "auth0|dev"),
            iss=payload_dict.get("iss", "https://dev.auth0.com/"),
            aud=payload_dict.get("aud", "https://api.contractriskedge.com"),
            exp=payload_dict.get("exp", int(time.time()) + 86400),
            iat=payload_dict.get("iat", int(time.time())),
            scope=payload_dict.get("scope", ""),
            permissions=payload_dict.get("permissions", []),
            tenant_id=payload_dict.get("tenant_id"),
            email=payload_dict.get("email"),
        )
    except Exception:
        return None


class Auth0Settings(BaseModel):
    """Auth0 configuration settings."""

    domain: str = Field(
        default_factory=lambda: os.getenv("AUTH0_DOMAIN", ""),
        description="Auth0 tenant domain",
    )
    audience: str = Field(
        default_factory=lambda: os.getenv("AUTH0_AUDIENCE", ""),
        description="Auth0 API audience identifier",
    )
    issuer: str = Field(
        default_factory=lambda: os.getenv("AUTH0_ISSUER", ""),
        description="Auth0 issuer URL",
    )
    jwks_url: str = Field(default="", description="JWKS endpoint URL")
    algorithm: str = "RS256"

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.jwks_url and self.domain:
            self.jwks_url = f"https://{self.domain}/.well-known/jwks.json"
        if not self.issuer and self.domain:
            self.issuer = f"https://{self.domain}/"


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str = Field(..., description="Subject (user ID)")
    iss: str = Field(..., description="Issuer")
    aud: Union[str, List[str]] = Field(..., description="Audience")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    scope: str = Field(default="", description="OAuth2 scopes")
    permissions: List[str] = Field(default_factory=list, description="API permissions")
    tenant_id: Optional[str] = Field(None, description="Tenant ID from app_metadata")
    email: Optional[str] = Field(None, description="User email")


class Auth0JWTValidator:
    """Validates Auth0 JWT tokens with JWKS key caching.

    Caches JWKS keys for 1 hour and validates tokens using RS256.
    Supports both access tokens and ID tokens.
    """

    JWKS_CACHE_TTL = 3600  # 1 hour

    def __init__(self, settings: Optional[Auth0Settings] = None) -> None:
        """Initialize the JWT validator.

        Args:
            settings: Auth0 configuration. Uses env vars if not provided.
        """
        self.settings = settings or Auth0Settings()
        self._jwks_cache: Dict[str, Any] = {}
        self._jwks_cache_time: float = 0
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            An httpx AsyncClient instance.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=10.0,
                limits=httpx.Limits(max_keepalive_connections=5),
            )
        return self._http_client

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS keys from Auth0, with caching.

        Returns:
            The JWKS key set as a dict.

        Raises:
            HTTPException: If JWKS fetch fails.
        """
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache_time) < self.JWKS_CACHE_TTL:
            return self._jwks_cache

        if not self.settings.jwks_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Auth0 JWKS URL not configured",
            )

        client = await self._get_client()
        try:
            response = await client.get(self.settings.jwks_url)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_time = now
            logger.debug("JWKS keys fetched and cached")
            return self._jwks_cache
        except httpx.HTTPStatusError as exc:
            logger.error("Failed to fetch JWKS: HTTP %d", exc.response.status_code)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch authentication keys",
            )
        except httpx.RequestError as exc:
            logger.error("Failed to fetch JWKS: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication service unreachable",
            )

    async def validate_token(self, token: str) -> TokenPayload:
        """Validate a JWT token and return its payload.

        Args:
            token: The JWT string to validate.

        Returns:
            Decoded TokenPayload.

        Raises:
            HTTPException: If the token is invalid or expired.
        """
        # Try dev token first (development mode)
        if os.getenv("ENVIRONMENT", "development") == "development":
            dev_payload = _decode_dev_token(token)
            if dev_payload is not None:
                return dev_payload

        if not self.settings.domain:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Auth0 domain not configured",
            )

        try:
            # Get the unverified header to find the key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID (kid)",
                )

            # Fetch JWKS and find the matching key
            jwks = await self._fetch_jwks()
            rsa_key: Optional[Dict[str, Any]] = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

            if not rsa_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No matching signing key found",
                )

            # Construct the public key
            public_key = jwk.construct(rsa_key)

            # Verify and decode the token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.settings.algorithm],
                audience=self.settings.audience,
                issuer=self.settings.issuer,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "sub", "iss", "aud"],
                },
            )

            # Extract permissions from scope
            scope_str = payload.get("scope", "")
            permissions = scope_str.split() if scope_str else []

            # Also check for Auth0 permissions claim
            permissions.extend(payload.get("permissions", []))

            # Extract tenant from app_metadata or custom claim
            app_metadata = payload.get("app_metadata", {}) or {}
            tenant_id = (
                app_metadata.get("tenant_id")
                or payload.get("https://contractriskanalyzer.com/tenant_id")
            )

            return TokenPayload(
                sub=payload["sub"],
                iss=payload["iss"],
                aud=payload["aud"],
                exp=payload["exp"],
                iat=payload["iat"],
                scope=scope_str,
                permissions=list(set(permissions)),
                tenant_id=tenant_id,
                email=payload.get("email"),
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTClaimsError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token claims: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None


security_scheme = HTTPBearer(auto_error=False)

# Global validator instance
_validator: Optional[Auth0JWTValidator] = None


def get_validator() -> Auth0JWTValidator:
    """Get or create the global JWT validator.

    Returns:
        The global Auth0JWTValidator instance.
    """
    global _validator
    if _validator is None:
        _validator = Auth0JWTValidator()
    return _validator


async def get_current_user(request: Request) -> TokenPayload:
    """Extract and validate the current user from the request.

    Dependency for FastAPI endpoints requiring authentication.

    Args:
        request: The incoming request.

    Returns:
        Validated TokenPayload.

    Raises:
        HTTPException: If authentication fails.
    """
    token_payload: Optional[TokenPayload] = getattr(request.state, "user", None)
    if token_payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return token_payload


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for Auth0 JWT authentication.

    Validates Bearer tokens on all requests except those in
    exclude_paths. Adds the validated TokenPayload to request.state.user.
    """

    def __init__(
        self,
        app: Any,
        exclude_paths: Optional[Set[str]] = None,
    ) -> None:
        """Initialize the auth middleware.

        Args:
            app: The ASGI application.
            exclude_paths: Set of URL paths to exclude from auth.
        """
        super().__init__(app)
        raw_exclude = exclude_paths or set()
        self.exclude_paths = raw_exclude
        self.exclude_paths_canonical = {_canonical_request_path(p) for p in raw_exclude}
        self.validator = get_validator()

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process the request through authentication.

        Args:
            request: Incoming request.
            call_next: Next middleware/route handler.

        Returns:
            Response from the next handler.
        """
        # Skip auth for excluded paths (exact + canonical / trailing-slash tolerant)
        req_path = request.url.path
        if req_path in self.exclude_paths or _canonical_request_path(req_path) in self.exclude_paths_canonical:
            return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "Missing or invalid Authorization header. "
                    "Use: Authorization: Bearer <token>",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            payload = await self.validator.validate_token(token)
            request.state.user = payload

            # Set tenant ID from token or header (header overrides for testing)
            tenant_id = request.headers.get("X-Tenant-ID") or payload.tenant_id
            request.state.tenant_id = tenant_id

            logger.debug(
                "Authenticated user %s (tenant: %s)",
                payload.sub,
                tenant_id,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Authentication error: %s", exc)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "Authentication failed",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)


def require_permission(permission: str):
    """Dependency factory for permission-based access control.

    Creates a FastAPI dependency that checks if the authenticated user
    has the required permission. Use as a Depends() in route handlers.

    Args:
        permission: The required permission string (e.g., 'read:contracts').

    Returns:
        A FastAPI dependency function.

    Example:
        @router.get("/contracts")
        async def list_contracts(
            user: TokenPayload = Depends(get_current_user),
            _: None = Depends(require_permission("read:contracts")),
        ):
            ...
    """

    async def _check_permission(
        user: TokenPayload = Depends(get_current_user),
    ) -> None:
        """Check if the user has the required permission."""
        if permission not in user.permissions:
            logger.warning(
                "Permission denied: user %s lacks '%s' (has: %s)",
                user.sub,
                permission,
                user.permissions,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": f"Missing required permission: {permission}",
                    "required_permission": permission,
                    "user_permissions": user.permissions,
                },
            )

    return _check_permission


class Permissions:
    """Central registry of all API permission constants.

    See middleware.rbac for the full role-to-permission mapping.
    """

    READ_CONTRACTS = "read:contracts"
    WRITE_CONTRACTS = "write:contracts"
    DELETE_CONTRACTS = "delete:contracts"
    ANNOTATE_CONTRACTS = "annotate:contracts"
    READ_REDLINES = "read:redlines"
    WRITE_REDLINES = "write:redlines"
    ACCEPT_REDLINES = "accept:redlines"
    READ_BENCHMARKS = "read:benchmarks"
    WRITE_PLAYBOOKS = "write:playbooks"
    READ_AUDIT = "read:audit"
    EXPORT_AUDIT = "export:audit"
    EXPORT_DATA = "export:data"
    MANAGE_USERS = "manage:users"
    MANAGE_BILLING = "manage:billing"
    MANAGE_INTEGRATIONS = "manage:integrations"
    ADMIN_TENANT = "admin:tenant"
    ADMIN_SYSTEM = "admin:system"
