"""Retrieval grounding validation — claim-to-clause source matching.

Provides claim-to-clause source matching that ensures each risk flag
links to specific clauses in the source contract. Validates that
retrieved evidence supports the generated analysis.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class EvidenceLink:
    """A link between a claim and evidence in the source contract."""

    claim_text: str
    evidence_text: str
    chunk_id: str
    relevance_score: float
    match_type: str  # exact, semantic, partial


@dataclass
class GroundingValidationResult:
    """Result of grounding validation for a retrieval-augmented generation."""

    total_claims: int
    grounded_claims: int
    ungrounded_claims: int
    grounding_score: float
    evidence_links: List[EvidenceLink]
    ungrounded_claims_list: List[str]
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)


class RetrievalGroundingValidator:
    """Validates that generated claims are grounded in retrieved evidence.

    Performs claim-to-clause source matching:
    1. Extracts claims from generated analysis.
    2. Matches each claim against retrieved chunks.
    3. Computes grounding score based on evidence support.
    4. Produces evidence links for each grounded claim.

    Usage:
        validator = RetrievalGroundingValidator()
        result = validator.validate(
            generated_text="...",
            retrieved_chunks=[...],
        )
        print(f"Grounding score: {result.grounding_score}")
        print(f"Evidence links: {len(result.evidence_links)}")
    """

    def __init__(
        self,
        min_grounding_threshold: float = 0.3,
        min_relevance_score: float = 0.15,
    ) -> None:
        """Initialize the retrieval grounding validator.

        Args:
            min_grounding_threshold: Minimum grounding score to pass.
            min_relevance_score: Minimum relevance for evidence link.
        """
        self._min_grounding_threshold = min_grounding_threshold
        self._min_relevance_score = min_relevance_score

    def validate(
        self,
        generated_text: str,
        retrieved_chunks: List[RetrievedChunk],
    ) -> GroundingValidationResult:
        """Validate grounding of generated text against retrieved chunks.

        Args:
            generated_text: The AI-generated analysis text.
            retrieved_chunks: The retrieved evidence chunks.

        Returns:
            GroundingValidationResult with evidence links and score.
        """
        # Extract claims from generated text
        claims = self._extract_claims(generated_text)

        evidence_links: List[EvidenceLink] = []
        ungrounded: List[str] = []

        for claim in claims:
            best_match = self._find_best_evidence(claim, retrieved_chunks)

            if best_match and best_match["score"] >= self._min_relevance_score:
                evidence_links.append(
                    EvidenceLink(
                        claim_text=claim[:200],
                        evidence_text=best_match["text"][:300],
                        chunk_id=best_match["chunk_id"],
                        relevance_score=round(best_match["score"], 3),
                        match_type=best_match["match_type"],
                    )
                )
            else:
                ungrounded.append(claim)

        total = len(claims)
        grounded = len(evidence_links)
        grounding_score = grounded / total if total > 0 else 0.5
        passed = grounding_score >= self._min_grounding_threshold

        return GroundingValidationResult(
            total_claims=total,
            grounded_claims=grounded,
            ungrounded_claims=len(ungrounded),
            grounding_score=round(grounding_score, 3),
            evidence_links=evidence_links,
            ungrounded_claims_list=ungrounded,
            passed=passed,
            details={
                "min_grounding_threshold": self._min_grounding_threshold,
                "min_relevance_score": self._min_relevance_score,
                "total_chunks_retrieved": len(retrieved_chunks),
                "claims_with_evidence": [
                    {"claim": e.claim_text, "match_type": e.match_type, "score": e.relevance_score}
                    for e in evidence_links
                ],
            },
        )

    def _extract_claims(self, text: str) -> List[str]:
        """Extract individual claims from generated text.

        Args:
            text: The generated analysis text.

        Returns:
            List of claim strings.
        """
        claims = []

        # Try to parse as JSON first
        try:
            data = json.loads(text)
            # Flatten JSON values into text
            text = self._flatten_json_to_text(data)
        except (json.JSONDecodeError, ValueError):
            pass

        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Filter for substantive claim sentences
            if self._is_substantive_claim(sentence):
                claims.append(sentence)

        return claims

    def _flatten_json_to_text(self, data: Any, depth: int = 0) -> str:
        """Flatten JSON data into text for claim extraction.

        Args:
            data: JSON data to flatten.
            depth: Current recursion depth.

        Returns:
            Flattened text string.
        """
        if depth > 3:
            return ""

        if isinstance(data, dict):
            parts = []
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    parts.append(str(value))
                elif isinstance(value, (list, dict)):
                    parts.append(self._flatten_json_to_text(value, depth + 1))
            return " ".join(parts)

        if isinstance(data, list):
            return " ".join(
                self._flatten_json_to_text(item, depth + 1)
                for item in data
                if isinstance(item, (dict, str))
            )

        if isinstance(data, str):
            return data

        return str(data)

    def _is_substantive_claim(self, sentence: str) -> bool:
        """Determine if a sentence is a substantive claim.

        Args:
            sentence: The sentence to check.

        Returns:
            True if this is a substantive claim.
        """
        if len(sentence) < 20:
            return False

        # Skip non-claim patterns
        skip_patterns = [
            r"^\{", r"^\}", r"^\[", r"^\]",
            r"^output format", r"^respond with",
            r"^json", r"^note:",
            r"^example \d+",
        ]
        for pattern in skip_patterns:
            if re.match(pattern, sentence, re.IGNORECASE):
                return False

        # Must contain claim-like verbs or content
        claim_indicators = [
            "is", "are", "was", "were", "has", "have",
            "indicates", "suggests", "shows", "demonstrates",
            "contains", "includes", "provides", "requires",
            "poses", "creates", "results", "leads",
            "this clause", "the clause", "this provision",
            "risk", "concern", "issue",
        ]

        sentence_lower = sentence.lower()
        return any(indicator in sentence_lower for indicator in claim_indicators)

    def _find_best_evidence(
        self,
        claim: str,
        chunks: List[RetrievedChunk],
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching evidence for a claim from retrieved chunks.

        Args:
            claim: The claim to match.
            chunks: Retrieved evidence chunks.

        Returns:
            Dict with best match info, or None.
        """
        claim_lower = claim.lower()
        claim_words = set(claim_lower.split())

        best_match = None
        best_score = 0.0

        for chunk in chunks:
            chunk_lower = chunk.text.lower()
            chunk_words = set(chunk_lower.split())

            # Compute word overlap
            common_words = claim_words & chunk_words
            overlap_score = len(common_words) / len(claim_words) if claim_words else 0

            # Compute phrase overlap (2-3 word phrases)
            claim_phrases = self._extract_ngrams(claim_lower, 2, 3)
            chunk_phrases = self._extract_ngrams(chunk_lower, 2, 3)
            common_phrases = claim_phrases & chunk_phrases
            phrase_score = len(common_phrases) / len(claim_phrases) if claim_phrases else 0

            # Combined score
            combined_score = overlap_score * 0.5 + phrase_score * 0.3 + (chunk.score or 0) * 0.2

            if combined_score > best_score:
                best_score = combined_score
                best_match = {
                    "text": chunk.text,
                    "chunk_id": chunk.chunk_id,
                    "score": combined_score,
                    "match_type": "exact" if combined_score >= 0.5
                    else "semantic" if combined_score >= 0.25
                    else "partial",
                }

        return best_match

    def _extract_ngrams(
        self, text: str, min_n: int, max_n: int
    ) -> set:
        """Extract n-grams from text.

        Args:
            text: Text to extract n-grams from.
            min_n: Minimum n-gram size.
            max_n: Maximum n-gram size.

        Returns:
            Set of n-gram strings.
        """
        words = text.split()
        ngrams = set()

        for n in range(min_n, min(max_n + 1, len(words) + 1)):
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i + n])
                if len(ngram) > 3:  # Skip very short n-grams
                    ngrams.add(ngram)

        return ngrams

    def validate_risk_flag(
        self,
        clause_text: str,
        risk_flag_data: Dict[str, Any],
    ) -> GroundingValidationResult:
        """Validate that a risk flag's claims are grounded in the clause.

        Convenience method for validating individual risk flags.

        Args:
            clause_text: The source clause text.
            risk_flag_data: The risk flag data dict.

        Returns:
            GroundingValidationResult.
        """
        # Construct a RetrievedChunk from the clause text
        chunk = RetrievedChunk(
            chunk_id="source_clause",
            text=clause_text,
            score=1.0,
            metadata={"source": "contract", "type": "clause"},
        )

        # Extract all text fields from risk flag data
        text_parts = []
        for field in ["why_flagged", "rationale", "suggested_remediation",
                       "potential_business_impact", "market_benchmark_comparison"]:
            value = risk_flag_data.get(field, "")
            if value:
                text_parts.append(str(value))

        generated_text = "\n".join(text_parts)

        return self.validate(generated_text, [chunk])
