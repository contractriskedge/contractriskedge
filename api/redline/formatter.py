"""Redline output formatter: original vs. proposed with rationale.

Formats redline suggestions into a structured output with original text,
proposed text, change type, word diff, rationale, confidence score,
and attorney review flag.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import (
    RedlineSuggestion,
    RedlineRequest,
    ClauseType,
    ChangeType,
)
from .diff_engine import DiffEngine, WordDiff

logger = logging.getLogger(__name__)


@dataclass
class FormattedRedline:
    """Complete formatted redline output with all display fields."""

    original_text: str
    proposed_text: str
    change_type: str
    word_diff: str
    word_diff_details: List[Dict[str, Any]]
    rationale: str
    confidence: float
    attorney_review_required: bool
    risk_impact: str
    issues_found: List[Dict[str, Any]]
    negotiation_strategy: Optional[Dict[str, Any]] = None
    market_context: Optional[str] = None
    diff_stats: Dict[str, int] = field(default_factory=dict)
    processing_metadata: Dict[str, Any] = field(default_factory=dict)


class RedlineFormatter:
    """Formats raw LLM redline output into structured redline suggestions.

    Takes the JSON output from an LLM redline prompt and transforms it
    into a FormattedRedline with computed word diffs and quality checks.

    Usage:
        formatter = RedlineFormatter()
        formatted = formatter.format_redline(
            original_text=original,
            llm_output=llm_json,
            request=redline_request,
        )
        suggestion = formatter.to_suggestion(formatted, contract_id)
    """

    def __init__(self) -> None:
        """Initialize the redline formatter with a diff engine."""
        self._diff_engine = DiffEngine()

    def format_redline(
        self,
        original_text: str,
        llm_output: Dict[str, Any],
        request: RedlineRequest,
        processing_time_ms: int = 0,
    ) -> FormattedRedline:
        """Format raw LLM output into a structured redline.

        Args:
            original_text: The original clause text.
            llm_output: The parsed JSON output from the LLM.
            request: The original redline request.
            processing_time_ms: Time taken to generate the suggestion.

        Returns:
            A FormattedRedline with all display fields populated.

        Raises:
            ValueError: If required fields are missing from LLM output.
        """
        proposed_text = llm_output.get("proposed_text", "")
        if not proposed_text:
            raise ValueError("LLM output missing required field: proposed_text")

        rationale = llm_output.get("rationale", "")
        if not rationale:
            raise ValueError("LLM output missing required field: rationale")

        # Compute word diff
        word_diffs = self._diff_engine.compute_word_diff(
            original_text, proposed_text
        )
        diff_stats = self._diff_engine.compute_diff_stats(word_diffs)
        word_diff_summary = self._diff_engine.get_word_diff_summary(
            original_text, proposed_text
        )

        # Determine change type
        change_type = llm_output.get(
            "change_type",
            self._diff_engine.compute_change_type(
                original_text, proposed_text, word_diffs
            ),
        )

        # Parse confidence
        confidence = float(llm_output.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        # Parse attorney review flag
        attorney_review = bool(
            llm_output.get("attorney_review_required", True)
        )

        # Parse risk impact
        risk_impact = llm_output.get("risk_impact", "medium")
        valid_impacts = {"critical", "high", "medium", "low"}
        if risk_impact not in valid_impacts:
            risk_impact = "medium"

        # Parse issues
        issues_found = llm_output.get("issues_found", [])

        # Parse optional fields
        negotiation_strategy = llm_output.get("negotiation_strategy")
        market_context = llm_output.get("market_context")

        # Build word diff details
        word_diff_details = [
            {
                "operation": wd.operation.value,
                "text": wd.text,
                "position": wd.position,
            }
            for wd in word_diffs
        ]

        return FormattedRedline(
            original_text=original_text,
            proposed_text=proposed_text,
            change_type=change_type,
            word_diff=word_diff_summary,
            word_diff_details=word_diff_details,
            rationale=rationale,
            confidence=confidence,
            attorney_review_required=attorney_review,
            risk_impact=risk_impact,
            issues_found=issues_found,
            negotiation_strategy=negotiation_strategy,
            market_context=market_context,
            diff_stats=diff_stats,
            processing_metadata={
                "processing_time_ms": processing_time_ms,
                "clause_type": request.clause_type.value,
                "party_role": request.party_role.value,
                "deal_size_tier": request.deal_size_tier.value,
                "industry": request.industry.value,
                "jurisdiction": request.jurisdiction,
            },
        )

    def to_suggestion(
        self,
        formatted: FormattedRedline,
        contract_id: str,
        clause_type: ClauseType,
    ) -> RedlineSuggestion:
        """Convert a FormattedRedline to a RedlineSuggestion model.

        Args:
            formatted: The formatted redline output.
            contract_id: The contract identifier.
            clause_type: The type of clause.

        Returns:
            A RedlineSuggestion Pydantic model instance.
        """
        return RedlineSuggestion(
            contract_id=contract_id,
            clause_type=clause_type,
            original_text=formatted.original_text,
            proposed_text=formatted.proposed_text,
            change_type=formatted.change_type,
            word_diff=formatted.word_diff,
            rationale=formatted.rationale,
            confidence=formatted.confidence,
            attorney_review_required=formatted.attorney_review_required,
            risk_impact=formatted.risk_impact,
            metadata={
                "diff_stats": formatted.diff_stats,
                "issues_found": formatted.issues_found,
                "negotiation_strategy": formatted.negotiation_strategy,
                "market_context": formatted.market_context,
                "word_diff_details": formatted.word_diff_details,
                "processing_metadata": formatted.processing_metadata,
            },
        )

    def to_dict(self, formatted: FormattedRedline) -> Dict[str, Any]:
        """Convert FormattedRedline to a serializable dict.

        Args:
            formatted: The formatted redline output.

        Returns:
            Dict representation suitable for JSON serialization.
        """
        return {
            "original_text": formatted.original_text,
            "proposed_text": formatted.proposed_text,
            "change_type": formatted.change_type,
            "word_diff": formatted.word_diff,
            "word_diff_details": formatted.word_diff_details,
            "rationale": formatted.rationale,
            "confidence": formatted.confidence,
            "attorney_review_required": formatted.attorney_review_required,
            "risk_impact": formatted.risk_impact,
            "issues_found": formatted.issues_found,
            "negotiation_strategy": formatted.negotiation_strategy,
            "market_context": formatted.market_context,
            "diff_stats": formatted.diff_stats,
            "processing_metadata": formatted.processing_metadata,
        }

    def format_batch(
        self,
        original_text: str,
        llm_outputs: List[Dict[str, Any]],
        request: RedlineRequest,
        processing_time_ms: int = 0,
    ) -> List[FormattedRedline]:
        """Format multiple LLM outputs for the same original text.

        Useful for generating multiple alternative suggestions.

        Args:
            original_text: The original clause text.
            llm_outputs: List of parsed LLM outputs.
            request: The original redline request.
            processing_time_ms: Base processing time.

        Returns:
            List of FormattedRedline objects.
        """
        return [
            self.format_redline(
                original_text=original_text,
                llm_output=output,
                request=request,
                processing_time_ms=processing_time_ms,
            )
            for output in llm_outputs
        ]
