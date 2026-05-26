"""LLM-based severity scoring with chain-of-thought reasoning.

Provides severity scoring on a 1-10 scale using chain-of-thought
reasoning, confidence classification (high/medium/low), and
self-consistency checks through multiple sampling passes.
"""

from __future__ import annotations

import json
import logging
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from llm.client import LLMClient
from llm.models import LLMRequest, LLMResponse, Message, RoleType
from risk_engine.taxonomy import RiskTaxonomy

logger = logging.getLogger(__name__)


@dataclass
class DimensionScores:
    """Severity scores across multiple dimensions."""

    legal_risk: int = 5
    financial_risk: int = 5
    operational_risk: int = 5
    reputational_risk: int = 5


@dataclass
class SeverityResult:
    """Result of severity scoring for a clause."""

    severity_score: int
    confidence: str  # high, medium, low
    chain_of_thought: str
    dimension_scores: DimensionScores
    score_justification: str
    confidence_reasoning: str
    self_consistency_score: Optional[float] = None
    num_sampling_passes: int = 1


class SeverityScorer:
    """LLM-based severity scorer with chain-of-thought and self-consistency.

    Scores contract clause severity on a 1-10 scale using:
    - Chain-of-thought reasoning for structured analysis
    - Confidence classification (high/medium/low)
    - Self-consistency checks via multiple sampling passes
    - Multi-dimensional scoring (legal, financial, operational, reputational)

    Usage:
        taxonomy = RiskTaxonomy()
        llm_client = LLMClient(anthropic_key="...", openai_key="...")
        scorer = SeverityScorer(taxonomy, llm_client)
        result = await scorer.score(clause_text, "indemnification")
    """

    SEVERITY_LABELS: Dict[int, str] = {
        1: "Minimal",
        2: "Minor",
        3: "Low",
        4: "Low-Moderate",
        5: "Moderate",
        6: "Moderate-High",
        7: "High",
        8: "Very High",
        9: "Severe",
        10: "Critical",
    }

    def __init__(
        self,
        taxonomy: RiskTaxonomy,
        llm_client: LLMClient,
        num_consistency_passes: int = 3,
        consistency_threshold: float = 2.0,
    ) -> None:
        """Initialize the severity scorer.

        Args:
            taxonomy: The risk taxonomy for context.
            llm_client: The LLM client for scoring.
            num_consistency_passes: Number of sampling passes for
                self-consistency (1 = no consistency check).
            consistency_threshold: Max std dev for consistent results.
        """
        self._taxonomy = taxonomy
        self._llm_client = llm_client
        self._num_consistency_passes = num_consistency_passes
        self._consistency_threshold = consistency_threshold

    async def score(
        self,
        clause_text: str,
        category_id: str,
        sub_type_id: Optional[str] = None,
        context: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> SeverityResult:
        """Score the severity of a clause.

        Performs chain-of-thought scoring with optional self-consistency
        checks through multiple sampling passes.

        Args:
            clause_text: The clause text to score.
            category_id: The risk category identifier.
            sub_type_id: Optional sub-type for refined scoring.
            context: Optional assessment context from prior steps.
            tenant_id: Optional tenant identifier.

        Returns:
            SeverityResult with score, confidence, and reasoning.
        """
        category = self._taxonomy.get_category(category_id)
        sev_range = category.default_severity_range if category else (1, 10)

        # Build the scoring prompt
        prompt = self._build_scoring_prompt(
            clause_text, category_id, sub_type_id, sev_range, context
        )

        # Perform scoring with self-consistency
        if self._num_consistency_passes > 1:
            return await self._score_with_consistency(
                prompt, category_id, tenant_id
            )

        # Single pass scoring
        return await self._single_score(prompt, tenant_id)

    async def _single_score(
        self,
        messages: List[Message],
        tenant_id: Optional[str] = None,
    ) -> SeverityResult:
        """Perform a single scoring pass.

        Args:
            messages: The prompt messages.
            tenant_id: Optional tenant identifier.

        Returns:
            Severity result from this pass.
        """
        request = LLMRequest(
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            tenant_id=tenant_id,
        )

        response = await self._llm_client.complete(request)
        return self._parse_severity_response(response.content)

    async def _score_with_consistency(
        self,
        base_messages: List[Message],
        category_id: str,
        tenant_id: Optional[str] = None,
    ) -> SeverityResult:
        """Score with self-consistency through multiple passes.

        Runs multiple scoring passes at slightly different temperatures
        and checks if results are consistent.

        Args:
            base_messages: The base prompt messages.
            category_id: Risk category for context.
            tenant_id: Optional tenant identifier.

        Returns:
            Aggregated severity result with consistency metrics.
        """
        scores: list[int] = []
        results: list[SeverityResult] = []
        temperatures = [0.1, 0.2, 0.3]

        for i in range(self._num_consistency_passes):
            try:
                temp = temperatures[i % len(temperatures)]
                request = LLMRequest(
                    messages=base_messages,
                    temperature=temp,
                    max_tokens=2048,
                    tenant_id=tenant_id,
                )
                response = await self._llm_client.complete(request)
                result = self._parse_severity_response(response.content)
                scores.append(result.severity_score)
                results.append(result)
            except Exception as exc:
                logger.warning(
                    "Consistency pass %d failed: %s", i + 1, exc
                )

        if not scores:
            raise RuntimeError("All consistency passes failed")

        # Compute consistency metrics
        mean_score = statistics.mean(scores)
        stdev = statistics.stdev(scores) if len(scores) > 1 else 0.0
        median_score = statistics.median(scores)

        # Round median to integer for final score
        final_score = round(median_score)

        # Determine confidence based on consistency
        if stdev <= self._consistency_threshold / 2:
            confidence = "high"
        elif stdev <= self._consistency_threshold:
            confidence = "medium"
        else:
            confidence = "low"

        # Use the result closest to median for details
        closest_result = min(
            results,
            key=lambda r: abs(r.severity_score - median_score),
        )

        return SeverityResult(
            severity_score=final_score,
            confidence=confidence,
            chain_of_thought=closest_result.chain_of_thought,
            dimension_scores=closest_result.dimension_scores,
            score_justification=closest_result.score_justification,
            confidence_reasoning=(
                f"Self-consistency over {len(scores)} passes: "
                f"mean={mean_score:.1f}, std={stdev:.2f}, "
                f"scores={scores}"
            ),
            self_consistency_score=round(1.0 - (stdev / 10.0), 3),
            num_sampling_passes=len(scores),
        )

    def _build_scoring_prompt(
        self,
        clause_text: str,
        category_id: str,
        sub_type_id: Optional[str],
        severity_range: Tuple[int, int],
        context: Optional[str],
    ) -> List[Message]:
        """Build the severity scoring prompt.

        Args:
            clause_text: The clause text.
            category_id: Risk category.
            sub_type_id: Optional sub-type.
            severity_range: Valid severity range for this category.
            context: Optional assessment context.

        Returns:
            List of messages for the LLM.
        """
        category = self._taxonomy.get_category(category_id)
        category_name = category.name if category else category_id

        sub_type_info = ""
        if sub_type_id and category:
            for sub in category.sub_types:
                if sub.id == sub_type_id:
                    sub_type_info = (
                        f"\nSub-Type: {sub.name}\n"
                        f"Description: {sub.description}\n"
                    )
                    break

        context_str = ""
        if context:
            context_str = f"\nCONTEXT:\n{context}\n"

        system_prompt = (
            "You are an expert contract risk severity assessor. Your task is to "
            "score the severity of contract clauses on a scale of 1-10.\n\n"
            "SCORING GUIDELINES:\n"
            "1-3: Minor concern, standard market language, low business impact\n"
            "4-5: Moderate risk, some deviation from market standard\n"
            "6-7: Significant risk, clearly unfavorable terms\n"
            "8-9: Severe risk, highly unusual or aggressive terms\n"
            "10: Critical risk, potentially invalid or unenforceable provision\n\n"
            "Always show your chain-of-thought reasoning before giving the final score."
        )

        user_prompt = (
            f"SEVERITY SCORING\n\n"
            f"Clause Text:\n```\n{clause_text}\n```\n"
            f"Category: {category_name} ({category_id})\n"
            f"Valid Severity Range: {severity_range[0]}-{severity_range[1]}\n"
            f"{sub_type_info}"
            f"{context_str}\n\n"
            "Analyze this clause step by step, then provide:\n"
            "1. Chain-of-thought reasoning\n"
            "2. Severity score (1-10)\n"
            "3. Confidence level (high/medium/low)\n"
            "4. Dimension scores (legal, financial, operational, reputational)\n"
            "5. Score justification\n\n"
            "OUTPUT FORMAT (JSON):\n"
            "{\n"
            '  "chain_of_thought": "step by step reasoning",\n'
            '  "severity_score": integer,\n'
            '  "confidence": "high|medium|low",\n'
            '  "confidence_reasoning": "why you are confident",\n'
            '  "dimension_scores": {\n'
            '    "legal_risk": integer 1-10,\n'
            '    "financial_risk": integer 1-10,\n'
            '    "operational_risk": integer 1-10,\n'
            '    "reputational_risk": integer 1-10\n'
            "  },\n"
            '  "score_justification": "detailed justification"\n'
            "}"
        )

        return [
            Message(role=RoleType.SYSTEM, content=system_prompt),
            Message(role=RoleType.USER, content=user_prompt),
        ]

    def _parse_severity_response(self, response_text: str) -> SeverityResult:
        """Parse the LLM response into a SeverityResult.

        Args:
            response_text: Raw LLM response text.

        Returns:
            Parsed SeverityResult.

        Raises:
            ValueError: If response cannot be parsed.
        """
        # Try to extract JSON from the response
        import re

        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in severity response")

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse severity JSON: {exc}")

        # Extract dimension scores with defaults
        dims = data.get("dimension_scores", {})
        dimension_scores = DimensionScores(
            legal_risk=dims.get("legal_risk", 5),
            financial_risk=dims.get("financial_risk", 5),
            operational_risk=dims.get("operational_risk", 5),
            reputational_risk=dims.get("reputational_risk", 5),
        )

        return SeverityResult(
            severity_score=data.get("severity_score", 5),
            confidence=data.get("confidence", "medium"),
            chain_of_thought=data.get("chain_of_thought", ""),
            dimension_scores=dimension_scores,
            score_justification=data.get("score_justification", ""),
            confidence_reasoning=data.get("confidence_reasoning", ""),
        )

    def get_severity_label(self, score: int) -> str:
        """Get the human-readable label for a severity score.

        Args:
            score: Severity score (1-10).

        Returns:
            Label string.
        """
        return self.SEVERITY_LABELS.get(score, f"Score {score}")

    @staticmethod
    def score_to_risk_level(score: int) -> str:
        """Convert a numerical score to a risk level string.

        Args:
            score: Severity score (1-10).

        Returns:
            Risk level: 'critical', 'high', 'medium', 'low', or 'info'.
        """
        if score >= 9:
            return "critical"
        elif score >= 7:
            return "high"
        elif score >= 5:
            return "medium"
        elif score >= 3:
            return "low"
        else:
            return "info"
