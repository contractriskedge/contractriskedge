"""Central AI execution orchestrator for enterprise governance and traceable pipelines."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.domains.ai.orchestration.envelope import AIRequestEnvelope
from app.domains.ai.orchestration.plan import AIExecutionPlan
from app.domains.ai.orchestration.cost import AICostEstimator
from app.domains.ai.policy import AIPolicyEngine, AIPolicyContext, AIPolicyDecision, AIPolicyViolation
from app.domains.ai.providers.registry import llm_registry
from app.domains.ai.types import AIExecutionOutcome, LLMRequest
from app.domains.ai.guardrails import GuardrailEngine
from app.domains.ai.llm import StructuredOutputParser, RateLimitError, LLMProviderError
from app.domains.ai.schemas import AnalysisResult

from app.kernel.database.session_utils import release_session_before_io

logger = logging.getLogger(__name__)


def _is_registry_miss(exc: Exception) -> bool:
    return isinstance(exc, ValueError) and "No healthy LLM providers are available" in str(exc)


def _prefer_exception(current: Exception | None, candidate: Exception) -> Exception:
    """Keep API/rate-limit errors over registry miss noise from unregistered fallbacks."""
    if current is None:
        return candidate
    if _is_registry_miss(current) and not _is_registry_miss(candidate):
        return candidate
    if isinstance(candidate, (RateLimitError, LLMProviderError)) and _is_registry_miss(current):
        return candidate
    return current


class AIExecutionOrchestrator:
    """Single entry point for AI execution with governance, routing, validation and observability."""

    def __init__(self, session: Any, tenant_id: str, user_id: str | None = None):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.policy_engine = AIPolicyEngine(session, tenant_id)
        self.guardrail_engine = GuardrailEngine()

    async def execute(self, envelope: AIRequestEnvelope) -> AIExecutionOutcome:
        trace_id = envelope.trace_id or str(uuid.uuid4())
        execution_id = envelope.execution_id or str(uuid.uuid4())
        correlation_id = envelope.correlation_id or str(uuid.uuid4())

        logger.info(
            "Starting AI execution: tenant=%s operation=%s trace_id=%s execution_id=%s",
            envelope.tenant_id,
            envelope.operation_type,
            trace_id,
            execution_id,
        )

        policy_context = AIPolicyContext(
            tenant_id=envelope.tenant_id,
            operation=envelope.operation_type,
            user_id=self.user_id,
            user_role=envelope.audit_context.get("user_role"),
            upload_id=envelope.upload_id,
            contract_id=envelope.contract_id,
            provider=envelope.execution_plan.provider_name,
            model=envelope.execution_plan.model,
            prompt_length=len(envelope.audit_context.get("prompt_text", "")),
            max_tokens=envelope.execution_plan.token_budget,
            metadata={
                **envelope.audit_context,
                "request_chain_id": envelope.request_chain_id,
                "correlation_id": correlation_id,
            },
        )

        policy_decision = await self.policy_engine.validate(policy_context)
        if not policy_decision.allowed:
            logger.warning(
                "AI execution denied by policy engine: tenant=%s trace_id=%s violations=%s",
                envelope.tenant_id,
                trace_id,
                policy_decision.violations,
            )
            raise AIPolicyViolation("; ".join(policy_decision.violations))

        # Build the provider selection chain: primary + registered fallbacks only
        provider_chain = [envelope.execution_plan.provider_name]
        if envelope.execution_plan.fallback_chain.providers:
            registered = set(llm_registry.registered_names())
            for p in envelope.execution_plan.fallback_chain.providers:
                if p not in provider_chain and p in registered:
                    provider_chain.append(p)

        last_exception: Exception | None = None
        selected_provider = None
        result = None

        for provider_name in provider_chain:
            try:
                selected_provider = llm_registry.select_provider(preferred=[provider_name])
                if not selected_provider:
                    logger.warning(
                        "Provider %s not available in registry, trying next",
                        provider_name,
                    )
                    continue

                logger.info(
                    "Attempting provider: %s (chain: %s, trace_id=%s)",
                    selected_provider.provider_name,
                    provider_chain,
                    trace_id,
                )

                max_tokens = min(
                    envelope.execution_plan.token_budget,
                    envelope.execution_plan.provider_capabilities.max_response_tokens,
                )
                llm_request = LLMRequest(
                    prompt=envelope.audit_context.get("prompt_text", ""),
                    system_prompt=envelope.audit_context.get("system_prompt"),
                    model=envelope.execution_plan.model,
                    temperature=envelope.execution_plan.temperature,
                    max_tokens=max_tokens,
                    response_format=envelope.execution_plan.metadata.get("response_format"),
                )

                pre_violations = self.guardrail_engine.evaluate_prompt(llm_request.prompt)
                if self.guardrail_engine.has_critical_violation(pre_violations):
                    raise AIPolicyViolation("Critical guardrail violation prevented execution")

                cost_estimator = AICostEstimator()
                await release_session_before_io(self.session)
                start = time.monotonic()
                try:
                    result = await selected_provider.complete(llm_request)
                    latency_ms = int((time.monotonic() - start) * 1000)
                    result.cost_usd = cost_estimator.estimate(
                        result.model,
                        result.prompt_tokens,
                        result.completion_tokens,
                    )
                    llm_registry.report_outcome(
                        selected_provider.provider_name,
                        success=True,
                        latency_ms=latency_ms,
                        cost_usd=result.cost_usd,
                        timeout=False,
                    )
                except Exception as exc:
                    latency_ms = int((time.monotonic() - start) * 1000)
                    llm_registry.report_outcome(
                        selected_provider.provider_name,
                        success=False,
                        latency_ms=latency_ms,
                        cost_usd=0.0,
                        timeout=isinstance(exc, TimeoutError),
                    )
                    logger.warning(
                        "Provider %s failed: %s — %d fallback(s) remaining in chain",
                        selected_provider.provider_name,
                        exc,
                        len(provider_chain) - provider_chain.index(provider_name) - 1,
                    )
                    last_exception = _prefer_exception(last_exception, exc)
                    continue  # Try next provider in chain

                # Success — break out of provider chain
                break

            except Exception as exc:
                logger.warning(
                    "Provider selection/execution error for %s: %s",
                    provider_name,
                    exc,
                )
                last_exception = _prefer_exception(last_exception, exc)
                continue

        if result is None:
            # All providers in chain failed
            logger.error(
                "All providers failed for trace_id=%s chain=%s last_error=%s",
                trace_id,
                provider_chain,
                last_exception,
            )
            if last_exception:
                raise last_exception
            raise RuntimeError(f"All providers failed: {provider_chain}")

        post_violations = self.guardrail_engine.evaluate_response(llm_request.prompt, result.content)
        if self.guardrail_engine.has_critical_violation(post_violations):
            raise AIPolicyViolation("Critical guardrail violation in provider response")

        parsed = StructuredOutputParser.parse_json(result.content)
        validated = StructuredOutputParser.validate_model(parsed, AnalysisResult) if parsed else None
        if parsed is not None and validated is None:
            logger.warning(
                "AI response parsed but failed schema validation: trace_id=%s",
                trace_id,
            )

        guardrail_violations = [
            *pre_violations,
            *post_violations,
        ]

        return AIExecutionOutcome(
            response=result,
            policy_decision=policy_decision,
            plan=envelope.execution_plan,
            guardrail_violations=[v.model_dump() for v in guardrail_violations],
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
