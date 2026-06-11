"""Clause-type → mitigation registry mapping.

Findings use AI-canonical clause_type values (e.g. confidentiality, term).
The mitigation template registry uses compound category keys (e.g. liability_indemnity).
This module bridges the two and picks a default mitigation type per finding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domains.ai.schemas import _canonicalize_clause_type
from app.domains.review.mitigation_effectiveness import MITIGATION_EFFECTIVENESS_REGISTRY


# Raw AI / NDA labels → mitigation registry category
MITIGATION_CATEGORY_MAP: dict[str, str] = {
    "liability": "liability_indemnity",
    "limitation_of_liability": "liability_indemnity",
    "indemnification": "liability_indemnity",
    "indemnity": "liability_indemnity",
    "confidentiality": "confidentiality",
    "non_disclosure": "confidentiality",
    "nda": "confidentiality",
    "return_of_information": "confidentiality",
    "return_of_materials": "confidentiality",
    "remedies": "confidentiality",
    "exclusions": "confidentiality",
    "residual_knowledge": "confidentiality",
    "survival": "term_termination",
    "term": "term_termination",
    "duration": "term_termination",
    "termination": "term_termination",
    "renewal": "term_termination",
    "data_privacy": "data_protection",
    "data_protection": "data_protection",
    "privacy": "data_protection",
    "gdpr": "data_protection",
    "intellectual_property": "intellectual_property",
    "ip": "intellectual_property",
    "no_license": "intellectual_property",
    "license": "intellectual_property",
    "payment": "payment_audit",
    "fees": "payment_audit",
    "audit": "payment_audit",
    "sla": "sla_support",
    "support": "sla_support",
    "service_levels": "sla_support",
    "governing_law": "governing_law_jurisdiction",
    "jurisdiction": "governing_law_jurisdiction",
    "dispute_resolution": "governing_law_jurisdiction",
    "arbitration": "governing_law_jurisdiction",
    "insurance": "insurance",
    "non_compete": "non_compete_exclusivity",
    "exclusivity": "non_compete_exclusivity",
    "assignment": "assignment_change_control",
    "force_majeure": "force_majeure",
    "compliance": "compliance",
    "security": "security",
    "warranty": "commercial_terms",
    "other": "confidentiality",
}

# Title / keyword hints for NDA-style findings stored as generic types
_TITLE_MITIGATION_HINTS: list[tuple[tuple[str, ...], str, str]] = [
    (("return of information", "return of materials", "return or destroy"), "confidentiality", "adding_return_of_information"),
    (("remedies", "injunctive", "irreparable harm"), "confidentiality", "adding_remedies_clause"),
    (("no license", "no licence", "license grant"), "intellectual_property", "clarifying_no_license"),
    (("exclusion", "excluded from confidentiality", "publicly available"), "confidentiality", "clarifying_exclusions"),
    (("survival", "survive termination"), "term_termination", "extending_notice_period"),
]


@dataclass(frozen=True)
class MitigationPlan:
    clause_category: str
    mitigation_type: str
    source: str  # exact | mapped | title_hint | fallback


def mitigation_category_for_clause_type(clause_type: Optional[str]) -> str:
    """Map a finding clause_type to a mitigation registry category key."""
    raw = _canonicalize_clause_type(clause_type or "other")
    return MITIGATION_CATEGORY_MAP.get(raw, raw)


def _hint_from_title(title: Optional[str], description: Optional[str] = None) -> Optional[MitigationPlan]:
    blob = f"{title or ''} {description or ''}".lower()
    if not blob.strip():
        return None
    for keywords, category, mitigation_type in _TITLE_MITIGATION_HINTS:
        if any(kw in blob for kw in keywords):
            return MitigationPlan(category, mitigation_type, "title_hint")
    return None


def resolve_mitigation_plan(
    clause_type: Optional[str],
    title: Optional[str] = None,
    description: Optional[str] = None,
    recommendation: Optional[str] = None,
) -> MitigationPlan:
    """Pick clause_category + mitigation_type for a finding needing a fallback redline."""
    raw = (clause_type or "").lower().strip()
    canonical = _canonicalize_clause_type(raw)

    # Direct NDA-specific raw types (before full canonicalization collapse)
    direct_nda: dict[str, tuple[str, str]] = {
        "return_of_information": ("confidentiality", "adding_return_of_information"),
        "return_of_materials": ("confidentiality", "adding_return_of_information"),
        "remedies": ("confidentiality", "adding_remedies_clause"),
        "no_license": ("intellectual_property", "clarifying_no_license"),
        "exclusions": ("confidentiality", "clarifying_exclusions"),
        "residual_knowledge": ("confidentiality", "broadening_confidentiality"),
    }
    if raw in direct_nda:
        cat, mt = direct_nda[raw]
        return MitigationPlan(cat, mt, "exact")

    hinted = _hint_from_title(title, f"{description or ''} {recommendation or ''}")
    if hinted:
        return hinted

    category = mitigation_category_for_clause_type(canonical)
    effects = MITIGATION_EFFECTIVENESS_REGISTRY.get(category, {})
    if effects:
        first_type = next(iter(effects.keys()))
        return MitigationPlan(category, first_type, "mapped")

    # Last resort — generic insert redline
    fallback_type = f"generic_{canonical or 'clause'}_recommendation"
    return MitigationPlan(category or "confidentiality", fallback_type, "fallback")
