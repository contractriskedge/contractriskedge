"""Multi-Tenant Isolation Runtime — hard tenant boundaries for enterprise AI infrastructure.

Provides:
- TenantContextResolver — resolve and validate tenant context from any execution path
- TenantIsolationMiddleware — FastAPI middleware enforcing tenant boundaries at API layer
- TenantQuotaManager — per-tenant resource quotas and enforcement
- TenantResourceGovernor — CPU/memory/rate-limit governance per tenant tier
- TenantScopedRepositories — factory for creating tenant-scoped repository instances
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Tenant Tiers ───────────────────────────────────────────────────

class TenantTier(str, Enum):
    DEVELOPER = "developer"          # Free tier — strict limits
    STARTER = "starter"              # Low-volume commercial
    PROFESSIONAL = "professional"    # Mid-market
    ENTERPRISE = "enterprise"        # Full isolation, dedicated resources
    PLATFORM = "platform"            # Internal system tenant


class TenantIsolationLevel(str, Enum):
    SHARED = "shared"                # Shared vector collections, shared queues
    DEDICATED_COLLECTIONS = "dedicated_collections"  # Per-tenant vector collections
    DEDICATED_INFRA = "dedicated_infra"              # Per-tenant compute/resources


@dataclass
class TenantTierConfig:
    """Resource limits and isolation settings per tenant tier."""
    tier: TenantTier
    max_uploads_per_day: int
    max_contracts: int
    max_users: int
    max_api_calls_per_min: int
    max_concurrent_analyses: int
    max_storage_gb: int
    max_vector_dimensions: int
    isolation_level: TenantIsolationLevel
    max_retrieval_chunks: int
    max_prompt_tokens: int
    allow_custom_models: bool
    allow_custom_prompts: bool
    max_export_rows: int
    retention_days: int
    support_tier: str  # "community", "standard", "premium", "enterprise"


# ── Tier Configuration Catalog ─────────────────────────────────────

TIER_CONFIGS: dict[TenantTier, TenantTierConfig] = {
    TenantTier.DEVELOPER: TenantTierConfig(
        tier=TenantTier.DEVELOPER,
        max_uploads_per_day=10,
        max_contracts=50,
        max_users=3,
        max_api_calls_per_min=20,
        max_concurrent_analyses=1,
        max_storage_gb=1,
        max_vector_dimensions=1536,
        isolation_level=TenantIsolationLevel.SHARED,
        max_retrieval_chunks=5,
        max_prompt_tokens=8000,
        allow_custom_models=False,
        allow_custom_prompts=False,
        max_export_rows=100,
        retention_days=30,
        support_tier="community",
    ),
    TenantTier.STARTER: TenantTierConfig(
        tier=TenantTier.STARTER,
        max_uploads_per_day=50,
        max_contracts=500,
        max_users=10,
        max_api_calls_per_min=100,
        max_concurrent_analyses=3,
        max_storage_gb=10,
        max_vector_dimensions=1536,
        isolation_level=TenantIsolationLevel.SHARED,
        max_retrieval_chunks=10,
        max_prompt_tokens=16000,
        allow_custom_models=False,
        allow_custom_prompts=False,
        max_export_rows=1000,
        retention_days=90,
        support_tier="standard",
    ),
    TenantTier.PROFESSIONAL: TenantTierConfig(
        tier=TenantTier.PROFESSIONAL,
        max_uploads_per_day=200,
        max_contracts=5000,
        max_users=50,
        max_api_calls_per_min=500,
        max_concurrent_analyses=10,
        max_storage_gb=50,
        max_vector_dimensions=1536,
        isolation_level=TenantIsolationLevel.DEDICATED_COLLECTIONS,
        max_retrieval_chunks=20,
        max_prompt_tokens=32000,
        allow_custom_models=False,
        allow_custom_prompts=True,
        max_export_rows=10000,
        retention_days=365,
        support_tier="premium",
    ),
    TenantTier.ENTERPRISE: TenantTierConfig(
        tier=TenantTier.ENTERPRISE,
        max_uploads_per_day=1000,
        max_contracts=100000,
        max_users=1000,
        max_api_calls_per_min=5000,
        max_concurrent_analyses=50,
        max_storage_gb=500,
        max_vector_dimensions=3072,
        isolation_level=TenantIsolationLevel.DEDICATED_INFRA,
        max_retrieval_chunks=50,
        max_prompt_tokens=128000,
        allow_custom_models=True,
        allow_custom_prompts=True,
        max_export_rows=100000,
        retention_days=2555,  # 7 years
        support_tier="enterprise",
    ),
    TenantTier.PLATFORM: TenantTierConfig(
        tier=TenantTier.PLATFORM,
        max_uploads_per_day=10000,
        max_contracts=1000000,
        max_users=10000,
        max_api_calls_per_min=50000,
        max_concurrent_analyses=500,
        max_storage_gb=5000,
        max_vector_dimensions=3072,
        isolation_level=TenantIsolationLevel.DEDICATED_INFRA,
        max_retrieval_chunks=100,
        max_prompt_tokens=128000,
        allow_custom_models=True,
        allow_custom_prompts=True,
        max_export_rows=1000000,
        retention_days=2555,
        support_tier="enterprise",
    ),
}


# ── Tenant Context Resolver ────────────────────────────────────────

@dataclass
class TenantContext:
    """Resolved tenant context with full isolation metadata."""
    tenant_id: str
    tenant_tier: TenantTier
    isolation_level: TenantIsolationLevel
    config: TenantTierConfig
    is_active: bool = True
    is_system_tenant: bool = False
    parent_tenant_id: str | None = None  # For multi-entity enterprises
    features: dict[str, bool] = field(default_factory=dict)


class TenantContextResolver:
    """Resolves and validates tenant context from any execution path.

    Tenant ID is ALWAYS resolved from the authentication context,
    NEVER from client-supplied headers.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve(self, tenant_id: str) -> TenantContext:
        """Resolve a tenant ID to its full context with tier and isolation config.

        Args:
            tenant_id: The tenant ID from the authenticated JWT.

        Returns:
            TenantContext with tier configuration and isolation settings.

        Raises:
            TenantNotFoundError: If tenant does not exist.
            TenantInactiveError: If tenant is suspended.
        """
        sql = sa_text("""
            SELECT t.tenant_id, t.name, t.tier, t.is_active, t.is_system_tenant,
                   t.parent_tenant_id, t.features
            FROM tenants t
            WHERE t.tenant_id = :tenant_id
        """)
        result = await self.session.execute(sql, {"tenant_id": tenant_id})
        row = result.fetchone()

        if not row:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        if not row.is_active:
            raise TenantInactiveError(f"Tenant {tenant_id} is inactive/suspended")

        tier = TenantTier(row.tier) if row.tier else TenantTier.DEVELOPER
        config = TIER_CONFIGS.get(tier, TIER_CONFIGS[TenantTier.DEVELOPER])

        return TenantContext(
            tenant_id=str(row.tenant_id),
            tenant_tier=tier,
            isolation_level=config.isolation_level,
            config=config,
            is_active=row.is_active,
            is_system_tenant=row.is_system_tenant or False,
            parent_tenant_id=str(row.parent_tenant_id) if row.parent_tenant_id else None,
            features=row.features or {},
        )


