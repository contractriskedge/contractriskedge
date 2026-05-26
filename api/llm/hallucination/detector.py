"""Unsupported claim detection module — grounding validator per clause.

Provides a grounding validator that verifies each claim in the AI output
has supporting evidence in the source contract text. Detects unsupported
claims, hallucinations, and factual inconsistencies.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ClaimVerification:
    """Result of verifying a single claim against source evidence."""

    claim_text: str
    supported: bool
    evidence_excerpt: Optional[str] = None
    confidence: float = 0.0  # 0.0-1.0
    reason: str = ""


@dataclass
class GroundingValidationResult:
    """Complete result of grounding validation for a clause."""

    clause_text: str
    ai_output_text: str
    claims_verified: int = 0
    claims_supported: int = 0
    claims_unsupported: int = 0
    grounding_score: float = 0.0  # 0.0-1.0
    passed: bool = False
    verifications: List[ClaimVerification] = field(default_factory=list)
    unsupported_claims: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class GroundingValidator:
    """Validates that AI-generated claims are grounded in source contract text.

    Performs per-claim verification:
    1. Extracts claims from AI output.
    2. Checks each claim against source clause text.
    3. Identifies unsupported or hallucinated claims.
    4. Produces a grounding score for the overall analysis.

    Usage:
        validator = GroundingValidator()
        result = validator.validate(clause_text, ai_output)
        print(f"Grounding score: {result.grounding_score}")
        print(f"Unsupported claims: {result.unsupported_claims}")
    """

    def __init__(
        self,
        min_grounding_threshold: float = 0.3,
    ) -> None:
        """Initialize the grounding validator.

        Args:
            min_grounding_threshold: Minimum grounding score to pass.
        """
        self._min_grounding_threshold = min_grounding_threshold

    def validate(
        self,
        clause_text: str,
        ai_output_text: str,
    ) -> GroundingValidationResult:
        """Validate that AI output claims are grounded in clause text.

        Args:
            clause_text: The original source contract clause text.
            ai_output_text: The AI-generated analysis text.

        Returns:
            GroundingValidationResult with per-claim verification.
        """
        clause_lower = clause_text.lower()
        ai_lower = ai_output_text.lower()

        # Extract claims from AI output
        claims = self._extract_claims(ai_output_text)
        clause_key_phrases = self._extract_key_phrases(clause_text)

        verifications: List[ClaimVerification] = []
        unsupported: List[str] = []

        for claim in claims:
            verification = self._verify_claim(
                claim, clause_lower, clause_text, clause_key_phrases
            )
            verifications.append(verification)
            if not verification.supported:
                unsupported.append(claim)

        total = len(claims)
        supported = sum(1 for v in verifications if v.supported)
        grounding_score = supported / total if total > 0 else 0.5

        # Also check for hallucination indicators
        hallucination_indicators = self._check_hallucination_indicators(
            ai_lower, clause_lower
        )

        passed = grounding_score >= self._min_grounding_threshold and not hallucination_indicators.get("severe", False)

        return GroundingValidationResult(
            clause_text=clause_text[:500],
            ai_output_text=ai_output_text[:1000],
            claims_verified=total,
            claims_supported=supported,
            claims_unsupported=len(unsupported),
            grounding_score=round(grounding_score, 3),
            passed=passed,
            verifications=verifications,
            unsupported_claims=unsupported,
            details={
                "hallucination_indicators": hallucination_indicators,
                "clause_key_phrases": clause_key_phrases[:15],
                "total_claims": total,
                "supported_claims": supported,
                "unsupported_claims": len(unsupported),
            },
        )

    def _extract_claims(self, text: str) -> List[str]:
        """Extract individual claims from AI output text.

        Splits the text into claim-like statements.

        Args:
            text: The AI-generated text.

        Returns:
            List of claim strings.
        """
        claims = []

        # Try to parse as JSON first
        try:
            data = json.loads(text)
            text = json.dumps(data, indent=2)
        except (json.JSONDecodeError, ValueError):
            pass

        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Filter for claim-like sentences (assertions, findings)
            if self._is_claim_sentence(sentence):
                claims.append(sentence)

        return claims

    def _is_claim_sentence(self, sentence: str) -> bool:
        """Determine if a sentence is a claim that needs verification.

        Args:
            sentence: The sentence to check.

        Returns:
            True if this is a claim-like sentence.
        """
        # Skip short sentences
        if len(sentence) < 15:
            return False

        # Skip instructions and formatting
        skip_patterns = [
            r"^output format",
            r"^respond with",
            r"^\{",
            r"^\}",
            r"^step \d+",
            r"^task",
            r"^example",
            r"^note:",
            r"^json",
        ]
        for pattern in skip_patterns:
            if re.match(pattern, sentence, re.IGNORECASE):
                return False

        # Claim indicators
        claim_indicators = [
            "is", "are", "was", "were", "has", "have", "had",
            "indicates", "suggests", "shows", "demonstrates",
            "poses", "creates", "results in", "leads to",
            "contains", "includes", "provides", "requires",
            "this clause", "the clause", "this provision",
            "the contract", "this agreement",
            "risk", "concern", "issue", "problem",
        ]

        sentence_lower = sentence.lower()
        return any(indicator in sentence_lower for indicator in claim_indicators)

    def _verify_claim(
        self,
        claim: str,
        clause_lower: str,
        clause_text: str,
        key_phrases: List[str],
    ) -> ClaimVerification:
        """Verify a single claim against the source clause text.

        Args:
            claim: The claim to verify.
            clause_lower: Lowercased clause text.
            clause_text: Original clause text.
            key_phrases: Key phrases extracted from clause.

        Returns:
            ClaimVerification with support status.
        """
        claim_lower = claim.lower()

        # Check for direct text overlap
        words_in_claim = set(claim_lower.split())
        words_in_clause = set(clause_lower.split())

        # Compute word overlap
        common_words = words_in_claim & words_in_clause
        overlap_ratio = len(common_words) / len(words_in_claim) if words_in_claim else 0

        # Check key phrase presence
        phrases_found = sum(1 for p in key_phrases if p.lower() in claim_lower)
        phrase_ratio = phrases_found / len(key_phrases) if key_phrases else 0

        # Find best evidence excerpt
        evidence = self._find_evidence_excerpt(claim_lower, clause_text)

        # Combined confidence
        confidence = max(overlap_ratio * 0.6 + phrase_ratio * 0.4, 0.0)
        supported = confidence >= 0.15

        reason_parts = []
        if supported:
            reason_parts.append(f"Word overlap: {overlap_ratio:.2f}")
            if phrases_found > 0:
                reason_parts.append(f"Key phrases matched: {phrases_found}")
        else:
            reason_parts.append("Insufficient evidence in clause text")
            if evidence:
                reason_parts.append("Partial match found but confidence low")

        return ClaimVerification(
            claim_text=claim[:200],
            supported=supported,
            evidence_excerpt=evidence[:200] if evidence else None,
            confidence=round(confidence, 3),
            reason="; ".join(reason_parts),
        )

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text for matching.

        Args:
            text: Text to extract phrases from.

        Returns:
            List of key phrase strings.
        """
        phrases = []

        # Extract quoted phrases
        quoted = re.findall(r'"([^"]+)"', text)
        phrases.extend(quoted)

        # Extract legal terms and noun phrases
        legal_terms = [
            "indemnify", "indemnification", "hold harmless",
            "liability", "liable", "damages",
            "termination", "terminate", "breach",
            "confidential", "confidentiality",
            "warrant", "warranty", "representation",
            "governing law", "jurisdiction", "venue",
            "force majeure", "assignment", "waiver",
            "limitation", "exclusion", "cap",
            "insurance", "compliance", "regulation",
        ]

        text_lower = text.lower()
        for term in legal_terms:
            if term in text_lower:
                # Find the actual occurrence for case preservation
                idx = text_lower.index(term)
                actual = text[idx:idx + len(term)]
                phrases.append(actual)

        # Extract capitalized phrases (proper nouns, defined terms)
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        phrases.extend(capitalized)

        # Remove duplicates, preserve order
        seen = set()
        unique_phrases = []
        for p in phrases:
            p_lower = p.lower().strip()
            if p_lower not in seen and len(p_lower) > 2:
                seen.add(p_lower)
                unique_phrases.append(p.strip())

        return unique_phrases[:20]

    def _find_evidence_excerpt(
        self, claim_lower: str, clause_text: str
    ) -> Optional[str]:
        """Find the best matching evidence excerpt in the clause text.

        Args:
            claim_lower: Lowercased claim text.
            clause_text: Original clause text.

        Returns:
            Best matching excerpt, or None.
        """
        clause_lower = clause_text.lower()

        # Try to find exact sentence match
        sentences = re.split(r'(?<=[.!?])\s+', clause_text)
        best_match = None
        best_score = 0.0

        for sentence in sentences:
            sentence_lower = sentence.lower()
            words_claim = set(claim_lower.split())
            words_sentence = set(sentence_lower.split())
            common = words_claim & words_sentence
            score = len(common) / len(words_claim) if words_claim else 0

            if score > best_score:
                best_score = score
                best_match = sentence

        return best_match if best_score >= 0.1 else None

    def _check_hallucination_indicators(
        self, ai_lower: str, clause_lower: str
    ) -> Dict[str, Any]:
        """Check for indicators of hallucination in AI output.

        Args:
            ai_lower: Lowercased AI output.
            clause_lower: Lowercased clause text.

        Returns:
            Dict with hallucination indicator flags.
        """
        indicators: Dict[str, Any] = {
            "severe": False,
            "warnings": [],
        }

        # Check for vague language without specifics
        vague_patterns = [
            "generally speaking", "in general", "it is important to note",
            "it should be noted", "as mentioned", "as stated",
        ]
        for pattern in vague_patterns:
            if pattern in ai_lower:
                indicators["warnings"].append(f"Vague language: '{pattern}'")

        # Check for references to information not in clause
        external_refs = [
            "according to industry standards",
            "industry practice",
            "market standard",
            "typical clause",
            "standard language",
        ]
        for ref in external_refs:
            if ref in ai_lower and ref not in clause_lower:
                indicators["warnings"].append(f"External reference: '{ref}'")

        # Check for invented specifics
        invented = [
            "section 1", "section 2", "paragraph (a)", "paragraph (b)",
            "subsection", "article 1",
        ]
        for inv in invented:
            if inv in ai_lower and inv not in clause_lower:
                indicators["warnings"].append(f"Possible invented reference: '{inv}'")

        # Severe hallucination if multiple warnings
        if len(indicators["warnings"]) >= 3:
            indicators["severe"] = True

        return indicators
