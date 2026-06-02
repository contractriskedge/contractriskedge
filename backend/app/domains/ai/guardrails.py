"""AI guardrails engine scaffolding for enterprise AI safety and compliance."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable, Optional

from app.domains.ai.schemas import AIGuardrailViolation, SeverityLevel

logger = logging.getLogger(__name__)


@dataclass
class GuardrailRule:
    """A single guardrail rule for AI prompt and response validation."""

    rule_id: str
    description: str
    severity: SeverityLevel
    validator: Callable[[str, Optional[str]], Optional[str]]


class GuardrailEngine:
    """Evaluates prompts and responses against a configurable guardrail policy."""

    def __init__(self, rules: list[GuardrailRule] | None = None):
        self.rules = rules or self._default_rules()

    @staticmethod
    def _default_rules() -> list[GuardrailRule]:
        return [
            GuardrailRule(
                rule_id="no_section_numbering",
                description="Detect and block AI output that reintroduces numbered sections in contract edits.",
                severity=SeverityLevel.MEDIUM,
                validator=lambda prompt, response: (
                    "AI output must not introduce numbered legal sections in proposed redlines."
                    if response and re.search(r"^\s*\d+[\.\)]", response, re.MULTILINE)
                    else None
                ),
            ),
            GuardrailRule(
                rule_id="direct_contract_edit_request",
                description="Flag prompts that ask the model to directly edit contract text without reviewer approval.",
                severity=SeverityLevel.HIGH,
                validator=lambda prompt, response: (
                    "Guardrail: prompt should not ask the model to make direct contract edits without review approval."
                    if prompt and re.search(r"\b(edit|rewrite|amend|change)\b.*\b(contract|clause|term|agreement)\b", prompt, re.IGNORECASE)
                    else None
                ),
            ),
            GuardrailRule(
                rule_id="max_prompt_length",
                description="Warn if the AI prompt exceeds the recommended contract analysis length.",
                severity=SeverityLevel.LOW,
                validator=lambda prompt, response: (
                    "Prompt length exceeds 40,000 characters; truncated input may reduce traceability."
                    if prompt and len(prompt) > 40000
                    else None
                ),
            ),
            GuardrailRule(
                rule_id="sensitive_action_confirmed",
                description="Ensure the model does not claim it can approve contract terms on behalf of the business.",
                severity=SeverityLevel.MEDIUM,
                validator=lambda prompt, response: (
                    "AI should not be instructed to approve legal language; it should provide recommendations only."
                    if prompt and re.search(r"\b(approve|authorize|sign|commit)\b", prompt, re.IGNORECASE)
                    else None
                ),
            ),
        ]

    def evaluate_prompt(self, prompt: str) -> list[AIGuardrailViolation]:
        """Evaluate the prompt text against configured guardrails."""
        violations: list[AIGuardrailViolation] = []
        for rule in self.rules:
            message = rule.validator(prompt, None)
            if message:
                logger.debug("Guardrail prompt violation: %s", rule.rule_id)
                violations.append(AIGuardrailViolation(
                    rule_id=rule.rule_id,
                    message=message,
                    severity=rule.severity,
                ))
        return violations

    def evaluate_response(self, prompt: str, response: str) -> list[AIGuardrailViolation]:
        """Evaluate the LLM response for policy and safety violations."""
        violations: list[AIGuardrailViolation] = []
        for rule in self.rules:
            message = rule.validator(prompt, response)
            if message:
                logger.debug("Guardrail response violation: %s", rule.rule_id)
                violations.append(AIGuardrailViolation(
                    rule_id=rule.rule_id,
                    message=message,
                    severity=rule.severity,
                ))
        return violations

    def has_critical_violation(self, violations: list[AIGuardrailViolation]) -> bool:
        return any(v.severity == SeverityLevel.CRITICAL for v in violations)
