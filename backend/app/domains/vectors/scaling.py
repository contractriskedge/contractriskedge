"""Vector Scaling Architecture — shard balancing, hot/cold tiers, tenant migration, ANN optimization, semantic cache.

One of the biggest scaling bottlenecks for AI platforms.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VectorTier(str, Enum):
    HOT = "hot"           # Frequently accessed, full precision, in memory
    WARM = "warm"         # Moderate access, standard precision
    COLD = "cold"         # Rarely accessed, compressed, on disk
    ARCHIVE = "archive"   # Historical, not searchable without restore


@dataclass
class VectorShard:
    """A shard in the vector index."""
    shard_id: str
    tier: VectorTier
    tenant_ids: list[str] = field(default_factory=list)
    chunk_count: int = 0
    size_bytes: int = 0
    query_count_24h: int = 0
    avg_latency_ms: int = 0
    is_balanced: bool = True
    last_optimized: str = ""


@dataclass
class SemanticCacheEntry:
    """A cached semantic search result."""
    query_hash: str
    query_text: str
    result_ids: list[str] = field(default_factory=list)
    hit_count: int = 0
    created_at: str = ""
    last_accessed: str = ""
    ttl_seconds: int = 300


@dataclass
class VectorScaleManager:
    """Manages vector index scaling, tiering, caching, and optimization.

    Features:
    - Shard balancing across vector nodes
    - Hot/warm/cold tiering based on access patterns
    - Tenant vector migration between tiers
    - ANN index optimization scheduling
    - Semantic cache for repeated queries
    - Embedding lifecycle at scale
    """

    _shards: dict[str, VectorShard] = field(default_factory=dict)
    _cache: dict[str, SemanticCacheEntry] = field(default_factory=dict)
    _tier_thresholds: dict[VectorTier, int] = field(default_factory=lambda: {
        VectorTier.HOT: 100,      # >100 queries/day = hot
        VectorTier.WARM: 10,      # >10 queries/day = warm
        VectorTier.COLD: 1,       # >1 query/day = cold
        VectorTier.ARCHIVE: 0,    # 0 queries/day = archive
    })

    def __post_init__(self):
        self._register_default_shards()

    def _register_default_shards(self) -> None:
        """Register default vector shards."""
        for i in range(4):
            self._shards[f"shard_{i}"] = VectorShard(
                shard_id=f"shard_{i}",
                tier=VectorTier.HOT if i < 2 else VectorTier.WARM,
            )

    def resolve_tier(self, query_count_24h: int) -> VectorTier:
        """Resolve the appropriate tier based on access frequency."""
        if query_count_24h >= self._tier_thresholds[VectorTier.HOT]:
            return VectorTier.HOT
        elif query_count_24h >= self._tier_thresholds[VectorTier.WARM]:
            return VectorTier.WARM
        elif query_count_24h >= self._tier_thresholds[VectorTier.COLD]:
            return VectorTier.COLD
        return VectorTier.ARCHIVE

    def assign_tenant_to_shard(self, tenant_id: str, tier: VectorTier = VectorTier.WARM) -> str:
        """Assign a tenant to the best available shard."""
        # Find shard with least chunks in the target tier
        candidates = [
            s for s in self._shards.values()
            if s.tier == tier and s.is_balanced
        ]
        if not candidates:
            # Fall back to any tier
            candidates = list(self._shards.values())

        candidates.sort(key=lambda s: s.chunk_count)
        shard = candidates[0]
        if tenant_id not in shard.tenant_ids:
            shard.tenant_ids.append(tenant_id)
        return shard.shard_id

    async def migrate_tenant(
        self,
        tenant_id: str,
        from_shard: str,
        to_shard: str,
    ) -> dict[str, Any]:
        """Migrate a tenant's vectors from one shard to another."""
        source = self._shards.get(from_shard)
        target = self._shards.get(to_shard)

        if not source or not target:
            raise ValueError(f"Shard not found: {from_shard} or {to_shard}")

        if tenant_id in source.tenant_ids:
            source.tenant_ids.remove(tenant_id)
        if tenant_id not in target.tenant_ids:
            target.tenant_ids.append(tenant_id)

        logger.info("Migrated tenant %s from shard %s to %s", tenant_id[:8], from_shard, to_shard)
        return {
            "tenant_id": tenant_id,
            "from_shard": from_shard,
            "to_shard": to_shard,
            "migrated_at": datetime.utcnow().isoformat(),
        }

    async def rebalance(self) -> list[dict[str, Any]]:
        """Rebalance chunks across shards for even distribution."""
        actions = []
        shards = sorted(self._shards.values(), key=lambda s: s.chunk_count)
        if len(shards) < 2:
            return actions

        avg = sum(s.chunk_count for s in shards) / len(shards)
        overloaded = [s for s in shards if s.chunk_count > avg * 1.2]
        underloaded = [s for s in shards if s.chunk_count < avg * 0.8]

        for over in overloaded:
            for under in underloaded:
                if over.chunk_count > under.chunk_count:
                    actions.append({
                        "from": over.shard_id,
                        "to": under.shard_id,
                        "chunks_to_move": (over.chunk_count - under.chunk_count) // 2,
                    })
        return actions

    # ── Semantic Cache ─────────────────────────────────────────────

    def get_cache_key(self, query: str, tenant_id: str, filters: dict | None = None) -> str:
        """Generate a deterministic cache key for a query."""
        content = f"{tenant_id}:{query}:{str(filters or {})}"
        return hashlib.sha256(content.encode()).hexdigest()

    def cache_get(self, cache_key: str) -> list[str] | None:
        """Get cached results if available and not expired."""
        entry = self._cache.get(cache_key)
        if not entry:
            return None

        age = (datetime.utcnow() - datetime.fromisoformat(entry.last_accessed)).total_seconds()
        if age > entry.ttl_seconds:
            del self._cache[cache_key]
            return None

        entry.hit_count += 1
        entry.last_accessed = datetime.utcnow().isoformat()
        return entry.result_ids

    def cache_set(self, cache_key: str, query: str, result_ids: list[str], ttl: int = 300) -> None:
        """Cache search results."""
        self._cache[cache_key] = SemanticCacheEntry(
            query_hash=cache_key,
            query_text=query[:100],
            result_ids=result_ids,
            created_at=datetime.utcnow().isoformat(),
            last_accessed=datetime.utcnow().isoformat(),
            ttl_seconds=ttl,
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """Get semantic cache statistics."""
        entries = list(self._cache.values())
        total_hits = sum(e.hit_count for e in entries)
        return {
            "cache_size": len(entries),
            "total_hits": total_hits,
            "avg_hits_per_entry": round(total_hits / max(len(entries), 1), 1),
            "cache_hit_rate": 0.0,  # Would need total query count
        }

    def get_scale_status(self) -> dict[str, Any]:
        """Get vector scaling status report."""
        return {
            "shards": {
                sid: {
                    "tier": s.tier.value,
                    "chunks": s.chunk_count,
                    "tenants": len(s.tenant_ids),
                    "queries_24h": s.query_count_24h,
                    "avg_latency_ms": s.avg_latency_ms,
                    "balanced": s.is_balanced,
                }
                for sid, s in self._shards.items()
            },
            "tier_distribution": {
                t.value: sum(1 for s in self._shards.values() if s.tier == t)
                for t in VectorTier
            },
            "cache": self.get_cache_stats(),
            "total_chunks": sum(s.chunk_count for s in self._shards.values()),
        }


# ── Global singleton ───────────────────────────────────────────────

vector_scale_manager = VectorScaleManager()
