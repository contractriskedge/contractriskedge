"""Semantic insertion heuristics — maps clause types to expected document positions.

Uses a legal topology graph (from models.py) to determine where clauses
typically belong in a well-structured contract. Provides human-readable
placement explanations suitable for legal professionals.

Priority for INSERT_NEW:
  1. Find existing related section → insert within it
  2. Find legal domain neighbor → insert adjacent
  3. Use legal ordering heuristics → insert at expected position
  4. Fallback → append near end
"""

from __future__ import annotations

import re
from typing import Optional

from app.domains.review.locator.models import (
    CLAUSE_TYPE_TO_DOMAIN,
    InsertPosition,
    LEGAL_TOPOLOGY,
    SectionHierarchy,
    SectionNode,
)


# ── Clause type synonyms ────────────────────────────────────────

_CLAUSE_SYNONYMS: dict[str, str] = {
    "non_disclosure": "confidentiality",
    "nda": "confidentiality",
    "confidential_information": "confidentiality",
    # Intellectual Property — critical: feedback/ownership must map to ip, NOT data_privacy
    "intellectual_property": "ip",
    "ip_rights": "ip",
    "ip_ownership": "ip",
    "ip_transfer": "ip",
    "proprietary_rights": "ip",
    "license": "ip",
    "licensing": "ip",
    "feedback": "ip",
    "feedback_rights": "ip",
    "feedback_ownership": "ip",
    "ownership_rights": "ip",
    "derivative_works": "ip",
    "work_product": "ip",
    # Payment
    "fees": "payment",
    "compensation": "payment",
    "pricing": "payment",
    "fee_increase": "payment",
    "fee_cap": "payment",
    "refund": "payment",
    "subscription_fees": "payment",
    # Warranty
    "representations": "warranty",
    "representations_and_warranties": "warranty",
    # Liability
    "liability": "limitation_of_liability",
    "cap_on_liability": "limitation_of_liability",
    "limitation_of_liability": "limitation_of_liability",
    # Governing Law
    "choice_of_law": "governing_law",
    "jurisdiction": "governing_law",
    # Dispute
    "disputes": "dispute_resolution",
    "arbitration": "dispute_resolution",
    # Term
    "duration": "term",
    "effective_date": "term",
    # Renewal — note: auto_renewal is about the renewal lifecycle, not just "term"
    "renewal": "renewal",
    "auto_renewal": "renewal",
    # Scope
    "services": "scope",
    "scope_of_work": "scope",
    # Indemnification
    "indemnification": "indemnity",
    "indemnify": "indemnity",
    # Data Privacy — ONLY actual data/personal_data concerns, not IP
    "data_privacy": "data_privacy",
    "data_protection": "data_privacy",
    "gdpr": "data_privacy",
    "personal_data": "data_privacy",
    "data_processing": "data_privacy",
    # General
    "entire_agreement": "general_provisions",
    "merger": "general_provisions",
    "integration": "general_provisions",
    "amendment": "general_provisions",
    "waiver": "general_provisions",
    "severability": "general_provisions",
    "boilerplate": "general_provisions",
}


def normalize_clause_type(clause_type: Optional[str]) -> Optional[str]:
    """Normalize a clause type to its canonical form."""
    if not clause_type:
        return None
    ct = clause_type.lower().strip().replace(" ", "_").replace("-", "_")
    return _CLAUSE_SYNONYMS.get(ct, ct)


def clause_type_to_domain(clause_type: Optional[str]) -> Optional[str]:
    """Map a clause type to its legal domain."""
    canonical = normalize_clause_type(clause_type)
    if not canonical:
        return None
    return CLAUSE_TYPE_TO_DOMAIN.get(canonical, canonical)


def _humanize_reason(
    clause_type: str,
    action: str,
    anchor_title: str,
    before_title: Optional[str] = None,
) -> str:
    """Generate a human-readable placement explanation for legal professionals."""
    domain = clause_type_to_domain(clause_type)
    topology = LEGAL_TOPOLOGY.get(domain or "", {})

    label = topology.get("label", clause_type.replace("_", " ").title())

    if action == "within":
        return (
            f"Suggested placement: Add this {label.lower()} provision "
            f"within the existing {anchor_title} section."
        )
    elif action == "after" and before_title:
        return (
            f"Suggested placement: Add this {label.lower()} clause "
            f"after the {anchor_title} section and before the {before_title} section."
        )
    elif action == "after":
        return (
            f"Suggested placement: Add this {label.lower()} clause "
            f"after the {anchor_title} section."
        )
    elif action == "before":
        return (
            f"Suggested placement: Add this {label.lower()} clause "
            f"before the {anchor_title} section."
        )
    elif action == "append":
        return (
            f"Suggested placement: Add this {label.lower()} clause "
            f"at the end of the agreement, after the {anchor_title} section."
        )
    return (
        f"Suggested placement: This {label.lower()} provision "
        f"should be reviewed and placed in the appropriate section."
    )


def _build_domain_order() -> list[str]:
    """Build ordered list of legal domains from the topology graph."""
    domains = list(LEGAL_TOPOLOGY.keys())
    position_order = {
        "early": 0,
        "early_middle": 1,
        "middle": 2,
        "middle_late": 3,
        "late": 4,
        "end": 5,
    }
    return sorted(domains, key=lambda d: position_order.get(
        LEGAL_TOPOLOGY[d].get("expected_position", "middle"), 2
    ))


