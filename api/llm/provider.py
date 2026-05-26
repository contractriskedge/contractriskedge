"""Abstract LLM provider with Claude 3.5 Sonnet and GPT-4o implementations.

Defines the base provider interface and concrete implementations for
Anthropic's Claude 3.5 Sonnet (primary) and OpenAI's GPT-4o (fallback).
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator

import httpx

from .models import (
    LLMRequest,
    LLMResponse,
    Message,
    ProviderType,
    RoleType,
    TokenUsage,
    StreamingEvent,
)

logger = logging.getLogger(__name__)

# ── Pricing per 1K tokens (USD) ──────────────────────────────────────────────
CLAUDE_SONNET_35_PRICES: Dict[str, float] = {
    "input": 0.003,  # $3 per 1M input tokens
    "output": 0.015,  # $15 per 1M output tokens
    "cache_write": 0.00375,  # $3.75 per 1M cache write tokens
    "cache_read": 0.00030,  # $0.30 per 1M cache read tokens
}

GPT4O_PRICES: Dict[str, float] = {
    "input": 0.0025,  # $2.50 per 1M input tokens
    "output": 0.010,  # $10 per 1M output tokens
}

DEEPSEEK_CHAT_PRICES: Dict[str, float] = {
    "input": 0.00027,  # $0.27 per 1M input tokens (cache hit)
    "input_miss": 0.00110,  # $1.10 per 1M input tokens (cache miss)
    "output": 0.00440,  # $4.40 per 1M output tokens
}


def calculate_cost(
    provider: ProviderType,
    prompt_tokens: int,
    completion_tokens: int,
    cache_hit_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """Calculate the cost of an LLM request in USD.

    Args:
        provider: The LLM provider used.
        prompt_tokens: Number of prompt tokens.
        completion_tokens: Number of completion tokens.
        cache_hit_tokens: Number of tokens served from cache.
        cache_creation_tokens: Number of tokens used for cache creation.

    Returns:
        Total cost in USD.
    """
    if provider == ProviderType.CLAUDE_SONNET_35:
        pricing = CLAUDE_SONNET_35_PRICES
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        cache_write_cost = (cache_creation_tokens / 1000) * pricing["cache_write"]
        cache_read_credit = (cache_hit_tokens / 1000) * (
            pricing["input"] - pricing["cache_read"]
        )
        return round(input_cost + output_cost + cache_write_cost - cache_read_credit, 6)
    elif provider == ProviderType.GPT4O:
        pricing = GPT4O_PRICES
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    elif provider == ProviderType.DEEPSEEK_CHAT:
        pricing = DEEPSEEK_CHAT_PRICES
        input_cost = (prompt_tokens / 1000) * pricing["input_miss"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    return 0.0


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Defines the interface that all provider implementations must follow,
    including completion, streaming, and health check methods.
    """

    def __init__(self, api_key: str, model_name: str, base_url: Optional[str] = None) -> None:
        """Initialize the provider.

        Args:
            api_key: API key for authentication.
            model_name: The model identifier to use.
            base_url: Optional custom base URL for the API.
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type enum value."""
        ...

    @abstractmethod
    def _build_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """Build the provider-specific request payload.

        Args:
            request: The standardized LLM request.

        Returns:
            Provider-specific request body dictionary.
        """
        ...

    @abstractmethod
    def _parse_response(
        self, response_data: Dict[str, Any], request: LLMRequest, latency_ms: float
    ) -> LLMResponse:
        """Parse provider-specific response into standardized format.

        Args:
            response_data: Raw response data from the provider.
            request: The original request.
            latency_ms: Request latency in milliseconds.

        Returns:
            Standardized LLM response.
        """
        ...

    @abstractmethod
    def _parse_streaming_chunk(
        self, chunk: bytes, request_id: str
    ) -> Optional[StreamingEvent]:
        """Parse a streaming chunk from the provider.

        Args:
            chunk: Raw bytes chunk from the stream.
            request_id: The request identifier.

        Returns:
            A streaming event or None if chunk is incomplete.
        """
        ...

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            Configured async HTTP client.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(120.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request to the provider.

        Args:
            request: The LLM request to send.

        Returns:
            The LLM response.

        Raises:
            httpx.HTTPError: If the API request fails.
            ValueError: If the response cannot be parsed.
        """
        client = await self._get_client()
        payload = self._build_request_payload(request)
        start_time = time.monotonic()

        logger.debug(
            "Sending request to %s model=%s tokens_est=%d",
            self.provider_type.value,
            self.model_name,
            sum(len(m.content) for m in request.messages) // 4,
        )

        response = await client.post(
            self._get_endpoint(),
            json=payload,
            headers=self._get_headers(),
        )
        response.raise_for_status()

        latency_ms = (time.monotonic() - start_time) * 1000
        data = response.json()

        return self._parse_response(data, request, latency_ms)

    async def complete_stream(
        self, request: LLMRequest
    ) -> AsyncGenerator[StreamingEvent, None]:
        """Stream a completion response from the provider.

        Args:
            request: The LLM request with stream=True.

        Yields:
            Streaming events as they arrive.
        """
        client = await self._get_client()
        payload = self._build_request_payload(request)

        async with client.stream(
            "POST",
            self._get_endpoint(),
            json=payload,
            headers=self._get_headers(),
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                event = self._parse_streaming_chunk(
                    chunk, request.request_id or "unknown"
                )
                if event is not None:
                    yield event

    @abstractmethod
    def _get_endpoint(self) -> str:
        """Get the API endpoint path.

        Returns:
            The endpoint path for completions.
        """
        ...

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    async def health_check(self) -> bool:
        """Check if the provider API is reachable.

        Returns:
            True if the provider is healthy, False otherwise.
        """
        try:
            client = await self._get_client()
            response = await client.get(self._get_health_endpoint(), timeout=5.0)
            return response.status_code < 500
        except Exception as exc:
            logger.warning("Health check failed for %s: %s", self.provider_type.value, exc)
            return False

    @abstractmethod
    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint.

        Returns:
            Health check URL path.
        """
        ...

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert standardized messages to provider format.

        Args:
            messages: List of standardized messages.

        Returns:
            List of provider-format message dicts.
        """
        return [{"role": m.role.value, "content": m.content} for m in messages]


class ClaudeSonnetProvider(LLMProvider):
    """Anthropic Claude 3.5 Sonnet provider implementation."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        """Initialize the Claude Sonnet provider.

        Args:
            api_key: Anthropic API key.
            model_name: Claude model identifier.
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url="https://api.anthropic.com/v1",
        )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CLAUDE_SONNET_35

    def _get_endpoint(self) -> str:
        return "/messages"

    def _get_health_endpoint(self) -> str:
        return "/messages"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
        }

    def _build_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        system_messages = [
            m for m in request.messages if m.role == RoleType.SYSTEM
        ]
        non_system_messages = [
            m for m in request.messages if m.role != RoleType.SYSTEM
        ]

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "messages": [
                {"role": m.role.value, "content": m.content}
                for m in non_system_messages
            ],
        }

        if system_messages:
            system_content = "\n\n".join(m.content for m in system_messages)
            # Enable prompt caching on long system prompts
            if len(system_content) > 2000:
                payload["system"] = [
                    {
                        "type": "text",
                        "text": system_content,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                payload["system"] = system_content

        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences

        if request.stream:
            payload["stream"] = True

        return payload

    def _parse_response(
        self, response_data: Dict[str, Any], request: LLMRequest, latency_ms: float
    ) -> LLMResponse:
        content_blocks = response_data.get("content", [])
        full_content = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )

        usage = response_data.get("usage", {})
        token_usage = TokenUsage(
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            cache_hit_tokens=usage.get("cache_read_input_tokens", 0),
            cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
        )

        return LLMResponse(
            content=full_content,
            provider=ProviderType.CLAUDE_SONNET_35,
            model_name=self.model_name,
            token_usage=token_usage,
            latency_ms=latency_ms,
            finish_reason=response_data.get("stop_reason", "stop"),
            request_id=request.request_id or response_data.get("id", "unknown"),
        )

    def _parse_streaming_chunk(
        self, chunk: bytes, request_id: str
    ) -> Optional[StreamingEvent]:
        chunk_str = chunk.decode("utf-8").strip()
        if not chunk_str or not chunk_str.startswith("data: "):
            return None

        import json

        data_str = chunk_str[6:]
        if data_str == "[DONE]":
            return StreamingEvent(
                event_type="done",
                finish_reason="stop",
                request_id=request_id,
                provider=ProviderType.CLAUDE_SONNET_35,
            )

        try:
            data = json.loads(data_str)
            if data.get("type") == "content_block_delta":
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    return StreamingEvent(
                        event_type="content",
                        content=delta.get("text", ""),
                        request_id=request_id,
                        provider=ProviderType.CLAUDE_SONNET_35,
                    )
            elif data.get("type") == "message_stop":
                return StreamingEvent(
                    event_type="done",
                    finish_reason="stop",
                    request_id=request_id,
                    provider=ProviderType.CLAUDE_SONNET_35,
                )
        except (json.JSONDecodeError, KeyError):
            pass

        return None


class DeepSeekProvider(LLMProvider):
    """DeepSeek Chat provider implementation (OpenAI-compatible).

    Uses DeepSeek's OpenAI-compatible API, so it reuses the same
    request/response format as GPT-4o but with a different base URL.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
    ) -> None:
        """Initialize the DeepSeek provider.

        Args:
            api_key: DeepSeek API key.
            model_name: DeepSeek model identifier (default: deepseek-chat).
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url="https://api.deepseek.com",
        )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.DEEPSEEK_CHAT

    def _get_endpoint(self) -> str:
        return "/chat/completions"

    def _get_health_endpoint(self) -> str:
        return "/models"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _build_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": self.convert_messages(request.messages),
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        if request.stop_sequences:
            payload["stop"] = request.stop_sequences

        if request.stream:
            payload["stream"] = True

        return payload

    def _parse_response(
        self, response_data: Dict[str, Any], request: LLMRequest, latency_ms: float
    ) -> LLMResponse:
        choice = response_data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        usage = response_data.get("usage", {})
        token_usage = TokenUsage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

        return LLMResponse(
            content=content,
            provider=ProviderType.DEEPSEEK_CHAT,
            model_name=self.model_name,
            token_usage=token_usage,
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason", "stop"),
            request_id=request.request_id or response_data.get("id", "unknown"),
        )

    def _parse_streaming_chunk(
        self, chunk: bytes, request_id: str
    ) -> Optional[StreamingEvent]:
        chunk_str = chunk.decode("utf-8").strip()
        if not chunk_str or not chunk_str.startswith("data: "):
            return None

        import json

        data_str = chunk_str[6:]
        if data_str == "[DONE]":
            return StreamingEvent(
                event_type="done",
                finish_reason="stop",
                request_id=request_id,
                provider=ProviderType.DEEPSEEK_CHAT,
            )

        try:
            data = json.loads(data_str)
            choices = data.get("choices", [])
            if not choices:
                return None

            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                return StreamingEvent(
                    event_type="content",
                    content=content,
                    request_id=request_id,
                    provider=ProviderType.DEEPSEEK_CHAT,
                )

            finish_reason = choices[0].get("finish_reason")
            if finish_reason:
                return StreamingEvent(
                    event_type="done",
                    finish_reason=finish_reason,
                    request_id=request_id,
                    provider=ProviderType.DEEPSEEK_CHAT,
                )
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

        return None


