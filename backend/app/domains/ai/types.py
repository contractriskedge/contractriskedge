"""AI provider request/response types separated from provider implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMRequest:
    """Request contract for an LLM provider."""
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    response_format: Optional[dict] = None


@dataclass
class LLMResponse:
    """Response model returned by an LLM provider."""
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float = 0.0


@dataclass
class AIExecutionOutcome:
    """Execution result published by the orchestrator."""
    response: LLMResponse
    plan: "AIExecutionPlan" | None = None
    policy_decision: "AIPolicyDecision" | None = None
    guardrail_violations: list[dict[str, Any]] | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
