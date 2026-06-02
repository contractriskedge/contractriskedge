"""AI domain — orchestration, governance, replay, validation, telemetry, and evaluation.

NOTE: Sub-modules use lazy imports to avoid circular import deadlocks and
to prevent heavy SDK imports (e.g. openai) at package-load time.
"""

from __future__ import annotations

import typing as _t

if _t.TYPE_CHECKING:
    from app.domains.ai.orchestration import (
        AIExecutionOrchestrator,
        AIExecutionPlanner,
        AIExecutionPlan,
        AIRequestEnvelope,
        AICostEstimator,
    )
    from app.domains.ai.replay import ReplayAIExecutionService, ReplayComparison, ReplayResult
    from app.domains.ai.validation import LLMResponseValidator, ValidationResult
    from app.domains.ai.telemetry import AIExecutionMetrics, ExecutionMetrics, ai_execution_metrics
    from app.domains.ai.telemetry.tracing import AIExecutionTracer, get_tracer, trace_ai_execution
    from app.domains.ai.snapshots import RetrievalSnapshotService, RetrievalSnapshot
    from app.domains.ai.prompts import PromptRegistry, PromptTemplate, PromptStatus, prompt_registry
    from app.domains.ai.events import (
        AIExecutionStarted,
        AIExecutionCompleted,
        AIExecutionFailed,
        GuardrailViolationDetected,
        RetrievalSnapshotCreated,
        PromptVersionActivated,
        DriftDetected,
    )

__all__ = [
    # Orchestration
    "AIExecutionOrchestrator",
    "AIExecutionPlanner",
    "AIExecutionPlan",
    "AIRequestEnvelope",
    "AICostEstimator",
    # Replay
    "ReplayAIExecutionService",
    "ReplayComparison",
    "ReplayResult",
    # Validation
    "LLMResponseValidator",
    "ValidationResult",
    # Telemetry
    "AIExecutionMetrics",
    "ExecutionMetrics",
    "ai_execution_metrics",
    "AIExecutionTracer",
    "get_tracer",
    "trace_ai_execution",
    # Snapshots
    "RetrievalSnapshotService",
    "RetrievalSnapshot",
    # Prompts
    "PromptRegistry",
    "PromptTemplate",
    "PromptStatus",
    "prompt_registry",
    # Events
    "AIExecutionStarted",
    "AIExecutionCompleted",
    "AIExecutionFailed",
    "GuardrailViolationDetected",
    "RetrievalSnapshotCreated",
    "PromptVersionActivated",
    "DriftDetected",
]

# ── Lazy imports for runtime ──────────────────────────────────────

def __getattr__(name: str) -> _t.Any:
    """Lazy-load sub-module symbols only when accessed at runtime."""
    import importlib

    _LAZY_MAP: dict[str, str] = {
        "AIExecutionOrchestrator": "app.domains.ai.orchestration",
        "AIExecutionPlanner": "app.domains.ai.orchestration",
        "AIExecutionPlan": "app.domains.ai.orchestration",
        "AIRequestEnvelope": "app.domains.ai.orchestration",
        "AICostEstimator": "app.domains.ai.orchestration",
        "ReplayAIExecutionService": "app.domains.ai.replay",
        "ReplayComparison": "app.domains.ai.replay",
        "ReplayResult": "app.domains.ai.replay",
        "LLMResponseValidator": "app.domains.ai.validation",
        "ValidationResult": "app.domains.ai.validation",
        "AIExecutionMetrics": "app.domains.ai.telemetry",
        "ExecutionMetrics": "app.domains.ai.telemetry",
        "ai_execution_metrics": "app.domains.ai.telemetry",
        "AIExecutionTracer": "app.domains.ai.telemetry.tracing",
        "get_tracer": "app.domains.ai.telemetry.tracing",
        "trace_ai_execution": "app.domains.ai.telemetry.tracing",
        "RetrievalSnapshotService": "app.domains.ai.snapshots",
        "RetrievalSnapshot": "app.domains.ai.snapshots",
        "PromptRegistry": "app.domains.ai.prompts",
        "PromptTemplate": "app.domains.ai.prompts",
        "PromptStatus": "app.domains.ai.prompts",
        "prompt_registry": "app.domains.ai.prompts",
        "AIExecutionStarted": "app.domains.ai.events",
        "AIExecutionCompleted": "app.domains.ai.events",
        "AIExecutionFailed": "app.domains.ai.events",
        "GuardrailViolationDetected": "app.domains.ai.events",
        "RetrievalSnapshotCreated": "app.domains.ai.events",
        "PromptVersionActivated": "app.domains.ai.events",
        "DriftDetected": "app.domains.ai.events",
    }
    module_path = _LAZY_MAP.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_path)
    return getattr(module, name)
