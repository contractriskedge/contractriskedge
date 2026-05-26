"""Multi-provider LLM client with circuit breaker, retry, and failover.

Provides a robust client that uses Claude 3.5 Sonnet as the primary
provider with automatic failover to GPT-4o. Includes circuit breaker
pattern, configurable retry logic (3 attempts per provider), and
comprehensive error handling.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

import httpx

from .models import (
    LLMRequest,
    LLMResponse,
    ProviderType,
    StreamingEvent,
)
from .provider import LLMProvider, ClaudeSonnetProvider, DeepSeekProvider, GPT4oProvider, calculate_cost
from .cost_tracker import CostTracker
from .cache import PromptCache
from .monitoring import LLMMonitoring

# Prompt injection protection
try:
    from middleware.prompt_sanitizer import PromptSanitizer
    _HAS_SANITIZER = True
except ImportError:
    _HAS_SANITIZER = False
    PromptSanitizer = None  # type: ignore

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for provider failover.

    Tracks failure counts and opens the circuit when a threshold
    is exceeded, preventing cascading failures.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    _failure_count: int = 0
    _last_failure_time: float = 0.0
    _state: CircuitState = CircuitState.CLOSED

    def record_success(self) -> None:
        """Record a successful request, resetting failure count."""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("Circuit breaker closed after successful recovery")

    def record_failure(self) -> None:
        """Record a failed request, potentially opening the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN after %d failures",
                self._failure_count,
            )

    @property
    def is_available(self) -> bool:
        """Check if the circuit allows requests.

        Returns:
            True if requests are allowed (CLOSED or HALF_OPEN).
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker HALF_OPEN, testing recovery")
                return True
            return False

        # HALF_OPEN state allows a single test request
        return True

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = 0.0
        logger.info("Circuit breaker reset to CLOSED")


@dataclass
class RetryConfig:
    """Retry configuration for LLM requests."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    retryable_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)


