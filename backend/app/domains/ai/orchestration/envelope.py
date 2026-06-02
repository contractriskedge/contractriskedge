"""Immutable request envelope for AI execution boundary and traceability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.domains.ai.orchestration.plan import AIExecutionPlan


@dataclass
class AIRequestEnvelope:
    tenant_id: str
    user_id: Optional[str]
    contract_id: Optional[str]
    upload_id: Optional[str]
    operation_type: str
    execution_plan: AIExecutionPlan
    retrieval_context: dict[str, Any] = field(default_factory=dict)
    audit_context: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    execution_id: str = ""
    correlation_id: Optional[str] = None
    request_chain_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
