"""Structural section parser — builds a hierarchical section tree from extracted text.

Detects:
- Arabic numbering: 1., 1.1, 1.1.1, etc.
- Section prefix: "Section 5.", "SECTION 5", "§5."
- Article prefix: "Article 3.", "ARTICLE III", "Art. 3"
- Roman numerals: I., II., III., IV., etc.
- Mixed: "Article 3.1", "Section 4(a)"
"""

from __future__ import annotations

import re
from typing import Optional

from app.domains.review.locator.models import SectionHierarchy, SectionNode


# ── Regex patterns ──────────────────────────────────────────────

# Matches section headers like "1.", "1.1", "1.1.1", "Section 5.", "§5.", "Article 3."
_SECTION_HEADER_RE = re.compile(
    r"(?:^|\n)\s*"
    r"(?:"
    r"(?:Section|SECTION|section|§)\s+(\d+(?:\.\d+)*)\s*[\.\:\-\s]"          # Section 5. / §5.
    r"|"
    r"(?:Article|ARTICLE|article|Art\.?|ART\.?)\s+"                           # Article 3 / Art. 3
    r"(\d+(?:\.\d+)*|[IVXLCDM]+)"
    r"\s*[\.\:\-\s]"
    r"|"
    r"(\d+(?:\.\d+)*)\s*[\.\)]\s+"                                            # 1. / 1) / 1.1)
    r"|"
    r"([IVXLCDM]+)\s*[\.\)]\s+"                                               # I. / II. / III.
    r")"
    r"(.+)",  # Capture the title text
    re.MULTILINE,
)

# For detecting Roman numerals
_ROMAN_RE = re.compile(r"^[IVXLCDM]+$", re.I)

_ROMAN_TO_INT: dict[str, int] = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
    "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
    "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15,
    "xvi": 16, "xvii": 17, "xviii": 18, "xix": 19, "xx": 20,
}


def _roman_to_int(s: str) -> Optional[int]:
    return _ROMAN_TO_INT.get(s.lower())


def _section_sort_key(section_id: str) -> tuple:
    """Produce a sortable key from a dotted section number."""
    parts = section_id.replace("§", "").split(".")
    key = []
    for p in parts:
        try:
            key.append((0, int(p)))
        except ValueError:
            key.append((1, p))
    return tuple(key)


class SectionParser:
    """Parses extracted document text into a hierarchical section tree."""

    def parse(self, text: str, chunks: Optional[list] = None) -> SectionHierarchy:
        """Parse full document text into sections.

        Args:
            text: The full extracted document text.
            chunks: Optional list of chunk dicts with chunk_id, text fields
                    for mapping sections to chunks.

        Returns:
            SectionHierarchy with all detected sections.
        """
        hierarchy = SectionHierarchy()
        seen_sections: set[str] = set()

        for m in _SECTION_HEADER_RE.finditer(text):
            # Determine which group matched
            section_num = None
            for g in [m.group(1), m.group(2), m.group(3), m.group(4)]:
                if g is not None:
                    section_num = g.strip()
                    break

            title = m.group(5).strip() if m.lastindex and m.group(5) else ""
            # Clean up the title
            title = re.sub(r"\s+", " ", title).strip()
            # Remove trailing punctuation that's not part of the title
            title = re.sub(r"\s*[\.\:\;\,]\s*$", "", title)

            if not section_num:
                continue

            # Normalize Roman numerals to Arabic
            if _ROMAN_RE.match(section_num):
                arabic = _roman_to_int(section_num)
                if arabic is None:
                    continue
                section_id = str(arabic)
            else:
                section_id = section_num

            # Skip if we've already seen this exact section
            if section_id in seen_sections:
                continue
            seen_sections.add(section_id)

            # Determine level from number of dots
            level = section_id.count(".") + 1

            # Calculate offsets
            start_offset = m.start()
            # End offset: either the start of the next section or end of text
            next_match = _SECTION_HEADER_RE.search(text, m.end())
            end_offset = next_match.start() if next_match else len(text)

            # Map to chunks if provided
            chunk_ids: list[str] = []
            page_numbers: list[int] = []
            if chunks:
                for chunk in chunks:
                    chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else getattr(chunk, "text", "")
                    if not chunk_text:
                        continue
                    # Check if this section's text overlaps with the chunk
                    chunk_start = text.find(chunk_text[:100])
                    if chunk_start >= 0 and chunk_start < end_offset and chunk_start + len(chunk_text) > start_offset:
                        cid = chunk.get("chunk_id") if isinstance(chunk, dict) else getattr(chunk, "chunk_id", None)
                        if cid:
                            chunk_ids.append(cid)
                        pn = chunk.get("page_numbers", []) if isinstance(chunk, dict) else getattr(chunk, "page_numbers", [])
                        page_numbers.extend(pn)

            node = SectionNode(
                section_id=section_id,
                section_number=section_num,
                title=title,
                level=level,
                start_offset=start_offset,
                end_offset=end_offset,
                page_numbers=sorted(set(page_numbers)),
                chunk_ids=list(set(chunk_ids)),
                legal_domain=self.detect_clause_type(title),
            )
            hierarchy.sections.append(node)
            hierarchy.flat_index[section_id] = node

        # Build parent-child relationships
        self._build_parent_child(hierarchy)

        return hierarchy

    def _build_parent_child(self, hierarchy: SectionHierarchy) -> None:
        """Link parent-child relationships based on section numbering."""
        for node in hierarchy.sections:
            parts = node.section_id.split(".")
            if len(parts) > 1:
                parent_id = ".".join(parts[:-1])
                parent = hierarchy.flat_index.get(parent_id)
                if parent:
                    node.parent = parent
                    parent.children.append(node)

    def detect_clause_type(self, title: str) -> Optional[str]:
        """Infer clause type from section title."""
        title_lower = title.lower().strip()
        patterns = [
            ("indemnification", r"indemnif"),
            ("limitation_of_liability", r"limitation\s+of\s+liability|cap\s+of\s+liability|liability\s+(cap|limit)"),
            ("confidentiality", r"confidential|non.?disclosure|nda"),
            ("governing_law", r"governing\s+law|choice\s+of\s+(law|forum)|applicable\s+law|jurisdiction|venue"),
            ("termination", r"termination|cancellation"),
            ("warranty", r"warrant(y|ies)|representation"),
            ("payment", r"fee|payment|compensation|pricing|rate"),
            ("ip", r"intellectual\s+property|proprietary|patent|copyright|trademark|ownership|feedback"),
            ("data_privacy", r"data\s+protection|privacy|gdpr|personal\s+(data|information)"),
            ("force_majeure", r"force\s+majeure|act\s+of\s+god"),
            ("insurance", r"insurance"),
            ("non_compete", r"non.?compete|non.?solicit|exclusivity"),
            ("assignment", r"assignment|delegation"),
            ("dispute_resolution", r"dispute|arbitration|mediation|litigation"),
            ("entire_agreement", r"entire\s+agreement|merger|integration"),
            ("amendment", r"amendment|modification"),
            ("waiver", r"waiver"),
            ("severability", r"severab"),
            ("notice", r"notice"),
            ("definitions", r"definition"),
            ("scope", r"scope\s+of\s+(work|service)|services?\s+provided|statement\s+of\s+work"),
            ("term", r"^term|duration|effective\s+date|renewal"),
        ]
        for clause_type, pattern in patterns:
            if re.search(pattern, title_lower):
                return clause_type
        return None
