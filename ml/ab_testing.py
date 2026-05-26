"""A/B testing infrastructure with shadow mode for model comparison.

Provides A/B testing infrastructure for comparing model versions
in production, including shadow mode deployment, traffic splitting,
and metrics comparison.
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ABTestConfig:
    """Configuration for an A/B test."""

    experiment_name: str
    control_model_id: str
    treatment_model_id: str
    traffic_percentage: float = 10.0  # % of traffic to treatment
    min_sample_size: int = 500
    duration_hours: int = 168  # 7 days
    metrics: List[str] = field(
        default_factory=lambda: [
            "accuracy", "latency_ms", "severity_mae"
        ]
    )
    shadow_mode: bool = True  # Start in shadow mode


@dataclass
class ABTestResult:
    """Result of an A/B test comparison."""

    experiment_name: str
    control_metrics: Dict[str, float]
    treatment_metrics: Dict[str, float]
    improvements: Dict[str, float]
    is_significant: bool
    sample_size: int
    duration_hours: float
    recommendation: str


class ShadowDeployment:
    """Shadow mode deployment for safe model testing.

    Runs a new model version in shadow mode, processing requests
    alongside the production model but not serving results to users.
    This allows safe performance comparison without risk.
    """

    def __init__(
        self,
        production_model_fn: Callable,
        shadow_model_fn: Callable,
        experiment_name: str,
    ) -> None:
        """Initialize shadow deployment.

        Args:
            production_model_fn: Production model inference function.
            shadow_model_fn: Shadow (candidate) model inference function.
            experiment_name: Name for this experiment.
        """
        self._production_fn = production_model_fn
        self._shadow_fn = shadow_model_fn
        self._experiment_name = experiment_name
        self._results: list[Dict[str, Any]] = []

    async def run_shadow(
        self, input_data: Any
    ) -> Tuple[Any, Optional[Any]]:
        """Run both models and compare results.

        Args:
            input_data: Input to pass to both models.

        Returns:
            Tuple of (production_result, shadow_result).
        """
        # Run production model
        prod_start = time.monotonic()
        try:
            prod_result = await self._production_fn(input_data)
            prod_latency = (time.monotonic() - prod_start) * 1000
        except Exception as exc:
            logger.error("Production model failed: %s", exc)
            prod_result = None
            prod_latency = 0

        # Run shadow model
        shadow_start = time.monotonic()
        try:
            shadow_result = await self._shadow_fn(input_data)
            shadow_latency = (time.monotonic() - shadow_start) * 1000
        except Exception as exc:
            logger.warning("Shadow model failed: %s", exc)
            shadow_result = None
            shadow_latency = 0

        # Record comparison
        self._results.append({
            "timestamp": datetime.utcnow().isoformat(),
            "prod_latency_ms": prod_latency,
            "shadow_latency_ms": shadow_latency,
            "prod_success": prod_result is not None,
            "shadow_success": shadow_result is not None,
        })

        return prod_result, shadow_result

    def get_shadow_results(self) -> Dict[str, Any]:
        """Get aggregated shadow deployment results.

        Returns:
            Dict with comparison statistics.
        """
        if not self._results:
            return {"status": "no_results"}

        prod_latencies = [
            r["prod_latency_ms"] for r in self._results
            if r["prod_latency_ms"] > 0
        ]
        shadow_latencies = [
            r["shadow_latency_ms"] for r in self._results
            if r["shadow_latency_ms"] > 0
        ]

        prod_success = sum(1 for r in self._results if r["prod_success"])
        shadow_success = sum(1 for r in self._results if r["shadow_success"])
        total = len(self._results)

        return {
            "experiment": self._experiment_name,
            "total_requests": total,
            "production": {
                "success_rate": prod_success / total if total > 0 else 0,
                "avg_latency_ms": (
                    sum(prod_latencies) / len(prod_latencies)
                    if prod_latencies else 0
                ),
            },
            "shadow": {
                "success_rate": shadow_success / total if total > 0 else 0,
                "avg_latency_ms": (
                    sum(shadow_latencies) / len(shadow_latencies)
                    if shadow_latencies else 0
                ),
            },
        }


class ABTestingOrchestrator:
    """Orchestrates A/B tests between model versions.

    Manages the full lifecycle of A/B tests including configuration,
    traffic splitting, metrics collection, statistical analysis,
    and promotion decisions.

    Usage:
        orchestrator = ABTestingOrchestrator()
        config = ABTestConfig(
            experiment_name="lora-v1-vs-v2",
            control_model_id="lora-v1",
            treatment_model_id="lora-v2",
        )
        orchestrator.start_experiment(config)
        result = await orchestrator.evaluate()
    """

    def __init__(self) -> None:
        """Initialize the A/B testing orchestrator."""
        self._experiments: Dict[str, ABTestConfig] = {}
        self._results: Dict[str, List[Dict[str, Any]]] = {}
        self._shadow_deployments: Dict[str, ShadowDeployment] = {}

    def start_experiment(self, config: ABTestConfig) -> str:
        """Start a new A/B test experiment.

        Args:
            config: A/B test configuration.

        Returns:
            Experiment name.
        """
        self._experiments[config.experiment_name] = config
        self._results[config.experiment_name] = []
        logger.info(
            "Started A/B test '%s': %s vs %s (traffic=%d%%, shadow=%s)",
            config.experiment_name,
            config.control_model_id,
            config.treatment_model_id,
            config.traffic_percentage,
            config.shadow_mode,
        )
        return config.experiment_name

    def should_use_treatment(self, experiment_name: str) -> bool:
        """Determine if this request should use the treatment model.

        Args:
            experiment_name: The experiment name.

        Returns:
            True if this request should use treatment.
        """
        config = self._experiments.get(experiment_name)
        if config is None or config.shadow_mode:
            return False
        return random.random() * 100 < config.traffic_percentage

    def record_result(
        self,
        experiment_name: str,
        model_id: str,
        metrics: Dict[str, float],
    ) -> None:
        """Record a single A/B test result.

        Args:
            experiment_name: The experiment name.
            model_id: Which model was used.
            metrics: Performance metrics for this request.
        """
        if experiment_name not in self._results:
            self._results[experiment_name] = []

        self._results[experiment_name].append({
            "model_id": model_id,
            "timestamp": datetime.utcnow().isoformat(),
            **metrics,
        })

    async def evaluate(
        self, experiment_name: str
    ) -> Optional[ABTestResult]:
        """Evaluate the results of an A/B test.

        Args:
            experiment_name: The experiment to evaluate.

        Returns:
            ABTestResult with comparison and recommendation.
        """
        config = self._experiments.get(experiment_name)
        if config is None:
            logger.error("Experiment '%s' not found", experiment_name)
            return None

        results = self._results.get(experiment_name, [])
        if len(results) < config.min_sample_size:
            logger.info(
                "Experiment '%s': insufficient samples (%d/%d)",
                experiment_name,
                len(results),
                config.min_sample_size,
            )
            return None

        # Separate control and treatment results
        control_results = [
            r for r in results if r["model_id"] == config.control_model_id
        ]
        treatment_results = [
            r for r in results if r["model_id"] == config.treatment_model_id
        ]

        if not control_results or not treatment_results:
            logger.warning(
                "Experiment '%s': missing results for one arm", experiment_name
            )
            return None

        # Compute aggregated metrics
        control_metrics = self._aggregate_metrics(control_results, config.metrics)
        treatment_metrics = self._aggregate_metrics(treatment_results, config.metrics)

        # Compute improvements
        improvements = {}
        for metric in config.metrics:
            if metric in control_metrics and metric in treatment_metrics:
                if control_metrics[metric] != 0:
                    improvements[metric] = round(
                        ((treatment_metrics[metric] - control_metrics[metric])
                         / abs(control_metrics[metric])) * 100,
                        2,
                    )
                else:
                    improvements[metric] = 0.0

        # Determine significance and recommendation
        is_significant = self._check_statistical_significance(
            control_results, treatment_results, config.metrics
        )

        recommendation = self._generate_recommendation(
            improvements, is_significant, config
        )

        return ABTestResult(
            experiment_name=experiment_name,
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
            improvements=improvements,
            is_significant=is_significant,
            sample_size=len(results),
            duration_hours=self._get_experiment_duration(experiment_name),
            recommendation=recommendation,
        )

    def _aggregate_metrics(
        self,
        results: List[Dict[str, Any]],
        metrics: List[str],
    ) -> Dict[str, float]:
        """Aggregate metrics across results.

        Args:
            results: List of individual results.
            metrics: Metric names to aggregate.

        Returns:
            Dict of metric name to average value.
        """
        aggregated: Dict[str, float] = {}
        for metric in metrics:
            values = [
                r.get(metric, 0) for r in results
                if metric in r
            ]
            if values:
                aggregated[metric] = sum(values) / len(values)
            else:
                aggregated[metric] = 0.0
        return aggregated

    def _check_statistical_significance(
        self,
        control: List[Dict[str, Any]],
        treatment: List[Dict[str, Any]],
        metrics: List[str],
    ) -> bool:
        """Check if results are statistically significant.

        Uses a simple threshold-based approach. In production,
        this would use proper statistical tests (t-test, Mann-Whitney).

        Args:
            control: Control group results.
            treatment: Treatment group results.
            metrics: Metrics to check.

        Returns:
            True if results appear significant.
        """
        # Simplified significance check based on sample size
        # In production, use scipy.stats for proper tests
        min_samples = min(len(control), len(treatment))
        return min_samples >= 100

    def _generate_recommendation(
        self,
        improvements: Dict[str, float],
        is_significant: bool,
        config: ABTestConfig,
    ) -> str:
        """Generate a recommendation based on A/B test results.

        Args:
            improvements: Metric improvements.
            is_significant: Whether results are significant.
            config: Experiment configuration.

        Returns:
            Recommendation string.
        """
        if not is_significant:
            return (
                f"Insufficient data for definitive recommendation. "
                f"Continue collecting samples (target: {config.min_sample_size})."
            )

        # Check if treatment is better across key metrics
        positive_improvements = sum(
            1 for v in improvements.values() if v > 0
        )
        total_metrics = len(improvements)

        if positive_improvements >= total_metrics * 0.7:
            return (
                f"Treatment model '{config.treatment_model_id}' shows "
                f"consistent improvement. Consider promoting to production."
            )
        elif positive_improvements <= total_metrics * 0.3:
            return (
                f"Treatment model '{config.treatment_model_id}' underperforms "
                f"control. Consider discontinuing experiment."
            )
        else:
            return (
                f"Mixed results. Continue A/B test for more data or "
                f"investigate specific metrics for targeted improvements."
            )

    def _get_experiment_duration(self, experiment_name: str) -> float:
        """Get the duration of an experiment in hours.

        Args:
            experiment_name: The experiment name.

        Returns:
            Duration in hours.
        """
        config = self._experiments.get(experiment_name)
        if config is None:
            return 0.0
        # Approximate from config
        return float(config.duration_hours)

    def get_active_experiments(self) -> List[str]:
        """Get list of active experiment names.

        Returns:
            List of active experiment names.
        """
        return list(self._experiments.keys())

    def stop_experiment(self, experiment_name: str) -> None:
        """Stop an active experiment.

        Args:
            experiment_name: The experiment to stop.
        """
        self._experiments.pop(experiment_name, None)
        self._results.pop(experiment_name, None)
        logger.info("Stopped experiment '%s'", experiment_name)
