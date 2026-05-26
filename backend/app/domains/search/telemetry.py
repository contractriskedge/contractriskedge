"""Search telemetry — OpenTelemetry instrumentation for retrieval operations."""

from __future__ import annotations

import time
import logging
from contextlib import contextmanager
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)


class SearchTelemetry:
    """OpenTelemetry instrumentation for search and retrieval operations."""

    @staticmethod
    def trace_search(query: str, strategy: str, tenant_id: str):
        """Create a tracing decorator/context for search operations."""
        span = tracer.start_span(
            "search.execute",
            attributes={
                "search.query": query[:200],
                "search.strategy": strategy,
                "search.tenant_id": tenant_id,
            },
        )
        return span

    @staticmethod
    def trace_retrieval_stage(stage: str):
        """Create a span for a specific retrieval stage (vector, BM25, fusion)."""
        span = tracer.start_span(f"search.{stage}")
        return span

    @staticmethod
    def set_span_attributes(span: Span, attributes: dict):
        for key, value in attributes.items():
            span.set_attribute(key, value)

    @staticmethod
    def end_span(span: Span, error: Optional[str] = None):
        if error:
            span.set_status(Status(StatusCode.ERROR, error))
        else:
            span.set_status(Status(StatusCode.OK))
        span.end()


class RetrievalMetrics:
    """In-process retrieval metrics counters."""

    def __init__(self):
        self.total_searches = 0
        self.total_latency_ms = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.zero_result_queries = 0

    def record_search(self, latency_ms: int, result_count: int, from_cache: bool = False):
        self.total_searches += 1
        self.total_latency_ms += latency_ms
        if from_cache:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        if result_count == 0:
            self.zero_result_queries += 1

    @property
    def avg_latency_ms(self) -> float:
        if self.total_searches == 0:
            return 0.0
        return self.total_latency_ms / self.total_searches

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total


# Global metrics instance
search_metrics = RetrievalMetrics()
