"""Mitigation effectiveness engine — per-clause-type exposure reduction estimates.

Provides explainable remediation intelligence:
- Each mitigation type has an estimated effectiveness range
- Effectiveness varies by clause category
- Confidence intervals reflect real-world variability
- Results are used by the risk breakdown panel to show "why" a mitigation works

Enterprise semantics:
- effectiveness_pct: estimated reduction in that clause's contribution to remaining exposure
- confidence: how reliable the estimate is (0.0-1.0)
- source: basis for the estimate (legal precedent, industry standard, ML prediction)
"""

from __future__ import annotations

from typing import Optional

# ── Per-clause-type mitigation effectiveness registry ──────────────────────
# Format: { clause_category: { mitigation_type: { effectiveness, confidence, source } } }

MITIGATION_EFFECTIVENESS_REGISTRY: dict[str, dict[str, dict]] = {
    "liability_indemnity": {
        "adding_indemnification": {
            "effectiveness_pct": 0.18,
            "confidence": 0.85,
            "source": "industry_standard",
            "label": "Adding indemnification clause",
            "description": "Reduces litigation exposure by requiring counterparty to cover losses",
        },
        "adding_liability_cap": {
            "effectiveness_pct": 0.14,
            "confidence": 0.82,
            "source": "industry_standard",
            "label": "Adding liability cap",
            "description": "Limits maximum financial exposure to a fixed amount",
        },
        "narrowing_indemnity_scope": {
            "effectiveness_pct": 0.12,
            "confidence": 0.78,
            "source": "legal_precedent",
            "label": "Narrowing indemnity scope",
            "description": "Restricts indemnification to third-party claims only",
        },
        "removing_consequential_damages": {
            "effectiveness_pct": 0.15,
            "confidence": 0.80,
            "source": "industry_standard",
            "label": "Removing consequential damages waiver",
            "description": "Preserves right to claim lost profits and indirect damages",
        },
    },
    "intellectual_property": {
        "restricting_derivative_works": {
            "effectiveness_pct": 0.22,
            "confidence": 0.75,
            "source": "ml_prediction",
            "label": "Restricting derivative works and ML training",
            "description": "Prevents counterparty from using customer data for model training",
        },
        "adding_ip_ownership_clause": {
            "effectiveness_pct": 0.20,
            "confidence": 0.88,
            "source": "industry_standard",
            "label": "Adding IP ownership clause",
            "description": "Clarifies ownership of intellectual property and deliverables",
        },
        "narrowing_ip_license": {
            "effectiveness_pct": 0.15,
            "confidence": 0.80,
            "source": "legal_precedent",
            "label": "Narrowing IP license scope",
            "description": "Restricts license to specific use cases and timeframes",
        },
    },
    "data_privacy": {
        "restricting_data_use": {
            "effectiveness_pct": 0.22,
            "confidence": 0.82,
            "source": "industry_standard",
            "label": "Restricting data use and sharing",
            "description": "Limits how counterparty can collect, use, and share customer data",
        },
        "adding_compliance_language": {
            "effectiveness_pct": 0.15,
            "confidence": 0.78,
            "source": "regulatory_requirement",
            "label": "Adding GDPR/CCPA compliance language",
            "description": "Ensures contractual alignment with data protection regulations",
        },
        "adding_data_breach_protocol": {
            "effectiveness_pct": 0.18,
            "confidence": 0.85,
            "source": "industry_standard",
            "label": "Adding data breach notification protocol",
            "description": "Mandates timely breach disclosure and remediation responsibilities",
        },
    },
    "commercial_terms": {
        "adding_price_protection": {
            "effectiveness_pct": 0.12,
            "confidence": 0.75,
            "source": "industry_standard",
            "label": "Adding price protection / cap on increases",
            "description": "Limits annual price increases to a fixed percentage",
        },
        "adding_service_levels": {
            "effectiveness_pct": 0.14,
            "confidence": 0.80,
            "source": "industry_standard",
            "label": "Adding service level commitments",
            "description": "Defines minimum performance standards with remedy mechanisms",
        },
        "clarifying_warranty_scope": {
            "effectiveness_pct": 0.10,
            "confidence": 0.72,
            "source": "legal_precedent",
            "label": "Clarifying warranty scope and exclusions",
            "description": "Narrows warranty obligations to match industry practice",
        },
    },
    "termination_renewal": {
        "adding_for_cause_termination": {
            "effectiveness_pct": 0.16,
            "confidence": 0.86,
            "source": "industry_standard",
            "label": "Adding for-cause termination rights",
            "description": "Provides right to terminate for material breach or insolvency",
        },
        "reducing_termination_notice": {
            "effectiveness_pct": 0.10,
            "confidence": 0.78,
            "source": "legal_precedent",
            "label": "Reducing termination notice period",
            "description": "Shortens notice period from 90 to 30 days for faster exit",
        },
        "adding_auto_renewal_opt_out": {
            "effectiveness_pct": 0.12,
            "confidence": 0.84,
            "source": "industry_standard",
            "label": "Adding auto-renewal opt-out window",
            "description": "Ensures ability to exit before automatic renewal",
        },
    },
    "governance": {
        "adding_dispute_resolution": {
            "effectiveness_pct": 0.14,
            "confidence": 0.80,
            "source": "industry_standard",
            "label": "Adding dispute resolution clause",
            "description": "Establishes mediation/arbitration framework before litigation",
        },
        "adding_audit_rights": {
            "effectiveness_pct": 0.12,
            "confidence": 0.82,
            "source": "industry_standard",
            "label": "Adding audit and inspection rights",
            "description": "Provides right to verify compliance with contractual obligations",
        },
        "clarifying_governing_law": {
            "effectiveness_pct": 0.08,
            "confidence": 0.90,
            "source": "legal_precedent",
            "label": "Clarifying governing law and jurisdiction",
            "description": "Removes ambiguity about which legal framework applies",
        },
    },
    "security": {
        "adding_security_requirements": {
            "effectiveness_pct": 0.20,
            "confidence": 0.82,
            "source": "industry_standard",
            "label": "Adding security requirements and standards",
            "description": "Mandates specific security controls and certifications",
        },
        "adding_incident_response": {
            "effectiveness_pct": 0.16,
            "confidence": 0.78,
            "source": "industry_standard",
            "label": "Adding incident response obligations",
            "description": "Requires documented incident response plan and reporting",
        },
    },
    "compliance": {
        "adding_regulatory_compliance": {
            "effectiveness_pct": 0.18,
            "confidence": 0.85,
            "source": "regulatory_requirement",
            "label": "Adding regulatory compliance warranty",
            "description": "Requires counterparty to maintain all necessary licenses and approvals",
        },
        "adding_anti_corruption": {
            "effectiveness_pct": 0.16,
            "confidence": 0.88,
            "source": "regulatory_requirement",
            "label": "Adding anti-corruption / FCPA clause",
            "description": "Explicitly prohibits bribery and corrupt practices",
        },
    },
}


