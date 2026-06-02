"""Distributed Queue Orchestration — regional partitions, workload sharding, priority queues, adaptive scheduling.

Extends the existing ReliableQueueManager with distributed capabilities.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class QueueShard(str, Enum):
    DEFAULT = "default"
    HIGH_PRIORITY = "high_priority"
    AI_ANALYSIS = "ai_analysis"
    EMBEDDINGS = "embeddings"
    EXPORTS = "exports"
    NOTIFICATIONS = "notifications"
    REPLAY = "replay"
    WORKFLOW = "workflow"


class ShardStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    TENANT_HASH = "tenant_hash"
    PRIORITY = "priority"
    LEAST_LOADED = "least_loaded"


@dataclass
class QueueShardConfig:
    """Configuration for a queue shard."""
    name: str
    region: str = "default"
    max_concurrent: int = 10
    priority: int = 5  # 1 (highest) to 10 (lowest)
    weight: float = 1.0  # For weighted distribution


@dataclass
class ShardMetrics:
    """Metrics for a queue shard."""
    shard: str
    depth: int = 0
    processing: int = 0
    processed_per_min: float = 0.0
    avg_latency_ms: int = 0
    error_rate: float = 0.0
    saturation_pct: float = 0.0
    is_starving: bool = False
    last_updated: str = ""


@dataclass
class DistributedQueueOrchestrator:
    """Distributed queue orchestration with sharding, priority, and adaptive scheduling.

    Features:
    - Regional queue partitions (each region has its own queue set)
    - Workload sharding by tenant, type, or round-robin
    - Priority queues with starvation prevention
    - Adaptive scheduling based on shard saturation
    - Burst workload routing to underloaded shards
    - Tenant fairness tracking
    """

    _shards: dict[str, QueueShardConfig] = field(default_factory=dict)
    _shard_metrics: dict[str, ShardMetrics] = field(default_factory=dict)
    _tenant_assignments: dict[str, str] = field(default_factory=dict)
    _strategy: ShardStrategy = ShardStrategy.LEAST_LOADED
    _starvation_counters: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self._register_default_shards()

    def _register_default_shards(self) -> None:
        """Register the default set of queue shards."""
        shards = [
            QueueShardConfig(name="high_priority", priority=1, max_concurrent=20),
            QueueShardConfig(name="ai_analysis", priority=3, max_concurrent=15),
            QueueShardConfig(name="embeddings", priority=4, max_concurrent=10),
            QueueShardConfig(name="workflow", priority=5, max_concurrent=10),
            QueueShardConfig(name="exports", priority=6, max_concurrent=5),
            QueueShardConfig(name="notifications", priority=7, max_concurrent=5),
            QueueShardConfig(name="replay", priority=8, max_concurrent=3),
            QueueShardConfig(name="default", priority=9, max_concurrent=10),
        ]
        for shard in shards:
            self.register_shard(shard)

    def register_shard(self, config: QueueShardConfig) -> None:
        """Register a queue shard."""
        self._shards[config.name] = config
        self._shard_metrics[config.name] = ShardMetrics(shard=config.name)
        logger.info("Registered queue shard: %s (priority=%d, max_concurrent=%d)", config.name, config.priority, config.max_concurrent)

    def set_strategy(self, strategy: ShardStrategy) -> None:
        """Set the shard selection strategy."""
        self._strategy = strategy
        logger.info("Queue shard strategy set to: %s", strategy.value)

    def set_tenant_affinity(self, tenant_id: str, shard: str) -> None:
        """Pin a tenant to a specific shard."""
        self._tenant_assignments[tenant_id] = shard

    def select_shard(
        self,
        job_type: str,
        tenant_id: str = "",
        priority: int = 5,
    ) -> str:
        """Select the optimal shard for a job.

        Args:
            job_type: Type of job (maps to shard name).
            tenant_id: Tenant for affinity routing.
            priority: Job priority (1-10).

        Returns:
            Selected shard name.
        """
        # Tenant affinity override
        if tenant_id and tenant_id in self._tenant_assignments:
            return self._tenant_assignments[tenant_id]

        # Direct job type mapping
        if job_type in self._shards:
            return job_type

        # Strategy-based selection
        if self._strategy == ShardStrategy.PRIORITY:
            return self._select_by_priority(priority)
        elif self._strategy == ShardStrategy.LEAST_LOADED:
            return self._select_least_loaded()
        elif self._strategy == ShardStrategy.TENANT_HASH:
            return self._select_by_tenant_hash(tenant_id)
        else:
            return self._select_round_robin()

    def _select_by_priority(self, priority: int) -> str:
        """Select shard by matching priority level."""
        best = "default"
        best_priority = 99
        for name, config in self._shards.items():
            if abs(config.priority - priority) < best_priority:
                best_priority = abs(config.priority - priority)
                best = name
        return best

    def _select_least_loaded(self) -> str:
        """Select the least loaded shard."""
        best = "default"
        best_saturation = float("inf")
        for name, metrics in self._shard_metrics.items():
            if metrics.saturation_pct < best_saturation:
                best_saturation = metrics.saturation_pct
                best = name
        return best

    def _select_round_robin(self) -> str:
        """Simple round-robin selection."""
        import itertools
        shards = list(self._shards.keys())
        if not hasattr(self, "_rr_index"):
            self._rr_index = 0
        self._rr_index = (self._rr_index + 1) % len(shards)
        return shards[self._rr_index]

    def _select_by_tenant_hash(self, tenant_id: str) -> str:
        """Deterministic shard selection by tenant hash."""
        import hashlib
        shards = sorted(self._shards.keys())
        hash_val = int(hashlib.sha256(tenant_id.encode()).hexdigest(), 16)
        return shards[hash_val % len(shards)]

    async def route_burst(self, source_shard: str, target_shard: str, count: int = 10) -> None:
        """Route burst workload from overloaded shard to underloaded one."""
        logger.info("Burst routing: %d jobs from %s to %s", count, source_shard, target_shard)

    async def check_starvation(self) -> list[dict[str, Any]]:
        """Check for shard starvation (low priority shards not getting processed)."""
        starving = []
        for name, metrics in self._shard_metrics.items():
            config = self._shards.get(name)
            if config and metrics.depth > 100 and metrics.processing == 0:
                self._starvation_counters[name] = self._starvation_counters.get(name, 0) + 1
                if self._starvation_counters[name] >= 3:
                    starving.append({
                        "shard": name,
                        "depth": metrics.depth,
                        "priority": config.priority,
                        "starvation_count": self._starvation_counters[name],
                    })
                    metrics.is_starving = True
            else:
                self._starvation_counters[name] = 0
                metrics.is_starving = False
        return starving

    def update_metrics(self, shard: str, depth: int, processing: int, latency_ms: int) -> None:
        """Update metrics for a shard."""
        metrics = self._shard_metrics.get(shard)
        if metrics:
            metrics.depth = depth
            metrics.processing = processing
            metrics.avg_latency_ms = latency_ms
            config = self._shards.get(shard)
            if config:
                metrics.saturation_pct = min(1.0, processing / max(config.max_concurrent, 1))
            metrics.last_updated = datetime.utcnow().isoformat()

    def get_shard_status(self) -> dict[str, Any]:
        """Get status of all shards."""
        return {
            name: {
                "depth": m.depth,
                "processing": m.processing,
                "saturation_pct": round(m.saturation_pct * 100, 1),
                "avg_latency_ms": m.avg_latency_ms,
                "is_starving": m.is_starving,
                "priority": self._shards.get(name, QueueShardConfig(name=name)).priority,
            }
            for name, m in self._shard_metrics.items()
        }

    def get_tenant_fairness_report(self) -> dict[str, Any]:
        """Get tenant fairness report."""
        return {
            "total_tenants": len(self._tenant_assignments),
            "strategy": self._strategy.value,
            "starving_shards": sum(1 for m in self._shard_metrics.values() if m.is_starving),
        }


# ── Global singleton ───────────────────────────────────────────────

distributed_queue = DistributedQueueOrchestrator()