_DOMAIN_ORDER = _build_domain_order()
_DOMAIN_ORDER_INDEX = {d: i for i, d in enumerate(_DOMAIN_ORDER)}


class ClausePositionMapper:
    """Maps clause types to expected insertion positions using legal topology.

    Uses the canonical legal structure graph to determine where clauses
    belong, rather than simple numeric proximity.
    """

    def __init__(self, hierarchy: SectionHierarchy):
        self.hierarchy = hierarchy

    def suggest_insertion(
        self, clause_type: str,
    ) -> tuple[Optional[SectionNode], InsertPosition, str, Optional[str]]:
        """Suggest where to insert a new clause of the given type.

        Priority:
          1. Find existing section with same legal domain → insert within/before
          2. Find legal domain neighbor (preferred_neighbors) → insert adjacent
          3. Use legal ordering heuristics → insert between correct sections
          4. Fallback → append near end

        Returns:
            (anchor_section, insert_position, reason, before_section_title)
        """
        canonical = normalize_clause_type(clause_type) or clause_type
        domain = clause_type_to_domain(canonical)
        target_idx = _DOMAIN_ORDER_INDEX.get(domain or "", -1)

        if target_idx < 0:
            return self._append_fallback(canonical)

        topology = LEGAL_TOPOLOGY.get(domain or "", {})
        never_after_domains = set(topology.get("never_after", []))

        # ── Priority 1: Find existing section with same domain ──
        if domain:
            same_domain = self.hierarchy.find_by_domain(domain)
            if same_domain:
                section = same_domain[0]
                if topology.get("standalone_preferred", False):
                    reason = _humanize_reason(canonical, "before", section.title)
                    return section, InsertPosition.BEFORE_SECTION, reason, None
                else:
                    reason = _humanize_reason(canonical, "within", section.title)
                    return section, InsertPosition.WITHIN_SECTION, reason, None

        # ── Priority 2: Find legal domain neighbor ──
        if domain:
            neighbors = topology.get("preferred_neighbors", [])
            for neighbor_domain in neighbors:
                neighbor_sections = self.hierarchy.find_by_domain(neighbor_domain)
                if neighbor_sections:
                    neighbor = neighbor_sections[0]
                    neighbor_idx = _DOMAIN_ORDER_INDEX.get(neighbor_domain, -1)
                    # Skip if inserting after a disallowed domain
                    if neighbor_domain in never_after_domains:
                        continue
                    if neighbor_idx < target_idx:
                        reason = _humanize_reason(canonical, "after", neighbor.title)
                        return neighbor, InsertPosition.AFTER_SECTION, reason, None
                    else:
                        reason = _humanize_reason(canonical, "before", neighbor.title)
                        return neighbor, InsertPosition.BEFORE_SECTION, reason, None

        # ── Priority 3: Use legal ordering heuristics ──
        matched_sections: list[tuple[int, SectionNode]] = []
        for section in self.hierarchy.flat_index.values():
            if section.legal_domain:
                idx = _DOMAIN_ORDER_INDEX.get(section.legal_domain, -1)
                # Skip sections that this clause must never appear after
                if section.legal_domain in never_after_domains:
                    continue
                if idx >= 0:
                    matched_sections.append((idx, section))

        matched_sections.sort(key=lambda x: x[0])

        if matched_sections:
            before_section = None
            after_section = None

            for idx, section in matched_sections:
                if idx < target_idx:
                    after_section = section
                elif idx > target_idx and before_section is None:
                    before_section = section

            if after_section and before_section:
                reason = _humanize_reason(canonical, "after", after_section.title, before_section.title)
                return after_section, InsertPosition.AFTER_SECTION, reason, before_section.title
            elif after_section:
                reason = _humanize_reason(canonical, "after", after_section.title)
                return after_section, InsertPosition.AFTER_SECTION, reason, None
            elif before_section:
                reason = _humanize_reason(canonical, "before", before_section.title)
                return before_section, InsertPosition.BEFORE_SECTION, reason, None

        # ── Priority 4: Fallback ──
        return self._append_fallback(canonical)

    def _append_fallback(
        self, clause_type: str,
    ) -> tuple[Optional[SectionNode], InsertPosition, str, Optional[str]]:
        """Fallback: append after last section."""
        last = self._last_section()
        if last:
            reason = _humanize_reason(clause_type, "append", last.title)
            return last, InsertPosition.AFTER_SECTION, reason, None
        reason = (
            f"This agreement does not currently contain a "
            f"{clause_type.replace('_', ' ')} provision. "
            f"Please review and determine the appropriate placement."
        )
        return None, InsertPosition.APPEND_DOCUMENT, reason, None

    def _last_section(self) -> Optional[SectionNode]:
        """Get the last section in document order."""
        ordered = sorted(
            self.hierarchy.flat_index.values(),
            key=lambda s: _section_sort_key(s.section_number),
        )
        return ordered[-1] if ordered else None


def _section_sort_key(section_id: str) -> tuple:
    parts = section_id.split(".")
    key = []
    for p in parts:
        try:
            key.append((0, int(p)))
        except ValueError:
            key.append((1, p))
    return tuple(key)
