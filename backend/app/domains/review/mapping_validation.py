"""Redline-to-finding mapping integrity validation.

Ensures each redline references a finding whose category matches the redline
category. Cross-category mappings (e.g. liability redline → privacy finding)
are flagged as invalid_mapping and must not be accepted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional


CATEGORY_ALIASES: dict[str, list[str]] = {
    "fees": ["fees", "fee", "payment", "payments", "pricing", "invoice", "payment_terms"],
    "indemnification": ["indemnification", "indemnify", "indemn", "hold_harmless"],
    "liability": ["liability", "liability_caps", "limitation", "limitation_of_liability"],
    "termination": ["termination", "term", "renewal", "auto_renewal"],
    "confidentiality": ["confidentiality", "confidential", "nda"],
    "sla": ["sla", "service_level", "availability", "uptime"],
    "ip": ["ip", "intellectual_property", "intellectual", "ownership"],
    "data_protection": [
        "data_protection",
        "privacy",
        "gdpr",
        "dpa",
        "data_privacy",
        "data privacy",
    ],
}

TEXT_CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("indemnification", re.compile(r"\bindemnif", re.I)),
    ("liability", re.compile(r"\b(liabilit|limitation of liability|aggregate liability|liability cap)\b", re.I)),
    ("fees", re.compile(r"\b(fees?|payment terms?|pricing|invoice|payable)\b", re.I)),
    ("termination", re.compile(r"\b(terminat|renewal|non-?renewal)\b", re.I)),
    ("confidentiality", re.compile(r"\b(confidential|non-?disclosure)\b", re.I)),
    ("sla", re.compile(r"\b(service level|uptime|availability|sla)\b", re.I)),
    ("ip", re.compile(r"\b(intellectual property|infringement|work product)\b", re.I)),
    ("data_protection", re.compile(r"\b(personal data|gdpr|data processing|data privacy)\b", re.I)),
]


def _pick_string(*values: Any) -> str:
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _tokenize_category(raw: str) -> str:
    return re.sub(r"^_+|_+$", "", re.sub(r"[^a-z0-9]+", "_", raw.lower()))


def normalize_category(value: Optional[str]) -> Optional[str]:
    raw = _pick_string(value)
    if not raw:
        return None
    token = _tokenize_category(raw)
    for canonical, aliases in CATEGORY_ALIASES.items():
        if any(a in token or token in a for a in aliases):
            return canonical
    for canonical, pattern in TEXT_CATEGORY_PATTERNS:
        if pattern.search(raw):
            return canonical
    return token if len(token) > 2 else None


def categories_compatible(a: Optional[str], b: Optional[str]) -> bool:
    ca = normalize_category(a)
    cb = normalize_category(b)
    if not ca or not cb:
        return True
    return ca == cb


def _category_label(cat: Optional[str]) -> str:
    if not cat:
        return "unknown"
    return cat.replace("_", " ")


def derive_redline_title(
    redline: Any,
    *,
    locator_result: Optional[dict] = None,
) -> str:
    meta = getattr(redline, "redline_metadata", None) or {}
    trace = meta.get("traceability") if isinstance(meta, dict) else {}
    if isinstance(trace, dict):
        detected = _pick_string(trace.get("detected_risk"))
        if detected:
            return detected
    if locator_result:
        title = _pick_string(locator_result.get("summary_title"))
        if title:
            return title
    clause_type = _pick_string(getattr(redline, "clause_type", None))
    if clause_type:
        return clause_type.replace("_", " ").title()
    return "Redline"


@dataclass
class MappingValidationResult:
    valid: bool
    mapping_status: str  # "valid" | "invalid_mapping"
    warning: Optional[str]
    finding_id: Optional[str]
    finding_title: Optional[str]
    finding_category: Optional[str]
    redline_title: str
    redline_category: Optional[str]
    category: Optional[str]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "mapping_valid": self.valid,
            "mapping_status": self.mapping_status,
            "mapping_warning": self.warning,
            "finding_id": self.finding_id,
            "finding_title": self.finding_title,
            "finding_category": self.finding_category,
            "redline_title": self.redline_title,
            "redline_category": self.redline_category,
            "category": self.category,
        }


def validate_redline_finding_mapping(
    redline: Any,
    finding: Any | None,
    *,
    locator_result: Optional[dict] = None,
    displayed_finding_id: Optional[str] = None,
) -> MappingValidationResult:
    """Validate that a redline is correctly linked to its finding."""
    stored_finding_id = (
        str(redline.finding_id) if getattr(redline, "finding_id", None) else None
    )
    redline_category = normalize_category(getattr(redline, "clause_type", None))
    redline_title = derive_redline_title(redline, locator_result=locator_result)
    proposed_cat = normalize_category(
        infer_category_from_text(getattr(redline, "proposed_text", "") or "")
    )

    finding_id = stored_finding_id
    finding_title = None
    finding_category = None

    warnings: list[str] = []

    if not stored_finding_id:
        warnings.append("Redline is not linked to a finding.")
    elif not finding:
        warnings.append(
            f"Linked finding {stored_finding_id} was not found for this review."
        )
    else:
        finding_id = str(finding.finding_id)
        finding_title = _pick_string(getattr(finding, "title", None))
        finding_category = normalize_category(getattr(finding, "clause_type", None))

        if displayed_finding_id and displayed_finding_id != finding_id:
            warnings.append(
                f"Displayed finding ({displayed_finding_id}) does not match "
                f"stored finding ({finding_id})."
            )

        if not finding_title:
            warnings.append("Linked finding is missing a title.")

        if not finding_category:
            warnings.append("Linked finding is missing a category.")

        if redline_category and finding_category and not categories_compatible(
            redline_category, finding_category
        ):
            warnings.append(
                f"Redline category ({_category_label(redline_category)}) does not match "
                f"finding category ({_category_label(finding_category)})."
            )

        # Proposed text inference is a secondary check — only flag it when the
        # redline's explicit clause_type already matches the finding. The text
        # inference is unreliable (e.g. "Data Breach Notification" text may infer
        # "data_protection" while the finding is "compliance"), so it should not
        # override an explicit match.
        if proposed_cat and finding_category and not categories_compatible(
            proposed_cat, finding_category
        ):
            # Only add as a warning if the explicit categories also don't match
            if not (redline_category and finding_category and categories_compatible(
                redline_category, finding_category
            )):
                warnings.append(
                    f"Proposed redline text ({_category_label(proposed_cat)}) does not match "
                    f"finding category ({_category_label(finding_category)})."
                )

    category = finding_category or redline_category or proposed_cat
    valid = len(warnings) == 0
    warning = (
        " ".join(warnings) + " Cross-category mappings are not allowed — re-link before accepting."
        if warnings
        else None
    )

    return MappingValidationResult(
        valid=valid,
        mapping_status="valid" if valid else "invalid_mapping",
        warning=warning,
        finding_id=finding_id,
        finding_title=finding_title,
        finding_category=finding_category,
        redline_title=redline_title,
        redline_category=redline_category or proposed_cat,
        category=category,
    )


def infer_category_from_text(text: str) -> Optional[str]:
    t = _pick_string(text)
    if not t:
        return None
    matches = [canonical for canonical, pattern in TEXT_CATEGORY_PATTERNS if pattern.search(t)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        priority = [
            "liability",
            "indemnification",
            "ip",
            "data_protection",
            "termination",
            "confidentiality",
            "sla",
            "fees",
        ]
        for cat in priority:
            if cat in matches:
                return cat
        return matches[0]
    return normalize_category(t)
