"""OpenTelemetry instrumentation setup with Prometheus metrics bridge."""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import settings


def setup_tracing(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing with OTLP export.

    In production, set OTEL_ENABLED=true and OTEL_EXPORTER_OTLP_ENDPOINT
    to your OpenTelemetry collector endpoint.

    In development, tracing is disabled by default but can be enabled
    via environment variable.
    """
    if not settings.otel_enabled:
        return

    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": "1.0.0",
        "deployment.environment": settings.environment,
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)

    # Instrument SQLAlchemy for DB query tracing
    try:
        from app.kernel.database.session import Base
        if hasattr(Base, 'metadata') and Base.metadata.bind:
            SQLAlchemyInstrumentor().instrument(engine=Base.metadata.bind)
    except Exception:
        pass
