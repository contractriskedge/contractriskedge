"""LocatorService — resolves redline suggestions to document positions.

This is the core service that replaces the old chunk-based locate system.
It uses structural section parsing, legal topology, and confidence scoring
to determine WHERE a redline belongs in the document.

Flow:
1. Parse document into section hierarchy with legal domain mapping
2. Classify the redline action (MODIFY_EXISTING, INSERT_NEW, DELETE, WARNING_ONLY)
3. For MODIFY_EXISTING: try exact → fuzzy → semantic match
4. For INSERT_NEW: use legal topology graph + insertion priority
5. For DELETE: locate the text to remove
6. For WARNING_ONLY: no location needed
7. Return structured LocatorResult with humanized explanations
"""

from __future__ import annotations

import difflib
import logging
import re
from typing import Optional

from app.domains.review.locator.models import (
    AnchorType,
    CLAUSE_RISK_ALIASES,
    CLAUSE_RISK_RELATIONSHIPS,
    CLAUSE_TYPE_TO_DOMAIN,
    CLAUSE_TYPE_TO_RISK,
    InsertPosition,
    LEGAL_TOPOLOGY,
    LocatorResult,
    LocatorStatus,
    RedlineAction,
    SectionHierarchy,
    SectionNode,
)
from app.domains.review.locator.parser import SectionParser
from app.domains.review.locator.heuristics import (
    ClausePositionMapper,
    clause_type_to_domain,
    normalize_clause_type,
)

logger = logging.getLogger(__name__)

# ── Confidence thresholds by anchor type ────────────────────────
# Differentiated confidence — not all resolutions are equally reliable.

_CONFIDENCE_EXACT = 0.97          # 95-99%: exact text match in document
_CONFIDENCE_FUZZY = 0.82          # 75-90%: whitespace/case differences only
_CONFIDENCE_SEMANTIC = 0.68       # 50-85%: matched by clause type / legal domain
_CONFIDENCE_STRUCTURAL = 0.55     # 40-70%: placed by legal topology heuristics
_CONFIDENCE_FALLBACK = 0.30       # 20-50%: best guess, low confidence
_CONFIDENCE_UNRESOLVED = 0.0      # Could not determine placement

# ── Common clause type patterns for detection ───────────────────

_CLAUSE_TYPE_PATTERNS: dict[str, re.Pattern] = {
    "indemnification": re.compile(r"indemnif", re.I),
    "limitation_of_liability": re.compile(r"limitation\s+of\s+liability|cap\s+of\s+liability", re.I),
    "confidentiality": re.compile(r"confidential|non.?disclosure", re.I),
    "governing_law": re.compile(r"governing\s+law|choice\s+of\s+(law|forum)|jurisdiction|venue", re.I),
    "termination": re.compile(r"termination|cancellation", re.I),
    "warranty": re.compile(r"warrant|representation", re.I),
    "payment": re.compile(r"fee|payment|compensation|pricing", re.I),
    "ip": re.compile(r"intellectual\s+property|proprietary|patent|copyright", re.I),
    "data_privacy": re.compile(r"data\s+protection|privacy|gdpr", re.I),
    "force_majeure": re.compile(r"force\s+majeure", re.I),
    "insurance": re.compile(r"insurance", re.I),
    "non_compete": re.compile(r"non.?compete|non.?solicit", re.I),
    "assignment": re.compile(r"assignment|delegation", re.I),
    "dispute_resolution": re.compile(r"dispute|arbitration|mediation", re.I),
    "definitions": re.compile(r"definition", re.I),
    "scope": re.compile(r"scope\s+of\s+(work|service)|services?\s+provided", re.I),
    "term": re.compile(r"^term|duration|effective\s+date|renewal", re.I),
}