class GPT4oProvider(LLMProvider):
    """OpenAI GPT-4o provider implementation (fallback)."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-2024-08-06",
    ) -> None:
        """Initialize the GPT-4o provider.

        Args:
            api_key: OpenAI API key.
            model_name: GPT-4o model identifier.
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url="https://api.openai.com/v1",
        )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GPT4O

    def _get_endpoint(self) -> str:
        return "/chat/completions"

    def _get_health_endpoint(self) -> str:
        return "/models"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _build_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": self.convert_messages(request.messages),
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        if request.stop_sequences:
            payload["stop"] = request.stop_sequences

        if request.stream:
            payload["stream"] = True

        return payload

    def _parse_response(
        self, response_data: Dict[str, Any], request: LLMRequest, latency_ms: float
    ) -> LLMResponse:
        choice = response_data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        usage = response_data.get("usage", {})
        token_usage = TokenUsage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

        return LLMResponse(
            content=content,
            provider=ProviderType.GPT4O,
            model_name=self.model_name,
            token_usage=token_usage,
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason", "stop"),
            request_id=request.request_id or response_data.get("id", "unknown"),
        )

    def _parse_streaming_chunk(
        self, chunk: bytes, request_id: str
    ) -> Optional[StreamingEvent]:
        chunk_str = chunk.decode("utf-8").strip()
        if not chunk_str or not chunk_str.startswith("data: "):
            return None

        import json

        data_str = chunk_str[6:]
        if data_str == "[DONE]":
            return StreamingEvent(
                event_type="done",
                finish_reason="stop",
                request_id=request_id,
                provider=ProviderType.GPT4O,
            )

        try:
            data = json.loads(data_str)
            choices = data.get("choices", [])
            if not choices:
                return None

            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                return StreamingEvent(
                    event_type="content",
                    content=content,
                    request_id=request_id,
                    provider=ProviderType.GPT4O,
                )

            finish_reason = choices[0].get("finish_reason")
            if finish_reason:
                return StreamingEvent(
                    event_type="done",
                    finish_reason=finish_reason,
                    request_id=request_id,
                    provider=ProviderType.GPT4O,
                )
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

        return None
