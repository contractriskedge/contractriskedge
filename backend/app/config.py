"""Application configuration via pydantic-settings.

All configuration comes from environment variables (via .env file or actual env).
No hardcoded secrets. No default secrets in production.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from typing import List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    @field_validator("debug", mode="before")
    @classmethod
    def coerce_debug(cls, v: object) -> bool:
        """Coerce DEBUG env var to bool, accepting common string values."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)
    secret_key: str = ""

    @field_validator("secret_key")
    @classmethod
    def warn_if_default_secret(cls, v: str) -> str:
        """Warn if secret_key is still the placeholder or empty."""
        if not v or v in ("change-this-in-production",):
            import logging
            logging.warning(
                "SECRET_KEY is not set or still using default. "
                "Set a strong, unique SECRET_KEY in your .env file for production."
            )
        return v

    # ── Database ───────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev"
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_recycle: int = 300
    db_echo: bool = False
    db_statement_timeout_ms: int = 30000   # 30s — kill queries exceeding this
    db_lock_timeout_ms: int = 5000         # 5s — kill lock contention
    db_idle_transaction_timeout_s: int = 60  # 60s — abort idle transactions
    db_slow_query_threshold_ms: int = 500  # Log queries slower than this

    # ── Request Limits ─────────────────────────────────────────────
    max_request_body_bytes: int = 100_000_000  # 100MB
    max_upload_file_bytes: int = 100_000_000    # 100MB
    request_timeout_seconds: int = 30           # 30s default API timeout

    # ── Rate Limiting ──────────────────────────────────────────────
    rate_limit_enabled: bool = True
    """Enable or disable API rate limiting globally."""
    rate_limit_anonymous: int = 20
    """Max requests per minute for unauthenticated users."""
    rate_limit_authenticated: int = 100
    """Max requests per minute for authenticated users."""
    rate_limit_admin: int = 500
    """Max requests per minute for admin users."""
    rate_limit_window_seconds: int = 60
    """Sliding window size in seconds for rate limit tracking."""

    # ── Redis ──────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Auth0 ──────────────────────────────────────────────────────
    auth0_domain: str = ""
    auth0_audience: str = "https://api.contractriskedge.com"
    auth0_issuer: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""

    @property
    def auth0_jwks_url(self) -> str:
        return f"https://{self.auth0_domain}/.well-known/jwks.json" if self.auth0_domain else ""

    # ── Development Auth ───────────────────────────────────────────
    dev_jwt_secret: str = ""

    @field_validator("dev_jwt_secret")
    @classmethod
    def warn_if_default_dev_secret(cls, v: str) -> str:
        """Warn if dev_jwt_secret is still the placeholder or empty."""
        if not v or v in ("dev-secret-change-in-production",):
            import logging
            logging.warning(
                "DEV_JWT_SECRET is not set or still using default. "
                "Set DEV_JWT_SECRET in your .env file. "
                "This secret is used ONLY in development mode."
            )
        return v

    dev_auth_bypass: bool = False
    dev_tenant_id: str = "00000000-0000-4000-8000-000000000001"
    dev_user_id: str = "dev-user"

    # ── CORS ───────────────────────────────────────────────────────
    cors_origins_raw: str = '["http://localhost:3000", "http://localhost:8000"]'

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from JSON array or comma-separated string."""
        v = self.cors_origins_raw.strip()
        if v.startswith("["):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                pass
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # ── OpenTelemetry ──────────────────────────────────────────────
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "contractrisk-api"

    # ── Sentry ─────────────────────────────────────────────────────
    sentry_dsn: str = ""

    # ── Celery ─────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── SMTP / Email ──────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@contractriskedge.com"
    smtp_tls: bool = True
    app_url: str = "http://localhost:3000"

    # ── OpenAI / Embeddings ────────────────────────────────────────
    openai_api_key: str = ""
    """OpenAI API key. Required for embedding generation and AI features."""

    default_embedding_model: str = "text-embedding-3-small"
    """Default OpenAI embedding model. Override via DEFAULT_EMBEDDING_MODEL env var."""

    # ── S3 / MinIO ─────────────────────────────────────────────────
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"
    s3_bucket: str = "contractedge-documents"
    """Default S3/MinIO bucket for document storage."""
    s3_connect_timeout_seconds: int = 5
    s3_read_timeout_seconds: int = 120
    s3_operation_timeout_seconds: int = 60
    s3_skip_bucket_ensure: bool = True


settings = Settings()
