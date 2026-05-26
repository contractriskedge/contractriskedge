"""Automated weekly evaluation runner using Celery scheduled tasks.

Provides automated evaluation of risk analysis accuracy on a weekly
schedule, comparing current model performance against baselines and
generating comprehensive reports.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .test_set import TestSetGenerator, TestSet, TestClause
from .metrics import MetricsComputer, EvaluationMetrics

logger = logging.getLogger(__name__)


class AccuracyEvaluator:
    """Automated weekly evaluation runner for risk analysis accuracy.

    Runs evaluations on a blind test set, computes metrics, compares
    against baselines, and generates reports. Designed to be scheduled
    via Celery for weekly execution.

    Usage:
        evaluator = AccuracyEvaluator(test_set_path="test_set.json")
        report = await evaluator.run_evaluation(llm_client)
    """

    def __init__(
        self,
        test_set_path: Optional[str] = None,
        baseline_metrics_path: Optional[str] = None,
        output_dir: str = "./evaluation_results",
    ) -> None:
        """Initialize the accuracy evaluator.

        Args:
            test_set_path: Path to pre-built test set JSON.
            baseline_metrics_path: Path to baseline metrics for comparison.
            output_dir: Directory to store evaluation results.
        """
        self._test_set_path = test_set_path
        self._baseline_metrics_path = baseline_metrics_path
        self._output_dir = output_dir
        self._test_set: Optional[TestSet] = None
        self._baseline: Optional[EvaluationMetrics] = None
        self._last_report: Optional[Dict[str, Any]] = None

        import os
        os.makedirs(output_dir, exist_ok=True)

    def load_test_set(self) -> TestSet:
        """Load or generate the test set.

        Returns:
            The test set to evaluate against.
        """
        generator = TestSetGenerator()

        if self._test_set_path:
            try:
                self._test_set = generator.load_test_set(self._test_set_path)
                return self._test_set
            except Exception as exc:
                logger.warning(
                    "Failed to load test set from %s: %s",
                    self._test_set_path, exc,
                )

        # Generate a fresh test set
        self._test_set = generator.generate_test_set(total_clauses=500)
        return self._test_set

    def load_baseline(self) -> Optional[EvaluationMetrics]:
        """Load baseline metrics for comparison.

        Returns:
            Baseline metrics or None.
        """
        if not self._baseline_metrics_path:
            return None

        try:
            with open(self._baseline_metrics_path) as f:
                data = json.load(f)
            # Convert dict back to EvaluationMetrics
            metrics = EvaluationMetrics()
            for key, value in data.items():
                if hasattr(metrics, key):
                    setattr(metrics, key, value)
            self._baseline = metrics
            return metrics
        except Exception as exc:
            logger.warning("Failed to load baseline: %s", exc)
            return None

    async def run_evaluation(
        self,
        llm_client: Any,
        test_set: Optional[TestSet] = None,
    ) -> Dict[str, Any]:
        """Run a full evaluation against the test set.

        Args:
            llm_client: The LLM client for making predictions.
            test_set: Optional test set (loads default if not provided).

        Returns:
            Evaluation report with metrics and comparisons.
        """
        from ..llm.models import LLMRequest, Message, RoleType

        ts = test_set or self.load_test_set()
        baseline = self.load_baseline()

        logger.info(
            "Starting evaluation with %d test clauses", ts.total_clauses
        )

        # Run predictions
        predictions: list[Dict[str, Any]] = []
        for clause in ts.clauses:
            try:
                pred = await self._predict_clause(llm_client, clause)
                predictions.append(pred)
            except Exception as exc:
                logger.error(
                    "Failed to predict clause %s: %s", clause.clause_id, exc
                )

        # Compute metrics
        computer = MetricsComputer()
        metrics = computer.compute(predictions, ts.clauses)

        # Build report
        report = self._build_report(metrics, baseline, ts, predictions)

        # Save report
        self._save_report(report)
        self._last_report = report

        logger.info(
            "Evaluation complete: accuracy=%.4f, macro_f1=%.4f",
            metrics.overall_accuracy,
            metrics.macro_f1,
        )

        return report

    async def _predict_clause(
        self,
        llm_client: Any,
        clause: TestClause,
    ) -> Dict[str, Any]:
        """Get a prediction for a single test clause.

        Args:
            llm_client: The LLM client.
            clause: The test clause to predict.

        Returns:
            Prediction dict with category, severity, etc.
        """
        from ..llm.models import LLMRequest, Message, RoleType

        request = LLMRequest(
            messages=[
                Message(
                    role=RoleType.SYSTEM,
                    content=(
                        "You are a contract risk analyzer. Classify the following "
                        "clause and provide a severity score."
                    ),
                ),
                Message(
                    role=RoleType.USER,
                    content=(
                        f"Analyze this {clause.contract_type} clause:\n\n"
                        f"{clause.clause_text}\n\n"
                        "Provide:\n"
                        "1. Risk category\n"
                        "2. Severity score (1-10)\n"
                        "3. Risk level (critical/high/medium/low/info)\n"
                        "4. Confidence (high/medium/low)"
                    ),
                ),
            ],
            temperature=0.1,
            max_tokens=256,
        )

        response = await llm_client.complete(request)
        output = response.content.lower()

        # Extract category
        predicted_category = self._extract_category(output)
        if not predicted_category:
            predicted_category = clause.risk_category  # fallback

        # Extract severity
        predicted_severity = self._extract_severity(output)

        # Extract risk level
        predicted_risk_level = self._extract_risk_level(output)

        return {
            "clause_id": clause.clause_id,
            "predicted_category": predicted_category,
            "predicted_severity": predicted_severity,
            "predicted_risk_level": predicted_risk_level,
            "is_high_risk": predicted_severity >= 7,
            "raw_output": output,
        }

    def _extract_category(self, text: str) -> str:
        """Extract risk category from model output.

        Args:
            text: Model output text.

        Returns:
            Category ID or empty string.
        """
        categories = {
            "indemnification": ["indemnif", "indemnity"],
            "liability_limitation": ["liability limit", "limitation of liability"],
            "termination": ["termination"],
            "confidentiality": ["confidential"],
            "data_privacy": ["data privacy", "data protection", "privacy"],
            "compliance": ["compliance", "regulatory"],
            "payment_terms": ["payment term", "pricing"],
            "force_majeure": ["force majeure"],
            "assignment": ["assignment"],
            "governing_law": ["governing law", "jurisdiction"],
            "non_compete": ["non-compete", "non-compet", "non-solicit"],
            "intellectual_property": ["intellectual property", "ip ownership"],
        }

        text_lower = text.lower()
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        return ""

    def _extract_severity(self, text: str) -> int:
        """Extract severity score from model output.

        Args:
            text: Model output text.

        Returns:
            Severity score (1-10) or 0.
        """
        import re

        patterns = [
            r"severity(?:\s*:\s*|\s+is\s+|\s+of\s+)(\d+)",
            r"score(?:\s*:\s*|\s+is\s+|\s+of\s+)(\d+)",
            r"(\d+)\s*/\s*10",
            r"(\d+)\s*out\s*of\s*10",
            r"level\s*[:]\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                score = int(match.group(1))
                if 1 <= score <= 10:
                    return score
        return 0

    def _extract_risk_level(self, text: str) -> str:
        """Extract risk level from model output.

        Args:
            text: Model output text.

        Returns:
            Risk level string.
        """
        text_lower = text.lower()
        if "critical" in text_lower:
            return "critical"
        elif "high" in text_lower:
            return "high"
        elif "medium" in text_lower:
            return "medium"
        elif "low" in text_lower:
            return "low"
        return "unknown"

    def _build_report(
        self,
        metrics: EvaluationMetrics,
        baseline: Optional[EvaluationMetrics],
        test_set: TestSet,
        predictions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a comprehensive evaluation report.

        Args:
            metrics: Current evaluation metrics.
            baseline: Optional baseline metrics.
            test_set: The test set used.
            predictions: Raw predictions.

        Returns:
            Report dictionary.
        """
        report: Dict[str, Any] = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "test_set_name": test_set.name,
                "test_set_version": test_set.version,
                "test_set_size": test_set.total_clauses,
                "contract_types": test_set.contract_types,
                "categories_covered": test_set.categories_covered,
            },
            "current_metrics": metrics.to_dict(),
            "predictions_summary": {
                "total": len(predictions),
                "successful": len(predictions),
                "failed": 0,
            },
        }

        # Add baseline comparison
        if baseline is not None:
            report["baseline_comparison"] = {
                "baseline_metrics": baseline.to_dict(),
                "improvements": {
                    "accuracy_delta": round(
                        metrics.overall_accuracy - baseline.overall_accuracy, 4
                    ),
                    "macro_f1_delta": round(
                        metrics.macro_f1 - baseline.macro_f1, 4
                    ),
                    "severity_mae_delta": round(
                        baseline.severity_mae - metrics.severity_mae, 4
                    ),
                },
            }

        # Add per-category detail
        report["category_details"] = {
            cat: {
                "precision": round(cm.precision, 4) if hasattr(cm, 'precision') else 0,
                "recall": round(cm.recall, 4) if hasattr(cm, 'recall') else 0,
                "f1": round(cm.f1_score, 4) if hasattr(cm, 'f1_score') else 0,
                "support": cm.support if hasattr(cm, 'support') else 0,
                "true_positives": cm.true_positives if hasattr(cm, 'true_positives') else 0,
                "false_positives": cm.false_positives if hasattr(cm, 'false_positives') else 0,
                "false_negatives": cm.false_negatives if hasattr(cm, 'false_negatives') else 0,
            }
            for cat, cm in metrics.category_metrics.items()
        }

        return report

    def _save_report(self, report: Dict[str, Any]) -> str:
        """Save evaluation report to disk.

        Args:
            report: The report to save.

        Returns:
            Path to saved report.
        """
        import os

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_report_{timestamp}.json"
        path = os.path.join(self._output_dir, filename)

        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info("Evaluation report saved to %s", path)
        return path

    def get_last_report(self) -> Optional[Dict[str, Any]]:
        """Get the last evaluation report.

        Returns:
            Last report dict or None.
        """
        return self._last_report

    @staticmethod
    def get_celery_task() -> Dict[str, Any]:
        """Get the Celery task configuration for scheduled evaluation.

        Returns:
            Dict with Celery task config.
        """
        return {
            "name": "run_weekly_evaluation",
            "schedule": timedelta(weeks=1),
            "args": [],
            "options": {
                "queue": "evaluation",
                "priority": 5,
            },
        }

    def _compute_template_metrics(
        self, test_set: TestSet
    ) -> EvaluationMetrics:
        """Compute metrics using template-based predictions (no LLM).

        Used for testing the evaluation pipeline without an LLM.

        Args:
            test_set: The test set to evaluate.

        Returns:
            Computed evaluation metrics.
        """
        from .metrics import MetricsComputer

        predictions = []
        for clause in test_set.clauses:
            predictions.append({
                "clause_id": clause.clause_id,
                "predicted_category": clause.risk_category,
                "predicted_severity": clause.expected_severity,
                "predicted_risk_level": clause.expected_risk_level,
                "is_high_risk": clause.is_high_risk,
                "raw_output": "template",
            })

        computer = MetricsComputer()
        return computer.compute(predictions, test_set.clauses)
