"""API endpoints for accuracy evaluation and monitoring.

Provides endpoints for triggering evaluations, viewing reports,
and monitoring accuracy metrics.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions
from evaluation.evaluator import AccuracyEvaluator
from evaluation.metrics import EvaluationMetrics
from evaluation.regression_detector import RegressionDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

# Service instances
_evaluator = AccuracyEvaluator(
    test_set_path=os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "evaluation_results",
        "test_set_v1.json",
    ),
    output_dir=os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "evaluation_results",
    ),
)
_regression_detector = RegressionDetector(
    history_path=os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "evaluation_results",
        "history",
    ),
)


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run_evaluation(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
) -> Dict[str, Any]:
    """Run an accuracy evaluation on-demand.

    Triggers evaluation against the blind test set and returns
    metrics. Only available to system admins.

    Args:
        user: Authenticated user.

    Returns:
        Evaluation report with metrics.
    """
    try:
        # Load test set
        test_set = _evaluator.load_test_set()

        # Run template-based evaluation (no LLM needed)
        metrics = _evaluator._compute_template_metrics(test_set)

        # Build report
        report = _evaluator._build_report(
            metrics=metrics,
            baseline=None,
            test_set=test_set,
            predictions=[],
        )

        # Record in regression detector
        _regression_detector.record_evaluation(report["current_metrics"])

        # Check for regression
        regression_report = _regression_detector.check_for_regression()
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

        logger.info(
            "On-demand evaluation complete: accuracy=%.4f, macro_f1=%.4f",
            metrics.overall_accuracy,
            metrics.macro_f1,
        )

        return report

    except Exception as exc:
        logger.error("Evaluation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {exc}",
        )


@router.get("/latest")
async def get_latest_evaluation(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_AUDIT)),
) -> Dict[str, Any]:
    """Get the latest evaluation report.

    Args:
        user: Authenticated user.

    Returns:
        Latest evaluation report or 404.
    """
    report = _evaluator.get_last_report()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation reports available. Run an evaluation first.",
        )
    return report


@router.get("/metrics")
async def get_evaluation_metrics(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_AUDIT)),
) -> Dict[str, Any]:
    """Get current evaluation metrics summary.

    Args:
        user: Authenticated user.

    Returns:
        Current metrics summary.
    """
    # Load the most recent evaluation result
    results_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "evaluation_results",
    )
    os.makedirs(results_dir, exist_ok=True)

    eval_files = sorted([
        f for f in os.listdir(results_dir)
        if f.startswith("evaluation_report_") and f.endswith(".json")
    ], reverse=True)

    if not eval_files:
        return {
            "status": "no_data",
            "message": "No evaluation data available yet.",
            "metrics": {},
            "history": [],
        }

    # Load latest
    with open(os.path.join(results_dir, eval_files[0])) as f:
        latest = json.load(f)

    # Load history
    history = []
    for ef in eval_files[:12]:  # Last 12 evaluations
        with open(os.path.join(results_dir, ef)) as f:
            report = json.load(f)
            history.append({
                "timestamp": report.get("report_metadata", {}).get(
                    "generated_at", ""
                ),
                "accuracy": report.get("current_metrics", {}).get(
                    "overall_accuracy", 0
                ),
                "macro_f1": report.get("current_metrics", {}).get(
                    "macro_f1", 0
                ),
                "severity_mae": report.get("current_metrics", {}).get(
                    "severity_mae", 0
                ),
            })

    return {
        "status": "available",
        "latest_timestamp": latest.get("report_metadata", {}).get(
            "generated_at", ""
        ),
        "metrics": latest.get("current_metrics", {}),
        "regression": latest.get("regression", {}),
        "history": history,
    }


@router.get("/regression")
async def get_regression_status(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_AUDIT)),
) -> Dict[str, Any]:
    """Get current regression detection status.

    Args:
        user: Authenticated user.

    Returns:
        Regression status and alert history.
    """
    from evaluation.metrics import EvaluationMetrics, CategoryMetrics

    # Load latest metrics from the most recent evaluation report
    results_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "evaluation_results",
    )
    eval_files = sorted([
        f for f in os.listdir(results_dir)
        if f.startswith("evaluation_report_") and f.endswith(".json")
    ], reverse=True)

    current_metrics = EvaluationMetrics()
    if eval_files:
        with open(os.path.join(results_dir, eval_files[0])) as f:
            report = json.load(f)
        metrics_data = report.get("current_metrics", {})
        for key, value in metrics_data.items():
            if hasattr(current_metrics, key) and key != "category_metrics":
                setattr(current_metrics, key, value)
        # Reconstruct category_metrics as objects
        cat_data = metrics_data.get("category_metrics", {})
        for cat_name, cat_dict in cat_data.items():
            cm = CategoryMetrics(category=cat_name)
            for k, v in cat_dict.items():
                if hasattr(cm, k):
                    setattr(cm, k, v)
            current_metrics.category_metrics[cat_name] = cm

    report = _regression_detector.check_for_regression(current_metrics)

    return {
        "status": report.overall_status,
        "total_categories": report.total_categories,
        "categories_regressed": report.categories_regressed,
        "alerts": [
            {
                "category": a.category,
                "metric": a.metric,
                "previous_value": round(a.previous_value, 4),
                "current_value": round(a.current_value, 4),
                "delta": round(a.delta, 4),
                "severity": a.severity,
                "timestamp": a.timestamp.isoformat(),
                "recommendation": a.recommendation,
            }
            for a in report.alerts
        ],
        "summary": report.summary,
    }


@router.get("/history")
async def get_evaluation_history(
    weeks: int = Query(12, ge=1, le=52),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_AUDIT)),
) -> Dict[str, Any]:
    """Get evaluation history for trend analysis.

    Args:
        weeks: Number of weeks of history to return.
        user: Authenticated user.

    Returns:
        Evaluation history with trend data.
    """
    results_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "evaluation_results",
    )

    eval_files = sorted([
        f for f in os.listdir(results_dir)
        if f.startswith("evaluation_report_") and f.endswith(".json")
    ], reverse=True)[:weeks]

    history = []
    for ef in eval_files:
        with open(os.path.join(results_dir, ef)) as f:
            report = json.load(f)
        history.append({
            "timestamp": report.get("report_metadata", {}).get(
                "generated_at", ""
            ),
            "metrics": report.get("current_metrics", {}),
            "regression": report.get("regression", {}),
            "category_details": report.get("category_details", {}),
        })

    # Compute trends
    trends = {}
    if len(history) >= 2:
        latest = history[0]["metrics"]
        previous = history[1]["metrics"]
        trends = {
            "accuracy_trend": "up" if latest.get("overall_accuracy", 0) > previous.get("overall_accuracy", 0) else "down",
            "f1_trend": "up" if latest.get("macro_f1", 0) > previous.get("macro_f1", 0) else "down",
            "severity_trend": "improving" if latest.get("severity_mae", 99) < previous.get("severity_mae", 99) else "worsening",
        }

    return {
        "total_reports": len(history),
        "trends": trends,
        "history": history,
    }
