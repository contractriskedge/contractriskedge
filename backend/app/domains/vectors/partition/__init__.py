"""Vector DB Architecture — partition management, embedding lifecycle, re-index jobs, stale invalidation.

Provides:
- RetrievalPartitionManager — per-tenant collection strategy (shared vs dedicated)
- EmbeddingLifecycleManager — track embedding model versions, detect staleness
- ReIndexScheduler — schedule and track re-index jobs
- StaleEmbeddingInvalidator — detect and invalidate stale embeddings
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.tenant_runtime import TenantTier, TenantIsolationLevel

logger = logging.getLogger(__name__)


class PartitionStrategy(str, Enum):
    SHARED_COLLECTION = "shared_collection"              # All tenants in one collection, filtered by metadata
    PER_TENANT_COLLECTION = "per_tenant_collection"      # Each tenant gets its own collection
    PER_TENANT_INDEX = "per_tenant_index"                # Each tenant gets its own index within shared collection
    HYBRID = "hybrid"                                     # Small tenants shared, large tenants dedicated


class EmbeddingModelStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"  # Will be removed, re-embedding required
    REMOVED = "removed"


@dataclass
class EmbeddingModelVersion:
    """Tracks an embedding model version in the system."""
    model_name: str
    version: str
    dimensions: int
    status: EmbeddingModelStatus
    released_at: str = ""
    deprecated_at: str | None = None
    sunset_at: str | None = None
    migration_target: str | None = None  # Model to migrate to
    change_notes: str = ""


@dataclass
class CollectionConfig:
    """Configuration for a vector collection."""
    collection_name: str
    tenant_id: str | None = None  # None for shared collections
    partition_strategy: PartitionStrategy = PartitionStrategy.SHARED_COLLECTION
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1536
    is_active: bool = True
    created_at: str = ""
    chunk_count: int = 0


# ── Embedding Model Registry ───────────────────────────────────────

EMBEDDING_MODEL_REGISTRY: dict[str, EmbeddingModelVersion] = {
    "text-embedding-3-large": EmbeddingModelVersion(
        model_name="text-embedding-3-large",
        version="1.0.0",
        dimensions=1536,
        status=EmbeddingModelStatus.ACTIVE,
        released_at="2024-01-01",
    ),
    "text-embedding-3-small": EmbeddingModelVersion(
        model_name="text-embedding-3-small",
        version="1.0.0",
        dimensions=512,
        status=EmbeddingModelStatus.ACTIVE,
        released_at="2024-01-01",
    ),
    "text-embedding-ada-002": EmbeddingModelVersion(
        model_name="text-embedding-ada-002",
        version="1.0.0",
        dimensions=1536,
        status=EmbeddingModelStatus.DEPRECATED,
        deprecated_at="2024-06-01",
        sunset_at="2025-01-01",
        migration_target="text-embedding-3-large",
        change_notes="Replaced by text-embedding-3-large with better quality and same dimensions",
    ),
}


# ── Retrieval Partition Manager ────────────────────────────────────

@dataclass
class RetrievalPartitionManager:
    """Manages vector collection partitioning strategy per tenant.

    Small tenants -> shared collections with metadata filters
    Large enterprise tenants -> dedicated collections

    This prevents retrieval performance degradation at scale.
    """

    session: AsyncSession

    def resolve_collection(self, tenant_id: str, tier: TenantTier) -> CollectionConfig:
        """Resolve which collection a tenant should use based on tier."""
        tier_config_map = {
            TenantTier.DEVELOPER: PartitionStrategy.SHARED_COLLECTION,
            TenantTier.STARTER: PartitionStrategy.SHARED_COLLECTION,
            TenantTier.PROFESSIONAL: PartitionStrategy.PER_TENANT_COLLECTION,
            TenantTier.ENTERPRISE: PartitionStrategy.PER_TENANT_COLLECTION,
            TenantTier.PLATFORM: PartitionStrategy.PER_TENANT_COLLECTION,
        }

        strategy = tier_config_map.get(tier, PartitionStrategy.SHARED_COLLECTION)

        if strategy == PartitionStrategy.SHARED_COLLECTION:
            return CollectionConfig(
                collection_name="contracts_shared",
                tenant_id=None,
                partition_strategy=PartitionStrategy.SHARED_COLLECTION,
            )
        else:
            return CollectionConfig(
                collection_name=f"contracts_{tenant_id[:8]}",
                tenant_id=tenant_id,
                partition_strategy=PartitionStrategy.PER_TENANT_COLLECTION,
            )

    def get_search_filter(self, tenant_id: str, config: CollectionConfig) -> dict[str, Any]:
        """Get the metadata filter for tenant-scoped vector search."""
        if config.partition_strategy == PartitionStrategy.SHARED_COLLECTION:
            return {"tenant_id": tenant_id}
        return {}  # Dedicated collections don't need tenant filter

    async def get_collection_stats(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get statistics about vector collections."""
        if tenant_id:
            sql = sa_text("""
                SELECT COUNT(*) as total_chunks,
                       COUNT(DISTINCT upload_id) as total_documents,
                       AVG(token_count) as avg_tokens
                FROM chunks
                WHERE tenant_id = :tenant_id AND is_active = true
            """)
            result = await self.session.execute(sql, {"tenant_id": tenant_id})
        else:
            sql = sa_text("""
                SELECT COUNT(*) as total_chunks,
                       COUNT(DISTINCT upload_id) as total_documents,
                       AVG(token_count) as avg_tokens
                FROM chunks WHERE is_active = true
            """)
            result = await self.session.execute(sql)

        row = result.fetchone()
        return {
            "total_chunks": row.total_chunks or 0,
            "total_documents": row.total_documents or 0,
            "avg_tokens": round(row.avg_tokens or 0, 1),
        }


