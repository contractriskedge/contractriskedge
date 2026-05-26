"""Celery background tasks for weekly accuracy evaluation.

Runs automated evaluation on the blind test set every week,
computes metrics, checks for regression, and generates reports.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from celery import Celery
from celery.schedules import crontab
from kombu import Queue as KombuQueue

from evaluation.test_set import TestSetGenerator
from evaluation.evaluator import AccuracyEvaluator
from evaluation.metrics import EvaluationMetrics, MetricsComputer
from evaluation.regression_detector import RegressionDetector, RegressionAlert

logger = logging.getLogger(__name__)

# ── Celery App (shared with ingestion tasks) ─────────────────────────────────

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

evaluation_celery = Celery(
    "contract_risk_evaluation",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

evaluation_celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
)

# ── Queues ───────────────────────────────────────────────────────────────────

evaluation_celery.conf.task_queues = [
    KombuQueue("evaluation", routing_key="evaluation.#"),
]

evaluation_celery.conf.task_routes = {
    "run_weekly_evaluation": {"queue": "evaluation"},
    "run_evaluation_now": {"queue": "evaluation"},
}

# ── Scheduled Task ───────────────────────────────────────────────────────────

evaluation_celery.conf.beat_schedule = {
    "run-weekly-evaluation": {
        "task": "run_weekly_evaluation",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Monday 9am UTC
        "options": {"queue": "evaluation"},
    },
}


@evaluation_celery.task(
    name="run_weekly_evaluation",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
)
def run_weekly_evaluation(self: Any) -> Dict[str, Any]:
    """Run the weekly accuracy evaluation.

    Scheduled for Monday 9am UTC. Runs the full evaluation pipeline
    and checks for regression.

    Returns:
        Evaluation report summary.

    Raises:
        self.retry: On transient failures.
    """
    logger.info("Starting weekly accuracy evaluation...")

    try:
        # Initialize evaluator
        evaluator = AccuracyEvaluator(
            test_set_path=os.path.join(
                os.path.dirname(__file__), "test_set_v1.json"
            ),
            output_dir="./evaluation_results",
        )

        # Load test set
        test_set = evaluator.load_test_set()
        logger.info(
            "Loaded test set: %s (%d clauses)",
            test_set.name,
            test_set.total_clauses,
        )

        # Load baseline
        baseline = evaluator.load_baseline()

        # Run evaluation (uses template-based predictions for now)
        # In production, this would use the LLM client
        report = evaluator._build_report(
            metrics=evaluator._compute_template_metrics(test_set),
            baseline=baseline,
            test_set=test_set,
            predictions=[],
        )

        # Check for regression
        detector = RegressionDetector()
        detector.record_evaluation(report["current_metrics"])
        regression_report = detector.check_for_regression()

        # Add regression info to report
        report["regression"] = {
            "status": regression_report.overall_status,
            "categories_regressed": regression_report.categories_regressed,
            "alerts": [
                {
                    "category": a.category,
                    "metric": a.metric,
                    "delta": round(a.delta, 4),
                    "severity": a.severity,
                }
                for a in regression_report.alerts
            ],
        }

        # Generate dashboard data
        report["dashboard_data"] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": report["current_metrics"],
            "regression": report["regression"],
        }

        # Log summary
        metrics = report["current_metrics"]
        logger.info(
            "Weekly evaluation complete: "
            "accuracy=%.4f, macro_f1=%.4f, severity_mae=%.4f, "
            "regression_status=%s",
            metrics["overall_accuracy"],
            metrics["macro_f1"],
            metrics["severity_mae"],
            regression_report.overall_status,
        )

        # Trigger alerts if regression detected
        if regression_report.categories_regressed > 0:
            _trigger_regression_alerts(regression_report)

        return report

    except Exception as exc:
        logger.error("Weekly evaluation failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@evaluation_celery.task(
    name="run_evaluation_now",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def run_evaluation_now(self: Any) -> Dict[str, Any]:
    """Run evaluation on-demand (triggered via API).

    Returns:
        Evaluation report.
    """
    return run_weekly_evaluation()


def _trigger_regression_alerts(report: Any) -> None:
    """Trigger alerts for detected regression.

    Args:
        report: RegressionReport from the detector.
    """
    for alert in report.alerts:
        logger.warning(
            "REGRESSION ALERT [%s]: %s %s dropped by %.4f "
            "(threshold: %.4f). %s",
            alert.severity.upper(),
            alert.category,
            alert.metric,
            alert.delta,
            alert.threshold,
            alert.recommendation,
        )

        # In production, this would send Slack/PagerDuty alerts
        # slack_client.send_message(
        #     channel="#ml-alerts",
        #     text=f"*{alert.severity.upper()}*: {alert.category} {alert.metric} "
        #          f"dropped by {alert.delta:.4f} (threshold: {alert.threshold})",
        # )


# ── Helper: Generate initial test set ────────────────────────────────────────


def generate_test_set(output_path: str = "./evaluation_results") -> str:
    """Generate the initial 500-clause blind test set.

    Args:
        output_path: Directory to save the test set.

    Returns:
        Path to saved test set.
    """
    os.makedirs(output_path, exist_ok=True)

    generator = TestSetGenerator(seed=42)
    test_set = generator.generate_test_set(total_clauses=500)

    filepath = os.path.join(output_path, "test_set_v1.json")
    generator.save_test_set(test_set, filepath)

    logger.info(
        "Test set generated: %d clauses across %d contract types, "
        "saved to %s",
        test_set.total_clauses,
        len(test_set.contract_types),
        filepath,
    )

    return filepath
