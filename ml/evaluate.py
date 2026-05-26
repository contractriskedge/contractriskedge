"""Evaluation of fine-tuned models vs zero-shot baseline.

Provides comprehensive evaluation comparing LoRA fine-tuned models
against zero-shot baselines across precision, recall, F1, and
severity accuracy metrics.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .dataset import CUDADatasetProcessor, InstructionExample

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Metrics from model evaluation."""

    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0
    severity_mae: float = 0.0
    severity_rmse: float = 0.0
    total_examples: int = 0
    correct_predictions: int = 0
    category_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary.

        Returns:
            Dict of all metrics.
        """
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "accuracy": round(self.accuracy, 4),
            "severity_mae": round(self.severity_mae, 4),
            "severity_rmse": round(self.severity_rmse, 4),
            "total_examples": self.total_examples,
            "correct_predictions": self.correct_predictions,
            "category_metrics": self.category_metrics,
        }


class ModelEvaluator:
    """Evaluates fine-tuned models against zero-shot baselines.

    Compares LoRA fine-tuned model performance against the base model
    (zero-shot) across classification accuracy, severity scoring
    accuracy, and per-category metrics.

    Usage:
        evaluator = ModelEvaluator()
        baseline_metrics = evaluator.evaluate_zero_shot(model, test_set)
        finetuned_metrics = evaluator.evaluate_finetuned(model, test_set)
        comparison = evaluator.compare(baseline_metrics, finetuned_metrics)
    """

    def __init__(self, test_set_path: Optional[str] = None) -> None:
        """Initialize the evaluator.

        Args:
            test_set_path: Optional path to a pre-built test set.
        """
        self._test_set_path = test_set_path
        self._test_examples: list[InstructionExample] = []

    def load_test_set(
        self,
        path: Optional[str] = None,
        num_examples: Optional[int] = None,
    ) -> List[InstructionExample]:
        """Load the evaluation test set.

        Args:
            path: Path to test set JSON file.
            num_examples: Optional limit on examples.

        Returns:
            List of test instruction examples.
        """
        load_path = path or self._test_set_path

        if load_path:
            try:
                with open(load_path) as f:
                    data = json.load(f)
                examples = [
                    InstructionExample(**item) for item in data
                ]
                logger.info("Loaded %d test examples from %s", len(examples), load_path)
                self._test_examples = examples
                return examples
            except (FileNotFoundError, json.JSONDecodeError) as exc:
                logger.warning("Failed to load test set: %s", exc)

        # Generate synthetic test set
        processor = CUDADatasetProcessor()
        all_examples = processor._generate_synthetic_examples(
            num_examples or 200
        )
        _, _, test_examples = processor.train_test_split(
            all_examples, test_ratio=1.0, val_ratio=0.0
        )
        self._test_examples = test_examples
        logger.info(
            "Generated %d synthetic test examples", len(test_examples)
        )
        return test_examples

    async def evaluate_zero_shot(
        self,
        llm_client: Any,
        test_examples: Optional[List[InstructionExample]] = None,
    ) -> EvaluationMetrics:
        """Evaluate a base model in zero-shot mode.

        Args:
            llm_client: The LLM client (without fine-tuning).
            test_examples: Test examples to evaluate on.

        Returns:
            Evaluation metrics for zero-shot performance.
        """
        from ..api.llm.models import LLMRequest, Message, RoleType

        examples = test_examples or self._test_examples
        if not examples:
            examples = self.load_test_set()

        metrics = EvaluationMetrics(total_examples=len(examples))
        category_correct: Dict[str, int] = {}
        category_total: Dict[str, int] = {}
        severity_errors: list[float] = []

        for example in examples:
            try:
                request = LLMRequest(
                    messages=[
                        Message(
                            role=RoleType.SYSTEM,
                            content="Classify this contract clause's risk category.",
                        ),
                        Message(
                            role=RoleType.USER,
                            content=example.input_text,
                        ),
                    ],
                    temperature=0.1,
                    max_tokens=256,
                )

                response = await llm_client.complete(request)
                prediction = response.content.strip().lower()

                # Extract category from prediction
                predicted_category = self._extract_category(prediction)
                actual_category = example.category or ""

                # Track category metrics
                if actual_category:
                    category_total[actual_category] = (
                        category_total.get(actual_category, 0) + 1
                    )
                    if predicted_category == actual_category:
                        category_correct[actual_category] = (
                            category_correct.get(actual_category, 0) + 1
                        )
                        metrics.correct_predictions += 1

                # Track severity error
                if example.severity is not None:
                    predicted_severity = self._extract_severity(prediction)
                    if predicted_severity > 0:
                        severity_errors.append(
                            abs(predicted_severity - example.severity)
                        )

            except Exception as exc:
                logger.warning("Evaluation example failed: %s", exc)

        # Compute aggregate metrics
        metrics.accuracy = (
            metrics.correct_predictions / metrics.total_examples
            if metrics.total_examples > 0 else 0.0
        )

        if severity_errors:
            metrics.severity_mae = sum(severity_errors) / len(severity_errors)
            metrics.severity_rmse = (
                sum(e ** 2 for e in severity_errors) / len(severity_errors)
            ) ** 0.5

        # Compute per-category metrics
        for cat in category_total:
            correct = category_correct.get(cat, 0)
            total = category_total[cat]
            metrics.category_metrics[cat] = {
                "accuracy": correct / total if total > 0 else 0.0,
                "total": total,
                "correct": correct,
            }

        logger.info(
            "Zero-shot evaluation: accuracy=%.4f, severity_MAE=%.4f",
            metrics.accuracy,
            metrics.severity_mae,
        )
        return metrics

    async def evaluate_finetuned(
        self,
        finetuned_model: Any,
        tokenizer: Any,
        test_examples: Optional[List[InstructionExample]] = None,
    ) -> EvaluationMetrics:
        """Evaluate a fine-tuned model.

        Args:
            finetuned_model: The fine-tuned PEFT model.
            tokenizer: The model's tokenizer.
            test_examples: Test examples to evaluate on.

        Returns:
            Evaluation metrics for fine-tuned performance.
        """
        import torch

        examples = test_examples or self._test_examples
        if not examples:
            examples = self.load_test_set()

        metrics = EvaluationMetrics(total_examples=len(examples))
        category_correct: Dict[str, int] = {}
        category_total: Dict[str, int] = {}
        severity_errors: list[float] = []

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        for example in examples:
            try:
                prompt = (
                    f"Classify the following contract clause into the "
                    f"appropriate risk category.\n\nClause: {example.input_text}\n\n"
                    f"Category:"
                )

                inputs = tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                ).to(device)

                with torch.no_grad():
                    outputs = finetuned_model.generate(
                        **inputs,
                        max_new_tokens=50,
                        temperature=0.1,
                        do_sample=False,
                    )

                prediction = tokenizer.decode(
                    outputs[0][inputs.input_ids.shape[1]:],
                    skip_special_tokens=True,
                ).strip().lower()

                # Extract and compare
                predicted_category = self._extract_category(prediction)
                actual_category = example.category or ""

                if actual_category:
                    category_total[actual_category] = (
                        category_total.get(actual_category, 0) + 1
                    )
                    if predicted_category == actual_category:
                        category_correct[actual_category] = (
                            category_correct.get(actual_category, 0) + 1
                        )
                        metrics.correct_predictions += 1

                if example.severity is not None:
                    predicted_severity = self._extract_severity(prediction)
                    if predicted_severity > 0:
                        severity_errors.append(
                            abs(predicted_severity - example.severity)
                        )

            except Exception as exc:
                logger.warning("Fine-tuned evaluation failed: %s", exc)

        metrics.accuracy = (
            metrics.correct_predictions / metrics.total_examples
            if metrics.total_examples > 0 else 0.0
        )

        if severity_errors:
            metrics.severity_mae = sum(severity_errors) / len(severity_errors)
            metrics.severity_rmse = (
                sum(e ** 2 for e in severity_errors) / len(severity_errors)
            ) ** 0.5

        for cat in category_total:
            correct = category_correct.get(cat, 0)
            total = category_total[cat]
            metrics.category_metrics[cat] = {
                "accuracy": correct / total if total > 0 else 0.0,
                "total": total,
                "correct": correct,
            }

        logger.info(
            "Fine-tuned evaluation: accuracy=%.4f, severity_MAE=%.4f",
            metrics.accuracy,
            metrics.severity_mae,
        )
        return metrics

    def compare(
        self,
        baseline: EvaluationMetrics,
        finetuned: EvaluationMetrics,
    ) -> Dict[str, Any]:
        """Compare baseline vs fine-tuned performance.

        Args:
            baseline: Zero-shot baseline metrics.
            finetuned: Fine-tuned model metrics.

        Returns:
            Comparison report with deltas and improvements.
        """
        comparison = {
            "baseline": baseline.to_dict(),
            "finetuned": finetuned.to_dict(),
            "improvements": {
                "accuracy_delta": round(
                    finetuned.accuracy - baseline.accuracy, 4
                ),
                "severity_mae_delta": round(
                    baseline.severity_mae - finetuned.severity_mae, 4
                ),
                "accuracy_improvement_pct": (
                    round(
                        ((finetuned.accuracy - baseline.accuracy)
                         / baseline.accuracy * 100)
                        if baseline.accuracy > 0 else 0,
                        2,
                    )
                ),
            },
            "category_comparison": {},
        }

        # Per-category comparison
        all_categories = set()
        all_categories.update(baseline.category_metrics.keys())
        all_categories.update(finetuned.category_metrics.keys())

        for cat in sorted(all_categories):
            base_metrics = baseline.category_metrics.get(cat, {})
            ft_metrics = finetuned.category_metrics.get(cat, {})
            base_acc = base_metrics.get("accuracy", 0.0)
            ft_acc = ft_metrics.get("accuracy", 0.0)

            comparison["category_comparison"][cat] = {
                "baseline_accuracy": base_acc,
                "finetuned_accuracy": ft_acc,
                "delta": round(ft_acc - base_acc, 4),
                "baseline_samples": base_metrics.get("total", 0),
                "finetuned_samples": ft_metrics.get("total", 0),
            }

        logger.info(
            "Comparison: accuracy improved by %+.2f%%",
            comparison["improvements"]["accuracy_improvement_pct"],
        )

        return comparison

    def _extract_category(self, text: str) -> str:
        """Extract risk category from model output.

        Args:
            text: Raw model output text.

        Returns:
            Extracted category ID or empty string.
        """
        category_keywords = {
            "indemnification": ["indemnif", "indemnity"],
            "liability_limitation": ["liability", "limitation of liability"],
            "termination": ["termination"],
            "confidentiality": ["confidential"],
            "data_privacy": ["data privacy", "data protection", "privacy"],
            "compliance": ["compliance", "regulatory", "anti-corruption"],
            "payment_terms": ["payment", "pricing"],
            "force_majeure": ["force majeure"],
            "assignment": ["assignment"],
            "governing_law": ["governing law", "jurisdiction"],
            "non_compete": ["non-compete", "non-compet", "non-solicit"],
            "intellectual_property": ["intellectual property", "ip", "copyright"],
        }

        text_lower = text.lower()
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        return ""

    def _extract_severity(self, text: str) -> int:
        """Extract severity score from model output.

        Args:
            text: Raw model output text.

        Returns:
            Extracted severity score (1-10) or 0.
        """
        import re

        # Look for numbers in context of severity
        patterns = [
            r"severity(?:\s*:|\s+is|\s+of)\s*(\d+)",
            r"score(?:\s*:|\s+is|\s+of)\s*(\d+)",
            r"(\d+)\s*/\s*10",
            r"(\d+)\s*out\s*of\s*10",
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                score = int(match.group(1))
                if 1 <= score <= 10:
                    return score

        return 0

    def generate_report(
        self, comparison: Dict[str, Any], output_path: str
    ) -> None:
        """Generate and save an evaluation report.

        Args:
            comparison: Comparison data from compare().
            output_path: Path to save the report JSON.
        """
        report = {
            "report_metadata": {
                "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
                "total_baseline_examples": comparison["baseline"]["total_examples"],
                "total_finetuned_examples": comparison["finetuned"]["total_examples"],
            },
            "summary": {
                "baseline_accuracy": comparison["baseline"]["accuracy"],
                "finetuned_accuracy": comparison["finetuned"]["accuracy"],
                "accuracy_improvement": comparison["improvements"]["accuracy_improvement_pct"],
                "severity_mae_improvement": comparison["improvements"]["severity_mae_delta"],
            },
            "category_breakdown": comparison["category_comparison"],
            "detailed_metrics": comparison,
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info("Evaluation report saved to %s", output_path)