def get_mitigation_effectiveness(
    clause_category: str,
    mitigation_type: Optional[str] = None,
) -> list[dict]:
    """Get effectiveness estimates for a clause category.

    Args:
        clause_category: Canonical clause category key (e.g. 'liability_indemnity')
        mitigation_type: Optional specific mitigation type. If None, returns all.

    Returns:
        List of mitigation effectiveness estimates, each containing:
        - mitigation_type: machine key
        - label: human-readable name
        - description: what the mitigation does
        - effectiveness_pct: estimated reduction (0.0-1.0)
        - confidence: reliability of estimate (0.0-1.0)
        - source: basis for estimate
    """
    category_effects = MITIGATION_EFFECTIVENESS_REGISTRY.get(clause_category, {})
    if not category_effects:
        return []

    if mitigation_type:
        entry = category_effects.get(mitigation_type)
        if not entry:
            return []
        return [{"mitigation_type": mitigation_type, **entry}]

    return [
        {"mitigation_type": mt, **details}
        for mt, details in category_effects.items()
    ]


def compute_mitigation_impact(
    finding_contribution: float,
    clause_category: str,
    mitigation_type: str,
) -> dict:
    """Compute the estimated exposure reduction for a specific mitigation.

    Args:
        finding_contribution: The finding's contribution to remaining exposure (0.0-1.0)
        clause_category: Canonical clause category key
        mitigation_type: Specific mitigation type to apply

    Returns:
        Dict with:
        - estimated_reduction: absolute reduction in exposure points
        - estimated_reduction_pct: percentage reduction in exposure
        - confidence: reliability of estimate
        - source: basis for estimate
        - range_low: lower bound of estimate (95% confidence)
        - range_high: upper bound of estimate (95% confidence)
    """
    effects = get_mitigation_effectiveness(clause_category, mitigation_type)
    if not effects:
        return {
            "estimated_reduction": 0.0,
            "estimated_reduction_pct": 0.0,
            "confidence": 0.0,
            "source": "unknown",
            "range_low": 0.0,
            "range_high": 0.0,
        }

    effect = effects[0]
    effectiveness = effect["effectiveness_pct"]
    confidence = effect["confidence"]

    estimated_reduction = finding_contribution * effectiveness
    # 95% confidence interval: ±20% of effectiveness at confidence=1.0, wider at lower confidence
    margin = 0.20 * (1.0 + (1.0 - confidence) * 0.5)

    return {
        "estimated_reduction": round(estimated_reduction, 4),
        "estimated_reduction_pct": round(effectiveness, 4),
        "confidence": round(confidence, 2),
        "source": effect["source"],
        "range_low": round(estimated_reduction * (1.0 - margin), 4),
        "range_high": round(estimated_reduction * (1.0 + margin), 4),
        "label": effect["label"],
        "description": effect["description"],
    }


def suggest_mitigations(
    clause_category: str,
    finding_contribution: float,
    max_suggestions: int = 3,
) -> list[dict]:
    """Suggest the most effective mitigations for a clause category.

    Args:
        clause_category: Canonical clause category key
        finding_contribution: The finding's contribution to remaining exposure
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of mitigation suggestions sorted by effectiveness (highest first),
        each with computed impact estimates.
    """
    all_effects = get_mitigation_effectiveness(clause_category)
    if not all_effects:
        return []

    scored = []
    for effect in all_effects:
        impact = compute_mitigation_impact(
            finding_contribution, clause_category, effect["mitigation_type"]
        )
        scored.append({
            **impact,
            "mitigation_type": effect["mitigation_type"],
        })

    scored.sort(key=lambda x: x["estimated_reduction"], reverse=True)
    return scored[:max_suggestions]
