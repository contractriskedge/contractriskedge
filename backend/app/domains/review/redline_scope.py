"""Redline Scope Accuracy — ensures AI modifies ONLY the intended clause.

Provides:
- Sentence boundary detection
- Clause segmentation
- Localized replacement validation
- Similarity validation to prevent over-reach

This prevents the common issue where AI redlines replace too much or too
little text, causing loss of context or broken clauses.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)


# ── Sentence Boundary Detection ───────────────────────────────────


# Common sentence-ending patterns
SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'({])')
# Clause boundary indicators
CLAUSE_BOUNDARIES = re.compile(
    r'(?i)\b(?:provided\s+that|however|notwithstanding|subject\s+to|'
    r'except\s+as|in\s+the\s+event\s+that|if\s+|whereas|'
    r'where|when|unless|but\s+only|without\s+limiting|'
    r'for\s+the\s+purpose|in\s+respect\s+of|with\s+respect\s+to)\b'
)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using boundary detection.

    Handles common legal abbreviations and edge cases.
    """
    # Protect common legal abbreviations
    protected = text
    protected = re.sub(r'(?i)\b(e\.g\.|i\.e\.|etc\.|vs\.|Mr\.|Mrs\.|Dr\.|Inc\.|Ltd\.|Corp\.|LLC\.|Co\.)', 
                       lambda m: m.group(0).replace('.', '\x00'), protected)
    
    # Split on sentence boundaries
    parts = SENTENCE_END.split(protected)
    
    # Restore periods
    result = [p.replace('\x00', '.') for p in parts if p.strip()]
    return result


def split_clauses(text: str) -> list[str]:
    """Split text into clauses at boundary indicators.

    Returns a list of clause segments, preserving the boundary marker
    at the start of each segment for context.
    """
    segments = []
    parts = CLAUSE_BOUNDARIES.split(text)
    
    if len(parts) <= 1:
        return [text.strip()]
    
    # Rebuild segments with boundary markers
    current = parts[0]
    for i in range(1, len(parts)):
        boundary = parts[i]
        # Check if this part starts with a boundary word
        match = CLAUSE_BOUNDARIES.match(boundary)
        if match:
            if current.strip():
                segments.append(current.strip())
            current = boundary
        else:
            current += " " + boundary
    
    if current.strip():
        segments.append(current.strip())
    
    return segments


# ── Localized Replacement ─────────────────────────────────────────


def find_localized_replacement(
    original_text: str,
    proposed_text: str,
    full_document_text: Optional[str] = None,
) -> dict:
    """Find the safest localized replacement within a document.

    Ensures the replacement targets ONLY the intended clause/sentence
    and doesn't over-reach into surrounding context.

    Returns:
        dict with:
        - 'replacement_text': the text to replace
        - 'context_before': text before the replacement for anchoring
        - 'context_after': text after the replacement for anchoring
        - 'confidence': float 0-1 indicating match quality
        - 'scope': 'exact' | 'sentence' | 'clause' | 'paragraph'
    """
    result = {
        "replacement_text": original_text,
        "context_before": "",
        "context_after": "",
        "confidence": 1.0,
        "scope": "exact",
    }

    if not full_document_text:
        return result

    # Try exact match first
    if original_text in full_document_text:
        idx = full_document_text.index(original_text)
        result["context_before"] = _get_context(full_document_text, idx, before=True)
        result["context_after"] = _get_context(full_document_text, idx + len(original_text), before=False)
        result["confidence"] = 1.0
        result["scope"] = "exact"
        return result

    # Try sentence-level match
    sentences = split_sentences(full_document_text)
    for sentence in sentences:
        if original_text in sentence:
            result["replacement_text"] = sentence
            result["confidence"] = 0.95
            result["scope"] = "sentence"
            idx = full_document_text.index(sentence)
            result["context_before"] = _get_context(full_document_text, idx, before=True)
            result["context_after"] = _get_context(full_document_text, idx + len(sentence), before=False)
            return result

    # Try clause-level match
    clauses = split_clauses(full_document_text)
    for clause in clauses:
        if original_text in clause:
            result["replacement_text"] = clause
            result["confidence"] = 0.85
            result["scope"] = "clause"
            idx = full_document_text.index(clause)
            result["context_before"] = _get_context(full_document_text, idx, before=True)
            result["context_after"] = _get_context(full_document_text, idx + len(clause), before=False)
            return result

    # Fuzzy match — find best similarity
    best_ratio = 0.0
    best_match = ""
    for sentence in sentences:
        ratio = SequenceMatcher(None, original_text, sentence).ratio()
        if ratio > best_ratio and ratio > 0.6:
            best_ratio = ratio
            best_match = sentence

    if best_match:
        result["replacement_text"] = best_match
        result["confidence"] = best_ratio
        result["scope"] = "fuzzy"
        idx = full_document_text.index(best_match) if best_match in full_document_text else 0
        result["context_before"] = _get_context(full_document_text, idx, before=True)
        result["context_after"] = _get_context(full_document_text, idx + len(best_match), before=False)

    return result


