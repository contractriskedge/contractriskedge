"""Attorney-reviewed quality scoring for benchmark corpus entries.

Evaluates the quality of each clause before it enters the benchmark
corpus. Only clauses with a quality score > 0.85 are admitted.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import BenchmarkClause

logger = logging.getLogger(__name__)

# Quality threshold for corpus admission
QUALITY_THRESHOLD = 0.85


@dataclass
class QualityScore:
    """Detailed quality score for a benchmark clause."""

    overall: float = 0.0
    completeness: float = 0.0
    clarity: float = 0.0
    legal_coherence: float = 0.0
    no_ambiguity: float = 0.0
    proper_formatting: float = 0.0
    is_attorney_reviewed: bool = False
    review_notes: List[str] = field(default_factory=list)

    def passes_threshold(self, threshold: float = QUALITY_THRESHOLD) -> bool:
        """Check if the quality score meets the threshold.

        Args:
            threshold: Minimum overall score required.

        Returns:
            True if the score meets or exceeds the threshold.
        """
        return self.overall >= threshold


class QualityFilter:
    """Quality filter for benchmark corpus entries.

    Evaluates clause quality based on completeness, clarity, legal
    coherence, and proper formatting. Only admits clauses with a
    quality score > 0.85.

    Usage:
        filter = QualityFilter()
        score = filter.evaluate(clause)
        if score.passes_threshold():
            corpus.add(clause)
    """

    def __init__(self, threshold: float = QUALITY_THRESHOLD) -> None:
        """Initialize the quality filter.

        Args:
            threshold: Minimum quality score for admission.
        """
        self._threshold = threshold

    def evaluate(self, clause: BenchmarkClause) -> QualityScore:
        """Evaluate the quality of a benchmark clause.

        Args:
            clause: The clause to evaluate.

        Returns:
            QualityScore with detailed scoring breakdown.
        """
        text = clause.clause_text

        completeness = self._score_completeness(text)
        clarity = self._score_clarity(text)
        legal_coherence = self._score_legal_coherence(text)
        no_ambiguity = self._score_no_ambiguity(text)
        proper_formatting = self._score_formatting(text)

        # Weighted overall score
        overall = (
            completeness * 0.25
            + clarity * 0.20
            + legal_coherence * 0.25
            + no_ambiguity * 0.15
            + proper_formatting * 0.15
        )

        # Bonus for attorney-reviewed clauses
        if clause.is_attorney_reviewed:
            overall = min(1.0, overall + 0.05)

        review_notes = self._generate_notes(
            completeness, clarity, legal_coherence, no_ambiguity, proper_formatting
        )

        return QualityScore(
            overall=round(overall, 4),
            completeness=round(completeness, 4),
            clarity=round(clarity, 4),
            legal_coherence=round(legal_coherence, 4),
            no_ambiguity=round(no_ambiguity, 4),
            proper_formatting=round(proper_formatting, 4),
            is_attorney_reviewed=clause.is_attorney_reviewed,
            review_notes=review_notes,
        )

    @staticmethod
    def _score_completeness(text: str) -> float:
        """Score the completeness of a clause.

        A complete clause should have a minimum length, proper sentence
        structure, and defined terms.

        Args:
            text: The clause text.

        Returns:
            Score between 0 and 1.
        """
        score = 0.0
        stripped = text.strip()

        # Length check
        if len(stripped) < 50:
            return 0.1
        elif len(stripped) < 100:
            score += 0.3
        elif len(stripped) < 200:
            score += 0.5
        else:
            score += 0.8

        # Sentence structure
        sentences = re.split(r'[.!?]\s+', stripped)
        if len(sentences) >= 2:
            score += 0.1
        if len(sentences) >= 4:
            score += 0.05

        # Has defined terms (ALL CAPS phrases)
        if re.search(r'\b[A-Z][A-Z\s]{2,}[A-Z]\b', stripped):
            score += 0.05

        return min(1.0, score)

    @staticmethod
    def _score_clarity(text: str) -> float:
        """Score the clarity of clause language.

        Clear language avoids vague terms, uses precise definitions,
        and has logical flow.

        Args:
            text: The clause text.

        Returns:
            Score between 0 and 1.
        """
        score = 0.5

        # Penalize vague terms
        vague_terms = [
            r'\breasonable\s+(?:efforts?|endeavours?)\b(?!\s*commercially)',
            r'\bas\s+soon\s+as\s+(?:practicable|reasonably\s+practicable)\b',
            r'\bbest\s+efforts?\b',
            r'\bpromptly\b',
        ]
        for pattern in vague_terms:
            if re.search(pattern, text, re.IGNORECASE):
                score -= 0.1

        # Reward specific language
        specific_markers = [
            r'\b(?:shall|must|will)\b',
            r'\b(?:including|including\s+but\s+not\s+limited\s+to)\b',
            r'\b(?:provided\s+that|provided\s+however)\b',
            r'\b(?:notwithstanding|subject\s+to)\b',
            r'\bdays?\s+(?:prior|before|after|following)\b',
        ]
        for pattern in specific_markers:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.1

        return min(1.0, max(0.0, score))

    @staticmethod
    def _score_legal_coherence(text: str) -> float:
        """Score the legal coherence of a clause.

        Legally coherent clauses use proper legal terminology and
        follow standard legal drafting conventions.

        Args:
            text: The clause text.

        Returns:
            Score between 0 and 1.
        """
        score = 0.3

        # Legal drafting markers
        legal_markers = [
            r'\b(?:hereunder|thereof|thereunder|herein|therein)\b',
            r'\b(?:notwithstanding|subject\s+to|provided\s+that)\b',
            r'\b(?:indemnify|hold\s+harmless|defend)\b',
            r'\b(?:warrant|represent|covenant)\b',
            r'\b(?:terminat|breach|default|cure)\w+\b',
            r'\b(?:liability|indemnification|confidentiality)\b',
            r'\b(?:pursuant\s+to|in\s+accordance\s+with)\b',
            r'\([a-zA-Z0-9]+\)',  # Section references
        ]
        for pattern in legal_markers:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.1

        return min(1.0, score)

    @staticmethod
    def _score_no_ambiguity(text: str) -> float:
        """Score the lack of ambiguity in a clause.

        Penalizes ambiguous phrasing and rewards clear, unambiguous
        language.

        Args:
            text: The clause text.

        Returns:
            Score between 0 and 1.
        """
        score = 0.7

        # Penalize ambiguous phrases
        ambiguous = [
            r'\betc\.?\b',
            r'\band/ or\b',
            r'\bsuch\s+other\b',
            r'\bwhatsoever\b',
            r'\bhowsoever\s+arising\b',
        ]
        for pattern in ambiguous:
            if re.search(pattern, text, re.IGNORECASE):
                score -= 0.1

        # Reward explicit scope limitations
        scope_markers = [
            r'\b(?:solely|exclusively|only)\b',
            r'\b(?:to\s+the\s+extent|in\s+the\s+event)\b',
            r'\b(?:except|excluding|other\s+than)\b',
        ]
        for pattern in scope_markers:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.1

        return min(1.0, max(0.0, score))

    @staticmethod
    def _score_formatting(text: str) -> float:
        """Score the formatting quality of a clause.

        Well-formatted clauses have proper capitalization, section
        numbering, and paragraph structure.

        Args:
            text: The clause text.

        Returns:
            Score between 0 and 1.
        """
        score = 0.5

        # Proper capitalization
        if text[0].isupper():
            score += 0.1

        # Section numbering
        if re.search(r'\(\s*[a-zA-Z0-9]\s*\)', text):
            score += 0.15
        if re.search(r'(?:^|\n)\s*\d+\.\s+', text):
            score += 0.1

        # Defined terms in ALL CAPS
        if re.search(r'\b[A-Z]{3,}\b', text):
            score += 0.1

        # Paragraph breaks for long text
        if len(text) > 300 and '\n\n' in text:
            score += 0.05

        return min(1.0, score)

    @staticmethod
    def _generate_notes(
        completeness: float,
        clarity: float,
        legal_coherence: float,
        no_ambiguity: float,
        proper_formatting: float,
    ) -> List[str]:
        """Generate review notes based on dimension scores.

        Args:
            completeness: Completeness score.
            clarity: Clarity score.
            legal_coherence: Legal coherence score.
            no_ambiguity: Ambiguity score.
            proper_formatting: Formatting score.

        Returns:
            List of review note strings.
        """
        notes: List[str] = []

        if completeness < 0.5:
            notes.append("Clause appears incomplete or too short")
        elif completeness < 0.7:
            notes.append("Clause could benefit from more detail")

        if clarity < 0.5:
            notes.append("Language is vague — consider more specific terms")
        elif clarity < 0.7:
            notes.append("Some terms could be more precisely defined")

        if legal_coherence < 0.5:
            notes.append("Lacks standard legal drafting conventions")
        elif legal_coherence < 0.7:
            notes.append("Could use more precise legal terminology")

        if no_ambiguity < 0.5:
            notes.append("Contains ambiguous language that may cause disputes")

        if proper_formatting < 0.5:
            notes.append("Formatting does not follow legal drafting standards")

        return notes

    def should_admit(self, score: QualityScore) -> bool:
        """Determine if a clause should be admitted to the corpus.

        Args:
            score: The quality score.

        Returns:
            True if the clause meets the quality threshold.
        """
        return score.passes_threshold(self._threshold)

    @property
    def threshold(self) -> float:
        """Get the current quality threshold.

        Returns:
            The quality threshold value.
        """
        return self._threshold
