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

    # ── AI Rate Limiting ───────────────────────────────────────────
    ai_rate_limit_analyze_per_user: int = 5
    """Max analyze requests per user per window."""
    ai_rate_limit_analyze_per_tenant: int = 100
    """Max analyze requests per tenant per tenant window."""
    ai_rate_limit_analyze_window_seconds: int = 60
    """Per-user sliding window for analyze requests."""
    ai_rate_limit_tenant_window_seconds: int = 3600
    """Per-tenant sliding window (1 hour)."""
    ai_rate_limit_copilot_per_user: int = 20
    """Max copilot suggest requests per user per window."""
    ai_rate_limit_copilot_per_tenant: int = 200
    """Max copilot suggest requests per tenant per hour."""
    ai_max_concurrent_analyses: int = 1
    """Max simultaneous AI analyses per tenant across all workers.
    Default 1 fits OpenAI Tier-1 TPM (30k). Raise via AI_MAX_CONCURRENT_ANALYSES when limits increase."""
    ai_concurrency_retry_seconds: int = 30
    """Max retry delay (seconds) when concurrent analysis limit reached.
    Actual delay uses exponential backoff: 5s, 10s, 20s, capped at this value."""

    @property
    def effective_max_concurrent(self) -> int:
        """Return environment-appropriate concurrency limit.
        Production is more conservative than development.
        """
        if self.environment == "production":
            return min(self.ai_max_concurrent_analyses, 3)
        return self.ai_max_concurrent_analyses

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
    # Override in production: CORS_ORIGINS_RAW='["https://app.contractriskedge.com"]'
    # Wildcard "*" is NEVER allowed in production — validated at startup.
    cors_origins_raw: str = '["http://localhost:3000", "http://localhost:8000"]'

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from JSON array or comma-separated string.

        In production, wildcard "*" is rejected (startup-blocked by _validate_secrets).
        Returns a list of explicit origins for the CORSMiddleware.
        """
        v = self.cors_origins_raw.strip()
        if v.startswith("["):
            import json
            try:
                origins = json.loads(v)
                if not isinstance(origins, list):
                    return []
                return [str(o).strip() for o in origins if o and str(o).strip()]
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

    # ── Resend ────────────────────────────────────────────────────
    resend_api_key: str = ""
    """Resend API key. Leave empty to disable email sending."""
    resend_from_email: str = "notifications@resend.dev"
    """Sender email address. Use resend.dev for development."""
    resend_from_name: str = "Contract Risk Edge"
    email_worker_enabled: bool = True
    email_retry_interval_minutes: int = 15
    email_max_attempts: int = 3

    app_url: str = "http://localhost:3000"

    # ── OpenAI / Embeddings ────────────────────────────────────────
    openai_api_key: str = ""
    """OpenAI API key. Required for embedding generation and AI features."""

    default_embedding_model: str = "text-embedding-3-small"
    """Default OpenAI embedding model. Override via DEFAULT_EMBEDDING_MODEL env var."""

    embedding_max_concurrent: int = 2
    """Max parallel OpenAI embedding API calls per tenant (all workers/threads)."""

    dev_inline_ingestion_max_concurrent: int = 2
    """Max parallel inline ingestion threads in development mode."""

    ai_allowed_models: list[str] = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "deepseek-v4-flash", "deepseek-v4-pro"]
    """List of allowed AI models for analysis. Override via AI_ALLOWED_MODELS env var."""

    ai_max_tokens: int = 128000
    """Maximum estimated prompt/context tokens for policy checks. Override via AI_MAX_TOKENS env var."""

    ai_max_response_tokens: int = 16384
    """Maximum completion (output) tokens per model call. Override via AI_MAX_RESPONSE_TOKENS env var."""

    ai_max_clause_size: int = 50000
    """Maximum clause size in characters. Override via AI_MAX_CLAUSE_SIZE env var."""

    ai_allowed_regions: list[str] = ["us", "eu", "uk"]
    """List of allowed regions for AI execution. Override via AI_ALLOWED_REGIONS env var."""

    ai_pii_protection_enabled: bool = True
    """Enable PII detection in prompts. Override via AI_PII_PROTECTION_ENABLED env var."""

    ai_min_confidence_threshold: float = 0.3
    """Minimum confidence threshold for AI responses. Override via AI_MIN_CONFIDENCE_THRESHOLD env var."""

    ai_provider_fallback_order: list[str] = ["openai"]
    """Provider fallback priority. Override via AI_PROVIDER_FALLBACK_ORDER env var."""

    deepseek_api_key: str = ""
    """DeepSeek API key for bulk ingestion. Override via DEEPSEEK_API_KEY env var."""

    deepseek_default_model: str = "deepseek-chat"
    """Default DeepSeek model. Override via DEEPSEEK_DEFAULT_MODEL env var."""

    ai_hybrid_routing: bool = False
    """When True, route risk analysis to DeepSeek and redlines to GPT-4o.
    Override via AI_HYBRID_ROUTING env var."""

    ai_feature_flags: list[str] = ["risk_analysis", "redline_generation", "clause_classification"]
    """Enabled AI feature flags. Override via AI_FEATURE_FLAGS env var."""

    ai_default_token_budget: int = 16384
    """Default completion token budget for AI analysis. Override via AI_DEFAULT_TOKEN_BUDGET env var."""

    ai_analysis_max_chunks: int = 20
    """Max document chunks sent to risk-analysis prompt (controls input TPM)."""

    ai_analysis_max_chunk_chars: int = 1200
    """Max characters per chunk in risk-analysis prompt."""

    # ── S3 / MinIO ─────────────────────────────────────────────────
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"
    s3_bucket: str = "contractrisk-documents"
    """Default S3/MinIO bucket for document storage."""
    s3_connect_timeout_seconds: int = 5
    s3_read_timeout_seconds: int = 120
    s3_operation_timeout_seconds: int = 60
    s3_skip_bucket_ensure: bool = True


settings = Settings()
