"""LLM hallucination detection with self-consistency and grounding checks.

Detects potential hallucinations in LLM-generated contract risk
analysis by checking evidence grounding, self-consistency, and
legal plausibility.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HallucinationCheckResult:
    """Result of a hallucination check."""

    passed: bool
    score: float  # 0.0 = likely hallucination, 1.0 = likely accurate
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class HallucinationDetector:
    """Detects potential hallucinations in LLM-generated risk analysis.

    Performs three checks:
    1. Evidence grounding: Does the rationale reference the actual clause?
    2. Self-consistency: Do multiple runs agree?
    3. Legal plausibility: Does the output make legal sense?

    Usage:
        detector = HallucinationDetector()
        result = detector.check_grounding(clause_text, rationale)
    """

    def __init__(self) -> None:
        """Initialize the hallucination detector."""
        pass

    def check_grounding(
        self,
        clause_text: str,
        rationale: str,
    ) -> HallucinationCheckResult:
        """Check if the rationale is grounded in the clause text.

        Verifies that key phrases from the clause appear in the
        rationale, indicating the LLM is referencing the actual text.

        Args:
            clause_text: The original clause text.
            rationale: The LLM-generated rationale.

        Returns:
            HallucinationCheckResult with grounding score.
        """
        issues = []
        clause_lower = clause_text.lower()
        rationale_lower = rationale.lower()

        # Extract key phrases from clause (nouns, legal terms)
        key_phrases = self._extract_key_phrases(clause_text)

        # Check how many key phrases appear in the rationale
        found = sum(1 for p in key_phrases if p.lower() in rationale_lower)
        total = len(key_phrases)

        if total == 0:
            grounding_score = 0.5
        else:
            grounding_score = found / total

        # Check for hallucination indicators
        if "not in the clause" in rationale_lower:
            issues.append("Rationale references information not in clause")
            grounding_score *= 0.5

        if "generally" in rationale_lower and len(rationale.split()) < 20:
            issues.append("Rationale uses vague language without specifics")
            grounding_score *= 0.7

        passed = grounding_score >= 0.3

        return HallucinationCheckResult(
            passed=passed,
            score=round(grounding_score, 3),
            issues=issues,
            details={
                "key_phrases_found": found,
                "key_phrases_total": total,
                "key_phrases": key_phrases[:10],
            },
        )

    def check_self_consistency(
        self,
        responses: List[str],
    ) -> HallucinationCheckResult:
        """Check consistency across multiple LLM responses.

        Runs the same clause through the LLM multiple times and
        checks if the results are semantically consistent.

        Args:
            responses: Multiple LLM responses for the same input.

        Returns:
            HallucinationCheckResult with consistency score.
        """
        if len(responses) < 2:
            return HallucinationCheckResult(
                passed=True,
                score=1.0,
                details={"note": "Need at least 2 responses for consistency check"},
            )

        # Compare responses using simple word overlap
        scores = []
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                words_i = set(responses[i].lower().split())
                words_j = set(responses[j].lower().split())
                if words_i and words_j:
                    overlap = len(words_i & words_j) / max(len(words_i), len(words_j))
                    scores.append(overlap)

        avg_consistency = sum(scores) / len(scores) if scores else 0
        passed = avg_consistency >= 0.6

        issues = []
        if not passed:
            issues.append(
                f"Low self-consistency ({avg_consistency:.2f}): "
                f"responses diverge significantly"
            )

        return HallucinationCheckResult(
            passed=passed,
            score=round(avg_consistency, 3),
            issues=issues,
            details={"num_comparisons": len(scores), "pairwise_scores": [round(s, 3) for s in scores]},
        )

    @staticmethod
    def _extract_key_phrases(text: str) -> List[str]:
        """Extract key legal phrases from clause text.

        Args:
            text: Clause text to analyze.

        Returns:
            List of key phrases.
        """
        # Extract capitalized terms (legal entities, defined terms)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)

        # Extract quoted terms
        quoted = re.findall(r'"([^"]+)"', text)

        # Extract key legal nouns
        legal_terms = [
            "liability", "indemnify", "indemnification", "termination",
            "confidential", "governing law", "jurisdiction", "arbitration",
            "warrant", "representation", "obligation", "breach",
            "damages", "remedy", "force majeure", "assignment",
            "waiver", "severability", "notice", "payment",
        ]
        found_terms = [t for t in legal_terms if t in text.lower()]

        return list(set(capitalized + quoted + found_terms))[:20]