class LLMClient:
    """Multi-provider LLM client with circuit breaker and failover.

    Uses Claude 3.5 Sonnet as the primary provider with GPT-4o as
    fallback. Implements retry logic (3 attempts per provider),
    circuit breaker pattern, and comprehensive monitoring.

    Usage:
        client = LLMClient(
            anthropic_key="sk-...",
            openai_key="sk-...",
            deepseek_key="sk-...",
        )
        response = await client.complete(request)
    """

    def __init__(
        self,
        anthropic_key: str = "",
        openai_key: str = "",
        deepseek_key: str = "",
        claude_model: str = "claude-3-5-sonnet-20241022",
        gpt4o_model: str = "gpt-4o-2024-08-06",
        deepseek_model: str = "deepseek-chat",
        retry_config: Optional[RetryConfig] = None,
        cost_tracker: Optional[CostTracker] = None,
        cache: Optional[PromptCache] = None,
        monitoring: Optional[LLMMonitoring] = None,
    ) -> None:
        """Initialize the multi-provider LLM client.

        Provider priority: DeepSeek (primary) -> Claude (fallback 1) -> GPT-4o (fallback 2).
        Falls back to the next available provider if the current one fails.

        Args:
            anthropic_key: API key for Anthropic Claude.
            openai_key: API key for OpenAI GPT-4o.
            deepseek_key: API key for DeepSeek Chat.
            claude_model: Claude model identifier.
            gpt4o_model: GPT-4o model identifier.
            deepseek_model: DeepSeek model identifier.
            retry_config: Optional custom retry configuration.
            cost_tracker: Optional cost tracker instance.
            cache: Optional prompt cache instance.
            monitoring: Optional monitoring instance.
        """
        self._providers: List[Tuple[LLMProvider, CircuitBreaker]] = []

        if deepseek_key:
            self._providers.append((
                DeepSeekProvider(api_key=deepseek_key, model_name=deepseek_model),
                CircuitBreaker(),
            ))
        if anthropic_key:
            self._providers.append((
                ClaudeSonnetProvider(api_key=anthropic_key, model_name=claude_model),
                CircuitBreaker(),
            ))
        if openai_key:
            self._providers.append((
                GPT4oProvider(api_key=openai_key, model_name=gpt4o_model),
                CircuitBreaker(),
            ))

        if not self._providers:
            raise ValueError(
                "At least one API key (deepseek_key, anthropic_key, or openai_key) is required"
            )

        self._retry_config = retry_config or RetryConfig()
        self._cost_tracker = cost_tracker or CostTracker()
        self._cache = cache
        self._monitoring = monitoring
        self._cost_tracker = cost_tracker or CostTracker()
        self._cache = cache
        self._monitoring = monitoring

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request with automatic failover.

        Attempts providers in priority order (DeepSeek -> Claude -> GPT-4o).
        Falls back to the next provider if the current one fails after retries.
        Tracks costs and monitors performance.

        Applies prompt injection sanitization to user messages before
        sending to any provider.

        Args:
            request: The LLM request to send.

        Returns:
            The LLM response from the successful provider.

        Raises:
            RuntimeError: If all providers fail after all retries.
        """
        # Apply prompt injection sanitization to all user messages
        if _HAS_SANITIZER:
            sanitizer = PromptSanitizer()
            sanitized_messages = []
            for msg in request.messages:
                if msg.role == "user" and msg.content:
                    clean_content = sanitizer.sanitize(str(msg.content))
                    if sanitizer.has_injection_attempt():
                        logger.warning(
                            "Prompt injection detected in request %s: %s",
                            request.request_id,
                            sanitizer.get_injection_details(),
                        )
                    from .models import Message, RoleType
                    sanitized_messages.append(Message(
                        role=RoleType.USER,
                        content=clean_content,
                    ))
                else:
                    sanitized_messages.append(msg)
            request.messages = sanitized_messages
        else:
            logger.debug("PromptSanitizer not available; skipping sanitization")

        if request.request_id is None:
            request.request_id = str(uuid.uuid4())

        # Check cache first
        if self._cache is not None and not request.skip_cache and request.cache_key:
            cached_response = await self._cache.get(request.cache_key)
            if cached_response is not None:
                logger.info("Cache hit for key=%s", request.cache_key)
                if self._monitoring:
                    self._monitoring.record_cache_hit(request.request_id)
                return cached_response

        errors: List[Exception] = []

        for provider, circuit in self._providers:
            provider_name = provider.provider_type.value
            if circuit.is_available:
                try:
                    response = await self._execute_with_retry(provider, request)
                    circuit.record_success()
                    await self._post_process(request, response)
                    return response
                except Exception as exc:
                    circuit.record_failure()
                    logger.warning(
                        "Provider %s failed: %s. Attempting next provider.",
                        provider_name,
                        exc,
                    )
                    errors.append(exc)
                    if self._monitoring:
                        self._monitoring.record_provider_failover(
                            provider.provider_type, str(exc)
                        )
            else:
                logger.info("Skipping provider %s (circuit open)", provider_name)

        # All providers failed
        error_msg = (
            f"All LLM providers failed after retries. "
            f"Attempted providers: {[p.provider_type.value for p, _ in self._providers]}"
        )
        logger.error(error_msg)
        if self._monitoring:
            self._monitoring.record_request_failure(request.request_id, error_msg)
        raise RuntimeError(error_msg)

    async def complete_stream(
        self, request: LLMRequest
    ) -> AsyncGenerator[StreamingEvent, None]:
        """Stream a completion response with automatic failover.

        Attempts providers in priority order (DeepSeek -> Claude -> GPT-4o).

        Args:
            request: The LLM request with stream=True.

        Yields:
            Streaming events from the available provider.

        Raises:
            RuntimeError: If all providers fail.
        """
        if request.request_id is None:
            request.request_id = str(uuid.uuid4())
        request.stream = True

        for provider, circuit in self._providers:
            provider_name = provider.provider_type.value
            if circuit.is_available:
                try:
                    async for event in provider.complete_stream(request):
                        yield event
                    circuit.record_success()
                    return
                except Exception as exc:
                    circuit.record_failure()
                    logger.warning(
                        "Provider %s streaming failed: %s. Attempting next.",
                        provider_name,
                        exc,
                    )
            else:
                logger.info("Skipping provider %s (circuit open)", provider_name)

        raise RuntimeError("All providers failed for streaming request")

    async def _execute_with_retry(
        self, provider: LLMProvider, request: LLMRequest
    ) -> LLMResponse:
        """Execute a request with retry logic.

        Retries up to max_retries times with exponential backoff.

        Args:
            provider: The provider to use.
            request: The LLM request.

        Returns:
            The LLM response.

        Raises:
            The last exception if all retries fail.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(1, self._retry_config.max_retries + 1):
            try:
                start_time = time.monotonic()
                response = await provider.complete(request)
                duration_ms = (time.monotonic() - start_time) * 1000

                if self._monitoring:
                    self._monitoring.record_request(
                        provider=provider.provider_type,
                        duration_ms=duration_ms,
                        token_count=response.token_usage.total_tokens,
                        request_id=request.request_id or "unknown",
                    )

                return response

            except httpx.HTTPStatusError as exc:
                last_exception = exc
                if exc.response.status_code in self._retry_config.retryable_status_codes:
                    if attempt < self._retry_config.max_retries:
                        delay = self._get_retry_delay(attempt)
                        logger.info(
                            "Retry %d/%d for %s after status %d. Waiting %.1fs",
                            attempt,
                            self._retry_config.max_retries,
                            provider.provider_type.value,
                            exc.response.status_code,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                else:
                    # Non-retryable status code
                    raise

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exception = exc
                if attempt < self._retry_config.max_retries:
                    delay = self._get_retry_delay(attempt)
                    logger.info(
                        "Retry %d/%d for %s after network error. Waiting %.1fs",
                        attempt,
                        self._retry_config.max_retries,
                        provider.provider_type.value,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue

            except Exception as exc:
                # Non-retryable exception
                last_exception = exc
                if attempt < self._retry_config.max_retries:
                    delay = self._get_retry_delay(attempt)
                    logger.info(
                        "Retry %d/%d for %s after error: %s",
                        attempt,
                        self._retry_config.max_retries,
                        provider.provider_type.value,
                        exc,
                    )
                    await asyncio.sleep(delay)
                    continue

        raise RuntimeError(
            f"All {self._retry_config.max_retries} retries exhausted for "
            f"{provider.provider_type.value}: {last_exception}"
        ) from last_exception

    def _get_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (1-indexed).

        Returns:
            Delay in seconds.
        """
        delay = self._retry_config.base_delay * (
            self._retry_config.backoff_factor ** (attempt - 1)
        )
        import random
        jitter = random.uniform(0, 0.1 * delay)
        return min(delay + jitter, self._retry_config.max_delay)

    async def _post_process(
        self, request: LLMRequest, response: LLMResponse
    ) -> None:
        """Post-process a successful response.

        Handles caching, cost tracking, and monitoring.

        Args:
            request: The original request.
            response: The response to process.
        """
        # Cache the response if caching is configured
        if self._cache is not None and request.cache_key and not response.cached:
            await self._cache.set(request.cache_key, response)

        # Track costs
        cost = calculate_cost(
            provider=response.provider,
            prompt_tokens=response.token_usage.prompt_tokens,
            completion_tokens=response.token_usage.completion_tokens,
            cache_hit_tokens=response.token_usage.cache_hit_tokens,
            cache_creation_tokens=response.token_usage.cache_creation_input_tokens,
        )
        await self._cost_tracker.record_cost(
            request_id=request.request_id or response.request_id,
            provider=response.provider,
            model_name=response.model_name,
            prompt_tokens=response.token_usage.prompt_tokens,
            completion_tokens=response.token_usage.completion_tokens,
            total_tokens=response.token_usage.total_tokens,
            cost_usd=cost,
            tenant_id=request.tenant_id,
            duration_ms=response.latency_ms,
            cached=response.cached,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all providers.

        Returns:
            Dict with provider health status.
        """
        result: Dict[str, Any] = {}
        for provider, circuit in self._providers:
            try:
                healthy = await provider.health_check()
            except Exception:
                healthy = False
            result[provider.provider_type.value] = {
                "provider": provider.provider_type.value,
                "model": provider.model_name,
                "healthy": healthy,
                "circuit_state": circuit._state.value,
            }
        return result

    async def close(self) -> None:
        """Close all provider connections and release resources."""
        for provider, _ in self._providers:
            await provider.close()
        if self._cache is not None:
            await self._cache.close()
        logger.info("LLM client closed")
