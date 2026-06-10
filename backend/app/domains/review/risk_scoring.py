"""Canonical contract risk scoring — single source of truth for all dashboard widgets.

Enterprise semantics:
- overall_risk_score: immutable Original AI Risk
- current_contract_risk / remaining_exposure: dominant live metric
- normalized_contribution: absolute remaining exposure points per category (sums to remaining_exposure)
- exposure_share_pct: share of remaining (sums to 100%) — display-only derivative
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from app.domains.ai.schemas import _canonicalize_clause_type

SEVERITY_WEIGHTS = {
    "critical": 1.0,
    "high": 0.7,
    "medium": 0.4,
    "low": 0.15,
    "info": 0.0,
}

# ── Canonical legal taxonomy (uniform abstraction level) ─────────────────

CANONICAL_CATEGORIES: dict[str, str] = {
    "commercial_terms": "Commercial Terms",
    "liability_indemnity": "Liability & Indemnity",
    "intellectual_property": "Intellectual Property",
    "data_privacy": "Data Privacy",
    "termination_renewal": "Termination & Renewal",
    "governance": "Governance",
    "security": "Security",
    "compliance": "Compliance",
}

# Map raw / legacy clause_type keys → canonical category
CLAUSE_TO_CANONICAL: dict[str, str] = {
    # Commercial Terms
    "payment": "commercial_terms",
    "payment_terms": "commercial_terms",
    "fees": "commercial_terms",
    "pricing": "commercial_terms",
    "warranty": "commercial_terms",
    "warranties": "commercial_terms",
    "general": "commercial_terms",
    "other": "commercial_terms",
    "sla": "commercial_terms",
    "service_levels": "commercial_terms",
    "escrow": "commercial_terms",
    "feedback": "commercial_terms",
    "data_rights": "commercial_terms",
    # Liability & Indemnity
    "liability": "liability_indemnity",
    "limitation_of_liability": "liability_indemnity",
    "indemnification": "liability_indemnity",
    "indemnity": "liability_indemnity",
    "insurance": "liability_indemnity",
    # IP
    "intellectual_property": "intellectual_property",
    "ip": "intellectual_property",
    "ai_usage": "intellectual_property",
    "ai_training": "intellectual_property",
    # Data Privacy
    "data_privacy": "data_privacy",
    "privacy": "data_privacy",
    # Termination & Renewal
    "termination": "termination_renewal",
    "renewal": "termination_renewal",
    "term": "termination_renewal",
    "force_majeure": "termination_renewal",
    # Governance
    "governing_law": "governance",
    "dispute_resolution": "governance",
    "assignment": "governance",
    "non_compete": "governance",
    "non_solicit": "governance",
    "audit": "governance",
    "audit_rights": "governance",
    "confidentiality": "governance",
    # Security / Compliance
    "security": "security",
    "compliance": "compliance",
}


def canonical_category(clause_type: Optional[str]) -> str:
    """Map any clause_type to a canonical legal taxonomy key."""
    if not clause_type:
        return "commercial_terms"
    raw = _canonicalize_clause_type(clause_type)
    if raw in CLAUSE_TO_CANONICAL:
        return CLAUSE_TO_CANONICAL[raw]
    normalized = raw.lower().strip().replace(" ", "_").replace("-", "_")
    if normalized in CLAUSE_TO_CANONICAL:
        return CLAUSE_TO_CANONICAL[normalized]
    if normalized in CANONICAL_CATEGORIES:
        return normalized
    return "commercial_terms"


def category_label(canonical_key: str) -> str:
    return CANONICAL_CATEGORIES.get(
        canonical_key,
        canonical_key.replace("_", " ").title(),
    )


def risk_score_label(score: float) -> str:
    if score >= 0.81:
        return "Critical"
    if score >= 0.61:
        return "High"
    if score >= 0.41:
        return "Elevated"
    if score >= 0.21:
        return "Moderate"
    return "Minimal"


def normalize_severity(value: Optional[str], default: str = "medium") -> str:
    raw = (value or default).strip().lower()
    return raw if raw in SEVERITY_WEIGHTS else default


def resolution_value(resolution: Any) -> Optional[str]:
    if resolution is None:
        return None
    if hasattr(resolution, "value"):
        return resolution.value
    return str(resolution) if resolution else None


def resolution_type_label(resolution: Optional[str]) -> str:
    if resolution == "resolved":
        return "mitigated"
    if resolution in ("dismissed", "false_positive"):
        return "dismissed"
    if resolution == "acknowledged":
        return "accepted_risk"
    return "open"


def _finding_weight(finding: Any) -> float:
    return SEVERITY_WEIGHTS.get(normalize_severity(getattr(finding, "severity", None)), 0.0)


def _extract_traceability_fields(redline: Any) -> dict[str, str]:
    meta = getattr(redline, "redline_metadata", None) or {}
    if not isinstance(meta, dict):
        return {}
    trace = meta.get("traceability")
    if not isinstance(trace, dict):
        return {}
    return {
        "business_impact": (trace.get("business_impact") or "").strip(),
        "recommended_mitigation": (trace.get("mitigation_strategy") or "").strip(),
        "detected_risk": (trace.get("detected_risk") or "").strip(),
    }


def _default_business_impact(severity: str, title: str) -> str:
    if severity == "critical":
        return f"Material commercial and legal exposure: {title}"
    if severity == "high":
        return f"Significant financial or operational exposure: {title}"
    if severity == "medium":
        return f"Moderate contractual exposure requiring review: {title}"
    return f"Contractual consideration: {title}"


def compute_exposure_metrics(findings: list[Any], overall: float) -> dict[str, float]:
    """Core weighted exposure model — used by every widget."""
    total_weight = sum(_finding_weight(f) for f in findings) or 1.0

    mitigated_weight = dismissed_weight = accepted_weight = open_weight = 0.0
    for f in findings:
        w = _finding_weight(f)
        res = resolution_value(getattr(f, "resolution", None))
        if res == "resolved":
            mitigated_weight += w
        elif res in ("dismissed", "false_positive"):
            dismissed_weight += w
        elif res == "acknowledged":
            accepted_weight += w
        else:
            open_weight += w

    remaining_weight = open_weight + accepted_weight
    scale = overall / total_weight if total_weight > 0 and overall > 0 else 0.0

    remaining_exposure = remaining_weight * scale
    risk_reduction = mitigated_weight * scale
    dismissed_reduction = dismissed_weight * scale
    accepted_reduction = accepted_weight * scale

    return {
        "total_weight": total_weight,
        "remaining_weight": remaining_weight,
        "remaining_exposure": round(remaining_exposure, 4),
        "risk_reduction": round(risk_reduction, 4),
        "dismissed_reduction": round(dismissed_reduction, 4),
        "accepted_reduction": round(accepted_reduction, 4),
        "open_weight": open_weight,
        "accepted_weight": accepted_weight,
        "mitigated_weight": mitigated_weight,
        "dismissed_weight": dismissed_weight,
    }


def compute_category_breakdown(
    findings: list[Any],
    overall: float,
    metrics: dict[str, float],
) -> tuple[list[dict], list[dict]]:
    """Build category breakdown + exposure contributors from identical normalized_contribution."""
    groups: dict[str, list[Any]] = defaultdict(list)
    for f in findings:
        cat = canonical_category(getattr(f, "clause_type", None))
        groups[cat].append(f)

    remaining_exposure = metrics["remaining_exposure"]
    remaining_weight = metrics["remaining_weight"] or 1.0
    total_weight = metrics["total_weight"]

    breakdown: list[dict] = []
    for cat, cat_findings in groups.items():
        cat_weight = sum(_finding_weight(f) for f in cat_findings)
        contribution = round((cat_weight / total_weight) * overall if overall > 0 else 0.0, 4)

        cat_open = cat_accepted = cat_mitigated = cat_dismissed = 0.0
        for f in cat_findings:
            w = _finding_weight(f)
            res = resolution_value(getattr(f, "resolution", None))
            if res == "resolved":
                cat_mitigated += w
            elif res in ("dismissed", "false_positive"):
                cat_dismissed += w
            elif res == "acknowledged":
                cat_accepted += w
            else:
                cat_open += w

        cat_remaining_weight = cat_open + cat_accepted
        if remaining_weight > 0 and overall > 0:
            normalized = round(
                (cat_remaining_weight / remaining_weight) * remaining_exposure, 4
            )
        else:
            normalized = contribution

        exposure_share_pct = round(
            (normalized / remaining_exposure * 100) if remaining_exposure > 0 else 0.0, 1
        )

        max_severity = max(
            cat_findings,
            key=lambda f: SEVERITY_WEIGHTS.get(normalize_severity(f.severity), 0.0),
        ).severity

        drill_down = []
        for f in cat_findings:
            res_val = resolution_value(f.resolution)
            finding_contrib = round(
                (_finding_weight(f) / total_weight) * overall if overall > 0 else 0.0, 4
            )
            remaining_contrib = finding_contrib
            if res_val in ("resolved", "dismissed", "false_positive"):
                remaining_contrib = 0.0
            elif res_val == "acknowledged":
                remaining_contrib = finding_contrib

            risk_reduction_value = 0.0
            if res_val == "resolved":
                risk_reduction_value = finding_contrib

            drill_down.append({
                "finding_id": str(getattr(f, "finding_id", "")),
                "title": f.title,
                "severity": normalize_severity(f.severity),
                "risk_score": getattr(f, "risk_score", None),
                "contribution": finding_contrib,
                "remaining_contribution": round(remaining_contrib, 4),
                "risk_reduction_value": round(risk_reduction_value, 4),
                "resolution": res_val,
                "resolution_type": resolution_type_label(res_val),
                "clause_type": canonical_category(f.clause_type),
                "clause_label": category_label(canonical_category(f.clause_type)),
                "recommended_mitigation": (getattr(f, "recommendation", None) or "").strip() or None,
                "business_impact": _default_business_impact(normalize_severity(f.severity), f.title),
            })

        breakdown.append({
            "category": cat,
            "label": category_label(cat),
            "contribution": contribution,
            "normalized_contribution": normalized,
            "exposure_share_pct": exposure_share_pct,
            "finding_count": len(cat_findings),
            "severity": normalize_severity(max_severity),
            "mitigated_count": sum(
                1 for f in cat_findings if resolution_value(f.resolution) == "resolved"
            ),
            "dismissed_count": sum(
                1
                for f in cat_findings
                if resolution_value(f.resolution) in ("dismissed", "false_positive")
            ),
            "accepted_count": sum(
                1 for f in cat_findings if resolution_value(f.resolution) == "acknowledged"
            ),
            "open_count": sum(
                1 for f in cat_findings if resolution_value(f.resolution) is None
            ),
            "findings": drill_down,
        })

    breakdown.sort(key=lambda x: x["normalized_contribution"], reverse=True)

    contributors = []
    for item in breakdown:
        cat = item["category"]
        cat_findings = groups[cat]
        cat_open = cat_accepted = cat_mitigated = cat_dismissed = 0.0
        for f in cat_findings:
            w = _finding_weight(f)
            res = resolution_value(f.resolution)
            if res == "resolved":
                cat_mitigated += w
            elif res in ("dismissed", "false_positive"):
                cat_dismissed += w
            elif res == "acknowledged":
                cat_accepted += w
            else:
                cat_open += w

        contributors.append({
            "category": cat,
            "label": item["label"],
            "contribution": item["contribution"],
            "normalized_contribution": item["normalized_contribution"],
            "exposure_share_pct": item["exposure_share_pct"],
            "open_weight": round(cat_open, 4),
            "accepted_weight": round(cat_accepted, 4),
            "mitigated_weight": round(cat_mitigated, 4),
            "dismissed_weight": round(cat_dismissed, 4),
            "details": [],
        })

    contributors.sort(key=lambda x: x["normalized_contribution"], reverse=True)
    return breakdown, contributors


def build_finding_lists(
    findings: list[Any],
    overall: float,
    total_weight: float,
    redlines_by_finding: dict[str, list[Any]],
) -> dict[str, list[dict]]:
    """Build open / mitigated / accepted / dismissed lists with decision-support fields."""
    mitigated_list: list[dict] = []
    accepted_list: list[dict] = []
    dismissed_list: list[dict] = []
    open_list: list[dict] = []

    for f in findings:
        res_val = resolution_value(f.resolution)
        sev = normalize_severity(f.severity)
        contrib = round(
            (_finding_weight(f) / total_weight) * overall if overall > 0 else 0.0, 4
        )
        linked = redlines_by_finding.get(str(getattr(f, "finding_id", "")), [])
        trace = {}
        for rl in linked:
            trace = _extract_traceability_fields(rl)
            if trace.get("business_impact") or trace.get("recommended_mitigation"):
                break

        business_impact = trace.get("business_impact") or _default_business_impact(
            sev, f.title
        )
        recommended_mitigation = (
            trace.get("recommended_mitigation")
            or (getattr(f, "recommendation", None) or "").strip()
            or "Review proposed redline and negotiate protective language."
        )

        item = {
            "finding_id": str(getattr(f, "finding_id", "")),
            "title": f.title,
            "clause_type": canonical_category(f.clause_type),
            "clause_label": category_label(canonical_category(f.clause_type)),
            "severity": sev,
            "remaining_contribution": contrib if res_val not in ("resolved", "dismissed", "false_positive") else 0.0,
            "risk_reduction_value": contrib if res_val == "resolved" else 0.0,
            "business_impact": business_impact,
            "recommended_mitigation": recommended_mitigation,
            "review_state": resolution_type_label(res_val),
            "linked_redline_count": len(linked),
        }

        if res_val == "resolved":
            item["resolution"] = "mitigated"
            item["resolution_label"] = "Mitigated"
            mitigated_list.append(item)
        elif res_val in ("dismissed", "false_positive"):
            item["resolution"] = res_val
            item["resolution_label"] = "Dismissed"
            dismissed_list.append(item)
        elif res_val == "acknowledged":
            item["resolution"] = "accepted_risk"
            item["resolution_label"] = "Accepted Exposure"
            accepted_list.append(item)
        else:
            item["resolution"] = "open"
            item["resolution_label"] = "Open Exposure"
            open_list.append(item)

    open_list.sort(
        key=lambda x: (
            -SEVERITY_WEIGHTS.get(x["severity"], 0),
            -x.get("remaining_contribution", 0),
        )
    )
    return {
        "open_findings": open_list,
        "mitigated_findings": mitigated_list,
        "accepted_risk_findings": accepted_list,
        "dismissed_findings": dismissed_list,
    }


def build_delta_explanations(metrics: dict[str, float]) -> list[dict]:
    """Human-readable risk delta timeline entries."""
    explanations: list[dict] = []
    if metrics["risk_reduction"] > 0:
        explanations.append({
            "category": "mitigation",
            "label": "Mitigated through accepted changes",
            "contribution": -metrics["risk_reduction"],
            "details": [
                f"Risk reduced by {metrics['risk_reduction']:.0%} via resolved findings and redlines",
            ],
        })
    if metrics["dismissed_reduction"] > 0:
        explanations.append({
            "category": "dismissed",
            "label": "Dismissed false positives",
            "contribution": -metrics["dismissed_reduction"],
            "details": [
                f"Removed {metrics['dismissed_reduction']:.0%} from exposure equation (not real risk)",
            ],
        })
    if metrics["accepted_reduction"] > 0:
        explanations.append({
            "category": "accepted",
            "label": "Business-accepted exposure",
            "contribution": metrics["accepted_reduction"],
            "details": [
                f"{metrics['accepted_reduction']:.0%} retained as accepted business exposure",
            ],
        })
    return explanations


def build_mitigation_effectiveness(metrics: dict[str, float], overall: float) -> dict:
    """Explainable mitigation scoring summary."""
    mitigated = metrics["risk_reduction"]
    dismissed = metrics["dismissed_reduction"]
    accepted = metrics["accepted_reduction"]
    remaining = metrics["remaining_exposure"]
    total_addressed = mitigated + dismissed
    effectiveness_pct = round(
        (mitigated / overall * 100) if overall > 0 else 0.0, 1
    )
    return {
        "mitigated_pct": round(mitigated * 100, 1),
        "dismissed_pct": round(dismissed * 100, 1),
        "accepted_pct": round(accepted * 100, 1),
        "remaining_pct": round(remaining * 100, 1),
        "effectiveness_score": effectiveness_pct,
        "total_risk_addressed": round(total_addressed, 4),
    }


def build_per_finding_mitigation_suggestions(
    breakdown: list[dict],
) -> list[dict]:
    """Attach mitigation effectiveness estimates to each category in the breakdown.

    Uses the mitigation_effectiveness engine to suggest the most effective
    mitigations for each clause category based on its remaining exposure.
    """
    try:
        from app.domains.review.mitigation_effectiveness import suggest_mitigations

        suggestions_by_category: list[dict] = []
        for item in breakdown:
            normalized = item.get("normalized_contribution", 0.0)
            if normalized <= 0:
                continue
            cat = item.get("category", "")
            mitigations = suggest_mitigations(cat, normalized)
            if mitigations:
                suggestions_by_category.append({
                    "category": cat,
                    "label": item.get("label", cat),
                    "remaining_contribution": normalized,
                    "suggested_mitigations": mitigations,
                })
        return suggestions_by_category
    except ImportError:
        return []
    except Exception:
        return []


def compute_top_recommended_actions(
    mitigation_suggestions: list[dict],
    max_actions: int = 3,
    current_contract_risk: float = 1.0,
) -> dict:
    """Compute the top recommended actions across ALL categories, sorted by impact.

    Returns an executive summary widget showing the highest-impact mitigations
    available across the entire contract, with total potential reduction.

    The `total_potential_reduction_pct` is computed relative to the current
    contract risk (remaining exposure), so the math is consistent:
        current_contract_risk - total_potential_reduction_abs = estimated residual
        total_potential_reduction_pct = total_potential_reduction_abs / current_contract_risk

    Example:
        current_contract_risk = 0.76 (76%)
        total_potential_reduction_abs = 0.10 (10pp)
        total_potential_reduction_pct = 0.10 / 0.76 = 0.13 (13%)
        estimated residual = 0.76 - 0.10 = 0.66 (66%)
        User sees: "Potential: -13% → Est. residual: 66%"
        Math check: 76% - (13% of 76%) = 76% - 10% = 66% ✓

    Args:
        mitigation_suggestions: Output from build_per_finding_mitigation_suggestions
        max_actions: Number of top actions to return (default 3)
        current_contract_risk: Current remaining exposure (denominator for % calc)

    Returns:
    {
        "top_actions": [...],
        "total_potential_reduction_pct": 0.13,   # Relative to current risk
        "total_potential_reduction_abs": 0.10,   # Absolute exposure points
        "action_count": 3,
    }
    """
    all_actions: list[dict] = []
    for suggestion in mitigation_suggestions:
        category = suggestion.get("category", "")
        label = suggestion.get("label", category)
        remaining = suggestion.get("remaining_contribution", 0.0)
        for mitigation in suggestion.get("suggested_mitigations", []):
            reduction_pct = mitigation.get("estimated_reduction_pct", 0.0)
            reduction_abs = remaining * reduction_pct
            all_actions.append({
                "category": category,
                "label": label,
                "mitigation_type": mitigation.get("mitigation_type", ""),
                "mitigation_label": mitigation.get("label", ""),
                "description": mitigation.get("description", ""),
                "estimated_reduction_pct": round(reduction_pct, 4),
                "estimated_reduction_abs": round(reduction_abs, 4),
                "confidence": round(mitigation.get("confidence", 0.0), 2),
                "source": mitigation.get("source", ""),
                "remaining_contribution": round(remaining, 4),
            })

    # Sort by absolute reduction (highest impact first)
    all_actions.sort(key=lambda x: x["estimated_reduction_abs"], reverse=True)
    top_actions = all_actions[:max_actions]

    total_potential_abs = sum(a["estimated_reduction_abs"] for a in top_actions)
    # Total potential as percentage of CURRENT contract risk (consistent math)
    total_potential_pct = (
        round(total_potential_abs / current_contract_risk, 4) if current_contract_risk > 0 else 0.0
    )

    return {
        "top_actions": top_actions,
        "total_potential_reduction_pct": round(total_potential_pct, 4),
        "total_potential_reduction_abs": round(total_potential_abs, 4),
        "action_count": len(top_actions),
    }


def determine_exposure_mode(
    metrics: dict[str, float],
    review_status: Optional[str],
    review_started: bool,
) -> str:
    """Return 'detected' pre-review, 'remaining' once review activity exists.

    Enterprise semantics:
    - Before review starts → "detected" (show Original AI Risk)
    - After review starts → "remaining" (show Remaining Exposure)

    The Original AI Risk score is always preserved as `overall_risk_score`
    and displayed as a reference line.
    """
    if review_started:
        return "remaining"
    # If any resolution activity exists, consider review started
    if metrics.get("remaining_weight", 0) < metrics.get("total_weight", 0):
        return "remaining"
    return "detected"


def risk_breakdown_payload(
    overall: float,
    findings: list[Any],
    *,
    review_status: Optional[str] = None,
    review_started: bool = False,
    redlines_by_finding: Optional[dict[str, list[Any]]] = None,
    status: Optional[str] = None,
    extra_breakdown: Optional[list] = None,
) -> dict:
    """Assemble full risk-breakdown API response."""
    redlines_by_finding = redlines_by_finding or {}
    metrics = compute_exposure_metrics(findings, overall)
    breakdown, contributors = compute_category_breakdown(findings, overall, metrics)
    if extra_breakdown:
        breakdown = extra_breakdown

    lists = build_finding_lists(
        findings, overall, metrics["total_weight"], redlines_by_finding
    )
    exposure_mode = determine_exposure_mode(metrics, review_status, review_started)
    current_contract_risk = metrics["remaining_exposure"]

    mitigation_suggestions = build_per_finding_mitigation_suggestions(breakdown)
    top_actions = compute_top_recommended_actions(
        mitigation_suggestions,
        current_contract_risk=current_contract_risk,
    )

    payload = {
        "overall_risk_score": round(overall, 4),
        "overall_label": risk_score_label(overall),
        "original_risk_score": round(overall, 4),
        "current_contract_risk": current_contract_risk,
        "remaining_exposure": current_contract_risk,
        "remaining_label": risk_score_label(current_contract_risk),
        "exposure_mode": exposure_mode,
        "review_started": review_started,
        "breakdown": breakdown,
        "risk_reduction": metrics["risk_reduction"],
        "dismissed_reduction": metrics["dismissed_reduction"],
        "accepted_reduction": metrics["accepted_reduction"],
        "risk_delta": round(overall - current_contract_risk, 4),
        "mitigation_effectiveness": build_mitigation_effectiveness(metrics, overall),
        "mitigation_suggestions": mitigation_suggestions,
        "top_recommended_actions": top_actions,
        "delta_explanations": build_delta_explanations(metrics),
        "exposure_contributors": contributors,
        **lists,
    }
    if status:
        payload["status"] = status
    return payload


def risk_breakdown_shell(overall: float = 0.0, *, status: Optional[str] = None, **extra) -> dict:
    """Consistent early-return payload."""
    remaining = extra.get("remaining_exposure", overall)
    contract_value = float(extra.get("contract_value", 0) or 0)
    currency = extra.get("currency", "USD")
    current_risk = float(remaining or 0)
    after_mitigation = round(min(current_risk * 0.18, 0.05), 4)

    return {
        "overall_risk_score": round(overall, 4),
        "overall_label": risk_score_label(overall),
        "original_risk_score": round(overall, 4),
        "current_contract_risk": round(remaining, 4),
        "remaining_exposure": round(remaining, 4),
        "remaining_label": risk_score_label(remaining),
        "exposure_mode": extra.get("exposure_mode", "remaining"),
        "review_started": extra.get("review_started", False),
        "breakdown": extra.get("breakdown", []),
        "risk_reduction": round(extra.get("risk_reduction", 0.0), 4),
        "dismissed_reduction": round(extra.get("dismissed_reduction", 0.0), 4),
        "accepted_reduction": round(extra.get("accepted_reduction", 0.0), 4),
        "risk_delta": round(extra.get("risk_delta", 0.0), 4),
        "mitigation_effectiveness": extra.get("mitigation_effectiveness", {}),
        "mitigation_suggestions": extra.get("mitigation_suggestions", []),
        "top_recommended_actions": extra.get("top_recommended_actions", {}),
        "mitigated_findings": extra.get("mitigated_findings", []),
        "accepted_risk_findings": extra.get("accepted_risk_findings", []),
        "dismissed_findings": extra.get("dismissed_findings", []),
        "open_findings": extra.get("open_findings", []),
        "delta_explanations": extra.get("delta_explanations", []),
        "exposure_contributors": extra.get("exposure_contributors", []),
        "financial_impact": {
            "contract_value": round(contract_value, 2),
            "currency": currency,
            "current_risk_pct": round(current_risk * 100, 1),
            "current_exposure": round(contract_value * current_risk, 2),
            "after_mitigation_pct": round(after_mitigation * 100, 1),
            "after_mitigation_exposure": round(contract_value * after_mitigation, 2),
            "potential_savings": round(contract_value * (current_risk - after_mitigation), 2),
        },
        **({"status": status} if status else {}),
    }
