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

        # ── Workflow Instance Metrics ──
        self.workflow_instances_started = Counter(
            "workflow_instances_started_total",
            "Total workflow instances started",
            ["workflow_type"],
        )
        self.workflow_instances_completed = Counter(
            "workflow_instances_completed_total",
            "Total workflow instances completed",
            ["workflow_type", "outcome"],  # approved, rejected, escalated
        )
        self.workflow_instances_rejected = Counter(
            "workflow_instances_rejected_total",
            "Total workflow instances rejected",
            ["workflow_type"],
        )
        self.workflow_instances_escalated = Counter(
            "workflow_instances_escalated_total",
            "Total workflow instances escalated",
            ["workflow_type"],
        )
        self.workflow_duration_seconds = Histogram(
            "workflow_duration_seconds",
            "Workflow instance duration in seconds",
            ["workflow_type", "outcome"],
            buckets=(10, 60, 300, 900, 3600, 14400, 86400, 259200),
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

        # ── WebSocket / Realtime Metrics ──
        self.ws_connections_total = Counter(
            "ws_connections_total",
            "Total WebSocket connections by tenant",
            ["tenant_id"],
        )
        self.ws_disconnections_total = Counter(
            "ws_disconnections_total",
            "Total WebSocket disconnections by tenant",
            ["tenant_id"],
        )
        self.ws_active_connections = Gauge(
            "ws_active_connections",
            "Current active WebSocket connections",
            ["tenant_id"],
        )
        self.ws_messages_sent_total = Counter(
            "ws_messages_sent_total",
            "Total WebSocket messages sent by tenant and event type",
            ["tenant_id", "event_type"],
        )
        self.ws_messages_delivered_total = Counter(
            "ws_messages_delivered_total",
            "Total WebSocket messages delivered (ACK'd) by tenant",
            ["tenant_id"],
        )
        self.ws_delivery_failures_total = Counter(
            "ws_delivery_failures_total",
            "Total WebSocket delivery failures by tenant and reason",
            ["tenant_id", "reason"],
        )
        self.ws_reconnect_events_total = Counter(
            "ws_reconnect_events_total",
            "Total WebSocket reconnection events by tenant",
            ["tenant_id"],
        )
        self.ws_replay_events_total = Counter(
            "ws_replay_events_total",
            "Total replay events sent by tenant",
            ["tenant_id"],
        )
        self.ws_delivery_latency_seconds = Histogram(
            "ws_delivery_latency_seconds",
            "WebSocket event delivery latency (create → client receipt)",
            ["tenant_id"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )

        # ── Event Outbox / Diagnostics Metrics ──
        self.outbox_events_created_total = Counter(
            "outbox_events_created_total",
            "Total outbox events created by tenant and event type",
            ["tenant_id", "event_type"],
        )
        self.outbox_events_dead_letter_total = Counter(
            "outbox_events_dead_letter_total",
            "Total outbox events moved to dead-letter by tenant",
            ["tenant_id"],
        )
        self.outbox_events_replayed_total = Counter(
            "outbox_events_replayed_total",
            "Total outbox events replayed from dead-letter by tenant",
            ["tenant_id"],
        )
        self.outbox_queue_depth = Gauge(
            "outbox_queue_depth",
            "Current pending outbox event count by tenant",
            ["tenant_id"],
        )

        # ── Stale Event / Idempotency Metrics ──
        self.stale_events_rejected_total = Counter(
            "stale_events_rejected_total",
            "Total stale events rejected by review_id and reason",
            ["reason"],
        )
        self.duplicate_invalidations_suppressed_total = Counter(
            "duplicate_invalidations_suppressed_total",
            "Total duplicate cache invalidations suppressed by debounce",
            ["resource_type"],
        )
        self.reconnect_storm_detections_total = Counter(
            "reconnect_storm_detections_total",
            "Total reconnect storm detections by tenant",
            ["tenant_id"],
        )

        # ── Worker Heartbeat Metrics ──
        self.worker_heartbeats_total = Counter(
            "worker_heartbeats_total",
            "Total worker heartbeats received by worker and queue",
            ["worker_id", "queue"],
        )
        self.worker_stuck_jobs_total = Counter(
            "worker_stuck_jobs_total",
            "Total stuck jobs detected by queue",
            ["queue"],
        )
        self.active_workers = Gauge(
            "active_workers",
            "Currently active workers by queue",
            ["queue"],
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
