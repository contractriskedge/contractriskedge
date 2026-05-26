"""Model routing optimization engine (V2-029).

Routes LLM requests to the optimal model based on cost vs. accuracy
tradeoff rules. Supports configurable routing policies per tenant,
request type, and complexity level.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    """Complexity levels for LLM tasks."""

    SIMPLE = "simple"          # Basic classification, simple extraction
    MEDIUM = "medium"          # Clause analysis, standard risk scoring
    COMPLEX = "complex"        # Multi-step reasoning, redline generation
    CRITICAL = "critical"      # Legal reasoning, high-stakes analysis


class RoutingStrategy(str, Enum):
    """Strategies for model routing."""

    COST_OPTIMIZED = "cost_optimized"     # Always pick cheapest adequate model
    ACCURACY_OPTIMIZED = "accuracy_optimized"  # Always pick most capable model
    BALANCED = "balanced"                 # Balance cost and accuracy
    TENANT_CONFIG = "tenant_config"       # Use tenant-specific configuration


@dataclass
class ModelOption:
    """An available model with its capabilities and costs."""

    provider: str
    model_name: str
    display_name: str
    cost_per_input_token: float  # USD per token
    cost_per_output_token: float
    capabilities: List[str]  # e.g., ["reasoning", "code", "json_mode", "vision"]
    max_tokens: int
    latency_p50_ms: float
    quality_score: float  # 0-10, relative quality ranking
    is_fallback: bool = False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        return (input_tokens * self.cost_per_input_token) + \
               (output_tokens * self.cost_per_output_token)


class ModelRouter:
    """Routes LLM requests to optimal models.

    Uses configurable rules to select the best model for each request
    based on task type, complexity, cost constraints, and quality needs.

    Usage:
        router = ModelRouter()
        model = router.select_model(task_type="risk_analysis", complexity="complex")
    """

    def __init__(self) -> None:
        """Initialize the model router with default model catalog."""
        self._models: List[ModelOption] = self._default_catalog()
        self._tenant_overrides: Dict[str, Dict[str, Any]] = {}
        self._strategy: RoutingStrategy = RoutingStrategy.BALANCED
        self._routing_rules: List[Dict[str, Any]] = self._default_rules()

    def _default_catalog(self) -> List[ModelOption]:
        """Create the default model catalog.

        Returns:
            List of available model options.
        """
        return [
            ModelOption(
                provider="openai",
                model_name="gpt-4o",
                display_name="GPT-4o",
                cost_per_input_token=2.5e-6,
                cost_per_output_token=10.0e-6,
                capabilities=["reasoning", "code", "json_mode", "vision", "function_calling"],
                max_tokens=16384,
                latency_p50_ms=2000,
                quality_score=9.5,
            ),
            ModelOption(
                provider="openai",
                model_name="gpt-4o-mini",
                display_name="GPT-4o Mini",
                cost_per_input_token=0.15e-6,
                cost_per_output_token=0.6e-6,
                capabilities=["reasoning", "json_mode", "function_calling"],
                max_tokens=16384,
                latency_p50_ms=800,
                quality_score=7.5,
            ),
            ModelOption(
                provider="anthropic",
                model_name="claude-3-5-sonnet-20241022",
                display_name="Claude 3.5 Sonnet",
                cost_per_input_token=3.0e-6,
                cost_per_output_token=15.0e-6,
                capabilities=["reasoning", "code", "json_mode", "vision", "function_calling"],
                max_tokens=8192,
                latency_p50_ms=2500,
                quality_score=9.8,
            ),
            ModelOption(
                provider="deepseek",
                model_name="deepseek-chat",
                display_name="DeepSeek Chat",
                cost_per_input_token=0.27e-6,
                cost_per_output_token=1.10e-6,
                capabilities=["reasoning", "code", "json_mode"],
                max_tokens=8192,
                latency_p50_ms=1500,
                quality_score=8.5,
            ),
        ]

    def _default_rules(self) -> List[Dict[str, Any]]:
        """Create default routing rules.

        Returns:
            List of routing rule dicts.
        """
        return [
            # Critical tasks -> most capable model
            {
                "task_type": "*",
                "complexity": "critical",
                "strategy": "accuracy_optimized",
                "preferred_model": "claude-3-5-sonnet-20241022",
                "fallback_model": "gpt-4o",
            },
            # Complex tasks -> high quality
            {
                "task_type": "*",
                "complexity": "complex",
                "strategy": "balanced",
                "preferred_model": "gpt-4o",
                "fallback_model": "claude-3-5-sonnet-20241022",
            },
            # Medium tasks -> balanced
            {
                "task_type": "*",
                "complexity": "medium",
                "strategy": "balanced",
                "preferred_model": "deepseek-chat",
                "fallback_model": "gpt-4o-mini",
            },
            # Simple tasks -> cheapest capable
            {
                "task_type": "*",
                "complexity": "simple",
                "strategy": "cost_optimized",
                "preferred_model": "gpt-4o-mini",
                "fallback_model": "deepseek-chat",
            },
            # Embedding tasks
            {
                "task_type": "embedding",
                "complexity": "simple",
                "strategy": "cost_optimized",
                "preferred_model": "text-embedding-3-large",
                "fallback_model": None,
            },
        ]

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Set the global routing strategy.

        Args:
            strategy: The routing strategy to use.
        """
        self._strategy = strategy
        logger.info("Model router strategy set to %s", strategy.value)

    def set_tenant_config(
        self,
        tenant_id: str,
        strategy: Optional[RoutingStrategy] = None,
        preferred_models: Optional[List[str]] = None,
        max_cost_per_request: Optional[float] = None,
    ) -> None:
        """Set tenant-specific routing configuration.

        Args:
            tenant_id: The tenant identifier.
            strategy: Optional routing strategy override.
            preferred_models: Optional list of preferred model names.
            max_cost_per_request: Optional max cost per request.
        """
        config: Dict[str, Any] = {}
        if strategy:
            config["strategy"] = strategy
        if preferred_models:
            config["preferred_models"] = preferred_models
        if max_cost_per_request is not None:
            config["max_cost_per_request"] = max_cost_per_request

        self._tenant_overrides[tenant_id] = config
        logger.info("Set routing config for tenant %s: %s", tenant_id, config)

    def select_model(
        self,
        task_type: str,
        complexity: TaskComplexity,
        tenant_id: Optional[str] = None,
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 500,
        required_capabilities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Select the optimal model for a request.

        Args:
            task_type: Type of task (e.g., "risk_analysis", "redline", "embedding").
            complexity: Task complexity level.
            tenant_id: Optional tenant for tenant-specific routing.
            estimated_input_tokens: Estimated input token count.
            estimated_output_tokens: Estimated output token count.
            required_capabilities: Required model capabilities.

        Returns:
            Dict with selected model and routing info.
        """
        # Get tenant config if available
        tenant_config = self._tenant_overrides.get(tenant_id, {}) if tenant_id else {}
        strategy = tenant_config.get("strategy", self._strategy)
        preferred_models = tenant_config.get("preferred_models")
        max_cost = tenant_config.get("max_cost_per_request")

        # Find matching rule
        rule = self._find_matching_rule(task_type, complexity)

        # Determine candidate models
        candidates = self._get_candidates(rule, strategy, preferred_models)

        # Filter by required capabilities
        if required_capabilities:
            candidates = [
                m for m in candidates
                if all(cap in m.capabilities for cap in required_capabilities)
            ]

        if not candidates:
            logger.warning("No suitable model found for task_type=%s, complexity=%s",
                           task_type, complexity)
            # Return cheapest as absolute fallback
            fallback = min(self._models, key=lambda m: m.cost_per_input_token)
            return {
                "selected_model": fallback.model_name,
                "provider": fallback.provider,
                "strategy": "fallback",
                "estimated_cost": fallback.estimate_cost(estimated_input_tokens, estimated_output_tokens),
                "quality_score": fallback.quality_score,
                "reason": "No matching model - using cheapest fallback",
            }

        # Apply strategy-based selection
        if strategy == RoutingStrategy.COST_OPTIMIZED:
            selected = min(candidates, key=lambda m: m.estimate_cost(
                estimated_input_tokens, estimated_output_tokens))
            reason = "cost_optimized"
        elif strategy == RoutingStrategy.ACCURACY_OPTIMIZED:
            selected = max(candidates, key=lambda m: m.quality_score)
            reason = "accuracy_optimized"
        else:  # BALANCED or TENANT_CONFIG
            # Score: 70% quality, 30% cost efficiency
            best_quality = max(m.quality_score for m in candidates)
            best_cost = min(m.estimate_cost(estimated_input_tokens, estimated_output_tokens)
                           for m in candidates)

            def score(m: ModelOption) -> float:
                quality_norm = m.quality_score / best_quality if best_quality > 0 else 0
                cost = m.estimate_cost(estimated_input_tokens, estimated_output_tokens)
                cost_norm = best_cost / cost if cost > 0 else 0
                return 0.7 * quality_norm + 0.3 * cost_norm

            selected = max(candidates, key=score)
            reason = "balanced_scoring"

        # Check cost constraint
        estimated_cost = selected.estimate_cost(estimated_input_tokens, estimated_output_tokens)
        if max_cost and estimated_cost > max_cost:
            # Try to find a cheaper model
            cheaper = [m for m in candidates if m.estimate_cost(
                estimated_input_tokens, estimated_output_tokens) <= max_cost]
            if cheaper:
                selected = max(cheaper, key=lambda m: m.quality_score)
                reason = "cost_constraint_applied"

        return {
            "selected_model": selected.model_name,
            "provider": selected.provider,
            "display_name": selected.display_name,
            "strategy": strategy.value if isinstance(strategy, RoutingStrategy) else str(strategy),
            "estimated_cost": round(estimated_cost, 8),
            "estimated_input_cost": round(estimated_input_tokens * selected.cost_per_input_token, 8),
            "estimated_output_cost": round(estimated_output_tokens * selected.cost_per_output_token, 8),
            "quality_score": selected.quality_score,
            "reason": reason,
            "is_fallback": selected.is_fallback,
        }

    def _find_matching_rule(
        self,
        task_type: str,
        complexity: TaskComplexity,
    ) -> Dict[str, Any]:
        """Find the first matching routing rule.

        Args:
            task_type: Task type identifier.
            complexity: Task complexity.

        Returns:
            Matching rule dict.
        """
        complexity_val = complexity.value if isinstance(complexity, TaskComplexity) else complexity

        for rule in self._routing_rules:
            task_match = rule["task_type"] == "*" or rule["task_type"] == task_type
            complexity_match = rule["complexity"] == complexity_val
            if task_match and complexity_match:
                return rule

        # Default rule
        return {
            "task_type": "*",
            "complexity": "medium",
            "strategy": "balanced",
            "preferred_model": "deepseek-chat",
            "fallback_model": "gpt-4o-mini",
        }

    def _get_candidates(
        self,
        rule: Dict[str, Any],
        strategy: RoutingStrategy,
        preferred_models: Optional[List[str]] = None,
    ) -> List[ModelOption]:
        """Get candidate models for a rule.

        Args:
            rule: The matching routing rule.
            strategy: The routing strategy.
            preferred_models: Optional preferred model list.

        Returns:
            List of candidate ModelOptions.
        """
        model_names = []

        if preferred_models:
            model_names = preferred_models
        else:
            preferred = rule.get("preferred_model")
            fallback = rule.get("fallback_model")
            if preferred:
                model_names.append(preferred)
            if fallback:
                model_names.append(fallback)

        # Add all models for certain strategies
        if strategy in (RoutingStrategy.ACCURACY_OPTIMIZED, RoutingStrategy.BALANCED):
            all_names = [m.model_name for m in self._models]
            model_names = list(dict.fromkeys(model_names + all_names))  # Deduplicate preserving order

        return [m for m in self._models if m.model_name in model_names]

    def get_model_catalog(self) -> List[Dict[str, Any]]:
        """Get the full model catalog with capabilities.

        Returns:
            List of model info dicts.
        """
        return [
            {
                "provider": m.provider,
                "model_name": m.model_name,
                "display_name": m.display_name,
                "cost_per_input_token": m.cost_per_input_token,
                "cost_per_output_token": m.cost_per_output_token,
                "capabilities": m.capabilities,
                "max_tokens": m.max_tokens,
                "latency_p50_ms": m.latency_p50_ms,
                "quality_score": m.quality_score,
            }
            for m in self._models
        ]

    def get_routing_rules(self) -> List[Dict[str, Any]]:
        """Get the current routing rules.

        Returns:
            List of routing rule dicts.
        """
        return self._routing_rules

    def add_routing_rule(self, rule: Dict[str, Any]) -> None:
        """Add a custom routing rule.

        Args:
            rule: Rule dict with task_type, complexity, strategy,
                  preferred_model, fallback_model.
        """
        self._routing_rules.append(rule)
        logger.info("Added routing rule: %s", rule)
