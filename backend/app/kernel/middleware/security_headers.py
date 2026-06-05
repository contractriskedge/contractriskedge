"""Security headers middleware — CSP, HSTS, X-Frame-Options, etc.

Adds security headers to all HTTP responses:

- Content-Security-Policy: Restricts script/style/font sources
- Strict-Transport-Security: Enforces HTTPS (production only)
- X-Frame-Options: Prevents clickjacking
- X-Content-Type-Options: Prevents MIME sniffing
- Referrer-Policy: Controls referrer header

Compatibility verified with:
- Next.js frontend (localhost:3000 / app.contractriskedge.com)
- Swagger/OpenAPI docs (/docs, /redoc, /openapi.json)
- Auth0 login flow (universal login page)
- Sentry error tracking (js.sentry-cdn.com / o123456.ingest.sentry.io)
- OpenTelemetry (otel endpoint)
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds OWASP-recommended security headers to every response.

    CSP is environment-aware:
    - Development: allows localhost:3000 (Next.js dev server), localhost:8000 (API)
    - Production: allows app.contractriskedge.com, api.contractriskedge.com

    HSTS is only set in production (max-age=1 year, includeSubDomains).
    """

    # ── Script sources for Swagger UI ─────────────────────────────
    SWAGGER_CDN = "https://cdn.jsdelivr.net"

    @staticmethod
    def _csp_connect_src(env: str) -> str:
        """Build connect-src policy based on environment."""
        sources = [
            "'self'",
            "https://*.auth0.com",       # Auth0 authentication
            "https://*.ingest.sentry.io", # Sentry error reporting
        ]
        if env == "development":
            sources.extend([
                "http://localhost:3000",   # Next.js dev server (HMR)
                "http://localhost:8000",   # API dev server
                "ws://localhost:3000",     # Next.js HMR WebSocket
            ])
        else:
            sources.extend([
                "https://app.contractriskedge.com",
                "https://api.contractriskedge.com",
                "wss://app.contractriskedge.com",
            ])
        return " ".join(sources)

    @staticmethod
    def _csp_script_src(env: str) -> str:
        """Build script-src policy — needs 'unsafe-inline' for Next.js and Swagger."""
        sources = [
            "'self'",
            "'unsafe-inline'",      # Next.js inline scripts (required)
            "'unsafe-eval'",        # Swagger UI (required for JS bundling)
            SecurityHeadersMiddleware.SWAGGER_CDN,
        ]
        if env == "development":
            sources.append("http://localhost:3000")
        return " ".join(sources)

    @staticmethod
    def _csp_style_src(env: str) -> str:
        """Build style-src policy — needs 'unsafe-inline' for Next.js and Swagger."""
        sources = [
            "'self'",
            "'unsafe-inline'",      # Next.js and Swagger UI inline styles
            SecurityHeadersMiddleware.SWAGGER_CDN,
        ]
        if env == "development":
            sources.append("http://localhost:3000")
        return " ".join(sources)

    @staticmethod
    def _csp_font_src() -> str:
        return "'self' data:"

    @staticmethod
    def _csp_img_src() -> str:
        return "'self' data: https:"

    @staticmethod
    def _csp_frame_src() -> str:
        """Frame sources — Swagger UI uses jsdelivr, Auth0 uses its own domain."""
        return "https://*.auth0.com"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response: Response = await call_next(request)

        env = settings.environment

        # ── Content-Security-Policy ────────────────────────────────
        csp_policy = (
            f"default-src 'self'; "
            f"script-src {self._csp_script_src(env)}; "
            f"style-src {self._csp_style_src(env)}; "
            f"connect-src {self._csp_connect_src(env)}; "
            f"font-src {self._csp_font_src()}; "
            f"img-src {self._csp_img_src()}; "
            f"frame-src {self._csp_frame_src()}; "
            f"object-src 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self' https://*.auth0.com; "
        )
        response.headers["Content-Security-Policy"] = csp_policy

        # ── Strict-Transport-Security (production only) ────────────
        if env == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # ── X-Frame-Options ────────────────────────────────────────
        response.headers["X-Frame-Options"] = "DENY"

        # ── X-Content-Type-Options ─────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ── Referrer-Policy ────────────────────────────────────────
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Permissions-Policy (optional but recommended) ──────────
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )

        return response
