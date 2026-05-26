"""Structured security event logging.

All security events are logged in a consistent JSON format suitable
for SIEM ingestion. Every event includes: timestamp, event type,
severity, actor, tenant context, request context, and details.
"""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """Canonical security event types."""
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    TOKEN_INVALID = "token.invalid"
    TOKEN_EXPIRED = "token.expired"
    TOKEN_REVOKED = "token.revoked"
    PERMISSION_DENIED = "permission.denied"
    TENANT_ACCESS_DENIED = "tenant.access_denied"
    RLS_CONTEXT_MISSING = "rls.context_missing"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    SUSPICIOUS_REQUEST = "request.suspicious"
    API_KEY_INVALID = "api_key.invalid"
    API_KEY_CROSS_TENANT = "api_key.cross_tenant"
    ADMIN_OVERRIDE = "admin.tenant_override"
    CROSS_TENANT_ATTEMPT = "cross_tenant.attempt"
    AUDIT_TAMPERING = "audit.tampering_detected"


class SecurityEventSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def log_security_event(
    event_type: SecurityEventType,
    severity: SecurityEventSeverity = SecurityEventSeverity.WARNING,
    message: str = "",
    actor_id: str | None = None,
    tenant_id: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
) -> None:
    """Log a structured security event.

    All events are logged at WARNING level or higher to ensure they
    are captured by log aggregation and alerting systems.

    Output format (production JSON):
    {
        "timestamp": "2026-05-15T12:00:00.000Z",
        "security_event": "auth.failure",
        "severity": "warning",
        "message": "Invalid token signature",
        "actor_id": "auth0|user123",
        "tenant_id": "tenant-uuid",
        "request_id": "req-abc-123",
        "ip_address": "192.168.1.1",
        "details": {"reason": "signature_mismatch"}
    }
    """
    extra = {
        "security_event": event_type.value,
        "event_severity": severity.value,
    }
    if actor_id:
        extra["actor_id"] = actor_id
    if tenant_id:
        extra["tenant_id"] = tenant_id
    if request_id:
        extra["request_id"] = request_id
    if ip_address:
        extra["ip_address"] = ip_address
    if details:
        extra["details"] = details

    log_method = getattr(logger, severity.value, logger.warning)
    log_method(f"SECURITY: {message}", extra=extra)
