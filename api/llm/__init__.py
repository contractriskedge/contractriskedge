"""LLM integration module for AI Contract Risk Analyzer.

Provides multi-provider LLM client with Claude 3.5 Sonnet (primary)
and GPT-4o (fallback), streaming support, cost tracking, prompt caching,
and OpenTelemetry monitoring.
"""

from __future__ import annotations

from .client import LLMClient
from .provider import LLMProvider
from .models import (
    LLMRequest,
    LLMResponse,
    TokenUsage,
    CostRecord,
    ProviderType,
    StreamingEvent,
)
from .cost_tracker import CostTracker
from .cache import PromptCache
from .monitoring import LLMMonitoring

__all__ = [
    "LLMClient",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "TokenUsage",
    "CostRecord",
    "ProviderType",
    "StreamingEvent",
    "CostTracker",
    "PromptCache",
    "LLMMonitoring",
]
