"""Centralized AI cost estimation separate from provider execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass
class AICostEstimator:
    """Compute AI cost centrally from token usage and model rates."""
    default_rates: dict[str, dict[str, float]] | None = None

    def __post_init__(self):
        self.default_rates = self.default_rates or getattr(settings, "ai_cost_rates", {
            "gpt-4o": {"input": 0.0000025, "output": 0.00001},
            "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
            "gpt-4-turbo": {"input": 0.00001, "output": 0.00003},
        })

    def estimate(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = self.default_rates.get(model) or self.default_rates.get("gpt-4o", {})
        return (prompt_tokens * rates.get("input", 0.0)) + (completion_tokens * rates.get("output", 0.0))