def _get_context(text: str, position: int, before: bool = True, max_chars: int = 100) -> str:
    """Get surrounding context text for anchoring."""
    if before:
        start = max(0, position - max_chars)
        return text[start:position].strip()
    else:
        end = min(len(text), position + max_chars)
        return text[position:end].strip()


# ── Similarity Validation ─────────────────────────────────────────


def validate_redline_scope(
    original_text: str,
    proposed_text: str,
    full_document_text: Optional[str] = None,
    min_similarity: float = 0.3,
) -> dict:
    """Validate that a redline's scope is appropriate.

    Checks:
    1. The original text exists (or is similar to) the document
    2. The proposed change is not excessively larger than original
    3. The change is localized (not replacing entire document)

    Returns:
        dict with:
        - 'valid': bool
        - 'issues': list[str] of validation issues
        - 'suggested_scope': str suggesting how to fix
    """
    issues = []
    result = {
        "valid": True,
        "issues": issues,
        "suggested_scope": None,
    }

    # Check 1: Length ratio — proposed shouldn't be way larger than original
    if len(proposed_text) > len(original_text) * 5 and len(original_text) > 0:
        issues.append(
            f"Proposed text ({len(proposed_text)} chars) is >5x longer than "
            f"original ({len(original_text)} chars). May be over-reaching."
        )
        result["suggested_scope"] = "sentence"

    # Check 2: Original text too short — may be ambiguous
    if len(original_text) < 20:
        issues.append(
            f"Original text is very short ({len(original_text)} chars). "
            f"Consider including more context for accurate matching."
        )
        result["suggested_scope"] = "clause"

    # Check 3: If full document text available, verify match quality
    if full_document_text:
        if original_text in full_document_text:
            pass  # Exact match — good
        else:
            # Check similarity
            sentences = split_sentences(full_document_text)
            best_ratio = max(
                (SequenceMatcher(None, original_text, s).ratio() for s in sentences),
                default=0.0,
            )
            if best_ratio < min_similarity:
                issues.append(
                    f"Original text has low similarity ({best_ratio:.2f}) to any "
                    f"sentence in the document. May not be found during replacement."
                )
                result["suggested_scope"] = "exact"
            elif best_ratio < 0.6:
                issues.append(
                    f"Original text similarity ({best_ratio:.2f}) is moderate. "
                    f"Consider verifying the match."
                )

    # Check 4: Proposed text is too similar to original (no meaningful change)
    similarity = SequenceMatcher(None, original_text, proposed_text).ratio()
    if similarity > 0.95 and len(original_text) > 0:
        issues.append(
            f"Proposed text is {similarity:.1%} similar to original. "
            f"Change may be too minor to justify a redline."
        )

    result["valid"] = len(issues) == 0
    return result


# ── Redline Text Resolution ───────────────────────────────────────


def resolve_redline_text(
    original_text: str,
    proposed_text: str,
    full_document_text: Optional[str] = None,
) -> dict:
    """Resolve the final text that should be used for a redline replacement.

    Uses scope detection to ensure the replacement is localized correctly.
    Returns the exact text to replace and the replacement text.
    """
    scope_info = find_localized_replacement(original_text, proposed_text, full_document_text)
    validation = validate_redline_scope(original_text, proposed_text, full_document_text)

    return {
        "find_text": scope_info["replacement_text"],
        "replace_with": proposed_text,
        "scope": scope_info["scope"],
        "confidence": scope_info["confidence"],
        "context_before": scope_info["context_before"],
        "context_after": scope_info["context_after"],
        "validation": validation,
    }
