"""Policy-to-finding linkage — match, persist, and build violation DTOs."""

from __future__ import annotations

from typing import Any, Optional


def normalize_clause_category(value: Optional[str]) -> str:
    return (value or "").lower().replace(" ", "_").replace("-", "_")


def rule_matches_finding(finding: dict, rule: dict) -> bool:
    clause = normalize_clause_category(finding.get("clause_type"))
    if not clause:
        return False
    target = normalize_clause_category(rule.get("target_category"))
    if target and target == clause:
        return True
    cond = rule.get("conditions") or {}
    if isinstance(cond, dict):
        cond_cat = normalize_clause_category(cond.get("clause_category"))
        if cond_cat and cond_cat == clause:
            return True

    # DB-driven keyword pattern matching — replaces the old hardcoded name_map.
    # Each rule can store keyword_patterns as a JSONB list of strings.
    # If any pattern is found in the rule name or finding title, and the
    # pattern maps to the finding's clause type, the rule matches.
    keyword_patterns: list = rule.get("keyword_patterns") or []
    if keyword_patterns:
        name = (rule.get("name") or "").lower()
        title = (finding.get("title") or "").lower()
        for pattern in keyword_patterns:
            pattern_str = normalize_clause_category(str(pattern))
            if pattern_str == clause:
                # Direct clause-type match via pattern
                return True
            if pattern_str in name or pattern_str in title:
                return True

    return False


def pick_best_rule(finding: dict, rules: list[dict]) -> Optional[dict]:
    matches = [r for r in rules if rule_matches_finding(finding, r)]
    if not matches:
        return None
    return sorted(matches, key=lambda r: (r.get("priority") or 999))[0]


def build_violation_dto(
    *,
    finding: dict,
    rule: dict,
    playbook: Optional[dict],
    version_label: Optional[str],
    review_id: str,
    clause_standard: Optional[dict] = None,
    redline_count: int = 0,
    status: str = "open",
    waiver: Optional[dict] = None,
) -> dict:
    playbook_name = (playbook or {}).get("name") or "Policy"
    rule_name = rule.get("name") or playbook_name
    fid = str(finding["finding_id"])
    rid = str(rule["rule_id"])
    violation = {
        "id": f"vio-{fid[:8]}-{rid[:8]}",
        "violation_id": f"vio-{fid[:8]}-{rid[:8]}",
        "finding_id": fid,
        "review_id": review_id,
        "rule_id": rid,
        "playbook_id": str(rule["playbook_id"]) if rule.get("playbook_id") else None,
        "evaluation_id": str(finding.get("evaluation_id")) if finding.get("evaluation_id") else None,
        "policy_name": playbook_name,
        "policy_rule_name": rule_name,
        "policy_version": version_label or "1.0",
        "policy_owner": (playbook or {}).get("created_by") or "Legal Ops",
        "rule_description": rule.get("description"),
        "policy_requirement": (clause_standard or {}).get("body") or rule.get("description"),
        "clause_requirement_title": (clause_standard or {}).get("title"),
        "clause_type": finding.get("clause_type"),
        "severity": finding.get("severity") or "medium",
        "finding_title": finding.get("title"),
        "finding_description": finding.get("description"),
        "recommendation": finding.get("recommendation"),
        "effect": rule.get("effect"),
        "is_mandatory": rule.get("is_mandatory", False),
        "status": status,
        "redline_count": redline_count,
        "created_at": None,
        "traceability": {
            "policy_name": playbook_name,
            "policy_version": version_label or "1.0",
            "rule_name": rule_name,
            "clause_requirement": (clause_standard or {}).get("title"),
            "finding_title": finding.get("title"),
            "redline_count": redline_count,
        },
    }
    if waiver:
        violation["waiver_status"] = waiver.get("status")
        violation["waiver_justification"] = waiver.get("justification")
        violation["waiver_requested_by"] = waiver.get("requested_by")
        violation["waiver_requested_at"] = (
            waiver["requested_at"].isoformat()
            if hasattr(waiver.get("requested_at"), "isoformat")
            else str(waiver.get("requested_at"))
        )
        if waiver.get("status") == "approved":
            violation["status"] = "waived"
    return violation
