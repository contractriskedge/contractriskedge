"""Redline coverage audit — findings vs generated redlines."""

from __future__ import annotations

from typing import Any, Optional

from app.domains.review.clause_category import (
    MITIGATION_CATEGORY_MAP,
    mitigation_category_for_clause_type,
    resolve_mitigation_plan,
)
from app.domains.review.mitigation_effectiveness import MITIGATION_EFFECTIVENESS_REGISTRY


def _has_registry_support(clause_type: Optional[str]) -> bool:
    category = mitigation_category_for_clause_type(clause_type)
    return bool(MITIGATION_EFFECTIVENESS_REGISTRY.get(category))


def audit_finding_redline_coverage(
    findings: list[Any],
    redlines: list[Any],
) -> dict[str, Any]:
    """Compare findings to redlines for a single review.

    Args:
        findings: ReviewFinding rows or dicts with finding_id, clause_type, title, severity
        redlines: ReviewRedline rows or dicts with finding_id, clause_type, redline_id

    Returns:
        Coverage report dict suitable for API responses and ops dashboards.
    """
    linked_by_finding: dict[str, list[str]] = {}
    redlines_by_clause: dict[str, int] = {}

    for r in redlines:
        rid = str(getattr(r, "redline_id", None) or r.get("redline_id", ""))
        fid = str(getattr(r, "finding_id", None) or r.get("finding_id") or "")
        ct = getattr(r, "clause_type", None) or r.get("clause_type") or "unknown"
        redlines_by_clause[ct] = redlines_by_clause.get(ct, 0) + 1
        if fid:
            linked_by_finding.setdefault(fid, []).append(rid)

    finding_rows: list[dict[str, Any]] = []
    missing_templates: dict[str, int] = {}
    unsupported: dict[str, int] = {}

    for f in findings:
        fid = str(getattr(f, "finding_id", None) or f.get("finding_id", ""))
        clause_type = getattr(f, "clause_type", None) or f.get("clause_type") or "other"
        title = getattr(f, "title", None) or f.get("title")
        severity = getattr(f, "severity", None) or f.get("severity") or "medium"
        has_redline = bool(linked_by_finding.get(fid))
        registry_ok = _has_registry_support(clause_type)
        plan = resolve_mitigation_plan(
            clause_type,
            title=title,
            description=getattr(f, "description", None) or f.get("description"),
            recommendation=getattr(f, "recommendation", None) or f.get("recommendation"),
        )

        if not has_redline:
            if not registry_ok and plan.source == "fallback":
                unsupported[clause_type] = unsupported.get(clause_type, 0) + 1
            elif plan.source in ("title_hint", "fallback"):
                missing_templates[clause_type] = missing_templates.get(clause_type, 0) + 1

        finding_rows.append({
            "finding_id": fid,
            "title": title,
            "clause_type": clause_type,
            "severity": severity,
            "has_redline": has_redline,
            "registry_supported": registry_ok,
            "suggested_mitigation_type": plan.mitigation_type,
            "suggested_clause_category": plan.clause_category,
            "mapping_source": plan.source,
        })

    total = len(findings)
    with_redline = sum(1 for row in finding_rows if row["has_redline"])
    coverage_pct = round((with_redline / total) * 100, 1) if total else 100.0

    supported_types = sorted(MITIGATION_CATEGORY_MAP.keys())
    all_finding_types = sorted({row["clause_type"] for row in finding_rows})
    unsupported_types = sorted(
        ct for ct in all_finding_types
        if not _has_registry_support(ct)
    )

    return {
        "findings": total,
        "redlines": len(redlines),
        "findings_with_redline": with_redline,
        "findings_without_redline": total - with_redline,
        "coverage_pct": coverage_pct,
        "missing_redline_templates": [
            {"clause_type": ct, "count": count}
            for ct, count in sorted(missing_templates.items(), key=lambda x: -x[1])
        ],
        "unsupported_clause_types": [
            {"clause_type": ct, "count": unsupported.get(ct, 0)}
            for ct in unsupported_types
        ],
        "supported_clause_types": supported_types,
        "registry_categories": sorted(MITIGATION_EFFECTIVENESS_REGISTRY.keys()),
        "finding_details": finding_rows,
        "redlines_by_clause_type": redlines_by_clause,
    }