# ── Embedding Lifecycle Manager ────────────────────────────────────

@dataclass
class EmbeddingLifecycleManager:
    """Manages the lifecycle of embedding models and detects stale embeddings.

    When an embedding model is upgraded, all embeddings created with the old
    model must be flagged as STALE and re-embedded.
    """

    session: AsyncSession

    def get_active_model(self) -> EmbeddingModelVersion:
        """Get the currently active embedding model."""
        for model in EMBEDDING_MODEL_REGISTRY.values():
            if model.status == EmbeddingModelStatus.ACTIVE:
                return model
        raise ValueError("No active embedding model found")

    def get_model(self, model_name: str) -> EmbeddingModelVersion | None:
        """Get a specific embedding model version."""
        return EMBEDDING_MODEL_REGISTRY.get(model_name)

    def is_model_stale(self, model_name: str) -> bool:
        """Check if an embedding model is deprecated or sunset."""
        model = self.get_model(model_name)
        if not model:
            return True
        return model.status in (EmbeddingModelStatus.DEPRECATED, EmbeddingModelStatus.SUNSET, EmbeddingModelStatus.REMOVED)

    async def find_stale_chunks(self, tenant_id: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        """Find chunks with stale embeddings that need re-embedding."""
        active_model = self.get_active_model()

        if tenant_id:
            sql = sa_text("""
                SELECT chunk_id, upload_id, tenant_id, embedding_model, chunk_index
                FROM chunks
                WHERE (embedding_model IS DISTINCT FROM :active_model
                   OR embedding_status = 'stale')
                  AND is_active = true
                  AND tenant_id = :tenant_id
                LIMIT :limit
            """)
            result = await self.session.execute(sql, {
                "active_model": active_model.model_name,
                "tenant_id": tenant_id,
                "limit": limit,
            })
        else:
            sql = sa_text("""
                SELECT chunk_id, upload_id, tenant_id, embedding_model, chunk_index
                FROM chunks
                WHERE (embedding_model IS DISTINCT FROM :active_model
                   OR embedding_status = 'stale')
                  AND is_active = true
                LIMIT :limit
            """)
            result = await self.session.execute(sql, {
                "active_model": active_model.model_name,
                "limit": limit,
            })

        return [
            {
                "chunk_id": str(row.chunk_id),
                "upload_id": str(row.upload_id),
                "tenant_id": str(row.tenant_id),
                "embedding_model": row.embedding_model,
                "chunk_index": row.chunk_index,
            }
            for row in result.fetchall()
        ]

    async def mark_stale_by_model(self, old_model: str) -> int:
        """Mark all chunks with a specific embedding model as stale."""
        sql = sa_text("""
            UPDATE chunks
            SET embedding_status = 'stale', updated_at = NOW()
            WHERE embedding_model = :old_model AND is_active = true
        """)
        result = await self.session.execute(sql, {"old_model": old_model})
        await self.session.flush()
        count = result.rowcount
        logger.info("Marked %d chunks as stale (model: %s)", count, old_model)
        return count

    async def count_stale_chunks(self, tenant_id: str | None = None) -> int:
        """Count chunks that need re-embedding."""
        if tenant_id:
            sql = sa_text("""
                SELECT COUNT(*) FROM chunks
                WHERE embedding_status = 'stale' AND tenant_id = :tenant_id
            """)
            result = await self.session.execute(sql, {"tenant_id": tenant_id})
        else:
            sql = sa_text("SELECT COUNT(*) FROM chunks WHERE embedding_status = 'stale'")
            result = await self.session.execute(sql)
        return result.scalar() or 0


# ── Re-Index Scheduler ─────────────────────────────────────────────

@dataclass
class ReIndexJob:
    """A scheduled re-index job for refreshing embeddings."""
    job_id: str = ""
    tenant_id: str | None = None
    reason: str = ""  # "model_upgrade", "manual", "scheduled"
    old_model: str = ""
    target_model: str = ""
    total_chunks: int = 0
    chunks_processed: int = 0
    chunks_failed: int = 0
    status: str = "pending"  # pending, processing, completed, failed
    started_at: str = ""
    completed_at: str | None = None
    error_message: str | None = None


@dataclass
class ReIndexScheduler:
    """Schedules and tracks re-index jobs for embedding model upgrades."""

    session: AsyncSession

    async def create_reindex_job(
        self,
        reason: str,
        old_model: str,
        target_model: str,
        tenant_id: str | None = None,
    ) -> ReIndexJob:
        """Create a re-index job to migrate embeddings to a new model."""
        import uuid
        job_id = str(uuid.uuid4())

        # Count affected chunks
        if tenant_id:
            sql = sa_text("""
                SELECT COUNT(*) FROM chunks
                WHERE embedding_model = :old_model
                  AND tenant_id = :tenant_id
                  AND is_active = true
            """)
            result = await self.session.execute(sql, {
                "old_model": old_model,
                "tenant_id": tenant_id,
            })
        else:
            sql = sa_text("""
                SELECT COUNT(*) FROM chunks
                WHERE embedding_model = :old_model AND is_active = true
            """)
            result = await self.session.execute(sql, {"old_model": old_model})

        total = result.scalar() or 0

        sql = sa_text("""
            INSERT INTO embedding_runs (run_id, upload_id, tenant_id, model, status, total_chunks)
            VALUES (:run_id, '00000000-0000-0000-0000-000000000000', :tenant_id, :model, 'pending', :total)
            RETURNING run_id
        """)
        await self.session.execute(sql, {
            "run_id": job_id,
            "tenant_id": tenant_id or "00000000-0000-0000-0000-000000000000",
            "model": target_model,
            "total": total,
        })
        await self.session.flush()

        job = ReIndexJob(
            job_id=job_id,
            tenant_id=tenant_id,
            reason=reason,
            old_model=old_model,
            target_model=target_model,
            total_chunks=total,
            status="pending",
            started_at=datetime.utcnow().isoformat(),
        )

        logger.info(
            "Created re-index job %s: %s -> %s (%d chunks, tenant=%s)",
            job_id[:8], old_model, target_model, total, tenant_id or "ALL",
        )
        return job

    async def get_pending_jobs(self) -> list[ReIndexJob]:
        """Get all pending re-index jobs."""
        sql = sa_text("""
            SELECT run_id, model, status, total_chunks, started_at, completed_at
            FROM embedding_runs
            WHERE status = 'pending'
            ORDER BY created_at ASC
        """)
        result = await self.session.execute(sql)
        return [
            ReIndexJob(
                job_id=str(row.run_id),
                target_model=row.model,
                status=row.status,
                total_chunks=row.total_chunks or 0,
                started_at=str(row.started_at) if row.started_at else "",
            )
            for row in result.fetchall()
        ]


# ── Stale Embedding Invalidator ────────────────────────────────────

@dataclass
class StaleEmbeddingInvalidator:
    """Detects and invalidates stale embeddings in the system.

    Should be run as a scheduled job (e.g., via Celery beat).
    """

    session: AsyncSession
    lifecycle_manager: EmbeddingLifecycleManager

    async def run_invalidation_pass(self, tenant_id: str | None = None) -> dict[str, int]:
        """Run a single invalidation pass — check for stale embeddings and mark them.

        Returns:
            Dict with counts of chunks invalidated.
        """
        active_model = self.lifecycle_manager.get_active_model()
        count = 0

        # Find chunks using deprecated/sunset models
        for model_name, model_version in EMBEDDING_MODEL_REGISTRY.items():
            if model_version.status in (EmbeddingModelStatus.DEPRECATED, EmbeddingModelStatus.SUNSET):
                c = await self.lifecycle_manager.mark_stale_by_model(model_name)
                count += c

        stale_count = await self.lifecycle_manager.count_stale_chunks(tenant_id)

        logger.info(
            "Invalidation pass complete: %d chunks marked stale, %d total stale",
            count, stale_count,
        )

        return {
            "chunks_invalidated": count,
            "total_stale": stale_count,
            "active_model": active_model.model_name,
        }

    async def get_invalidation_report(self) -> dict[str, Any]:
        """Get a report of embedding health across the system."""
        active = self.lifecycle_manager.get_active_model()

        sql = sa_text("""
            SELECT embedding_model, COUNT(*) as count,
                   MIN(created_at) as oldest, MAX(created_at) as newest
            FROM chunks
            WHERE is_active = true
            GROUP BY embedding_model
            ORDER BY count DESC
        """)
        result = await self.session.execute(sql)
        model_distribution = {
            str(row.embedding_model): {
                "count": row.count,
                "oldest": str(row.oldest) if row.oldest else "",
                "newest": str(row.newest) if row.newest else "",
            }
            for row in result.fetchall()
        }

        stale_count = await self.lifecycle_manager.count_stale_chunks()

        return {
            "active_model": active.model_name,
            "active_model_version": active.version,
            "model_distribution": model_distribution,
            "stale_chunks": stale_count,
            "models_requiring_migration": [
                {"model": name, "status": v.status.value, "migration_target": v.migration_target}
                for name, v in EMBEDDING_MODEL_REGISTRY.items()
                if v.status in (EmbeddingModelStatus.DEPRECATED, EmbeddingModelStatus.SUNSET)
            ],
        }
