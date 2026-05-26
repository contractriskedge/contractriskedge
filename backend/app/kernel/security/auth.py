"""JWT validation, Auth0 integration, and user context model.

Provides production-grade JWT validation with JWKS caching,
clock skew protection, and typed user context.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
from jose import jwk, jwt, JWTError

logger = logging.getLogger(__name__)


class TokenValidationError(Exception):
    """Raised when JWT validation fails."""


@dataclass
class UserContext:
    """Authenticated user context — set on request.state.user for every request."""

    id: str
    email: str
    tenant_id: str
    role: str
    permissions: list[str] = field(default_factory=list)
    is_m2m: bool = False
    is_api_key: bool = False


class JWKSProvider:
    """Cached JWKS key provider with automatic refresh.

    Fetches JWKS from Auth0 on first use and caches for 1 hour.
    """

    CACHE_TTL = 3600

    def __init__(self, jwks_url: str):
        self._jwks_url = jwks_url
        self._cache: dict[str, Any] = {}
        self._cache_time: float = 0

    async def get_key(self, kid: str) -> dict[str, Any]:
        """Get RSA public key by key ID."""
        await self._ensure_fresh()
        for key in self._cache.get("keys", []):
            if key.get("kid") == kid:
                return key
        raise TokenValidationError(f"No signing key found for kid: {kid}")

    async def _ensure_fresh(self) -> None:
        now = time.time()
        if self._cache and (now - self._cache_time) < self.CACHE_TTL:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self._jwks_url)
            response.raise_for_status()
            self._cache = response.json()
            self._cache_time = now
            logger.info("JWKS keys refreshed (%d keys)", len(self._cache.get("keys", [])))


class JWTValidator:
    """Validates Auth0 JWT tokens with JWKS caching and clock skew protection.

    Supports:
    - Auth0 RS256 tokens (production)
    - Dev HS256 tokens (development only)
    - Clock skew tolerance (30 seconds)
    """

    MAX_CLOCK_SKEW = 30

    def __init__(self, domain: str, audience: str, issuer: str, dev_secret: str, environment: str):
        self._domain = domain
        self._audience = audience
        self._issuer = issuer
        self._dev_secret = dev_secret
        self._environment = environment
        self._jwks = JWKSProvider(f"https://{domain}/.well-known/jwks.json") if domain else None

    async def validate(self, token: str) -> UserContext:
        """Validate a JWT token and return UserContext.

        In development mode, also attempts dev token validation.
        Raises TokenValidationError on any validation failure.
        """
        # Development mode: try dev token first
        if self._environment == "development":
            user = self._try_dev_token(token)
            if user is not None:
                return user

        # Production validation
        return await self._validate_auth0_token(token)

    async def _validate_auth0_token(self, token: str) -> UserContext:
        if not self._jwks:
            raise TokenValidationError("Auth0 domain not configured")

        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise TokenValidationError("Token missing key ID (kid)")

            rsa_key = await self._jwks.get_key(kid)
            public_key = jwk.construct(rsa_key)

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "sub", "iss", "aud"],
                    "leeway": self.MAX_CLOCK_SKEW,
                },
            )
        except JWTError as exc:
            raise TokenValidationError(f"JWT validation failed: {exc}")

        return self._payload_to_context(payload)

    def _payload_to_context(self, payload: dict) -> UserContext:
        namespace = f"{self._audience}/"
        permissions = list(payload.get("permissions", []))
        scope = payload.get("scope", "")
        permissions.extend(scope.split())

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
        """Validate development HS256 token. Never enabled in production."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts

            expected_sig = urlsafe_b64encode(
                hmac.new(
                    self._dev_secret.encode(),
                    f"{header_b64}.{payload_b64}".encode(),
                    hashlib.sha256,
                ).digest()
            ).rstrip(b"=").decode()

            if sig_b64 != expected_sig:
                return None

            padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(urlsafe_b64decode(padded))

            if payload.get("exp", 0) < time.time():
                return None

            from app.config import settings

            return UserContext(
                id=payload.get("sub", settings.dev_user_id),
                email=payload.get("email", "dev@example.com"),
                tenant_id=payload.get("tenant_id", settings.dev_tenant_id),
                role=payload.get("role", "tenant_admin"),
                permissions=payload.get("permissions", ["*"]),
            )
        except Exception:
            return None
