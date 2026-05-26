"""Prompt chain orchestrator with JSON output enforcement — 8-field explainability.

Orchestrates the multi-step prompt chain for risk analysis, ensuring
each step produces valid JSON output before proceeding to the next.
Handles parsing errors, retries, and partial results. Includes
hallucination detection, citation grounding verification, and the
8-field enterprise explainability output schema.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from risk_engine.taxonomy import RiskTaxonomy
from risk_engine.prompts import RiskPromptChain
from risk_engine.few_shot import FewShotExamples
from risk_engine.output_schema import (
    RiskFlagOutput,
    LinkedEvidence,
    JurisdictionalConsideration,
)
from llm.models import LLMRequest, LLMResponse, Message, RoleType
from llm.client import LLMClient

logger = logging.getLogger(__name__)


class JSONParsingError(Exception):
    """Raised when LLM output cannot be parsed as valid JSON."""

    def __init__(self, raw_output: str, parsing_error: str) -> None:
        self.raw_output = raw_output
        self.parsing_error = parsing_error
        super().__init__(f"Failed to parse JSON output: {parsing_error}")


@dataclass
class ChainStepResult:
    """Result of a single step in the prompt chain."""

    step_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    raw_output: str = ""
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class ChainResult:
    """Complete result of the prompt chain execution with 8-field explainability."""

    success: bool
    clause_text: str
    classification: Optional[ChainStepResult] = None
    assessment: Optional[ChainStepResult] = None
    severity: Optional[ChainStepResult] = None
    rationale: Optional[ChainStepResult] = None
    error: Optional[str] = None
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hallucination_check: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    citations: List[Dict[str, Any]] = field(default_factory=list)
    # 8-field explainability output
    why_flagged: Optional[str] = None
    potential_business_impact: Optional[str] = None
    market_benchmark_comparison: Optional[str] = None
    suggested_remediation: Optional[str] = None
    linked_evidence: List[Dict[str, Any]] = field(default_factory=list)
    jurisdictional_considerations: List[Dict[str, Any]] = field(default_factory=list)


class PromptChainOrchestrator:
    """Orchestrates the multi-step prompt chain for risk analysis.

    Runs the 4-step prompt chain with JSON output validation at each
    step. Supports retry on parsing failures, partial result handling,
    and configurable step execution.

    Usage:
        taxonomy = RiskTaxonomy()
        llm_client = LLMClient(anthropic_key="...", openai_key="...")
        orchestrator = PromptChainOrchestrator(taxonomy, llm_client)
        result = await orchestrator.run_chain(clause_text)
    """

    def __init__(
        self,
        taxonomy: RiskTaxonomy,
        llm_client: LLMClient,
        max_retries: int = 2,
        include_few_shot: bool = True,
    ) -> None:
        """Initialize the prompt chain orchestrator.

        Args:
            taxonomy: The risk taxonomy to use.
            llm_client: The LLM client for completions.
            max_retries: Maximum retries per step on JSON parse failure.
            include_few_shot: Whether to include few-shot examples.
        """
        self._taxonomy = taxonomy
        self._llm_client = llm_client
        self._prompts = RiskPromptChain(taxonomy)
        self._max_retries = max_retries
        self._include_few_shot = include_few_shot

    async def run_chain(
        self,
        clause_text: str,
        section_heading: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> ChainResult:
        """Run the complete 4-step prompt chain.

        Args:
            clause_text: The clause text to analyze.
            section_heading: Optional section heading for context.
            tenant_id: Optional tenant identifier for tracking.

        Returns:
            Complete chain result with all step outputs.
        """
        chain_id = str(uuid.uuid4())
        logger.info(
            "Starting prompt chain %s for clause (%d chars)",
            chain_id,
            len(clause_text),
        )

        result = ChainResult(
            success=False,
            clause_text=clause_text,
            chain_id=chain_id,
        )

        try:
            # Step 1: Classification
            result.classification = await self._execute_step(
                step_name="classification",
                messages=self._prompts.build_classification_prompt(
                    clause_text, section_heading
                ),
                tenant_id=tenant_id,
            )
            if not result.classification.success:
                result.error = f"Classification step failed: {result.classification.error}"
                return result

            classifications = result.classification.data or {}
            categories = classifications.get("classifications", [])
            if not categories:
                logger.warning("Chain %s: No classifications found", chain_id)
                result.error = "No risk categories identified"
                return result

            primary_category = categories[0]
            category_id = primary_category.get("category_id", "")
            sub_type_id = primary_category.get("sub_type_id")

            # Step 2: Assessment
            result.assessment = await self._execute_step(
                step_name="assessment",
                messages=self._prompts.build_assessment_prompt(
                    clause_text, category_id, sub_type_id, section_heading
                ),
                tenant_id=tenant_id,
            )
            if not result.assessment.success:
                result.error = f"Assessment step failed: {result.assessment.error}"
                return result

            assessment_data = result.assessment.data or {}
            assessment_summary = json.dumps(assessment_data, indent=2)

            # Step 3: Severity Scoring
            result.severity = await self._execute_step(
                step_name="severity",
                messages=self._prompts.build_severity_prompt(
                    clause_text, category_id, sub_type_id, assessment_summary
                ),
                tenant_id=tenant_id,
            )
            if not result.severity.success:
                result.error = f"Severity step failed: {result.severity.error}"
                return result

            severity_data = result.severity.data or {}
            severity_score = severity_data.get("severity_score", 5)

            # Step 4: Rationale
            result.rationale = await self._execute_step(
                step_name="rationale",
                messages=self._prompts.build_rationale_prompt(
                    clause_text,
                    category_id,
                    severity_score,
                    assessment_summary,
                ),
                tenant_id=tenant_id,
            )

            result.success = (
                result.classification.success
                and result.assessment.success
                and result.severity.success
                and (result.rationale is not None and result.rationale.success)
            )

            if result.success:
                logger.info("Chain %s completed successfully", chain_id)

                # Extract 8-field explainability data from rationale step
                if result.rationale and result.rationale.data:
                    rationale_data = result.rationale.data
                    result.why_flagged = rationale_data.get(
                        "why_flagged",
                        rationale_data.get("rationale", "")
                    )
                    result.potential_business_impact = rationale_data.get(
                        "potential_business_impact", ""
                    )
                    result.market_benchmark_comparison = rationale_data.get(
                        "market_benchmark_comparison", ""
                    )
                    result.suggested_remediation = rationale_data.get(
                        "suggested_remediation", ""
                    )
                    result.linked_evidence = rationale_data.get(
                        "linked_evidence", []
                    )
                    result.jurisdictional_considerations = rationale_data.get(
                        "jurisdictional_considerations", []
                    )

                # Run hallucination detection on the rationale
                rationale_text = ""
                if result.rationale and result.rationale.data:
                    rationale_text = json.dumps(result.rationale.data)
                elif result.rationale:
                    rationale_text = result.rationale.raw_output

                if rationale_text:
                    try:
                        from llm.hallucination import HallucinationDetector

                        detector = HallucinationDetector()
                        grounding = detector.check_grounding(clause_text, rationale_text)

                        # Calculate confidence score from hallucination check
                        result.hallucination_check = {
                            "passed": grounding.passed,
                            "grounding_score": grounding.score,
                            "issues": grounding.issues,
                            "details": grounding.details,
                        }
                        # Confidence = groundedness score mapped to 0-1
                        result.confidence_score = round(
                            max(0.0, min(1.0, grounding.score)), 3
                        )

                        # Build citations from key phrase matches
                        key_phrases = grounding.details.get("key_phrases", [])
                        for phrase in key_phrases[:5]:
                            if phrase.lower() in clause_text.lower():
                                # Find approximate position
                                pos = clause_text.lower().find(phrase.lower())
                                result.citations.append({
                                    "text": phrase,
                                    "position_start": pos if pos >= 0 else 0,
                                    "position_end": pos + len(phrase) if pos >= 0 else len(phrase),
                                    "confidence": 0.9,
                                })

                        logger.info(
                            "Hallucination check for chain %s: score=%.3f, passed=%s",
                            chain_id,
                            grounding.score,
                            grounding.passed,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Hallucination detection failed for chain %s: %s",
                            chain_id,
                            exc,
                        )
            else:
                result.error = "One or more steps failed"
                logger.warning("Chain %s completed with errors", chain_id)

        except Exception as exc:
            logger.error("Chain %s failed with exception: %s", chain_id, exc)
            result.error = str(exc)

        return result

    async def run_single_step(
        self,
        step_name: str,
        clause_text: str,
        section_heading: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> ChainStepResult:
        """Run a single step of the prompt chain.

        Args:
            step_name: The step to run ('classification', 'assessment',
                      'severity', or 'rationale').
            clause_text: The clause text.
            section_heading: Optional section heading.
            context: Optional context from previous steps.
            tenant_id: Optional tenant identifier.

        Returns:
            Result of the single step.
        """
        step_builders = {
            "classification": self._prompts.build_classification_prompt,
            "assessment": self._prompts.build_assessment_prompt,
            "severity": self._prompts.build_severity_prompt,
            "rationale": self._prompts.build_rationale_prompt,
        }

        builder = step_builders.get(step_name)
        if builder is None:
            return ChainStepResult(
                step_name=step_name,
                success=False,
                error=f"Unknown step: {step_name}",
            )

        if step_name == "classification":
            messages = builder(clause_text, section_heading)
        elif step_name == "assessment":
            cat_id = (context or {}).get("category_id", "indemnification")
            sub_id = (context or {}).get("sub_type_id")
            messages = builder(clause_text, cat_id, sub_id, section_heading)
        elif step_name == "severity":
            cat_id = (context or {}).get("category_id", "indemnification")
            sub_id = (context or {}).get("sub_type_id")
            assessment = (context or {}).get("assessment_summary", "")
            messages = builder(clause_text, cat_id, sub_id, assessment)
        elif step_name == "rationale":
            cat_id = (context or {}).get("category_id", "indemnification")
            score = (context or {}).get("severity_score", 5)
            summary = (context or {}).get("assessment_summary", "")
            messages = builder(clause_text, cat_id, score, summary)
        else:
            return ChainStepResult(
                step_name=step_name,
                success=False,
                error=f"Unhandled step: {step_name}",
            )

        return await self._execute_step(step_name, messages, tenant_id)

    async def _execute_step(
        self,
        step_name: str,
        messages: List[Dict[str, str]],
        tenant_id: Optional[str] = None,
    ) -> ChainStepResult:
        """Execute a single step with retry logic.

        Args:
            step_name: Name of the step for logging.
            messages: The prompt messages to send.
            tenant_id: Optional tenant identifier.

        Returns:
            Result of the step execution.
        """
        last_error: Optional[str] = None
        raw_output = ""

        for attempt in range(self._max_retries + 1):
            try:
                # Convert messages to LLM message format
                llm_messages = [
                    Message(role=RoleType(m["role"]), content=m["content"])
                    for m in messages
                ]

                # If including few-shot, append examples to the last user message
                if self._include_few_shot and attempt == 0:
                    llm_messages = self._inject_few_shot(
                        step_name, llm_messages
                    )

                request = LLMRequest(
                    messages=llm_messages,
                    temperature=0.1,
                    max_tokens=4096,
                    tenant_id=tenant_id,
                    request_id=f"chain_{step_name}_{uuid.uuid4().hex[:8]}",
                )

                response: LLMResponse = await self._llm_client.complete(request)
                raw_output = response.content

                # Parse and validate JSON output
                parsed = self._parse_json_output(raw_output)
                if parsed is None:
                    raise JSONParsingError(
                        raw_output, "No valid JSON found in response"
                    )

                # Validate required fields based on step
                self._validate_step_output(step_name, parsed)

                return ChainStepResult(
                    step_name=step_name,
                    success=True,
                    data=parsed,
                    raw_output=raw_output,
                    retry_count=attempt,
                )

            except JSONParsingError as exc:
                last_error = str(exc)
                logger.warning(
                    "Step '%s' attempt %d: JSON parsing error: %s",
                    step_name,
                    attempt + 1,
                    exc.parsing_error,
                )
                if attempt < self._max_retries:
                    # Add instruction to fix JSON format
                    messages.append({
                        "role": "assistant",
                        "content": raw_output,
                    })
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your response was not valid JSON. Please respond "
                            "with ONLY valid JSON matching the specified format. "
                            f"Error: {exc.parsing_error}"
                        ),
                    })

            except Exception as exc:
                last_error = str(exc)
                logger.error(
                    "Step '%s' attempt %d failed: %s",
                    step_name,
                    attempt + 1,
                    exc,
                )
                if attempt < self._max_retries:
                    continue

        return ChainStepResult(
            step_name=step_name,
            success=False,
            raw_output=raw_output,
            error=last_error or "Unknown error",
            retry_count=self._max_retries,
        )

    def _inject_few_shot(
        self, step_name: str, messages: List[Message]
    ) -> List[Message]:
        """Inject few-shot examples into the messages.

        Args:
            step_name: The current step name.
            messages: The current message list.

        Returns:
            Updated messages with few-shot examples.
        """
        example_map = {
            "classification": FewShotExamples.get_classification_examples(),
            "assessment": FewShotExamples.get_assessment_examples(),
            "severity": FewShotExamples.get_severity_examples(),
            "rationale": FewShotExamples.get_rationale_examples(),
        }

        examples = example_map.get(step_name, [])
        if not examples:
            return messages

        example_text = "\n\nEXAMPLES:\n"
        for i, example in enumerate(examples, 1):
            example_text += f"\nExample {i}:\n"
            example_text += f"Input clause: {example.get('clause', '')}\n"
            example_text += f"Expected output: {json.dumps(example.get('output', {}), indent=2)}\n"

        # Append examples to the last user message
        for msg in reversed(messages):
            if msg.role == RoleType.USER:
                msg.content += example_text
                break

        return messages

    def _parse_json_output(self, raw_output: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM output, handling markdown code blocks.

        Args:
            raw_output: Raw text output from the LLM.

        Returns:
            Parsed JSON dict, or None if parsing fails.
        """
        # Try direct parsing first
        try:
            return json.loads(raw_output.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            raw_output,
            re.DOTALL,
        )
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding any JSON object in the text
        brace_match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _validate_step_output(
        self, step_name: str, data: Dict[str, Any]
    ) -> None:
        """Validate step output has required fields.

        Args:
            step_name: The step name.
            data: Parsed JSON data.

        Raises:
            ValueError: If required fields are missing.
        """
        if step_name == "classification":
            if "classifications" not in data:
                raise ValueError("Missing 'classifications' field")
            if not isinstance(data["classifications"], list):
                raise ValueError("'classifications' must be a list")
            for cls in data["classifications"]:
                if "category_id" not in cls:
                    raise ValueError(
                        "Each classification must have 'category_id'"
                    )

        elif step_name == "assessment":
            required = {"risk_level", "risk_score", "key_concerns"}
            missing = required - set(data.keys())
            if missing:
                raise ValueError(f"Missing fields: {missing}")

        elif step_name == "severity":
            if "severity_score" not in data:
                raise ValueError("Missing 'severity_score' field")
            score = data["severity_score"]
            if not isinstance(score, int) or score < 1 or score > 10:
                raise ValueError(
                    f"severity_score must be integer 1-10, got {score}"
                )

        elif step_name == "rationale":
            if "rationale" not in data:
                raise ValueError("Missing 'rationale' field")
            if "suggested_action" not in data:
                raise ValueError("Missing 'suggested_action' field")
