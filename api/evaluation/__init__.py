"""Evaluation module for contract risk analysis accuracy.

Provides test set management, metrics computation, automated
evaluation runs, regression detection, and dashboard visualization.
"""

from __future__ import annotations

from .test_set import TestSetGenerator
from .metrics import EvaluationMetrics
from .evaluator import AccuracyEvaluator
from .regression_detector import RegressionDetector
from .dashboard import MetricsDashboard

__all__ = [
    "TestSetGenerator",
    "EvaluationMetrics",
    "AccuracyEvaluator",
    "RegressionDetector",
    "MetricsDashboard",
]
