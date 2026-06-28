"""Built-in Workflow Marketplace Packs — seeded packs that tenants can clone.

14 packs across 9 categories. Each is a template — tenants clone and customize.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Category Constants ─────────────────────────────────────────────


CATEGORY_REVIEW = "review"
CATEGORY_PROCUREMENT = "procurement"
CATEGORY_SALES = "sales"
CATEGORY_HR = "hr"
CATEGORY_RENEWAL = "renewal"
CATEGORY_COMPLIANCE = "compliance"
CATEGORY_LEGAL = "legal"
CATEGORY_SUPPLIER = "supplier"
CATEGORY_FINANCE = "finance"


# ── Built-in Pack Definitions ──────────────────────────────────────


BUILT_IN_PACKS: dict[str, dict[str, Any]] = {
    # ── Review Category ──────────────────────────────────────────
    "standard_review": {
        "name": "Standard Contract Review",
        "description": "Default review workflow with AI analysis, manual review, and standard approval chain.",
        "category": CATEGORY_REVIEW,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "AI Risk Analysis", "condition": {}}],
            },
            {
                "name": "AI Risk Analysis",
                "stage_type": "ai_analysis",
                "order": 2,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Manual Review", "condition": {}}],
            },
            {
                "name": "Manual Review",
                "stage_type": "review",
                "order": 3,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "contract_reviewer",
                "transitions": [
                    {"target": "Approval", "condition": {"==": [{"var": "contract.risk_score"}, "low"]}},
                    {"target": "Executive Approval", "condition": {">": [{"var": "contract.risk_score"}, 70]}},
                ],
            },
            {
                "name": "Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 24,
                "required_role": "contract_manager",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Executive Approval",
                "stage_type": "approval",
                "order": 5,
                "on_entry": ["require_approval"],
                "sla_hours": 72,
                "required_role": "director",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 6,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "high_risk_escalation",
                "description": "Escalate to executive approval when risk score exceeds 70.",
                "conditions": {">": [{"var": "risk.score"}, 70]},
                "effect": "escalate",
                "priority": 100,
            },
            {
                "rule_name": "low_risk_fast_track",
                "description": "Fast-track low-risk contracts through standard approval.",
                "conditions": {"<=": [{"var": "risk.score"}, 30]},
                "effect": "fast_track",
                "priority": 90,
            },
        ],
    },
    "ai_review": {
        "name": "AI-Powered Review",
        "description": "AI-first review workflow with automated clause detection and smart routing.",
        "category": CATEGORY_REVIEW,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Deep AI Analysis", "condition": {}}],
            },
            {
                "name": "Deep AI Analysis",
                "stage_type": "ai_analysis",
                "order": 2,
                "on_entry": ["auto_proceed"],
                "sla_hours": 2,
                "transitions": [
                    {"target": "Auto-Approved", "condition": {"<": [{"var": "ai.findings_count"}, 3]}},
                    {"target": "Manual Review", "condition": {">=": [{"var": "ai.findings_count"}, 3]}},
                ],
            },
            {
                "name": "Manual Review",
                "stage_type": "review",
                "order": 3,
                "on_entry": ["require_review"],
                "sla_hours": 24,
                "required_role": "contract_reviewer",
                "transitions": [{"target": "Approval", "condition": {}}],
            },
            {
                "name": "Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 24,
                "required_role": "contract_manager",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Auto-Approved",
                "stage_type": "approval",
                "order": 5,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 6,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "auto_approve_low_findings",
                "description": "Auto-approve contracts with fewer than 3 AI findings.",
                "conditions": {"<": [{"var": "ai.findings_count"}, 3]},
                "effect": "auto_approve",
                "priority": 100,
            },
        ],
    },
    "legal_review": {
        "name": "Legal Review",
        "description": "Legal-centric review workflow with counsel review and partner sign-off.",
        "category": CATEGORY_LEGAL,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Legal Counsel Review", "condition": {}}],
            },
            {
                "name": "Legal Counsel Review",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "legal_counsel",
                "transitions": [
                    {"target": "Partner Sign-Off", "condition": {"==": [{"var": "contract.risk_score"}, "high"]}},
                    {"target": "Completed", "condition": {"!=": [{"var": "contract.risk_score"}, "high"]}},
                ],
            },
            {
                "name": "Partner Sign-Off",
                "stage_type": "approval",
                "order": 3,
                "on_entry": ["require_approval"],
                "sla_hours": 72,
                "required_role": "legal_partner",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 4,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "partner_escalation",
                "description": "High-risk contracts require partner sign-off.",
                "conditions": {"==": [{"var": "risk.category"}, "high"]},
                "effect": "require_partner",
                "priority": 100,
            },
        ],
    },

    # ── Sales Category ───────────────────────────────────────────
    "sales_contract": {
        "name": "Sales Contract Review",
        "description": "Sales contract workflow with deal desk approval and commission validation.",
        "category": CATEGORY_SALES,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Deal Review", "condition": {}}],
            },
            {
                "name": "Deal Review",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 24,
                "required_role": "sales_manager",
                "transitions": [
                    {"target": "Deal Desk Approval", "condition": {">": [{"var": "contract.value"}, 50000]}},
                    {"target": "Auto-Approved", "condition": {"<=": [{"var": "contract.value"}, 50000]}},
                ],
            },
            {
                "name": "Deal Desk Approval",
                "stage_type": "approval",
                "order": 3,
                "on_entry": ["require_approval"],
                "sla_hours": 48,
                "required_role": "deal_desk",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Auto-Approved",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 5,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "value_threshold_escalation",
                "description": "Contracts over $50K require deal desk approval.",
                "conditions": {">": [{"var": "contract.value"}, 50000]},
                "effect": "escalate_to_deal_desk",
                "priority": 100,
            },
        ],
    },

    # ── Procurement Category ──────────────────────────────────────
    "procurement": {
        "name": "Procurement Contract Review",
        "description": "Procurement workflow with value-based approval chains and vendor review.",
        "category": CATEGORY_PROCUREMENT,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Procurement Review", "condition": {}}],
            },
            {
                "name": "Procurement Review",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "procurement_officer",
                "transitions": [
                    {"target": "Manager Approval", "condition": {"<=": [{"var": "contract.value"}, 100000]}},
                    {"target": "Director Approval", "condition": {">": [{"var": "contract.value"}, 100000]}},
                ],
            },
            {
                "name": "Manager Approval",
                "stage_type": "approval",
                "order": 3,
                "on_entry": ["require_approval"],
                "sla_hours": 24,
                "required_role": "procurement_manager",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Director Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 48,
                "required_role": "procurement_director",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 5,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "high_value_escalation",
                "description": "Contracts over $100K require director approval.",
                "conditions": {">": [{"var": "contract.value"}, 100000]},
                "effect": "escalate_to_director",
                "priority": 100,
            },
        ],
    },
    "supplier": {
        "name": "Supplier Contract Review",
        "description": "Supplier onboarding and contract review with tier-based routing.",
        "category": CATEGORY_SUPPLIER,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Supplier Due Diligence", "condition": {}}],
            },
            {
                "name": "Supplier Due Diligence",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 72,
                "required_role": "vendor_manager",
                "transitions": [
                    {"target": "Tier 1 Approval", "condition": {"==": [{"var": "supplier.tier"}, 1]}},
                    {"target": "Standard Approval", "condition": {"in": [{"var": "supplier.tier"}, [2, 3]]}},
                ],
            },
            {
                "name": "Tier 1 Approval",
                "stage_type": "approval",
                "order": 3,
                "on_entry": ["require_approval"],
                "sla_hours": 48,
                "required_role": "vendor_director",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Standard Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 24,
                "required_role": "vendor_manager",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 5,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "tier1_escalation",
                "description": "Tier 1 suppliers require director-level approval.",
                "conditions": {"==": [{"var": "supplier.tier"}, 1]},
                "effect": "escalate_to_director",
                "priority": 100,
            },
        ],
    },

    # ── HR Category ───────────────────────────────────────────────
    "hr": {
        "name": "HR Contract Review",
        "description": "HR contract workflow for employment agreements, contractor terms, and NDAs.",
        "category": CATEGORY_HR,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "HR Review", "condition": {}}],
            },
            {
                "name": "HR Review",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 24,
                "required_role": "hr_manager",
                "transitions": [
                    {"target": "Legal Review", "condition": {"==": [{"var": "contract.type"}, "employment"]}},
                    {"target": "HR Approval", "condition": {"!=": [{"var": "contract.type"}, "employment"]}},
                ],
            },
            {
                "name": "Legal Review",
                "stage_type": "review",
                "order": 3,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "legal_counsel",
                "transitions": [{"target": "HR Approval", "condition": {}}],
            },
            {
                "name": "HR Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 24,
                "required_role": "hr_director",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 5,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "employment_legal_review",
                "description": "Employment agreements require legal counsel review.",
                "conditions": {"==": [{"var": "contract.type"}, "employment"]},
                "effect": "require_legal_review",
                "priority": 100,
            },
        ],
    },

    # ── Renewal Category ──────────────────────────────────────────
    "renewal": {
        "name": "Contract Renewal",
        "description": "Renewal workflow with auto-renewal detection, renegotiation triggers, and approval.",
        "category": CATEGORY_RENEWAL,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Renewal Triggered",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Renewal Assessment", "condition": {}}],
            },
            {
                "name": "Renewal Assessment",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "contract_manager",
                "transitions": [
                    {"target": "Auto-Renew", "condition": {"==": [{"var": "contract.auto_renew"}, True]}},
                    {"target": "Renegotiation", "condition": {"==": [{"var": "contract.auto_renew"}, False]}},
                ],
            },
            {
                "name": "Auto-Renew",
                "stage_type": "approval",
                "order": 3,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Renegotiation",
                "stage_type": "review",
                "order": 4,
                "on_entry": ["require_review"],
                "sla_hours": 120,
                "required_role": "contract_negotiator",
                "transitions": [{"target": "Approval", "condition": {}}],
            },
            {
                "name": "Approval",
                "stage_type": "approval",
                "order": 5,
                "on_entry": ["require_approval"],
                "sla_hours": 48,
                "required_role": "contract_director",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 6,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "auto_renew_detection",
                "description": "Contracts with auto-renewal flag proceed directly.",
                "conditions": {"==": [{"var": "contract.auto_renew"}, True]},
                "effect": "auto_renew",
                "priority": 100,
            },
        ],
    },

    # ── Risk-Based Category ───────────────────────────────────────
    "high_risk": {
        "name": "High Risk Contract Review",
        "description": "Enhanced review for high-risk contracts with mandatory compliance and exec sign-off.",
        "category": CATEGORY_COMPLIANCE,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Enhanced AI Analysis", "condition": {}}],
            },
            {
                "name": "Enhanced AI Analysis",
                "stage_type": "ai_analysis",
                "order": 2,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Compliance Check", "condition": {}}],
            },
            {
                "name": "Compliance Check",
                "stage_type": "compliance_check",
                "order": 3,
                "on_entry": ["require_review"],
                "sla_hours": 24,
                "required_role": "compliance_officer",
                "transitions": [{"target": "Senior Review", "condition": {}}],
            },
            {
                "name": "Senior Review",
                "stage_type": "review",
                "order": 4,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "senior_reviewer",
                "transitions": [{"target": "Executive Sign-Off", "condition": {}}],
            },
            {
                "name": "Executive Sign-Off",
                "stage_type": "approval",
                "order": 5,
                "on_entry": ["require_approval"],
                "sla_hours": 72,
                "required_role": "executive",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 6,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "mandatory_compliance",
                "description": "High-risk contracts require compliance officer review.",
                "conditions": {"==": [{"var": "risk.category"}, "high"]},
                "effect": "require_compliance",
                "priority": 100,
            },
        ],
    },
    "low_risk": {
        "name": "Low Risk Express Review",
        "description": "Expedited review for low-risk contracts with minimal friction.",
        "category": CATEGORY_REVIEW,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Quick AI Scan", "condition": {}}],
            },
            {
                "name": "Quick AI Scan",
                "stage_type": "ai_analysis",
                "order": 2,
                "on_entry": ["auto_proceed"],
                "transitions": [
                    {"target": "Express Approval", "condition": {"<": [{"var": "ai.findings_count"}, 5]}},
                    {"target": "Standard Review", "condition": {">=": [{"var": "ai.findings_count"}, 5]}},
                ],
            },
            {
                "name": "Express Approval",
                "stage_type": "approval",
                "order": 3,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Standard Review",
                "stage_type": "review",
                "order": 4,
                "on_entry": ["require_review"],
                "sla_hours": 24,
                "required_role": "contract_reviewer",
                "transitions": [{"target": "Approval", "condition": {}}],
            },
            {
                "name": "Approval",
                "stage_type": "approval",
                "order": 5,
                "on_entry": ["require_approval"],
                "sla_hours": 12,
                "required_role": "contract_manager",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 6,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "express_route",
                "description": "Low-risk contracts with few AI findings take the express path.",
                "conditions": {"and": [
                    {"<=": [{"var": "risk.score"}, 30]},
                    {"<": [{"var": "ai.findings_count"}, 5]},
                ]},
                "effect": "express_approval",
                "priority": 100,
            },
        ],
    },

    # ── Compliance / Privacy Category ─────────────────────────────
    "privacy_dpa": {
        "name": "Privacy & DPA Review",
        "description": "Data Privacy Agreement workflow with GDPR/CCPA compliance checks.",
        "category": CATEGORY_COMPLIANCE,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "Privacy Compliance Check", "condition": {}}],
            },
            {
                "name": "Privacy Compliance Check",
                "stage_type": "compliance_check",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 24,
                "required_role": "privacy_officer",
                "transitions": [
                    {"target": "DPA Review", "condition": {"==": [{"var": "contract.has_data_privacy"}, True]}},
                    {"target": "Standard Approval", "condition": {"!=": [{"var": "contract.has_data_privacy"}, True]}},
                ],
            },
            {
                "name": "DPA Review",
                "stage_type": "review",
                "order": 3,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "data_protection_officer",
                "transitions": [{"target": "Privacy Approval", "condition": {}}],
            },
            {
                "name": "Privacy Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 48,
                "required_role": "privacy_director",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Standard Approval",
                "stage_type": "approval",
                "order": 5,
                "on_entry": ["require_approval"],
                "sla_hours": 24,
                "required_role": "contract_manager",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 6,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "dpa_required",
                "description": "Contracts with data privacy clauses require DPA review.",
                "conditions": {"==": [{"var": "contract.has_data_privacy"}, True]},
                "effect": "require_dpa",
                "priority": 100,
            },
        ],
    },

    # ── Legal Specialty Category ──────────────────────────────────
    "software_license": {
        "name": "Software License Review",
        "description": "Software license agreement workflow with SaaS terms and IP protection review.",
        "category": CATEGORY_LEGAL,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "License Terms Review", "condition": {}}],
            },
            {
                "name": "License Terms Review",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "it_legal_counsel",
                "transitions": [
                    {"target": "IP Protection Review", "condition": {"==": [{"var": "contract.has_ip_clauses"}, True]}},
                    {"target": "Tech Approval", "condition": {"!=": [{"var": "contract.has_ip_clauses"}, True]}},
                ],
            },
            {
                "name": "IP Protection Review",
                "stage_type": "review",
                "order": 3,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "ip_attorney",
                "transitions": [{"target": "Tech Approval", "condition": {}}],
            },
            {
                "name": "Tech Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 24,
                "required_role": "cto",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 5,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "ip_review_required",
                "description": "Contracts with IP clauses require IP attorney review.",
                "conditions": {"==": [{"var": "contract.has_ip_clauses"}, True]},
                "effect": "require_ip_review",
                "priority": 100,
            },
        ],
    },
    "nda": {
        "name": "NDA Review",
        "description": "Standard Non-Disclosure Agreement workflow with mutual/one-way routing.",
        "category": CATEGORY_LEGAL,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "NDA Review", "condition": {}}],
            },
            {
                "name": "NDA Review",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 24,
                "required_role": "contract_reviewer",
                "transitions": [
                    {"target": "Standard Approval", "condition": {"==": [{"var": "contract.nda_type"}, "standard"]}},
                    {"target": "Legal Review", "condition": {"in": [{"var": "contract.nda_type"}, ["mutual", "one-way"]]}},
                ],
            },
            {
                "name": "Legal Review",
                "stage_type": "review",
                "order": 3,
                "on_entry": ["require_review"],
                "sla_hours": 24,
                "required_role": "legal_counsel",
                "transitions": [{"target": "Standard Approval", "condition": {}}],
            },
            {
                "name": "Standard Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 12,
                "required_role": "contract_manager",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 5,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "nda_type_routing",
                "description": "Non-standard NDAs require legal counsel review.",
                "conditions": {"in": [{"var": "contract.nda_type"}, ["mutual", "one-way"]]},
                "effect": "require_legal_review",
                "priority": 100,
            },
        ],
    },
    "msa": {
        "name": "MSA Review",
        "description": "Master Services Agreement workflow with multi-stage approval for complex terms.",
        "category": CATEGORY_LEGAL,
        "is_built_in": True,
        "stages_definition": [
            {
                "name": "Document Ingestion",
                "stage_type": "start",
                "order": 1,
                "on_entry": ["auto_proceed"],
                "transitions": [{"target": "MSA Terms Review", "condition": {}}],
            },
            {
                "name": "MSA Terms Review",
                "stage_type": "review",
                "order": 2,
                "on_entry": ["require_review"],
                "sla_hours": 72,
                "required_role": "senior_legal_counsel",
                "transitions": [
                    {"target": "Finance Review", "condition": {">": [{"var": "contract.value"}, 250000]}},
                    {"target": "Standard Approval", "condition": {"<=": [{"var": "contract.value"}, 250000]}},
                ],
            },
            {
                "name": "Finance Review",
                "stage_type": "review",
                "order": 3,
                "on_entry": ["require_review"],
                "sla_hours": 48,
                "required_role": "finance_manager",
                "transitions": [{"target": "Executive Approval", "condition": {}}],
            },
            {
                "name": "Executive Approval",
                "stage_type": "approval",
                "order": 4,
                "on_entry": ["require_approval"],
                "sla_hours": 72,
                "required_role": "executive",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Standard Approval",
                "stage_type": "approval",
                "order": 5,
                "on_entry": ["require_approval"],
                "sla_hours": 48,
                "required_role": "legal_director",
                "transitions": [{"target": "Completed", "condition": {}}],
            },
            {
                "name": "Completed",
                "stage_type": "terminal",
                "order": 6,
                "on_entry": ["auto_proceed"],
                "transitions": [],
            },
        ],
        "rules_definition": [
            {
                "rule_name": "msa_high_value",
                "description": "MSAs over $250K require finance review and executive approval.",
                "conditions": {">": [{"var": "contract.value"}, 250000]},
                "effect": "require_finance_review",
                "priority": 100,
            },
        ],
    },
}


# ── Functions ──────────────────────────────────────────────────────


def get_built_in_pack(pack_name: str) -> Optional[dict[str, Any]]:
    """Retrieve a specific built-in pack definition by name.

    Args:
        pack_name: The key name of the built-in pack (e.g., 'standard_review').

    Returns:
        The pack definition dict, or None if not found.
    """
    pack = BUILT_IN_PACKS.get(pack_name)
    if pack is None:
        logger.warning("Built-in pack '%s' not found.", pack_name)
        return None
    return dict(pack)  # Return a copy to prevent mutation


def list_built_in_packs() -> dict[str, dict[str, Any]]:
    """List all built-in pack definitions.

    Returns:
        A shallow copy of all built-in packs.
    """
    return {k: dict(v) for k, v in BUILT_IN_PACKS.items()}


async def seed_built_in_packs(session: Any, tenant_id: str) -> list[str]:
    """Seed all built-in packs for a tenant.

    Creates a WorkflowPack record for each built-in pack definition
    and a corresponding WorkflowVersion record.

    Args:
        session: Database session.
        tenant_id: The tenant to seed packs for.

    Returns:
        List of pack_ids that were created.
    """
    from app.domains.workflow_packs.models import WorkflowPack, WorkflowVersion

    created_pack_ids: list[str] = []
    now = datetime.now(timezone.utc)

    for pack_key, pack_def in BUILT_IN_PACKS.items():
        pack_id = f"builtin_{pack_key}"

        # Check if already seeded
        existing = await session.get(WorkflowPack, pack_id)
        if existing:
            logger.debug("Built-in pack '%s' already seeded for tenant %s", pack_key, tenant_id)
            created_pack_ids.append(pack_id)
            continue

        pack = WorkflowPack(
            pack_id=pack_id,
            tenant_id=tenant_id,
            name=pack_def["name"],
            description=pack_def.get("description", ""),
            category=pack_def.get("category", "custom"),
            is_built_in=True,
            parent_pack_id=None,
            stages=pack_def.get("stages_definition", []),
            rules=pack_def.get("rules_definition", []),
            is_active=True,
            version=1,
            created_by="system",
            created_at=now,
            updated_at=now,
        )
        session.add(pack)
        await session.flush()

        # Create initial version
        version = WorkflowVersion(
            pack_id=pack_id,
            tenant_id=tenant_id,
            version_number=1,
            status="published",
            stages_definition=pack_def.get("stages_definition", []),
            rules_definition=pack_def.get("rules_definition", []),
            snapshot={
                "stages": pack_def.get("stages_definition", []),
                "rules": pack_def.get("rules_definition", []),
            },
            change_summary=f"Initial seed of built-in pack '{pack_def['name']}'.",
            created_by="system",
            published_by="system",
            published_at=now,
            created_at=now,
        )
        session.add(version)
        created_pack_ids.append(pack_id)
        logger.info("Seeded built-in pack '%s' (%s) for tenant %s", pack_key, pack_id, tenant_id)

    await session.flush()
    return created_pack_ids
