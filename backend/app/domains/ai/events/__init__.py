"""AI domain events for event-driven architecture.

These events enable loose coupling between AI orchestration and
downstream consumers (audit, notifications, analytics, etc.).

Events:
- AIExecutionStarted — emitted when an AI execution begins
- AIExecutionCompleted — emitted when execution succeeds
- AIExecutionFailed — emitted when execution fails
- GuardrailViolationDetected — emitted when a guardrail is triggered
- RetrievalSnapshotCreated — emitted when a retrieval snapshot is frozen
- PromptVersionActivated — emitted when a prompt version is activated
- DriftDetected — emitted when replay detects significant drift
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class AIExecutionStarted:
    """Emitted when an AI execution begins."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "ai.execution.started"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    execution_id: str = ""
    tenant_id: str = ""
    operation_type: str = ""
    provider: str = ""
    model: str = ""
    upload_id: str | None = None
    contract_id: str | None = None
    user_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    request_chain_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIExecutionCompleted:
    """Emitted when an AI execution completes successfully."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "ai.execution.completed"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    execution_id: str = ""
    tenant_id: str = ""
    operation_type: str = ""
    provider: str = ""
    model: str = ""
    upload_id: str | None = None

    # Results
    risk_score: float = 0.0
    findings_count: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    confidence: float = 0.0
    validation_score: float = 1.0

    # Guardrails
    guardrail_violations_count: int = 0
    guardrail_rejected: bool = False

    # Traceability
    correlation_id: str | None = None
    trace_id: str | None = None
    snapshot_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIExecutionFailed:
    """Emitted when an AI execution fails."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "ai.execution.failed"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    execution_id: str = ""
    tenant_id: str = ""
    operation_type: str = ""
    provider: str = ""
    model: str = ""
    upload_id: str | None = None

    error_message: str = ""
    error_type: str = ""
    retry_count: int = 0
    timed_out: bool = False
    fallback_used: bool = False
    fallback_provider: str | None = None

    correlation_id: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailViolationDetected:
    """Emitted when a guardrail violation is detected."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "ai.guardrail.violation"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    execution_id: str = ""
    tenant_id: str = ""
    rule_id: str = ""
    severity: str = ""
    message: str = ""
    violation_type: str = ""  # "pre_execution" or "post_execution"

    correlation_id: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalSnapshotCreated:
    """Emitted when a retrieval snapshot is created."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "ai.retrieval.snapshot_created"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    snapshot_id: str = ""
    execution_id: str = ""
    tenant_id: str = ""
    upload_id: str | None = None
    chunks_count: int = 0
    embedding_model: str = ""
    snapshot_hash: str = ""

    correlation_id: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptVersionActivated:
    """Emitted when a new prompt version is activated."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "ai.prompt.version_activated"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    prompt_key: str = ""
    version: str = ""
    previous_version: str | None = None
    activated_by: str = ""
    change_notes: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftDetected:
    """Emitted when replay detects significant output drift."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "ai.replay.drift_detected"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    execution_id: str = ""
    original_run_id: str = ""
    replay_run_id: str = ""
    tenant_id: str = ""
    drift_score: float = 0.0
    drift_severity: str = "none"
    findings_overlap: float = 1.0
    risk_score_delta: float = 0.0

    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Event type mapping for routing ────────────────────────────────

AI_EVENT_TYPES = {
    "ai.execution.started": AIExecutionStarted,
    "ai.execution.completed": AIExecutionCompleted,
    "ai.execution.failed": AIExecutionFailed,
    "ai.guardrail.violation": GuardrailViolationDetected,
    "ai.retrieval.snapshot_created": RetrievalSnapshotCreated,
    "ai.prompt.version_activated": PromptVersionActivated,
    "ai.replay.drift_detected": DriftDetected,
}
