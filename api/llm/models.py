"""Pydantic models for LLM requests, responses, and tracking.

Defines the data structures used throughout the LLM integration layer
for request/response handling, token accounting, and cost tracking.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    CLAUDE_SONNET_35 = "claude_sonnet_35"
    GPT4O = "gpt4o"
    DEEPSEEK_CHAT = "deepseek_chat"

    def __str__(self) -> str:
        return self.value


class RoleType(str, Enum):
    """Message role in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    def __str__(self) -> str:
        return self.value


class Message(BaseModel):
    """A single message in a conversation."""

    role: RoleType = Field(..., description="Message role")
    content: str = Field(..., description="Message content text")

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message content must not be empty")
        return stripped


class LLMRequest(BaseModel):
    """Request payload for an LLM completion."""

    messages: List[Message] = Field(
        ..., description="Conversation messages", min_length=1
    )
    temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=4096, ge=1, le=128_000, description="Maximum output tokens"
    )
    top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="Top-p sampling")
    stop_sequences: List[str] = Field(
        default_factory=list, description="Stop sequences"
    )
    stream: bool = Field(default=False, description="Whether to stream the response")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for tracking")
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    cache_key: Optional[str] = Field(
        None, description="Custom cache key for prompt caching"
    )
    skip_cache: bool = Field(
        default=False, description="Skip prompt cache lookup"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[Message]) -> List[Message]:
        if not v:
            raise ValueError("At least one message is required")
        return v


class TokenUsage(BaseModel):
    """Token usage statistics for an LLM request."""

    prompt_tokens: int = Field(..., ge=0, description="Tokens in the prompt")
    completion_tokens: int = Field(..., ge=0, description="Tokens in the completion")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    cache_hit_tokens: int = Field(
        default=0, ge=0, description="Tokens served from cache"
    )
    cache_creation_input_tokens: int = Field(
        default=0, ge=0, description="Tokens used to create cache entry"
    )

    @field_validator("total_tokens")
    @classmethod
    def total_matches_sum(cls, v: int, info: Any) -> int:
        data = info.data
        expected = data.get("prompt_tokens", 0) + data.get("completion_tokens", 0)
        if v != expected:
            raise ValueError(
                f"total_tokens ({v}) must equal prompt_tokens + completion_tokens ({expected})"
            )
        return v


class LLMResponse(BaseModel):
    """Response from an LLM completion."""

    content: str = Field(..., description="Generated response content")
    provider: ProviderType = Field(..., description="Provider that generated this")
    model_name: str = Field(..., description="Specific model name used")
    token_usage: TokenUsage = Field(..., description="Token usage stats")
    latency_ms: float = Field(..., ge=0, description="Request latency in milliseconds")
    finish_reason: str = Field(
        default="stop", description="Reason for completion (stop, length, etc.)"
    )
    request_id: str = Field(..., description="Unique request identifier")
    cached: bool = Field(default=False, description="Whether response was from cache")
    cache_key_used: Optional[str] = Field(
        None, description="Cache key if cached response"
    )


class CostRecord(BaseModel):
    """Cost tracking record for an LLM request."""

    request_id: str = Field(..., description="Request identifier")
    provider: ProviderType = Field(..., description="Provider used")
    model_name: str = Field(..., description="Model name")
    prompt_tokens: int = Field(..., ge=0, description="Prompt token count")
    completion_tokens: int = Field(..., ge=0, description="Completion token count")
    total_tokens: int = Field(..., ge=0, description="Total token count")
    cost_usd: float = Field(..., ge=0.0, description="Cost in USD")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the request occurred"
    )
    duration_ms: float = Field(..., ge=0, description="Request duration")
    cached: bool = Field(default=False, description="Whether cached response")


class StreamingEvent(BaseModel):
    """A single streaming event from an LLM response."""

    event_type: str = Field(
        ..., description="Event type (content, done, error)"
    )
    content: Optional[str] = Field(None, description="Content delta")
    finish_reason: Optional[str] = Field(None, description="Finish reason if done")
    error: Optional[str] = Field(None, description="Error message if error")
    request_id: str = Field(..., description="Associated request ID")
    provider: ProviderType = Field(..., description="Provider streaming this event")
