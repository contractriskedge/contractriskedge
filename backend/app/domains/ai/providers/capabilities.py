"""Provider capability and health model definitions for AI orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProviderCapabilities:
    provider_name: str
    supports_json_mode: bool = False
    supports_tool_calling: bool = False
    supports_streaming: bool = False
    supports_vision: bool = False
    supports_retrieval: bool = False
    max_context_tokens: int = 4096
    max_response_tokens: int = 1024
    supports_reasoning_depth: bool = True


@dataclass
class ProviderHealth:
    provider_name: str
    last_latency_ms: int = 0
    last_cost_usd: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    circuit_breaker_open: bool = False
    circuit_breaker_since: datetime | None = None
    updated_at: datetime | None = None

    @property
    def total_attempts(self) -> int:
        return self.success_count + self.failure_count

    @property
    def failure_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.failure_count / self.total_attempts

    @property
    def health_score(self) -> float:
        score = 1.0 - self.failure_rate
        if self.circuit_breaker_open:
            score *= 0.25
        return max(0.0, min(score, 1.0))

    def record_success(self, latency_ms: int, cost_usd: float) -> None:
        from datetime import datetime

        self.success_count += 1
        self.last_latency_ms = latency_ms
        self.last_cost_usd = cost_usd
        self.updated_at = datetime.utcnow()
        if self.circuit_breaker_open and self.failure_rate < 0.2:
            self.circuit_breaker_open = False
            self.circuit_breaker_since = None

    def record_failure(self, latency_ms: int, cost_usd: float, timeout: bool = False) -> None:
        from datetime import datetime

        self.failure_count += 1
        self.last_latency_ms = latency_ms
        self.last_cost_usd = cost_usd
        if timeout:
            self.timeout_count += 1
        self.updated_at = datetime.utcnow()
        if self.failure_rate >= 0.3:
            self.circuit_breaker_open = True
            self.circuit_breaker_since = datetime.utcnow()

    def is_available(self) -> bool:
        return not self.circuit_breaker_open and self.health_score > 0.3