class LocatorService:
    """Resolves redline suggestions to structured document locations."""

    def __init__(self, hierarchy: SectionHierarchy, full_text: str):
        self.hierarchy = hierarchy
        self.full_text = full_text
        self.position_mapper = ClausePositionMapper(hierarchy)

    # ── Public API ──────────────────────────────────────────────

    def locate(
        self,
        *,
        clause_type: Optional[str] = None,
        original_text: str = "",
        proposed_text: str = "",
        anchor_text: str = "",
        operation: Optional[str] = None,
    ) -> LocatorResult:
        """Main entry point — locate a redline in the document.

        Args:
            clause_type: Type of clause (e.g. "indemnification").
            original_text: The original text being modified (empty for inserts).
            proposed_text: The proposed new text.
            anchor_text: Optional anchor hint from the AI.
            operation: Operation type ("insert", "modification", "replace", "delete").

        Returns:
            LocatorResult with status, anchor_type, confidence, and position info.
        """
        action = self._classify_action(operation, original_text, proposed_text, clause_type)

        if action == RedlineAction.WARNING_ONLY:
            result = self._warning_only(clause_type, proposed_text)
        elif action == RedlineAction.DELETE:
            result = self._locate_delete(original_text)
        elif action == RedlineAction.INSERT_NEW:
            result = self._locate_insert(clause_type, proposed_text, anchor_text)
        else:  # MODIFY_EXISTING
            result = self._locate_modify(original_text, proposed_text, anchor_text, clause_type)

        # Enrich with risk metadata, rationale bullets, and business impact
        return self._enrich_with_risk_metadata(result, clause_type, operation)

    def _enrich_with_risk_metadata(
        self, result: LocatorResult, clause_type: Optional[str], operation: Optional[str],
    ) -> LocatorResult:
        """Add risk metadata, rationale bullets, and business impact to a result."""
        from app.domains.review.locator.heuristics import normalize_clause_type
        canonical = normalize_clause_type(clause_type) or ""

        # Try lookup by canonical name first, then by alias, then by domain
        risk_data = CLAUSE_RISK_RELATIONSHIPS.get(canonical, {})
        if not risk_data:
            alias = CLAUSE_RISK_ALIASES.get(canonical)
            if alias:
                risk_data = CLAUSE_RISK_RELATIONSHIPS.get(alias, {})
        if not risk_data:
            domain = CLAUSE_TYPE_TO_DOMAIN.get(canonical)
            if domain:
                risk_data = CLAUSE_RISK_RELATIONSHIPS.get(domain, {})

        # Set clause operation type
        if not result.clause_operation_type:
            if result.recommendation_type == "insert":
                # Check by canonical name with alias resolution
                insert_protection_types = {
                    "indemnification", "indemnity", "confidentiality", "non_disclosure",
                    "insurance", "data_privacy", "data_protection", "privacy",
                    "security", "data_security",
                }
                result.clause_operation_type = "add_protection" if canonical in insert_protection_types else "insert"
            elif result.recommendation_type == "modify":
                narrow_liability_types = {"limitation_of_liability", "liability", "cap_on_liability"}
                result.clause_operation_type = "narrow_liability" if canonical in narrow_liability_types else "modify"
            elif result.recommendation_type == "delete":
                result.clause_operation_type = "delete"
            elif result.recommendation_type == "warning":
                result.clause_operation_type = "warning"

        # Set rationale bullets
        if not result.rationale_bullets and risk_data.get("rationale_bullets"):
            result.rationale_bullets = risk_data["rationale_bullets"]

        # Set related risks
        if not result.related_risks and risk_data.get("related_risks"):
            result.related_risks = risk_data["related_risks"]

        # Set business impact
        if not result.impact_accepted and risk_data.get("impact_accepted"):
            result.impact_accepted = risk_data["impact_accepted"]
        if not result.impact_rejected and risk_data.get("impact_rejected"):
            result.impact_rejected = risk_data["impact_rejected"]

        # ── Compute compact summary fields ──────────────────────
        # summary_title: one-line title for collapsed card header
        domain_label = LEGAL_TOPOLOGY.get(canonical, {}).get("label", "")
        if not domain_label:
            domain_label = LEGAL_TOPOLOGY.get(
                CLAUSE_TYPE_TO_DOMAIN.get(canonical, ""), {}
            ).get("label", canonical.replace("_", " ").title())

        if result.recommendation_type == "insert":
            result.summary_title = f"Add {domain_label.lower()}"
        elif result.recommendation_type == "modify":
            result.summary_title = f"Modify {domain_label.lower()}"
        elif result.recommendation_type == "delete":
            result.summary_title = f"Remove {domain_label.lower()}"
        elif result.recommendation_type == "warning":
            result.summary_title = f"Review {domain_label.lower()}"
        else:
            result.summary_title = domain_label

        # summary_impact: first rationale bullet or impact_accepted
        if result.rationale_bullets:
            result.summary_impact = result.rationale_bullets[0]
        elif result.impact_accepted:
            result.summary_impact = result.impact_accepted.split(".")[0] + "."

        # action_label: display text for operation badge
        action_labels = {
            "add_protection": "ADD PROTECTION",
            "insert": "INSERT",
            "modify": "MODIFY",
            "narrow_liability": "NARROW",
            "delete": "DELETE",
            "replace": "REPLACE",
            "warning": "INFO",
        }
        result.action_label = action_labels.get(
            result.clause_operation_type or "",
            (result.clause_operation_type or "").upper(),
        )

        # group_key: for grouping redlines by risk type
        result.group_key = result.risk_type or result.legal_domain or "other"

        return result

    # ── Action classification ───────────────────────────────────

    def _classify_action(
        self,
        operation: Optional[str],
        original_text: str,
        proposed_text: str,
        clause_type: Optional[str],
    ) -> RedlineAction:
        """Classify the redline into one of the four canonical actions."""
        op = (operation or "").strip().lower()
        orig = (original_text or "").strip()
        prop = (proposed_text or "").strip()

        # WARNING_ONLY: no proposed text means informational
        if not prop:
            return RedlineAction.WARNING_ONLY

        # DELETE: original exists, proposed is empty
        if orig and not prop:
            return RedlineAction.DELETE

        # INSERT_NEW: no original text, or original is a chunk mistaken as clause
        if not orig:
            return RedlineAction.INSERT_NEW

        # Check if original_text is actually a chunk (too long, contains multiple sections)
        if len(orig) > 400:
            return RedlineAction.INSERT_NEW

        # Check if proposed section number doesn't exist in document
        proposed_section = self._extract_section_number(prop)
        if proposed_section and not self.hierarchy.get(proposed_section):
            # Section doesn't exist — this is an insert, not a modification
            return RedlineAction.INSERT_NEW

        # Check if original text actually exists in the document
        if not self._text_exists_in_document(orig):
            return RedlineAction.INSERT_NEW

        # By operation field
        if op in ("insert", "insert_after", "add"):
            return RedlineAction.INSERT_NEW

        if op in ("modification", "modify", "edit"):
            return RedlineAction.MODIFY_EXISTING

        if op in ("replace", "replacement"):
            return RedlineAction.MODIFY_EXISTING

        # Default: if original and proposed are similar, it's a modification
        ratio = self._text_similarity(orig, prop)
        if ratio > 0.3:
            return RedlineAction.MODIFY_EXISTING

        return RedlineAction.INSERT_NEW

    # ── Locate strategies ───────────────────────────────────────

    def _locate_modify(
        self,
        original_text: str,
        proposed_text: str,
        anchor_text: str,
        clause_type: Optional[str],
    ) -> LocatorResult:
        """Locate text to modify in the document."""
        canonical_type = normalize_clause_type(clause_type) or ""
        domain = clause_type_to_domain(clause_type)
        risk_type = CLAUSE_TYPE_TO_RISK.get(canonical_type)

        # 1. Try exact match
        exact = self._find_exact(original_text)
        if exact:
            return LocatorResult(
                status=LocatorStatus.RESOLVED,
                anchor_type=AnchorType.EXACT_TEXT_SPAN,
                confidence=_CONFIDENCE_EXACT,
                section_id=exact.section_id,
                section_title=exact.title,
                matched_text=original_text[:200],
                chunk_id=exact.chunk_ids[0] if exact.chunk_ids else None,
                offset_start=exact.start_offset,
                offset_end=exact.end_offset,
                reason="Exact text match found in document.",
                legal_domain=domain,
                risk_type=risk_type,
                recommendation_type="modify",
            )

        # 2. Try fuzzy match
        fuzzy = self._find_fuzzy(original_text)
        if fuzzy:
            return LocatorResult(
                status=LocatorStatus.RESOLVED,
                anchor_type=AnchorType.FUZZY_TEXT_SPAN,
                confidence=_CONFIDENCE_FUZZY,
                section_id=fuzzy.section_id,
                section_title=fuzzy.title,
                matched_text=original_text[:200],
                chunk_id=fuzzy.chunk_ids[0] if fuzzy.chunk_ids else None,
                reason="Text match found with minor formatting differences.",
                legal_domain=domain,
                risk_type=risk_type,
                recommendation_type="modify",
            )

        # 3. Try semantic clause match
        semantic = self._find_semantic(clause_type, original_text)
        if semantic:
            return LocatorResult(
                status=LocatorStatus.RESOLVED,
                anchor_type=AnchorType.SEMANTIC_CLAUSE_MATCH,
                confidence=_CONFIDENCE_SEMANTIC,
                section_id=semantic.section_id,
                section_title=semantic.title,
                reason=f"Located section '{semantic.title}' matching clause type '{clause_type}'.",
                legal_domain=domain,
                risk_type=risk_type,
                recommendation_type="modify",
            )

        # 4. Try to find by section number in proposed text
        section_from_proposed = self._find_by_proposed_section(proposed_text)
        if section_from_proposed:
            return LocatorResult(
                status=LocatorStatus.PARTIAL,
                anchor_type=AnchorType.STRUCTURAL_INSERTION,
                confidence=_CONFIDENCE_STRUCTURAL,
                section_id=section_from_proposed.section_id,
                section_title=section_from_proposed.title,
                reason=f"Could not find exact text. Located section '{section_from_proposed.title}' by section number reference.",
                legal_domain=domain,
                risk_type=risk_type,
                recommendation_type="modify",
            )

        # 5. Unresolved — fall through to INSERT_NEW logic since text doesn't exist
        return self._locate_insert(clause_type, proposed_text, anchor_text)

    def _locate_insert(
        self,
        clause_type: Optional[str],
        proposed_text: str,
        anchor_text: str,
    ) -> LocatorResult:
        """Determine where to insert new clause text.

        Rules:
        - NEVER use AI-generated section numbers (display_numbering=false)
        - Priority 1: Find existing related section → insert within
        - Priority 2: Use legal topology graph → insert at expected position
        - Priority 3: Fallback → append near end with explanation
        """
        canonical_type = normalize_clause_type(clause_type) or ""
        domain = clause_type_to_domain(clause_type)

        # Determine legal domain and risk type for the response
        legal_domain = domain
        risk_type = CLAUSE_TYPE_TO_RISK.get(canonical_type)
        rec_type = "insert"

        # ── Priority 1: Check if proposed section exists in document ──
        proposed_section = self._extract_section_number(proposed_text)
        if proposed_section:
            section = self.hierarchy.get(proposed_section)
            if section:
                # Section exists — insert within it, but NEVER use AI numbering
                label = LEGAL_TOPOLOGY.get(domain or "", {}).get("label", canonical_type.replace("_", " ").title())
                return LocatorResult(
                    status=LocatorStatus.RESOLVED,
                    anchor_type=AnchorType.STRUCTURAL_INSERTION,
                    confidence=_CONFIDENCE_STRUCTURAL,
                    section_id=section.section_id,
                    section_title=section.title,
                    insert_position=InsertPosition.WITHIN_SECTION,
                    reason=f"Suggested placement: Add this {label.lower()} provision within the existing {section.title} section.",
                    display_numbering=False,
                    legal_domain=legal_domain,
                    risk_type=risk_type,
                    recommendation_type=rec_type,
                )

            # Check if a PARENT section exists (e.g. "4.5" -> parent "4")
            if "." in proposed_section:
                parent_id = proposed_section.rsplit(".", 1)[0]
                parent = self.hierarchy.get(parent_id)
                if parent:
                    label = LEGAL_TOPOLOGY.get(domain or "", {}).get("label", canonical_type.replace("_", " ").title())
                    return LocatorResult(
                        status=LocatorStatus.RESOLVED,
                        anchor_type=AnchorType.STRUCTURAL_INSERTION,
                        confidence=_CONFIDENCE_STRUCTURAL,
                        section_id=parent.section_id,
                        section_title=parent.title,
                        insert_position=InsertPosition.WITHIN_SECTION,
                        reason=f"Suggested placement: Add this {label.lower()} provision within the {parent.title} section.",
                        display_numbering=False,
                        legal_domain=legal_domain,
                        risk_type=risk_type,
                        recommendation_type=rec_type,
                    )

        # ── Priority 2: Use legal topology graph ──
        if canonical_type:
            anchor_section, insert_pos, reason, before_title = (
                self.position_mapper.suggest_insertion(canonical_type)
            )
            if anchor_section:
                return LocatorResult(
                    status=LocatorStatus.RESOLVED if insert_pos != InsertPosition.APPEND_DOCUMENT else LocatorStatus.PARTIAL,
                    anchor_type=AnchorType.SEMANTIC_CLAUSE_MATCH,
                    confidence=_CONFIDENCE_SEMANTIC,
                    section_id=anchor_section.section_id,
                    section_title=anchor_section.title,
                    insert_position=insert_pos,
                    reason=reason,
                    display_numbering=False,
                    legal_domain=legal_domain,
                    risk_type=risk_type,
                    recommendation_type=rec_type,
                )

        # ── Priority 3: Try anchor_text as a section heading ──
        if anchor_text:
            anchor_section = self._find_section_by_heading(anchor_text)
            if anchor_section:
                label = LEGAL_TOPOLOGY.get(domain or "", {}).get("label", canonical_type.replace("_", " ").title())
                return LocatorResult(
                    status=LocatorStatus.RESOLVED,
                    anchor_type=AnchorType.STRUCTURAL_INSERTION,
                    confidence=_CONFIDENCE_FALLBACK,
                    section_id=anchor_section.section_id,
                    section_title=anchor_section.title,
                    insert_position=InsertPosition.AFTER_SECTION,
                    reason=f"Suggested placement: Add this {label.lower()} clause after the {anchor_section.title} section.",
                    display_numbering=False,
                    legal_domain=legal_domain,
                    risk_type=risk_type,
                    recommendation_type=rec_type,
                )

        # ── Priority 4: Fallback ──
        last = self._last_section()
        if last:
            label = LEGAL_TOPOLOGY.get(domain or "", {}).get("label", canonical_type.replace("_", " ").title())
            return LocatorResult(
                status=LocatorStatus.PARTIAL,
                anchor_type=AnchorType.STRUCTURAL_INSERTION,
                confidence=_CONFIDENCE_FALLBACK,
                section_id=last.section_id,
                section_title=last.title,
                insert_position=InsertPosition.AFTER_SECTION,
                reason=f"Suggested placement: Add this {label.lower()} clause at the end of the agreement, after the {last.title} section.",
                display_numbering=False,
                legal_domain=legal_domain,
                risk_type=risk_type,
                recommendation_type=rec_type,
            )

        return self._unresolved(clause_type, "Could not determine insertion point. No sections found in document.")

    def _locate_delete(self, original_text: str) -> LocatorResult:
        """Locate text to delete."""
        exact = self._find_exact(original_text)
        if exact:
            return LocatorResult(
                status=LocatorStatus.RESOLVED,
                anchor_type=AnchorType.EXACT_TEXT_SPAN,
                confidence=_CONFIDENCE_EXACT,
                section_id=exact.section_id,
                section_title=exact.title,
                matched_text=original_text[:200],
                offset_start=exact.start_offset,
                offset_end=exact.end_offset,
                reason="Text to delete found in document.",
                recommendation_type="delete",
            )
        return self._unresolved(None, "Could not locate text to delete in document.")

    def _warning_only(self, clause_type: Optional[str], proposed_text: str) -> LocatorResult:
        """Handle warning-only redlines (no text change)."""
        return LocatorResult(
            status=LocatorStatus.RESOLVED,
            anchor_type=AnchorType.UNRESOLVED,
            confidence=_CONFIDENCE_UNRESOLVED,
            reason=f"Review recommended for '{clause_type or 'unknown'}'. No document modification needed.",
            recommendation_type="warning",
        )

    def _unresolved(self, clause_type: Optional[str], reason: str) -> LocatorResult:
        """Return an unresolved result with a user-friendly suggestion."""
        canonical = normalize_clause_type(clause_type)
        domain = clause_type_to_domain(clause_type)
        risk_type = CLAUSE_TYPE_TO_RISK.get(canonical or "")
        suggestion = None

        if canonical:
            anchor, pos, human_reason, _ = self.position_mapper.suggest_insertion(canonical)
            if anchor:
                suggestion = (
                    f"This agreement does not currently contain a "
                    f"{canonical.replace('_', ' ')} provision. "
                    f"{human_reason}"
                )

        return LocatorResult(
            status=LocatorStatus.UNRESOLVED,
            anchor_type=AnchorType.UNRESOLVED,
            confidence=_CONFIDENCE_UNRESOLVED,
            reason=reason,
            suggestion=suggestion,
            legal_domain=domain,
            risk_type=risk_type,
            recommendation_type="fallback",
        )

    # ── Search helpers ──────────────────────────────────────────

    def _find_exact(self, text: str) -> Optional[SectionNode]:
        """Find a section containing an exact substring match."""
        if not text:
            return None
        search = text.strip()[:200]
        for section in self.hierarchy.flat_index.values():
            section_text = self.full_text[section.start_offset:section.end_offset]
            if search in section_text:
                return section
        return None

    def _find_fuzzy(self, text: str) -> Optional[SectionNode]:
        """Find a section containing a fuzzy match (normalized whitespace)."""
        if not text:
            return None
        search = re.sub(r"\s+", " ", text.strip().lower())[:200]
        for section in self.hierarchy.flat_index.values():
            section_text = re.sub(r"\s+", " ", self.full_text[section.start_offset:section.end_offset].lower())
            if search in section_text:
                return section
        return None

    def _find_semantic(self, clause_type: Optional[str], text: str) -> Optional[SectionNode]:
        """Find a section matching the clause type."""
        if not clause_type:
            return None
        canonical = normalize_clause_type(clause_type)
        if not canonical:
            return None
        pattern = _CLAUSE_TYPE_PATTERNS.get(canonical)
        if not pattern:
            return None
        for section in self.hierarchy.flat_index.values():
            if pattern.search(section.title):
                return section
        return None

    def _find_by_proposed_section(self, proposed_text: str) -> Optional[SectionNode]:
        """Extract section number from proposed text and find it in hierarchy."""
        section_num = self._extract_section_number(proposed_text)
        if section_num:
            return self.hierarchy.get(section_num)
        return None

    def _find_section_by_heading(self, anchor_text: str) -> Optional[SectionNode]:
        """Find a section whose title contains the anchor text."""
        if not anchor_text:
            return None
        search = anchor_text.strip().lower()
        for section in self.hierarchy.flat_index.values():
            if search in section.title.lower():
                return section
        return None

    def _last_section(self) -> Optional[SectionNode]:
        """Get the last section in document order."""
        ordered = sorted(
            self.hierarchy.flat_index.values(),
            key=lambda s: _section_sort_key(s.section_number),
        )
        return ordered[-1] if ordered else None

    def _text_exists_in_document(self, text: str) -> bool:
        """Check if text approximately exists in the document."""
        if not text:
            return False
        search = re.sub(r"\s+", " ", text.strip().lower())[:200]
        full = re.sub(r"\s+", " ", self.full_text.lower())
        return search in full

    def _text_similarity(self, a: str, b: str) -> float:
        """Compute text similarity ratio."""
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _extract_section_number(self, text: str) -> Optional[str]:
        """Extract a section number from text like '4. Indemnification' or '§4.'."""
        if not text:
            return None
        m = re.match(r"^(?:§)?(\d+(?:\.\d+)*)[.\s]", text.strip())
        if m:
            return m.group(1)
        # Try Roman numerals
        m = re.match(r"^([IVXLCDM]+)[.\s]", text.strip())
        if m:
            roman = m.group(1).lower()
            roman_map = {
                "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5",
                "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10",
            }
            return roman_map.get(roman)
        return None


def _section_sort_key(section_id: str) -> tuple:
    parts = section_id.split(".")
    key = []
    for p in parts:
        try:
            key.append((0, int(p)))
        except ValueError:
            key.append((1, p))
    return tuple(key)
