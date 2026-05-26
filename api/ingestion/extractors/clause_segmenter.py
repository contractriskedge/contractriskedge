"""ML-based clause boundary detection using spaCy.

Identifies clause boundaries in contract text using a combination
of rule-based patterns and spaCy's linguistic features. Detects
common contract clause structures including definitions,
representations, warranties, indemnification, and termination.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ingestion.extractors.models import ExtractedPage

logger = logging.getLogger(__name__)


class ClauseSegmenterError(Exception):
    """Raised when clause segmentation fails."""


# Common contract clause heading patterns
CLAUSE_HEADING_PATTERNS = [
    # Numbered clauses: "1.", "1.1", "Section 1.1", "ARTICLE I"
    re.compile(r"^(?:Section\s+)?(\d+(?:\.\d+)*)\s+[\.\)]\s+(.+)$", re.IGNORECASE),
    re.compile(r"^(?:ARTICLE|SECTION|CLAUSE)\s+([IVXLCDM]+|\d+)\s*[:\-–]\s*(.+)$", re.IGNORECASE),
    re.compile(r"^(\d+\.\d+(?:\.\d+)*)\s+(.+)$"),
    # All-caps headings: "DEFINITIONS", "REPRESENTATIONS AND WARRANTIES"
    re.compile(r"^([A-Z][A-Z\s&,]+)$"),
    # Capitalized phrase followed by colon
    re.compile(r"^([A-Z][a-zA-Z\s]+):\s*$"),
    # "X. Title" pattern
    re.compile(r"^([IVXLCDM]+)\.\s+(.+)$"),
]

# Clause types commonly found in contracts
CLAUSE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "definitions": ["definition", "defined", "means", "meaning", "herein"],
    "representations": ["represent", "warrant", "represents", "warrants"],
    "indemnification": ["indemnif", "hold harmless", "indemnity"],
    "termination": ["terminat", "termination", "terminate", "expiration"],
    "confidentiality": ["confidential", "non-disclosure", "proprietary"],
    "payment": ["payment", "fee", "compensation", "invoice", "payable"],
    "liability": ["liability", "limitation", "damages", "indemnify"],
    "governing_law": ["governing law", "jurisdiction", "venue"],
    "force_majeure": ["force majeure", "act of god"],
    "assignment": ["assignment", "assign", "delegate"],
    "entire_agreement": ["entire agreement", "merger", "integration"],
    "amendment": ["amendment", "modification", "waiver"],
    "notice": ["notice", "notices", "notification"],
    "dispute_resolution": ["dispute", "arbitration", "mediation", "litigation"],
    "insurance": ["insurance", "coverage", "policy"],
}


class ClauseBoundary:
    """Represents a detected clause boundary in the document."""

    def __init__(
        self,
        start_char: int,
        end_char: int,
        heading: Optional[str] = None,
        section_number: Optional[str] = None,
        level: int = 1,
        clause_type: Optional[str] = None,
        confidence: float = 1.0,
    ) -> None:
        self.start_char = start_char
        self.end_char = end_char
        self.heading = heading
        self.section_number = section_number
        self.level = level
        self.clause_type = clause_type
        self.confidence = confidence


class ClauseSegmenter:
    """Detects clause boundaries in contract text using ML and rules.

    Uses spaCy for linguistic analysis combined with regex patterns
    to identify clause headings, boundaries, and types. Supports
    nested clause hierarchies.

    Attributes:
        min_clause_chars: Minimum characters for a valid clause (default 20).
        max_clause_chars: Maximum characters before forcing a split (default 5000).
        use_spacy: Whether to use spaCy for enhanced detection (default True).
    """

    def __init__(
        self,
        min_clause_chars: int = 20,
        max_clause_chars: int = 5000,
        use_spacy: bool = True,
    ) -> None:
        """Initialize the clause segmenter.

        Args:
            min_clause_chars: Minimum characters to consider a clause.
            max_clause_chars: Maximum characters before forcing a split.
            use_spacy: Whether to use spaCy for linguistic features.
        """
        self.min_clause_chars = min_clause_chars
        self.max_clause_chars = max_clause_chars
        self.use_spacy = use_spacy
        self._nlp: Any = None

    def _get_nlp(self) -> Any:
        """Lazy-load the spaCy language model.

        Returns:
            The spaCy language model, or None if unavailable.
        """
        if self._nlp is not None:
            return self._nlp

        if not self.use_spacy:
            return None

        try:
            import spacy

            try:
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning(
                    "spaCy model 'en_core_web_sm' not found. "
                    "Install with: python -m spacy download en_core_web_sm"
                )
                self._nlp = spacy.blank("en")
            return self._nlp
        except ImportError:
            logger.warning(
                "spaCy not installed. Clause segmentation will use "
                "rule-based detection only."
            )
            return None

    def segment(
        self,
        pages: List[ExtractedPage],
    ) -> List[Dict[str, Any]]:
        """Segment document pages into clauses.

        Processes extracted pages and identifies clause boundaries
        using heading detection, pattern matching, and optional
        spaCy-based linguistic analysis.

        Args:
            pages: List of extracted pages from the document.

        Returns:
            List of clause dicts with keys:
                - clause_id: str
                - text: str
                - section_number: Optional[str]
                - heading: Optional[str]
                - page_number: int
                - start_char: int
                - end_char: int
                - level: int
                - clause_type: Optional[str]
                - confidence: float
                - metadata: dict

        Raises:
            ClauseSegmenterError: If segmentation fails catastrophically.
        """
        if not pages:
            logger.warning("No pages provided for clause segmentation")
            return []

        nlp = self._get_nlp()

        # Build full text with page boundaries
        full_text_parts: List[Tuple[str, int]] = []
        total_offset = 0
        page_offsets: List[Tuple[int, int, int]] = []  # (page_num, start_offset, end_offset)

        for page in pages:
            page_start = total_offset
            page_text = page.text
            full_text_parts.append((page_text, page.page_number))
            page_end = total_offset + len(page_text)
            page_offsets.append((page.page_number, page_start, page_end))
            total_offset += len(page_text) + 1  # +1 for separator
            full_text_parts.append(("\n", page.page_number))

        full_text = "".join(part[0] for part in full_text_parts)

        # Find clause boundaries
        boundaries = self._find_boundaries(full_text, nlp)

        if not boundaries:
            # No structured clauses found; treat entire document as one clause
            logger.info("No clause boundaries detected; treating document as single clause")
            boundaries = [
                ClauseBoundary(
                    start_char=0,
                    end_char=len(full_text),
                    heading=None,
                    section_number=None,
                    level=1,
                    clause_type=None,
                    confidence=0.5,
                )
            ]

        # Build clause dicts
        clauses: List[Dict[str, Any]] = []
        for i, boundary in enumerate(boundaries):
            # Determine page number from character offset
            page_number = 1
            for p_num, p_start, p_end in page_offsets:
                if p_start <= boundary.start_char < p_end:
                    page_number = p_num
                    break

            clause_text = full_text[boundary.start_char : boundary.end_char].strip()

            if len(clause_text) < self.min_clause_chars and i > 0:
                # Merge with previous clause if too short
                if clauses:
                    clauses[-1]["text"] += "\n" + clause_text
                    clauses[-1]["end_char"] = boundary.end_char
                continue

            clause_type = boundary.clause_type or self._detect_clause_type(clause_text)

            clause = {
                "clause_id": f"clause_{i + 1:04d}",
                "text": clause_text,
                "section_number": boundary.section_number,
                "heading": boundary.heading,
                "page_number": page_number,
                "start_char": boundary.start_char,
                "end_char": boundary.end_char,
                "level": boundary.level,
                "clause_type": clause_type,
                "confidence": boundary.confidence,
                "metadata": {
                    "char_length": len(clause_text),
                    "word_count": len(clause_text.split()),
                },
            }
            clauses.append(clause)

        logger.info(
            "Clause segmentation complete: %d clauses from %d pages",
            len(clauses),
            len(pages),
        )
        return clauses

    def _find_boundaries(
        self,
        text: str,
        nlp: Any,
    ) -> List[ClauseBoundary]:
        """Find clause boundary positions in text.

        Uses heading patterns, numbered section detection, and
        linguistic cues to identify where clauses begin and end.

        Args:
            text: Full document text.
            nlp: spaCy language model (or None).

        Returns:
            List of ClauseBoundary objects sorted by position.
        """
        lines = text.split("\n")
        boundaries: List[ClauseBoundary] = []
        current_pos = 0

        for line_idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                current_pos += len(line) + 1
                continue

            match = self._match_clause_heading(stripped)
            if match:
                section_number = match.get("section_number")
                heading = match.get("heading")
                level = match.get("level", 1)
                confidence = match.get("confidence", 0.8)

                boundary = ClauseBoundary(
                    start_char=current_pos,
                    end_char=current_pos + len(line),
                    heading=heading,
                    section_number=section_number,
                    level=level,
                    confidence=confidence,
                )
                boundaries.append(boundary)

            current_pos += len(line) + 1

        # Set end_char for each boundary to the start of the next
        for i in range(len(boundaries) - 1):
            boundaries[i].end_char = boundaries[i + 1].start_char - 1

        # Set the last boundary's end_char to the end of text
        if boundaries:
            boundaries[-1].end_char = len(text)

        # Use spaCy for additional sentence-boundary detection
        # within large unbroken text blocks
        if nlp and not boundaries:
            boundaries = self._detect_sentence_boundaries(text, nlp)

        return boundaries

    def _match_clause_heading(self, line: str) -> Optional[Dict[str, Any]]:
        """Match a line against known clause heading patterns.

        Args:
            line: A single line of text.

        Returns:
            Dict with section_number, heading, level, confidence if matched.
        """
        for pattern in CLAUSE_HEADING_PATTERNS:
            match = pattern.match(line)
            if match:
                groups = match.groups()

                if len(groups) == 2:
                    section_number, heading = groups
                    return {
                        "section_number": section_number.strip(),
                        "heading": heading.strip(),
                        "level": section_number.count(".") + 1,
                        "confidence": 0.9,
                    }
                elif len(groups) == 1:
                    return {
                        "section_number": None,
                        "heading": groups[0].strip(),
                        "level": 1,
                        "confidence": 0.7,
                    }

        return None

    def _detect_sentence_boundaries(
        self,
        text: str,
        nlp: Any,
    ) -> List[ClauseBoundary]:
        """Detect clause boundaries using spaCy sentence segmentation.

        Used as a fallback when no heading-based structure is found.

        Args:
            text: Full document text.
            nlp: spaCy language model.

        Returns:
            List of ClauseBoundary objects.
        """
        boundaries: List[ClauseBoundary] = []

        try:
            doc = nlp(text[:100000])  # Limit to 100k chars for performance
            for sent in doc.sents:
                sent_text = sent.text.strip()
                if len(sent_text) < self.min_clause_chars:
                    continue

                boundaries.append(
                    ClauseBoundary(
                        start_char=sent.start_char,
                        end_char=sent.end_char,
                        heading=None,
                        section_number=None,
                        level=1,
                        confidence=0.5,
                    )
                )
        except Exception as exc:
            logger.warning("spaCy sentence detection failed: %s", exc)

        return boundaries

    def _detect_clause_type(self, text: str) -> Optional[str]:
        """Detect the type of a clause based on keyword analysis.

        Args:
            text: Clause text to analyze.

        Returns:
            Detected clause type string, or None.
        """
        text_lower = text.lower()

        best_match = None
        best_score = 0

        for clause_type, keywords in CLAUSE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_match = clause_type

        return best_match if best_score > 0 else None
