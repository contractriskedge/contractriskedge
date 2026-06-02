"""Adaptive Runtime Optimization — dynamic chunk sizing, provider routing, prompt compression, cost-aware planning.

This becomes economically huge — optimizing every execution for cost and quality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OptimizationMode(str, Enum):
    QUALITY = "quality"           # Maximize output quality (premium models, full context)
    BALANCED = "balanced"         # Balance quality and cost (default)
    ECONOMY = "economy"           # Minimize cost (cheap models, compressed prompts)
    URGENT = "urgent"             # Minimize latency (fast models, minimal context)


@dataclass
class OptimizationContext:
    """Context for making optimization decisions."""
    tenant_id: str
    operation_type: str
    mode: OptimizationMode = OptimizationMode.BALANCED
    max_cost_usd: float = 0.0
    max_latency_ms: int = 30000
    required_quality: float = 0.7  # Minimum acceptable quality score
    budget_remaining_pct: float = 1.0


@dataclass
class OptimizationDecision:
    """Decision from the runtime optimizer."""
    selected_model: str
    selected_provider: str
    max_tokens: int
    temperature: float
    chunk_count: int
    compression_ratio: float = 1.0
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 0
    estimated_quality: float = 1.0
    reasoning: str = ""


@dataclass
class RuntimeOptimizer:
    """Adaptive runtime optimizer for cost-quality-latency tradeoffs.

    Optimizes:
    - Model selection (cheaper for simple tasks, premium for complex)
    - Chunk sizing (more chunks for detailed analysis, fewer for quick scan)
    - Prompt compression (remove redundant context)
    - Token budget (reduce for economy mode)
    - Provider routing (cheaper providers for non-critical)
    - Retrieval depth (fewer chunks for quick queries)
    """

    _execution_history: list[dict[str, Any]] = field(default_factory=list)
    _model_performance: dict[str, dict[str, float]] = field(default_factory=dict)

    MODEL_CAPABILITIES: dict[str, dict[str, float]] = field(default_factory=lambda: {
        "gpt-4o": {"quality": 0.95, "cost_per_token": 0.00001, "speed": 0.8},
        "gpt-4o-mini": {"quality": 0.75, "cost_per_token": 0.0000006, "speed": 0.95},
        "gpt-4-turbo": {"quality": 0.98, "cost_per_token": 0.00003, "speed": 0.6},
        "claude-3-opus": {"quality": 0.97, "cost_per_token": 0.000075, "speed": 0.5},
        "claude-3-sonnet": {"quality": 0.90, "cost_per_token": 0.000015, "speed": 0.7},
        "claude-3-haiku": {"quality": 0.70, "cost_per_token": 0.00000125, "speed": 0.95},
    })

    def optimize(self, context: OptimizationContext) -> OptimizationDecision:
        """Optimize execution parameters for the given context."""
        if context.mode == OptimizationMode.QUALITY:
            return self._optimize_for_quality(context)
        elif context.mode == OptimizationMode.ECONOMY:
            return self._optimize_for_economy(context)
        elif context.mode == OptimizationMode.URGENT:
            return self._optimize_for_speed(context)
        else:
            return self._optimize_balanced(context)

    def _optimize_for_quality(self, context: OptimizationContext) -> OptimizationDecision:
        """Maximize output quality."""
        model = "gpt-4-turbo"
        provider = "openai"
        caps = self.MODEL_CAPABILITIES.get(model, {})
        return OptimizationDecision(
            selected_model=model,
            selected_provider=provider,
            max_tokens=8192,
            temperature=0.2,
            chunk_count=20,
            compression_ratio=1.0,
            estimated_cost=0.05,
            estimated_latency_ms=15000,
            estimated_quality=caps.get("quality", 0.95),
            reasoning="Quality mode: using premium model with full context",
        )

    def _optimize_for_economy(self, context: OptimizationContext) -> OptimizationDecision:
        """Minimize cost."""
        model = "gpt-4o-mini"
        provider = "openai"
        caps = self.MODEL_CAPABILITIES.get(model, {})
        return OptimizationDecision(
            selected_model=model,
            selected_provider=provider,
            max_tokens=2048,
            temperature=0.1,
            chunk_count=5,
            compression_ratio=0.5,
            estimated_cost=0.001,
            estimated_latency_ms=2000,
            estimated_quality=caps.get("quality", 0.75),
            reasoning="Economy mode: using cheapest model with compressed context",
        )

    def _optimize_for_speed(self, context: OptimizationContext) -> OptimizationDecision:
        """Minimize latency."""
        model = "gpt-4o-mini"
        provider = "openai"
        return OptimizationDecision(
            selected_model=model,
            selected_provider=provider,
            max_tokens=1024,
            temperature=0.1,
            chunk_count=3,
            compression_ratio=0.3,
            estimated_cost=0.0005,
            estimated_latency_ms=500,
            estimated_quality=0.65,
            reasoning="Urgent mode: using fast model with minimal context",
        )

    def _optimize_balanced(self, context: OptimizationContext) -> OptimizationDecision:
        """Balance quality, cost, and latency."""
        model = "gpt-4o"
        provider = "openai"
        caps = self.MODEL_CAPABILITIES.get(model, {})
        return OptimizationDecision(
            selected_model=model,
            selected_provider=provider,
            max_tokens=4096,
            temperature=0.1,
            chunk_count=10,
            compression_ratio=0.8,
            estimated_cost=0.01,
            estimated_latency_ms=5000,
            estimated_quality=caps.get("quality", 0.95),
            reasoning="Balanced mode: standard model with moderate context",
        )

    def select_model_for_task(
        self,
        task_type: str,
        required_quality: float = 0.7,
        max_cost: float = 0.05,
    ) -> tuple[str, str]:
        """Select the best model for a task type within constraints."""
        candidates = [
            (name, caps) for name, caps in self.MODEL_CAPABILITIES.items()
            if caps["quality"] >= required_quality and caps["cost_per_token"] * 4000 <= max_cost
        ]
        if not candidates:
            # Fall back to cheapest that meets quality
            candidates = [
                (name, caps) for name, caps in self.MODEL_CAPABILITIES.items()
                if caps["quality"] >= required_quality
            ]
        if not candidates:
            return "gpt-4o-mini", "openai"

        # Sort by cost (cheapest first)
        candidates.sort(key=lambda x: x[1]["cost_per_token"])
        return candidates[0][0], "openai"

    def estimate_chunk_count(self, doc_length: int, mode: OptimizationMode) -> int:
        """Estimate optimal chunk count based on document length and mode."""
        base = max(1, doc_length // 1000)
        multipliers = {
            OptimizationMode.QUALITY: 2.0,
            OptimizationMode.BALANCED: 1.0,
            OptimizationMode.ECONOMY: 0.5,
            OptimizationMode.URGENT: 0.3,
        }
        return max(1, int(base * multipliers.get(mode, 1.0)))

    def record_execution(self, model: str, cost: float, latency_ms: int, quality: float) -> None:
        """Record execution metrics for continuous optimization."""
        if model not in self._model_performance:
            self._model_performance[model] = {"avg_cost": 0, "avg_latency": 0, "avg_quality": 0, "count": 0}
        perf = self._model_performance[model]
        n = perf["count"]
        perf["avg_cost"] = (perf["avg_cost"] * n + cost) / (n + 1)
        perf["avg_latency"] = (perf["avg_latency"] * n + latency_ms) / (n + 1)
        perf["avg_quality"] = (perf["avg_quality"] * n + quality) / (n + 1)
        perf["count"] = n + 1

        self._execution_history.append({
            "model": model,
            "cost": cost,
            "latency_ms": latency_ms,
            "quality": quality,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_optimization_report(self) -> dict[str, Any]:
        """Get optimization performance report."""
        return {
            "total_executions": len(self._execution_history),
            "model_performance": self._model_performance,
            "avg_cost": sum(e["cost"] for e in self._execution_history[-100:]) / min(100, max(1, len(self._execution_history))),
            "avg_latency": sum(e["latency_ms"] for e in self._execution_history[-100:]) / min(100, max(1, len(self._execution_history))),
        }


# ── Global singleton ───────────────────────────────────────────────

runtime_optimizer = RuntimeOptimizer()
