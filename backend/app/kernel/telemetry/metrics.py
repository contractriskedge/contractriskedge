"""Application metrics — Prometheus endpoint and business metric instruments.

Provides:
  - /metrics endpoint for Prometheus scraping
  - Business-level metric instruments (counters, histograms, gauges)
  - Request rate, error rate, latency tracking
  - Ingestion, AI, and workflow-specific metrics

Usage:
    from app.kernel.telemetry.metrics import metrics

    # Increment a counter
    metrics.uploads_total.labels(status="success").inc()

    # Observe a duration
    metrics.ai_analysis_duration.labels(model="gpt-4o").observe(seconds)

    # Set a gauge
    metrics.active_reviews.labels(status="in_review").set(42)
"""

from __future__ import annotations

import time
from typing import Optional

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, generate_latest,
    CONTENT_TYPE_LATEST, REGISTRY,
)
from starlette.responses import Response
from starlette.requests import Request
from starlette.routing import Route

# ── Application Metrics ────────────────────────────────────────────


class AppMetrics:
    """Central registry of all application metrics."""

    def __init__(self) -> None:
        # ── HTTP / API Metrics ──
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests by method, endpoint, and status",
            ["method", "endpoint", "status"],
        )
        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint", "status"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        )
        self.http_requests_in_flight = Gauge(
            "http_requests_in_flight",
            "Current number of in-flight HTTP requests",
            ["method"],
        )

        # ── Ingestion Metrics ──
        self.uploads_total = Counter(
            "uploads_total",
            "Total file uploads by status",
            ["status"],  # success, failed, duplicate, quarantined
        )
        self.upload_duration_seconds = Histogram(
            "upload_duration_seconds",
            "End-to-end upload ingestion duration",
            ["status"],
            buckets=(5, 15, 30, 60, 120, 300, 600),
        )
        self.ingestion_state_total = Counter(
            "ingestion_state_total",
            "Ingestion state transitions",
            ["from_state", "to_state"],
        )
        self.ocr_duration_seconds = Histogram(
            "ocr_duration_seconds",
            "OCR processing duration",
            buckets=(1, 5, 10, 30, 60, 120),
        )
        self.ocr_failures_total = Counter(
            "ocr_failures_total",
            "Total OCR failures by reason",
            ["reason"],
        )

        # ── Embedding Metrics ──
        self.embedding_duration_seconds = Histogram(
            "embedding_duration_seconds",
            "Embedding generation duration",
            buckets=(0.5, 1, 2, 5, 10, 30),
        )
        self.embedding_tokens_total = Counter(
            "embedding_tokens_total",
            "Total tokens embedded",
            ["model"],
        )
        self.embedding_failures_total = Counter(
            "embedding_failures_total",
            "Total embedding failures by reason",
            ["reason"],
        )

        # ── AI Analysis Metrics ──
        self.ai_analysis_total = Counter(
            "ai_analysis_total",
            "Total AI analysis runs by status",
            ["status", "model"],  # completed, failed, timeout
        )
        self.ai_analysis_duration_seconds = Histogram(
            "ai_analysis_duration_seconds",
            "AI analysis duration by model",
            ["model"],
            buckets=(5, 15, 30, 60, 120, 300, 600),
        )
        self.ai_token_usage_total = Counter(
            "ai_token_usage_total",
            "Total tokens consumed by AI analysis",
            ["model", "type"],  # prompt, completion
        )
        self.ai_cost_usd_total = Counter(
            "ai_cost_usd_total",
            "Total AI cost in USD",
            ["model"],
        )
        self.ai_retries_total = Counter(
            "ai_retries_total",
            "Total AI retry attempts by reason",
            ["reason"],
        )
        self.ai_failures_total = Counter(
            "ai_failures_total",
            "Total AI failures by type",
            ["failure_type"],
        )

        # ── Queue / Worker Metrics ──
        self.queue_task_total = Counter(
            "queue_task_total",
            "Total Celery tasks by queue and status",
            ["queue", "task_name", "status"],
        )
        self.queue_wait_duration_seconds = Histogram(
            "queue_wait_duration_seconds",
            "Time tasks wait in queue before processing",
            ["queue"],
            buckets=(0.1, 0.5, 1, 5, 10, 30, 60),
        )
        self.queue_task_duration_seconds = Histogram(
            "queue_task_duration_seconds",
            "Task execution duration",
            ["queue", "task_name"],
            buckets=(1, 5, 10, 30, 60, 120, 300, 600),
        )

        # ── Review / Workflow Metrics ──
        self.reviews_total = Counter(
            "reviews_total",
            "Total reviews created by status",
            ["status"],
        )
        self.review_duration_hours = Histogram(
            "review_duration_hours",
            "Review lifecycle duration in hours",
            ["final_status"],
            buckets=(1, 6, 12, 24, 48, 72, 168),
        )
        self.findings_total = Counter(
            "findings_total",
            "Total findings by severity and resolution",
            ["severity", "resolution"],
        )
        self.sla_breaches_total = Counter(
            "sla_breaches_total",
            "Total SLA breaches by priority",
            ["priority"],
        )

        # ── Search Metrics ──
        self.search_queries_total = Counter(
            "search_queries_total",
            "Total search queries by strategy",
            ["strategy"],
        )
        self.search_duration_seconds = Histogram(
            "search_duration_seconds",
            "Search query duration",
            ["strategy"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )
        self.search_cache_hit_total = Counter(
            "search_cache_hit_total",
            "Search cache hits vs misses",
            ["result"],
        )

        # ── Business Gauges ──
        self.active_uploads = Gauge(
            "active_uploads",
            "Currently active uploads by state",
            ["state"],
        )
        self.active_ai_runs = Gauge(
            "active_ai_runs",
            "Currently active AI analysis runs",
            ["status"],
        )
        self.active_reviews = Gauge(
            "active_reviews",
            "Currently active reviews by status",
            ["status"],
        )
        self.queue_depth = Gauge(
            "queue_depth",
            "Current queue depth by queue name",
            ["queue"],
        )
        self.db_pool_stats = Gauge(
            "db_pool_stats",
            "Database connection pool statistics",
            ["stat"],  # size, checked_in, checked_out, overflow
        )


# ── Singleton ──────────────────────────────────────────────────────

metrics = AppMetrics()


# ── Prometheus Metrics Endpoint ────────────────────────────────────

async def metrics_endpoint(request: Request) -> Response:
    """GET /metrics — Prometheus scrape endpoint.

    Returns all registered metrics in Prometheus text format.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    data = generate_latest(REGISTRY)
    return Response(
        content=data,
        media_type=CONTENT_TYPE_LATEST,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


# ── Middleware for automatic HTTP metrics ──────────────────────────

class MetricsMiddleware:
    """Starlette middleware that records HTTP request metrics.

    Automatically tracks:
      - Request count by method, endpoint, status
      - Request duration histogram
      - In-flight request gauge
    """

    async def __call__(self, request: Request, call_next):
        # Skip metrics endpoint itself to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        # Normalize path for high-cardinality endpoints
        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            path = route.path

        metrics.http_requests_in_flight.labels(method=method).inc()
        start = time.monotonic()

        try:
            response = await call_next(request)
            status = str(response.status_code)
            duration = time.monotonic() - start

            metrics.http_requests_total.labels(
                method=method, endpoint=path, status=status,
            ).inc()
            metrics.http_request_duration_seconds.labels(
                method=method, endpoint=path, status=status,
            ).observe(duration)

            return response
        except Exception:
            status = "500"
            duration = time.monotonic() - start
            metrics.http_requests_total.labels(
                method=method, endpoint=path, status=status,
            ).inc()
            metrics.http_request_duration_seconds.labels(
                method=method, endpoint=path, status=status,
            ).observe(duration)
            raise
        finally:
            metrics.http_requests_in_flight.labels(method=method).dec()