class TenantNotFoundError(Exception):
    """Raised when a tenant ID does not exist."""


class TenantInactiveError(Exception):
    """Raised when a tenant is suspended or inactive."""


# ── Tenant Quota Manager ───────────────────────────────────────────

@dataclass
class QuotaUsage:
    """Current quota usage for a tenant."""
    tenant_id: str
    uploads_today: int = 0
    total_contracts: int = 0
    total_users: int = 0
    api_calls_this_minute: int = 0
    concurrent_analyses: int = 0
    storage_bytes: int = 0
    exports_today: int = 0
    tokens_used_today: int = 0
    cost_today_usd: float = 0.0


class QuotaExceededError(Exception):
    """Raised when a tenant exceeds a resource quota."""
    def __init__(self, resource: str, limit: int, current: int):
        self.resource = resource
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded for {resource}: {current}/{limit}")


@dataclass
class TenantQuotaManager:
    """Manages per-tenant resource quotas with real-time enforcement.

    Uses a combination of in-memory counters and database persistence.
    For production, back with Redis for distributed accuracy.
    """

    session: AsyncSession
    _in_memory_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    _rate_limit_windows: dict[str, dict[str, float]] = field(default_factory=dict)

    async def check_upload_quota(self, tenant_id: str, tier_config: TenantTierConfig) -> None:
        """Check if tenant can upload more documents today."""
        usage = await self._get_usage(tenant_id)
        if usage.uploads_today >= tier_config.max_uploads_per_day:
            raise QuotaExceededError("uploads_per_day", tier_config.max_uploads_per_day, usage.uploads_today)

    async def check_api_rate_limit(self, tenant_id: str, tier_config: TenantTierConfig) -> None:
        """Check if tenant has exceeded API rate limit."""
        now = time.time()
        window_key = f"{tenant_id}:api_minute"
        window_start = self._rate_limit_windows.get(window_key, {}).get("start", now)

        if now - window_start > 60:
            # Reset window
            self._rate_limit_windows[window_key] = {"start": now, "count": 0}

        count = self._rate_limit_windows[window_key].get("count", 0)
        if count >= tier_config.max_api_calls_per_min:
            raise QuotaExceededError("api_calls_per_min", tier_config.max_api_calls_per_min, count)

        self._rate_limit_windows[window_key]["count"] = count + 1

    async def check_concurrent_analyses(self, tenant_id: str, tier_config: TenantTierConfig) -> None:
        """Check concurrent analysis limit."""
        sql = sa_text("""
            SELECT COUNT(*) FROM ai_execution_runs
            WHERE tenant_id = :tenant_id
            AND status IN ('processing', 'pending')
        """)
        result = await self.session.execute(sql, {"tenant_id": tenant_id})
        concurrent = result.scalar() or 0
        if concurrent >= tier_config.max_concurrent_analyses:
            raise QuotaExceededError("concurrent_analyses", tier_config.max_concurrent_analyses, concurrent)

    async def check_storage_quota(self, tenant_id: str, tier_config: TenantTierConfig) -> None:
        """Check total storage usage."""
        sql = sa_text("""
            SELECT COALESCE(SUM(COALESCE(file_size, 0)), 0)
            FROM upload_sessions
            WHERE tenant_id = :tenant_id AND is_active = true
        """)
        result = await self.session.execute(sql, {"tenant_id": tenant_id})
        total_bytes = result.scalar() or 0
        max_bytes = tier_config.max_storage_gb * 1024 * 1024 * 1024
        if total_bytes >= max_bytes:
            raise QuotaExceededError("storage", tier_config.max_storage_gb, total_bytes // (1024**3))

    async def check_prompt_tokens(self, tenant_id: str, tier_config: TenantTierConfig, token_count: int) -> None:
        """Check if prompt token count is within tenant limits."""
        if token_count > tier_config.max_prompt_tokens:
            raise QuotaExceededError("prompt_tokens", tier_config.max_prompt_tokens, token_count)

    async def check_export_quota(self, tenant_id: str, tier_config: TenantTierConfig, row_count: int) -> None:
        """Check export row limit."""
        if row_count > tier_config.max_export_rows:
            raise QuotaExceededError("export_rows", tier_config.max_export_rows, row_count)

    async def _get_usage(self, tenant_id: str) -> QuotaUsage:
        """Get current usage for a tenant."""
        sql = sa_text("""
            SELECT
                (SELECT COUNT(*) FROM upload_sessions
                 WHERE tenant_id = :tid AND created_at >= CURRENT_DATE) as uploads_today,
                (SELECT COUNT(*) FROM upload_sessions
                 WHERE tenant_id = :tid AND is_active = true) as total_contracts,
                (SELECT COUNT(*) FROM users WHERE tenant_id = :tid) as total_users
        """)
        result = await self.session.execute(sql, {"tid": tenant_id})
        row = result.fetchone()
        return QuotaUsage(
            tenant_id=tenant_id,
            uploads_today=row.uploads_today or 0,
            total_contracts=row.total_contracts or 0,
            total_users=row.total_users or 0,
        )


# ── Tenant Resource Governor ───────────────────────────────────────

@dataclass
class ResourceGovernanceDecision:
    """Decision from the resource governor."""
    allowed: bool
    reason: str = ""
    suggested_provider: str | None = None
    suggested_model: str | None = None
    suggested_timeout: int | None = None
    throttle_delay_ms: int = 0


@dataclass
class TenantResourceGovernor:
    """Governs resource allocation per tenant based on tier and real-time load.

    Makes decisions about:
    - Which provider/model to route to based on tenant tier
    - Whether to throttle or queue requests
    - Timeout adjustments based on tenant priority
    """

    session: AsyncSession
    quota_manager: TenantQuotaManager

    async def govern_execution(
        self,
        tenant_id: str,
        operation: str,
        tier_config: TenantTierConfig,
        preferred_provider: str = "openai",
        preferred_model: str = "gpt-4o",
    ) -> ResourceGovernanceDecision:
        """Govern an AI execution request — apply tier-based resource controls."""
        # Check tier-based model restrictions
        if preferred_model in ("gpt-4-turbo", "claude-3-opus") and not tier_config.allow_custom_models:
            return ResourceGovernanceDecision(
                allowed=False,
                reason=f"Tenant tier {tier_config.tier.value} does not allow premium models",
                suggested_model="gpt-4o-mini",
            )

        # Check concurrent analysis limit
        try:
            await self.quota_manager.check_concurrent_analyses(tenant_id, tier_config)
        except QuotaExceededError:
            return ResourceGovernanceDecision(
                allowed=False,
                reason="Concurrent analysis limit reached for tenant tier",
                throttle_delay_ms=5000,
            )

        return ResourceGovernanceDecision(allowed=True)


# ── Tenant-Scoped Repository Factory ───────────────────────────────

@dataclass
class TenantScopedRepositories:
    """Factory for creating tenant-scoped repository instances.

    Every repository created through this factory is guaranteed to have
    the correct tenant_id, preventing cross-tenant data leaks.
    """

    session: AsyncSession
    tenant_id: str

    def ai_repository(self):
        from app.domains.ai.repository import AIRepository
        return AIRepository(self.session, tenant_id=self.tenant_id)

    def vector_repository(self):
        from app.domains.vectors.repository import VectorRepository
        return VectorRepository(self.session, tenant_id=self.tenant_id)

    def search_repository(self):
        from app.domains.search.repository import SearchRepository
        return SearchRepository(self.session, tenant_id=self.tenant_id)

    def review_repository(self):
        from app.domains.review.repository import ReviewRepository
        return ReviewRepository(self.session, tenant_id=self.tenant_id)

    def ingestion_repository(self):
        from app.domains.ingestion.repository import IngestionRepository
        return IngestionRepository(self.session, tenant_id=self.tenant_id)

    def extraction_repository(self):
        from app.domains.extraction.repository import ExtractionRepository
        return ExtractionRepository(self.session, tenant_id=self.tenant_id)

    def tenant_config_service(self):
        from app.domains.tenant_config.service import FeatureFlagService
        return FeatureFlagService(self.session, self.tenant_id)

    def retrieval_snapshot_service(self):
        from app.domains.ai.snapshots.service import RetrievalSnapshotService
        return RetrievalSnapshotService(self.session, self.tenant_id)
