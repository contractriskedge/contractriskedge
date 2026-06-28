"""Structured JSON logging with mandatory fields for production observability.

Every log entry includes:
  - timestamp (ISO 8601)
  - tenant_id
  - correlation_id
  - user_id
  - request_id
  - module
  - action
  - severity
  - duration_ms
  - outcome

Supports filtering by any field via log aggregation tools (Datadog, Grafana, etc.).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog

# ── Correlation ID Context ─────────────────────────────────────────
# Thread-local / contextvar for propagating correlation_id across async boundaries.

from contextvars import ContextVar

correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
tenant_id_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_correlation_id() -> Optional[str]:
    return correlation_id_ctx.get()


def set_correlation_id(cid: Optional[str] = None) -> str:
    if not cid:
        cid = str(uuid4())
    correlation_id_ctx.set(cid)
    return cid


def get_tenant_id() -> Optional[str]:
    return tenant_id_ctx.get()


def set_tenant_id(tid: Optional[str]) -> None:
    tenant_id_ctx.set(tid)


def get_user_id() -> Optional[str]:
    return user_id_ctx.get()


def set_user_id(uid: Optional[str]) -> None:
    user_id_ctx.set(uid)


def get_request_id() -> Optional[str]:
    return request_id_ctx.get()


def set_request_id(rid: Optional[str]) -> None:
    request_id_ctx.set(rid)


# ── Structured Log Record ──────────────────────────────────────────

class StructuredLogRecord:
    """A structured log entry with mandatory observability fields."""

    __slots__ = (
        "timestamp", "tenant_id", "correlation_id", "user_id",
        "request_id", "module", "action", "severity", "duration_ms",
        "outcome", "message", "extra",
    )

    def __init__(
        self,
        message: str,
        *,
        module: str = "",
        action: str = "",
        severity: str = "INFO",
        outcome: str = "",
        duration_ms: Optional[float] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra: Any,
    ) -> None:
        import datetime
        self.timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        self.message = message
        self.module = module or ""
        self.action = action or ""
        self.severity = severity.upper()
        self.outcome = outcome or ""
        self.duration_ms = duration_ms
        self.tenant_id = tenant_id or get_tenant_id() or ""
        self.correlation_id = correlation_id or get_correlation_id() or ""
        self.user_id = user_id or get_user_id() or ""
        self.request_id = request_id or get_request_id() or ""
        self.extra = extra

    def to_dict(self) -> dict[str, Any]:
        d = {
            "timestamp": self.timestamp,
            "severity": self.severity,
            "message": self.message,
            "module": self.module,
            "action": self.action,
            "outcome": self.outcome,
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
        }
        if self.duration_ms is not None:
            d["duration_ms"] = round(self.duration_ms, 2)
        if self.extra:
            # Filter out None values for cleaner output
            d["extra"] = {k: v for k, v in self.extra.items() if v is not None}
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


# ── Structured Logger ──────────────────────────────────────────────

class StructuredLogger:
    """Logger that emits structured JSON records.

    Usage:
        log = StructuredLogger(__name__)
        log.info("Contract reviewed", action="review.complete", outcome="approved",
                 duration_ms=1234, tenant_id="...", contract_id="...")
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def _log(
        self,
        severity: str,
        message: str,
        *,
        action: str = "",
        outcome: str = "",
        duration_ms: Optional[float] = None,
        **extra: Any,
    ) -> None:
        record = StructuredLogRecord(
            message,
            module=self.name,
            action=action,
            severity=severity,
            outcome=outcome,
            duration_ms=duration_ms,
            **extra,
        )
        line = record.to_json()
        if severity.upper() in ("ERROR", "CRITICAL"):
            sys.stderr.write(line + "\n")
            sys.stderr.flush()
        else:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()

    def info(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log("CRITICAL", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log("DEBUG", message, **kwargs)


# ── Factory ─────────────────────────────────────────────────────────

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger for the given module name."""
    return StructuredLogger(name)


# ── Integration with existing structlog setup ──────────────────────

def patch_structlog() -> None:
    """Patch structlog to include correlation_id, tenant_id, user_id in all log entries.

    Call once at application startup after setup_logging().
    """
    from structlog.stdlib import ProcessorFormatter

    # Add context vars as log fields
    def add_context_vars(logger: Any, method_name: str, event_dict: dict) -> dict:
        cid = get_correlation_id()
        if cid:
            event_dict["correlation_id"] = cid
        tid = get_tenant_id()
        if tid:
            event_dict["tenant_id"] = tid
        uid = get_user_id()
        if uid:
            event_dict["user_id"] = uid
        rid = get_request_id()
        if rid:
            event_dict["request_id"] = rid
        return event_dict

    # Reconfigure structlog with the new processor
    existing_processors = structlog.get_config().get("processors", [])
    # Insert after TimeStamper, before renderer
    insert_at = 0
    for i, p in enumerate(existing_processors):
        if hasattr(p, "__name__") and "TimeStamper" in p.__name__:
            insert_at = i + 1
            break

    new_processors = existing_processors[:insert_at] + [add_context_vars] + existing_processors[insert_at:]

    structlog.configure(
        processors=new_processors,
        wrapper_class=structlog.get_config().get("wrapper_class", structlog.stdlib.BoundLogger),
        context_class=structlog.get_config().get("context_class", dict),
        logger_factory=structlog.get_config().get("logger_factory", structlog.stdlib.LoggerFactory()),
        cache_logger_on_first_use=structlog.get_config().get("cache_logger_on_first_use", True),
    )
