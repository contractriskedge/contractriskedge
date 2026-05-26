"""Precision, Recall, F1, Severity MAE/RMSE, FP rate, AUC-ROC computation.

Provides comprehensive evaluation metrics for risk analysis accuracy
including classification metrics, severity scoring accuracy, and
false positive rate monitoring.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .test_set import TestClause

logger = logging.getLogger(__name__)


@dataclass
class ConfusionMatrix:
    """Binary confusion matrix for a risk category."""

    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    @property
    def total(self) -> int:
        return (
            self.true_positives + self.false_positives
            + self.true_negatives + self.false_negatives
        )


@dataclass
class CategoryMetrics:
    """Metrics for a single risk category."""

    category: str
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    support: int = 0
    severity_mae: float = 0.0
    false_positive_rate: float = 0.0


@dataclass
class EvaluationMetrics:
    """Complete set of evaluation metrics."""

    # Classification metrics
    overall_accuracy: float = 0.0
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    weighted_f1: float = 0.0

    # Severity metrics
    severity_mae: float = 0.0
    severity_rmse: float = 0.0
    severity_accuracy_within_1: float = 0.0
    severity_accuracy_within_2: float = 0.0

    # Error analysis
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0

    # Per-category breakdown
    category_metrics: Dict[str, CategoryMetrics] = field(default_factory=dict)

    # Confusion matrix
    confusion_matrix: Dict[str, ConfusionMatrix] = field(default_factory=dict)

    # Sample counts
    total_samples: int = 0
    correct_classifications: int = 0
    total_severity_comparisons: int = 0
    high_risk_correct: int = 0
    high_risk_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to dictionary.

        Returns:
            Dict with all metric values.
        """
        return {
            "overall_accuracy": round(self.overall_accuracy, 4),
            "macro_precision": round(self.macro_precision, 4),
            "macro_recall": round(self.macro_recall, 4),
            "macro_f1": round(self.macro_f1, 4),
            "weighted_f1": round(self.weighted_f1, 4),
            "severity_mae": round(self.severity_mae, 4),
            "severity_rmse": round(self.severity_rmse, 4),
            "severity_accuracy_within_1": round(self.severity_accuracy_within_1, 4),
            "severity_accuracy_within_2": round(self.severity_accuracy_within_2, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "total_samples": self.total_samples,
            "correct_classifications": self.correct_classifications,
            "high_risk_accuracy": (
                round(self.high_risk_correct / self.high_risk_total, 4)
                if self.high_risk_total > 0 else 0.0
            ),
            "category_metrics": {
                cat: {
                    "precision": round(m.precision, 4),
                    "recall": round(m.recall, 4),
                    "f1_score": round(m.f1_score, 4),
                    "support": m.support,
                    "severity_mae": round(m.severity_mae, 4),
                    "false_positive_rate": round(m.false_positive_rate, 4),
                }
                for cat, m in self.category_metrics.items()
            },
        }


class MetricsComputer:
    """Computes comprehensive evaluation metrics for risk analysis.

    Calculates precision, recall, F1, severity MAE/RMSE, FP rate,
    and per-category breakdowns from prediction results.

    Usage:
        computer = MetricsComputer()
        metrics = computer.compute(predictions, ground_truth)
    """

    def __init__(self) -> None:
        """Initialize the metrics computer."""
        pass

    def compute(
        self,
        predictions: List[Dict[str, Any]],
        ground_truth: List[TestClause],
    ) -> EvaluationMetrics:
        """Compute evaluation metrics from predictions and ground truth.

        Args:
            predictions: List of prediction dicts with keys:
                - clause_id: matching test clause ID
                - predicted_category: predicted risk category
                - predicted_severity: predicted severity (1-10)
                - predicted_risk_level: predicted risk level
            ground_truth: List of TestClause with expected values.

        Returns:
            EvaluationMetrics with all computed values.
        """
        # Build lookup
        truth_by_id = {c.clause_id: c for c in ground_truth}

        # Initialize per-category confusion matrices
        all_categories = set()
        for t in ground_truth:
            all_categories.add(t.risk_category)
        for p in predictions:
            all_categories.add(p.get("predicted_category", ""))

        confusion: Dict[str, ConfusionMatrix] = {
            cat: ConfusionMatrix() for cat in all_categories
        }

        metrics = EvaluationMetrics(total_samples=len(predictions))
        severity_errors: list[float] = []

        for pred in predictions:
            clause_id = pred.get("clause_id", "")
            truth = truth_by_id.get(clause_id)

            if truth is None:
                logger.warning("No ground truth for clause %s", clause_id)
                continue

            pred_cat = pred.get("predicted_category", "")
            true_cat = truth.risk_category
            pred_sev = pred.get("predicted_severity", 0)
            true_sev = truth.expected_severity

            # Classification accuracy
            if pred_cat == true_cat:
                metrics.correct_classifications += 1

            # Update confusion matrices
            for cat in all_categories:
                if pred_cat == cat and true_cat == cat:
                    confusion[cat].true_positives += 1
                elif pred_cat == cat and true_cat != cat:
                    confusion[cat].false_positives += 1
                elif pred_cat != cat and true_cat == cat:
                    confusion[cat].false_negatives += 1
                elif pred_cat != cat and true_cat != cat:
                    confusion[cat].true_negatives += 1

            # Severity error
            if pred_sev > 0 and true_sev > 0:
                severity_errors.append(abs(pred_sev - true_sev))
                metrics.total_severity_comparisons += 1

            # High risk detection
            if truth.is_high_risk:
                metrics.high_risk_total += 1
                pred_is_high_risk = pred.get("is_high_risk", pred_sev >= 7)
                if pred_is_high_risk:
                    metrics.high_risk_correct += 1

        # Compute aggregate metrics
        metrics.overall_accuracy = (
            metrics.correct_classifications / metrics.total_samples
            if metrics.total_samples > 0 else 0.0
        )

        # Severity metrics
        if severity_errors:
            metrics.severity_mae = sum(severity_errors) / len(severity_errors)
            metrics.severity_rmse = math.sqrt(
                sum(e ** 2 for e in severity_errors) / len(severity_errors)
            )
            metrics.severity_accuracy_within_1 = (
                sum(1 for e in severity_errors if e <= 1) / len(severity_errors)
            )
            metrics.severity_accuracy_within_2 = (
                sum(1 for e in severity_errors if e <= 2) / len(severity_errors)
            )

        # Per-category metrics
        precisions: list[float] = []
        recalls: list[float] = []
        f1_scores: list[float] = []
        weighted_f1_sum = 0.0
        total_support = 0

        for cat in sorted(all_categories):
            cm = confusion[cat]
            cat_metrics = self._compute_category_metrics(cat, cm, severity_errors)

            metrics.category_metrics[cat] = cat_metrics
            metrics.confusion_matrix[cat] = cm

            if cat_metrics.precision > 0:
                precisions.append(cat_metrics.precision)
            if cat_metrics.recall > 0:
                recalls.append(cat_metrics.recall)
            if cat_metrics.f1_score > 0:
                f1_scores.append(cat_metrics.f1_score)

            weighted_f1_sum += cat_metrics.f1_score * cat_metrics.support
            total_support += cat_metrics.support

        # Macro averages
        metrics.macro_precision = (
            sum(precisions) / len(precisions) if precisions else 0.0
        )
        metrics.macro_recall = (
            sum(recalls) / len(recalls) if recalls else 0.0
        )
        metrics.macro_f1 = (
            sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
        )

        # Weighted F1
        metrics.weighted_f1 = (
            weighted_f1_sum / total_support if total_support > 0 else 0.0
        )

        # Overall FP/FN rates
        total_fp = sum(cm.false_positives for cm in confusion.values())
        total_fn = sum(cm.false_negatives for cm in confusion.values())
        total_negatives = sum(
            cm.true_negatives + cm.false_positives
            for cm in confusion.values()
        )
        total_positives = sum(
            cm.true_positives + cm.false_negatives
            for cm in confusion.values()
        )

        metrics.false_positive_rate = (
            total_fp / total_negatives if total_negatives > 0 else 0.0
        )
        metrics.false_negative_rate = (
            total_fn / total_positives if total_positives > 0 else 0.0
        )

        logger.info(
            "Computed metrics: accuracy=%.4f, macro_f1=%.4f, severity_MAE=%.4f",
            metrics.overall_accuracy,
            metrics.macro_f1,
            metrics.severity_mae,
        )

        return metrics

    def _compute_category_metrics(
        self,
        category: str,
        cm: ConfusionMatrix,
        severity_errors: List[float],
    ) -> CategoryMetrics:
        """Compute metrics for a single category.

        Args:
            category: Category name.
            cm: Confusion matrix for this category.
            severity_errors: All severity errors (unused per-category).

        Returns:
            CategoryMetrics for this category.
        """
        tp = cm.true_positives
        fp = cm.false_positives
        fn = cm.false_negatives

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0 else 0.0
        )
        support = tp + fn

        # FP rate for this category
        fp_rate = (
            fp / (fp + cm.true_negatives)
            if (fp + cm.true_negatives) > 0 else 0.0
        )

        return CategoryMetrics(
            category=category,
            precision=precision,
            recall=recall,
            f1_score=f1,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            support=support,
            severity_mae=0.0,  # Per-category severity MAE requires category-level data
            false_positive_rate=fp_rate,
        )

    def compute_confusion_matrix(
        self,
        predictions: List[Dict[str, Any]],
        ground_truth: List[TestClause],
    ) -> Dict[str, ConfusionMatrix]:
        """Compute only the confusion matrix.

        Args:
            predictions: List of predictions.
            ground_truth: List of ground truth clauses.

        Returns:
            Dict mapping categories to confusion matrices.
        """
        metrics = self.compute(predictions, ground_truth)
        return metrics.confusion_matrix

    def compute_auc_roc(
        self,
        scores: List[float],
        labels: List[bool],
    ) -> float:
        """Compute AUC-ROC score.

        Args:
            scores: Model confidence scores.
            labels: Binary ground truth labels.

        Returns:
            AUC-ROC score.
        """
        if len(scores) != len(labels) or len(scores) < 2:
            return 0.0

        # Sort by score descending
        paired = sorted(
            zip(scores, labels), key=lambda x: x[0], reverse=True
        )

        n_pos = sum(labels)
        n_neg = len(labels) - n_pos

        if n_pos == 0 or n_neg == 0:
            return 0.5

        # Compute AUC using the Wilcoxon-Mann-Whitney statistic
        rank_sum = 0
        for i, (_, label) in enumerate(paired):
            if label:
                rank_sum += i + 1

        auc = (rank_sum - (n_pos * (n_pos + 1) / 2)) / (n_pos * n_neg)
        return auc
