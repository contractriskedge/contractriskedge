"""Grafana dashboard JSON for metrics visualization.

Provides Grafana dashboard configurations for visualizing evaluation
metrics, regression trends, and per-category performance.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MetricsDashboard:
    """Generates Grafana dashboard JSON for metrics visualization.

    Creates comprehensive Grafana dashboards for monitoring risk
    analysis accuracy, severity scoring, and regression detection.

    Usage:
        dashboard = MetricsDashboard()
        dashboard_json = dashboard.generate_main_dashboard()
        with open("grafana_dashboard.json", "w") as f:
            f.write(dashboard_json)
    """

    @staticmethod
    def generate_main_dashboard() -> str:
        """Generate the main evaluation metrics dashboard.

        Returns:
            Grafana dashboard JSON string.
        """
        dashboard = {
            "__inputs": [],
            "__requires": [],
            "title": "Contract Risk Analyzer - Evaluation Metrics",
            "description": "Weekly evaluation metrics for risk analysis accuracy",
            "schemaVersion": 38,
            "version": 1,
            "timezone": "utc",
            "editable": True,
            "refresh": "1h",
            "panels": MetricsDashboard._build_panels(),
            "templating": {
                "list": [
                    {
                        "name": "category",
                        "type": "custom",
                        "query": (
                            "indemnification, liability_limitation, termination, "
                            "confidentiality, data_privacy, compliance, "
                            "payment_terms, force_majeure, assignment, "
                            "governing_law, non_compete, intellectual_property"
                        ),
                        "current": {"text": "All", "value": "all"},
                        "label": "Risk Category",
                        "includeAll": True,
                        "multi": True,
                    },
                    {
                        "name": "contract_type",
                        "type": "custom",
                        "query": (
                            "nda, service_agreement, license, employment, lease"
                        ),
                        "current": {"text": "All", "value": "all"},
                        "label": "Contract Type",
                        "includeAll": True,
                        "multi": True,
                    },
                ]
            },
            "annotations": {
                "list": [
                    {
                        "name": "Model Deployment",
                        "type": "events",
                        "datasource": "Prometheus",
                        "enable": True,
                        "iconColor": "rgba(255, 96, 96, 1)",
                        "query": "model_deployment{service=\"contract-risk-analyzer\"}",
                    },
                    {
                        "name": "Regression Alert",
                        "type": "events",
                        "datasource": "Prometheus",
                        "enable": True,
                        "iconColor": "rgba(255, 0, 0, 1)",
                        "query": "regression_alert{service=\"contract-risk-analyzer\"}",
                    },
                ]
            },
        }

        return json.dumps(dashboard, indent=2)

    @staticmethod
    def _build_panels() -> List[Dict[str, Any]]:
        """Build all dashboard panels.

        Returns:
            List of panel configurations.
        """
        return [
            # Row 1: Overview stats
            {
                "title": "Overall Accuracy",
                "type": "stat",
                "gridPos": {"h": 4, "w": 4, "x": 0, "y": 0},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "risk_analysis_accuracy{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "Accuracy",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percentunit",
                        "min": 0,
                        "max": 1,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": 0},
                                {"color": "yellow", "value": 0.7},
                                {"color": "green", "value": 0.85},
                            ],
                        },
                    }
                },
            },
            {
                "title": "Macro F1 Score",
                "type": "stat",
                "gridPos": {"h": 4, "w": 4, "x": 4, "y": 0},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "risk_analysis_macro_f1{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "Macro F1",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percentunit",
                        "min": 0,
                        "max": 1,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": 0},
                                {"color": "yellow", "value": 0.65},
                                {"color": "green", "value": 0.80},
                            ],
                        },
                    }
                },
            },
            {
                "title": "Severity MAE",
                "type": "stat",
                "gridPos": {"h": 4, "w": 4, "x": 8, "y": 0},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "risk_analysis_severity_mae{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "Severity MAE",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "none",
                        "min": 0,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 1.0},
                                {"color": "red", "value": 1.5},
                            ],
                        },
                    }
                },
            },
            {
                "title": "False Positive Rate",
                "type": "stat",
                "gridPos": {"h": 4, "w": 4, "x": 12, "y": 0},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "risk_analysis_false_positive_rate{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "FP Rate",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percentunit",
                        "min": 0,
                        "max": 1,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 0.05},
                                {"color": "red", "value": 0.07},
                            ],
                        },
                    }
                },
            },
            {
                "title": "High Risk Detection Rate",
                "type": "stat",
                "gridPos": {"h": 4, "w": 4, "x": 16, "y": 0},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "risk_analysis_high_risk_recall{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "High Risk Recall",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percentunit",
                        "min": 0,
                        "max": 1,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": 0},
                                {"color": "yellow", "value": 0.8},
                                {"color": "green", "value": 0.9},
                            ],
                        },
                    }
                },
            },
            {
                "title": "Total Evaluations",
                "type": "stat",
                "gridPos": {"h": 4, "w": 4, "x": 20, "y": 0},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "risk_analysis_total_evaluations{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "Total",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "none",
                    }
                },
            },
            # Row 2: Time series
            {
                "title": "Accuracy Trend (Weekly)",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "risk_analysis_accuracy{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "Overall Accuracy",
                    },
                    {
                        "expr": "risk_analysis_macro_f1{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "Macro F1",
                    },
                    {
                        "expr": "risk_analysis_weighted_f1{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "Weighted F1",
                    },
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percentunit",
                        "min": 0,
                        "max": 1,
                    }
                },
            },
            {
                "title": "Severity Error Trend (Weekly)",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "risk_analysis_severity_mae{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "MAE",
                    },
                    {
                        "expr": "risk_analysis_severity_rmse{service=\"contract-risk-analyzer\"}",
                        "legendFormat": "RMSE",
                    },
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "none",
                        "min": 0,
                    }
                },
            },
            # Row 3: Category breakdown
            {
                "title": "Per-Category F1 Score",
                "type": "bargauge",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 12},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": (
                            "risk_analysis_category_f1{"
                            "service=\"contract-risk-analyzer\", "
                            "category=~\"$category\"}"
                        ),
                        "legendFormat": "{{category}}",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percentunit",
                        "min": 0,
                        "max": 1,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": 0},
                                {"color": "yellow", "value": 0.65},
                                {"color": "green", "value": 0.80},
                            ],
                        },
                    }
                },
            },
            {
                "title": "Confusion Matrix Heatmap",
                "type": "heatmap",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 12},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": (
                            "risk_analysis_confusion_matrix{"
                            "service=\"contract-risk-analyzer\"}"
                        ),
                        "legendFormat": "{{true_category}} -> {{predicted_category}}",
                    }
                ],
            },
            # Row 4: Regression monitoring
            {
                "title": "Category F1 Regression Delta",
                "type": "bargauge",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 20},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": (
                            "risk_analysis_f1_delta_week_over_week{"
                            "service=\"contract-risk-analyzer\", "
                            "category=~\"$category\"}"
                        ),
                        "legendFormat": "{{category}}",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "none",
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": -1},
                                {"color": "yellow", "value": -0.02},
                                {"color": "green", "value": 0},
                            ],
                        },
                    }
                },
            },
            {
                "title": "Recent Regression Alerts",
                "type": "table",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 20},
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": (
                            "risk_analysis_regression_alerts{"
                            "service=\"contract-risk-analyzer\"}"
                        ),
                        "legendFormat": "{{category}} - {{metric}}",
                    }
                ],
                "transformations": [
                    {
                        "id": "groupBy",
                        "options": {
                            "fields": {
                                "category": {"aggregations": [], "operation": "groupby"},
                                "metric": {"aggregations": [], "operation": "groupby"},
                                "severity": {"aggregations": [], "operation": "groupby"},
                                "delta": {"aggregations": [], "operation": "groupby"},
                                "timestamp": {"aggregations": [], "operation": "groupby"},
                            }
                        },
                    }
                ],
            },
        ]

    @staticmethod
    def generate_cost_dashboard() -> str:
        """Generate a cost monitoring dashboard.

        Returns:
            Grafana dashboard JSON string for LLM costs.
        """
        dashboard = {
            "title": "Contract Risk Analyzer - LLM Costs",
            "description": "LLM API cost tracking and usage monitoring",
            "schemaVersion": 38,
            "version": 1,
            "timezone": "utc",
            "panels": [
                {
                    "title": "Daily API Cost",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "datasource": "Prometheus",
                    "targets": [
                        {
                            "expr": (
                                "sum by(provider) "
                                "(llm_cost_usd{service=\"contract-risk-analyzer\"})"
                            ),
                            "legendFormat": "{{provider}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "usd",
                        }
                    },
                },
                {
                    "title": "Token Usage",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "datasource": "Prometheus",
                    "targets": [
                        {
                            "expr": (
                                "sum by(type) "
                                "(llm_tokens_total{service=\"contract-risk-analyzer\"})"
                            ),
                            "legendFormat": "{{type}}",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "none",
                        }
                    },
                },
                {
                    "title": "Cache Hit Rate",
                    "type": "gauge",
                    "gridPos": {"h": 6, "w": 6, "x": 0, "y": 8},
                    "datasource": "Prometheus",
                    "targets": [
                        {
                            "expr": (
                                "llm_cache_hit_rate{service=\"contract-risk-analyzer\"}"
                            ),
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "min": 0,
                            "max": 1,
                        }
                    },
                },
                {
                    "title": "Request Latency P99",
                    "type": "timeseries",
                    "gridPos": {"h": 6, "w": 6, "x": 6, "y": 8},
                    "datasource": "Prometheus",
                    "targets": [
                        {
                            "expr": (
                                "llm_request_latency_p99{"
                                "service=\"contract-risk-analyzer\"}"
                            ),
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ms",
                        }
                    },
                },
            ],
        }

        return json.dumps(dashboard, indent=2)

    @staticmethod
    def save_dashboard(dashboard_json: str, path: str) -> None:
        """Save a dashboard JSON to file.

        Args:
            dashboard_json: Dashboard JSON string.
            path: Output file path.
        """
        with open(path, "w") as f:
            f.write(dashboard_json)
        logger.info("Dashboard saved to %s", path)
