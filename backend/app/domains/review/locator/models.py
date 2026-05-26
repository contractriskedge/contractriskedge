"""Locator data models — structural anchors for redline placement.

Replaces the old chunk-based fuzzy-locate system with a structured
locator that understands document hierarchy, insertion semantics,
legal domain topology, and confidence scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LegalDomain(str, Enum):
    RENEWAL = "renewal"
    PRICING = "pricing"
    PRIVACY = "privacy"
    LIABILITY = "liability"
    INDEMNITY = "indemnity"
    IP = "ip"
    TERMINATION = "termination"
    GOVERNING_LAW = "governing_law"
    CONFIDENTIALITY = "confidentiality"
    WARRANTY = "warranty"
    INSURANCE = "insurance"
    NON_COMPETE = "non_compete"
    ASSIGNMENT = "assignment"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    DEFINITIONS = "definitions"
    SCOPE = "scope"
    PAYMENT = "payment"
    DATA_PROTECTION = "data_protection"
    NOTICE = "notice"
    GENERAL = "general"


class RiskType(str, Enum):
    FINANCIAL = "financial"
    PRIVACY = "privacy"
    OPERATIONAL = "operational"
    LITIGATION = "litigation"
    COMPLIANCE = "compliance"
    VENDOR_LOCKIN = "vendor_lockin"
    IP_LOSS = "ip_loss"
    REPUTATIONAL = "reputational"
    SECURITY = "security"


class RecommendationType(str, Enum):
    MODIFY = "modify"
    INSERT = "insert"
    DELETE = "delete"
    WARNING = "warning"
    FALLBACK = "fallback"


class ClauseOperationType(str, Enum):
    """Semantic operation type for UI badge display."""
    INSERT = "insert"
    MODIFY = "modify"
    REPLACE = "replace"
    DELETE = "delete"
    NARROW_LIABILITY = "narrow_liability"
    ADD_PROTECTION = "add_protection"
    WARNING = "warning"


# ── Risk relationship graph ────────────────────────────────────
# Maps clause types to related risks and business impacts

CLAUSE_RISK_RELATIONSHIPS: dict[str, dict] = {
    "indemnification": {
        "related_risks": ["litigation", "ip_loss", "liability"],
        "impact_accepted": "Reduces third-party claim exposure. Provides defense cost coverage.",
        "impact_rejected": "Customer bears full cost of IP infringement defense and liability.",
        "rationale_bullets": [
            "Allocates risk of third-party claims to responsible party",
            "Provides legal defense cost coverage",
            "Reduces litigation exposure",
        ],
    },
    "limitation_of_liability": {
        "related_risks": ["financial", "litigation"],
        "impact_accepted": "Caps maximum financial exposure. Excludes consequential damages.",
        "impact_rejected": "Unlimited liability exposure remains. Potential for catastrophic damages.",
        "rationale_bullets": [
            "Caps maximum financial exposure",
            "Excludes consequential damages",
            "Sets predictable risk boundary",
        ],
    },
    "confidentiality": {
        "related_risks": ["ip_loss", "reputational", "security"],
        "impact_accepted": "Protects proprietary information. Limits disclosure risk.",
        "impact_rejected": "Confidential information may be exposed without remedy.",
        "rationale_bullets": [
            "Protects proprietary business information",
            "Defines permitted disclosure scope",
            "Sets handling and security requirements",
        ],
    },
    "payment": {
        "related_risks": ["financial", "vendor_lockin"],
        "impact_accepted": "Predictable fee structure. Protection against unilateral increases.",
        "impact_rejected": "Provider may raise fees without limit. Budget unpredictability.",
        "rationale_bullets": [
            "Caps annual fee increases",
            "Prevents unilateral pricing changes",
            "Provides termination right if fees exceed threshold",
        ],
    },
    "fee_increase": {
        "related_risks": ["financial", "vendor_lockin"],
        "impact_accepted": "Limits annual cost growth. Provides budget predictability.",
        "impact_rejected": "Uncontrolled fee escalation. Potential vendor lock-in.",
        "rationale_bullets": [
            "Caps annual fee increase percentage",
            "Requires advance notice of pricing changes",
            "Gives termination right if increase exceeds cap",
        ],
    },
    "termination": {
        "related_risks": ["operational", "vendor_lockin"],
        "impact_accepted": "Clear exit rights. Data return and transition assistance.",
        "impact_rejected": "Difficult to terminate. Risk of automatic lock-in.",
        "rationale_bullets": [
            "Defines clear termination rights",
            "Sets notice periods for convenience termination",
            "Requires data return and transition assistance",
        ],
    },
    "renewal": {
        "related_risks": ["vendor_lockin", "operational"],
        "impact_accepted": "Prevents automatic silent renewal. Requires affirmative consent.",
        "impact_rejected": "Contract may auto-renew without notice. Unwanted commitment.",
        "rationale_bullets": [
            "Prevents automatic silent renewal",
            "Requires advance notice before renewal",
            "Gives opportunity to renegotiate terms",
        ],
    },
    "data_privacy": {
        "related_risks": ["privacy", "compliance", "security"],
        "impact_accepted": "GDPR/compliance aligned. Data processing restrictions defined.",
        "impact_rejected": "Personal data may be processed without adequate protections.",
        "rationale_bullets": [
            "Defines data processing restrictions",
            "Sets data protection standards",
            "Addresses regulatory compliance requirements",
        ],
    },
    "ip": {
        "related_risks": ["ip_loss", "vendor_lockin"],
        "impact_accepted": "Clear IP ownership. License rights defined.",
        "impact_rejected": "IP ownership may default to provider. Customer loses rights.",
        "rationale_bullets": [
            "Defines intellectual property ownership",
            "Grants necessary license rights",
            "Protects pre-existing IP",
        ],
    },
    "governing_law": {
        "related_risks": ["litigation", "compliance"],
        "impact_accepted": "Predictable legal framework. Known jurisdiction.",
        "impact_rejected": "Disputes may be litigated in unfavorable jurisdiction.",
        "rationale_bullets": [
            "Chooses favorable governing law",
            "Sets predictable legal framework",
            "Defines dispute jurisdiction",
        ],
    },
    "force_majeure": {
        "related_risks": ["operational", "financial"],
        "impact_accepted": "Excused performance during unforeseen events. Mutual protection.",
        "impact_rejected": "Party may be liable for delays caused by events beyond control.",
        "rationale_bullets": [
            "Excuses performance during unforeseen events",
            "Sets notice requirements for force majeure events",
            "Provides termination right if event persists",
        ],
    },
    "insurance": {
        "related_risks": ["financial", "litigation"],
        "impact_accepted": "Adequate coverage for potential claims. Financial protection.",
        "impact_rejected": "Provider may lack sufficient insurance to cover claims.",
        "rationale_bullets": [
            "Requires adequate insurance coverage",
            "Sets minimum coverage limits",
            "Requires naming as additional insured",
        ],
    },
    "warranty": {
        "related_risks": ["litigation", "operational"],
        "impact_accepted": "Service quality guarantees. Remedies for non-conformance.",
        "impact_rejected": "No guarantee of service quality. Limited remedies available.",
        "rationale_bullets": [
            "Sets service quality guarantees",
            "Defines remedies for non-conformance",
            "Disclaims implied warranties appropriately",
        ],
    },
    "dispute_resolution": {
        "related_risks": ["litigation", "financial"],
        "impact_accepted": "Efficient dispute resolution. Avoids costly litigation.",
        "impact_rejected": "Disputes may proceed to costly and public court litigation.",
        "rationale_bullets": [
            "Sets binding arbitration or mediation process",
            "Avoids costly court litigation",
            "Defines dispute escalation timeline",
        ],
    },
    "non_compete": {
        "related_risks": ["operational", "ip_loss"],
        "impact_accepted": "Protects business interests. Prevents competitive harm.",
        "impact_rejected": "Counterparty may compete directly or solicit employees.",
        "rationale_bullets": [
            "Restricts competitive activity during and after term",
            "Prevents solicitation of employees",
            "Protects business relationships",
        ],
    },
    "assignment": {
        "related_risks": ["vendor_lockin", "operational"],
        "impact_accepted": "Controls transfer of agreement. Prevents unwanted assignment.",
        "impact_rejected": "Agreement may be assigned to competitor without consent.",
        "rationale_bullets": [
            "Requires consent for assignment",
            "Prevents assignment to competitors",
            "Permits assignment in mergers and acquisitions",
        ],
    },
    "audit": {
        "related_risks": ["compliance", "operational"],
        "impact_accepted": "Verifies contractual compliance. Ensures data integrity.",
        "impact_rejected": "No right to verify compliance. Potential hidden violations.",
        "rationale_bullets": [
            "Provides right to audit compliance",
            "Sets audit frequency and scope",
            "Requires remediation of findings",
        ],
    },
    "sla": {
        "related_risks": ["operational", "financial"],
        "impact_accepted": "Defined performance standards. Service credits for failures.",
        "impact_rejected": "No guaranteed service levels. Limited remedies for downtime.",
        "rationale_bullets": [
            "Sets minimum service performance standards",
            "Provides service credits for failures",
            "Defines escalation and remediation process",
        ],
    },
    "support": {
        "related_risks": ["operational"],
        "impact_accepted": "Defined support hours and response times. Escalation path.",
        "impact_rejected": "Support may be limited or undefined. Slow issue resolution.",
        "rationale_bullets": [
            "Defines support hours and coverage",
            "Sets response time targets by severity",
            "Provides escalation path for critical issues",
        ],
    },
}

# Domain aliases for CLAUSE_RISK_RELATIONSHIPS lookup
# Maps normalized clause types to their risk data keys
CLAUSE_RISK_ALIASES: dict[str, str] = {
    "indemnity": "indemnification",
    "liability": "limitation_of_liability",
    "non_disclosure": "confidentiality",
    "nda": "confidentiality",
    "fees": "payment",
    "pricing": "payment",
    "compensation": "payment",
    "fee_increase": "fee_increase",
    "refund": "payment",
    "intellectual_property": "ip",
    "proprietary_rights": "ip",
    "ip_ownership": "ip",
    "data_protection": "data_privacy",
    "privacy": "data_privacy",
    "gdpr": "data_privacy",
    "personal_data": "data_privacy",
    "data_security": "security",
    "information_security": "security",
    "breach_notification": "security",
    "cancellation": "termination",
    "representations": "warranty",
    "representations_and_warranties": "warranty",
    "arbitration": "dispute_resolution",
    "mediation": "dispute_resolution",
    "disputes": "dispute_resolution",
    "choice_of_law": "governing_law",
    "applicable_law": "governing_law",
    "jurisdiction": "governing_law",
    "non_solicit": "non_compete",
    "exclusivity": "non_compete",
    "delegation": "assignment",
    "auto_renewal": "renewal",
    "term": "termination",
    "duration": "termination",
    "sla": "sla",
    "service_levels": "sla",
    "technical_support": "support",
    "maintenance": "support",
    "compliance": "compliance",
    "audit": "audit",
    "audit_rights": "audit",
    "usage_restrictions": "usage_restrictions",
    "acceptable_use": "usage_restrictions",
    "scope_of_work": "scope",
    "services": "scope",
    "entire_agreement": "entire_agreement",
    "integration": "entire_agreement",
    "merger": "entire_agreement",
    "waiver": "waiver",
    "severability": "severability",
    "notices": "notice",
    "definitions": "definitions",
    "interpretation": "definitions",
    "general": "general_provisions",
    "miscellaneous": "general_provisions",
    "boilerplate": "general_provisions",
}


class RedlineAction(str, Enum):
    MODIFY_EXISTING = "modify_existing"
    INSERT_NEW = "insert_new"
    DELETE = "delete"
    WARNING_ONLY = "warning_only"


class AnchorType(str, Enum):
    EXACT_TEXT_SPAN = "exact_text_span"
    FUZZY_TEXT_SPAN = "fuzzy_text_span"
    SEMANTIC_CLAUSE_MATCH = "semantic_clause_match"
    STRUCTURAL_INSERTION = "structural_insertion"
    UNRESOLVED = "unresolved"


class InsertPosition(str, Enum):
    AFTER_SECTION = "after_section"
    BEFORE_SECTION = "before_section"
    WITHIN_SECTION = "within_section"
    APPEND_DOCUMENT = "append_document"
    PRECEDE_DOCUMENT = "precede_document"


class LocatorStatus(str, Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


LEGAL_TOPOLOGY: dict[str, dict] = {
    "definitions": {
        "label": "Definitions",
        "expected_position": "early",
        "preferred_neighbors": ["scope", "payment"],
        "standalone_preferred": True,
        "business_intents": ["clarify_terms", "set_scope"],
        "typical_sections": ["Definitions", "Interpretation", "Certain Definitions"],
    },
    "scope": {
        "label": "Scope of Services",
        "expected_position": "early",
        "preferred_neighbors": ["definitions", "payment", "sla"],
        "standalone_preferred": True,
        "business_intents": ["define_services", "set_deliverables", "set_boundaries"],
        "typical_sections": ["Services", "Scope of Work", "Statement of Work", "Services Provided"],
    },
    "sla": {
        "label": "Service Levels",
        "expected_position": "early_middle",
        "preferred_neighbors": ["scope", "payment", "support"],
        "standalone_preferred": True,
        "business_intents": ["define_performance", "set_uptime", "set_remedies"],
        "typical_sections": ["Service Levels", "SLA", "Performance", "Availability"],
    },
    "support": {
        "label": "Support",
        "expected_position": "early_middle",
        "preferred_neighbors": ["sla", "payment", "scope"],
        "standalone_preferred": True,
        "business_intents": ["define_support_hours", "set_response_times", "set_escalation"],
        "typical_sections": ["Support", "Technical Support", "Maintenance"],
    },
    "payment": {
        "label": "Payment & Fees",
        "expected_position": "early_middle",
        "preferred_neighbors": ["scope", "sla", "term", "renewal"],
        "standalone_preferred": False,
        "business_intents": ["set_pricing", "define_fees", "cap_increases", "set_payment_terms"],
        "typical_sections": ["Fees", "Payment", "Compensation", "Pricing", "Subscription Fees"],
    },
    "renewal": {
        "label": "Term & Renewal",
        "expected_position": "early_middle",
        "preferred_neighbors": ["payment", "term", "termination", "notice"],
        "standalone_preferred": True,
        "business_intents": ["prevent_silent_renewal", "set_renewal_terms", "require_notice"],
        "typical_sections": ["Renewal", "Auto-Renewal", "Term and Renewal"],
    },
    "term": {
        "label": "Term",
        "expected_position": "early_middle",
        "preferred_neighbors": ["payment", "renewal", "termination"],
        "standalone_preferred": True,
        "business_intents": ["set_duration", "set_effective_date", "define_commencement"],
        "typical_sections": ["Term", "Duration", "Effective Date"],
    },
    "audit": {
        "label": "Audit Rights",
        "expected_position": "middle",
        "preferred_neighbors": ["payment", "usage_restrictions", "compliance"],
        "standalone_preferred": False,
        "business_intents": ["verify_compliance", "audit_usage", "inspect_records"],
        "typical_sections": ["Audit", "Audit Rights", "Inspection", "Records"],
    },
    "usage_restrictions": {
        "label": "Usage Restrictions",
        "expected_position": "middle",
        "preferred_neighbors": ["scope", "audit", "compliance"],
        "standalone_preferred": False,
        "business_intents": ["restrict_use", "prevent_abuse", "limit_access"],
        "typical_sections": ["Use Restrictions", "Acceptable Use", "Prohibited Uses"],
    },
    "confidentiality": {
        "label": "Confidentiality",
        "expected_position": "middle",
        "preferred_neighbors": ["data_privacy", "security", "ip"],
        "standalone_preferred": True,
        "business_intents": ["protect_confidential_info", "define_nda", "set_handling"],
        "typical_sections": ["Confidentiality", "Non-Disclosure", "Confidential Information"],
    },
    "data_privacy": {
        "label": "Data Privacy",
        "expected_position": "middle",
        "preferred_neighbors": ["confidentiality", "security", "compliance"],
        "standalone_preferred": True,
        "business_intents": ["protect_personal_data", "comply_gdpr", "set_data_processing"],
        "typical_sections": ["Data Protection", "Privacy", "GDPR", "Personal Data", "Data Privacy"],
    },
    "security": {
        "label": "Security",
        "expected_position": "middle",
        "preferred_neighbors": ["data_privacy", "confidentiality", "compliance"],
        "standalone_preferred": True,
        "business_intents": ["set_security_standards", "define_breach_notification", "protect_systems"],
        "typical_sections": ["Security", "Information Security", "Data Security", "Breach Notification"],
    },
    "ip": {
        "label": "Intellectual Property",
        "expected_position": "middle",
        "preferred_neighbors": ["confidentiality", "usage_restrictions", "warranty"],
        "standalone_preferred": True,
        "business_intents": ["define_ownership", "grant_licenses", "protect_ip"],
        "typical_sections": ["Intellectual Property", "Proprietary Rights", "IP Ownership", "License"],
    },
    "warranty": {
        "label": "Warranties & Representations",
        "expected_position": "middle",
        "preferred_neighbors": ["ip", "compliance", "liability"],
        "standalone_preferred": True,
        "business_intents": ["set_warranties", "disclaim_liability", "define_representations"],
        "typical_sections": ["Representations", "Warranties", "Representations and Warranties"],
    },
    "compliance": {
        "label": "Compliance",
        "expected_position": "middle",
        "preferred_neighbors": ["warranty", "data_privacy", "security", "audit"],
        "standalone_preferred": True,
        "business_intents": ["ensure_regulatory_compliance", "set_standards", "define_certifications"],
        "typical_sections": ["Compliance", "Regulatory Compliance", "Legal Compliance"],
    },
    "insurance": {
        "label": "Insurance",
        "expected_position": "middle_late",
        "preferred_neighbors": ["warranty", "indemnity", "liability"],
        "standalone_preferred": True,
        "business_intents": ["require_coverage", "set_limits", "define_types"],
        "typical_sections": ["Insurance"],
    },
    "indemnity": {
        "label": "Indemnification",
        "expected_position": "middle_late",
        # Indemnification belongs near: warranty → liability → indemnification → termination
        # Never after boilerplate/modification-of-terms clauses
        "preferred_neighbors": ["liability", "warranty", "insurance", "ip", "termination"],
        "standalone_preferred": True,
        "business_intents": ["allocate_risk", "define_indemnity", "set_defense"],
        "typical_sections": ["Indemnification", "Indemnity"],
        "never_after": ["amendment", "modification_of_terms", "entire_agreement",
                        "general_provisions", "severability", "waiver"],
    },
    "liability": {
        "label": "Limitation of Liability",
        "expected_position": "middle_late",
        # Limitation of Liability: typically after warranty, before indemnification
        "preferred_neighbors": ["warranty", "indemnity", "ip", "compliance"],
        "standalone_preferred": True,
        "business_intents": ["cap_liability", "exclude_damages", "limit_exposure"],
        "typical_sections": ["Limitation of Liability", "Cap on Liability", "Liability", "Disclaimer"],
        "never_after": ["amendment", "modification_of_terms", "entire_agreement",
                        "general_provisions", "severability", "waiver"],
    },
    "termination": {
        "label": "Termination",
        "expected_position": "late",
        "preferred_neighbors": ["liability", "renewal", "force_majeure", "dispute_resolution"],
        "standalone_preferred": True,
        "business_intents": ["define_termination_rights", "set_notice_periods", "handle_breach"],
        "typical_sections": ["Termination", "Cancellation", "Termination for Cause"],
    },
    "force_majeure": {
        "label": "Force Majeure",
        "expected_position": "late",
        "preferred_neighbors": ["termination", "dispute_resolution", "liability"],
        "standalone_preferred": True,
        "business_intents": ["excuse_performance", "handle_disasters", "allocate_risk"],
        "typical_sections": ["Force Majeure", "Act of God", "Unforeseen Events"],
    },
    "dispute_resolution": {
        "label": "Dispute Resolution",
        "expected_position": "late",
        "preferred_neighbors": ["termination", "force_majeure", "governing_law", "jurisdiction"],
        "standalone_preferred": True,
        "business_intents": ["set_arbitration", "define_mediation", "resolve_disputes"],
        "typical_sections": ["Dispute Resolution", "Arbitration", "Mediation", "Disputes"],
    },
    "jurisdiction": {
        "label": "Jurisdiction",
        "expected_position": "late",
        "preferred_neighbors": ["governing_law", "dispute_resolution", "notice"],
        "standalone_preferred": False,
        "business_intents": ["set_venue", "define_courts", "choose_forum"],
        "typical_sections": ["Jurisdiction", "Venue", "Forum", "Consent to Jurisdiction"],
    },
    "governing_law": {
        "label": "Governing Law",
        "expected_position": "late",
        "preferred_neighbors": ["dispute_resolution", "jurisdiction", "notice"],
        "standalone_preferred": True,
        "business_intents": ["choose_law", "set_governance", "define_interpretation"],
        "typical_sections": ["Governing Law", "Choice of Law", "Applicable Law"],
    },
    "non_compete": {
        "label": "Non-Compete",
        "expected_position": "middle_late",
        "preferred_neighbors": ["confidentiality", "termination", "ip"],
        "standalone_preferred": True,
        "business_intents": ["restrict_competition", "prevent_solicitation", "protect_business"],
        "typical_sections": ["Non-Compete", "Non-Solicit", "Exclusivity"],
    },
    "assignment": {
        "label": "Assignment",
        "expected_position": "late",
        "preferred_neighbors": ["termination", "governing_law", "notice"],
        "standalone_preferred": True,
        "business_intents": ["restrict_transfer", "define_assignment", "protect_relationship"],
        "typical_sections": ["Assignment", "Delegation", "Assignment and Delegation"],
    },
    "notice": {
        "label": "Notices",
        "expected_position": "late",
        "preferred_neighbors": ["governing_law", "termination", "general_provisions"],
        "standalone_preferred": True,
        "business_intents": ["set_notice_method", "define_delivery", "require_written_notice"],
        "typical_sections": ["Notice", "Notices", "Notices and Communications"],
    },
    "general_provisions": {
        "label": "General Provisions",
        "expected_position": "end",
        "preferred_neighbors": ["governing_law", "notice", "waiver"],
        "standalone_preferred": True,
        "business_intents": ["consolidate_boilerplate", "set_miscellaneous", "define_interpretation"],
        "typical_sections": ["General", "Miscellaneous", "General Provisions", "Boilerplate"],
    },
    "waiver": {
        "label": "Waiver",
        "expected_position": "end",
        "preferred_neighbors": ["general_provisions", "severability"],
        "standalone_preferred": False,
        "business_intents": ["define_waiver", "set_non_waiver"],
        "typical_sections": ["Waiver", "No Waiver", "Waiver and Amendment"],
    },
    "severability": {
        "label": "Severability",
        "expected_position": "end",
        "preferred_neighbors": ["general_provisions", "waiver", "entire_agreement"],
        "standalone_preferred": False,
        "business_intents": ["save_invalid_terms", "preserve_balance"],
        "typical_sections": ["Severability", "Invalidity", "Unenforceability"],
    },
    "entire_agreement": {
        "label": "Entire Agreement",
        "expected_position": "end",
        "preferred_neighbors": ["general_provisions", "severability"],
        "standalone_preferred": True,
        "business_intents": ["supersede_prior", "consolidate_terms", "define_complete_agreement"],
        "typical_sections": ["Entire Agreement", "Integration", "Merger", "Complete Agreement"],
    },
}

CLAUSE_TYPE_TO_DOMAIN: dict[str, str] = {
    "indemnification": "indemnity", "indemnify": "indemnity", "indemnity": "indemnity",
    "limitation_of_liability": "liability", "cap_on_liability": "liability", "liability": "liability",
    "confidentiality": "confidentiality", "non_disclosure": "confidentiality", "nda": "confidentiality",
    "confidential_information": "confidentiality",
    "governing_law": "governing_law", "choice_of_law": "governing_law", "applicable_law": "governing_law",
    "termination": "termination", "cancellation": "termination", "termination_rights": "termination",
    "warranty": "warranty", "warranties": "warranty", "representations": "warranty",
    "representations_and_warranties": "warranty",
    "payment": "payment", "fees": "payment", "compensation": "payment", "pricing": "payment",
    "fee_increase": "payment", "fee_cap": "payment", "refund": "payment", "subscription_fees": "payment",
    # Intellectual Property — feedback/ownership belong here, NOT in data_privacy
    "ip": "ip", "intellectual_property": "ip", "ip_ownership": "ip", "proprietary_rights": "ip",
    "license": "ip", "licensing": "ip", "ip_rights": "ip", "ip_transfer": "ip",
    "feedback": "ip", "feedback_rights": "ip", "feedback_ownership": "ip",
    "ownership_rights": "ip", "derivative_works": "ip", "work_product": "ip",
    # Data Privacy — strictly personal data, GDPR, processing; NOT IP/feedback
    "data_privacy": "data_privacy", "data_protection": "data_privacy", "privacy": "data_privacy",
    "gdpr": "data_privacy", "personal_data": "data_privacy", "data_processing": "data_privacy",
    "security": "security", "data_security": "security", "information_security": "security",
    "breach_notification": "security",
    "force_majeure": "force_majeure", "insurance": "insurance",
    "non_compete": "non_compete", "non_solicit": "non_compete", "exclusivity": "non_compete",
    "non_solicitation": "non_compete",
    "assignment": "assignment", "delegation": "assignment",
    "dispute_resolution": "dispute_resolution", "arbitration": "dispute_resolution",
    "mediation": "dispute_resolution", "disputes": "dispute_resolution",
    "jurisdiction": "jurisdiction", "venue": "jurisdiction",
    "entire_agreement": "entire_agreement", "integration": "entire_agreement", "merger": "entire_agreement",
    "amendment": "general_provisions", "modification": "general_provisions",
    "waiver": "waiver", "severability": "severability",
    "notice": "notice", "notices": "notice",
    "definitions": "definitions", "interpretation": "definitions",
    "scope": "scope", "scope_of_work": "scope", "services": "scope",
    "sla": "sla", "service_levels": "sla", "service_level_agreement": "sla", "performance": "sla",
    "support": "support", "technical_support": "support", "maintenance": "support",
    "term": "term", "duration": "term", "effective_date": "term",
    "renewal": "renewal", "auto_renewal": "renewal",
    "compliance": "compliance", "regulatory_compliance": "compliance",
    "audit": "audit", "audit_rights": "audit",
    "usage_restrictions": "usage_restrictions", "use_restrictions": "usage_restrictions",
    "acceptable_use": "usage_restrictions",
    "general": "general_provisions", "miscellaneous": "general_provisions", "boilerplate": "general_provisions",
}

CLAUSE_TYPE_TO_RISK: dict[str, str] = {
    "indemnification": "litigation", "limitation_of_liability": "financial",
    "confidentiality": "ip_loss", "governing_law": "litigation",
    "termination": "operational", "warranty": "litigation",
    "payment": "financial", "fees": "financial", "fee_increase": "financial",
    "refund": "financial", "pricing": "financial",
    "ip": "ip_loss", "intellectual_property": "ip_loss", "license": "ip_loss",
    "data_privacy": "privacy", "data_protection": "privacy", "privacy": "privacy",
    "gdpr": "compliance",
    "security": "security", "data_security": "security", "breach_notification": "security",
    "force_majeure": "operational", "insurance": "financial",
    "non_compete": "operational", "assignment": "vendor_lockin",
    "dispute_resolution": "litigation", "arbitration": "litigation", "jurisdiction": "litigation",
    "notice": "operational",
    "renewal": "vendor_lockin", "auto_renewal": "vendor_lockin",
    "term": "vendor_lockin", "duration": "vendor_lockin",
    "sla": "operational", "service_levels": "operational", "support": "operational",
    "compliance": "compliance", "audit": "operational", "usage_restrictions": "operational",
    "definitions": "operational", "scope": "vendor_lockin", "services": "vendor_lockin",
    "entire_agreement": "litigation", "waiver": "litigation", "severability": "litigation",
    "general": "operational",
}

CLAUSE_INTENT: dict[str, str] = {
    "indemnification": "allocate_risk_of_third_party_claims",
    "limitation_of_liability": "cap_financial_exposure",
    "confidentiality": "protect_confidential_information",
    "governing_law": "choose_applicable_law",
    "termination": "define_exit_rights",
    "warranty": "set_quality_guarantees",
    "payment": "define_fee_structure",
    "fees": "define_fee_structure",
    "fee_increase": "prevent_uncontrolled_cost_escalation",
    "refund": "set_refund_obligations",
    "pricing": "define_fee_structure",
    "ip": "define_intellectual_property_ownership",
    "intellectual_property": "define_intellectual_property_ownership",
    "license": "grant_usage_rights",
    "data_privacy": "protect_personal_data",
    "data_protection": "protect_personal_data",
    "privacy": "protect_personal_data",
    "gdpr": "ensure_gdpr_compliance",
    "security": "protect_systems_and_data",
    "data_security": "protect_systems_and_data",
    "breach_notification": "ensure_timely_breach_reporting",
    "force_majeure": "excuse_performance_in_disasters",
    "insurance": "require_adequate_coverage",
    "non_compete": "restrict_competitive_activity",
    "assignment": "control_transfer_of_agreement",
    "dispute_resolution": "set_dispute_mechanism",
    "arbitration": "set_arbitration_process",
    "jurisdiction": "choose_legal_venue",
    "notice": "define_communication_method",
    "renewal": "prevent_automatic_silent_renewal",
    "auto_renewal": "prevent_automatic_silent_renewal",
    "term": "set_agreement_duration",
    "duration": "set_agreement_duration",
    "sla": "define_service_performance_standards",
    "service_levels": "define_service_performance_standards",
    "support": "define_support_obligations",
    "compliance": "ensure_regulatory_compliance",
    "audit": "verify_contractual_compliance",
    "usage_restrictions": "prevent_unauthorized_use",
    "scope": "define_services_provided",
    "services": "define_services_provided",
    "definitions": "clarify_contract_terminology",
    "entire_agreement": "consolidate_all_terms",
    "waiver": "define_non_waiver_principle",
    "severability": "preserve_balance_if_part_invalid",
    "general": "cover_miscellaneous_provisions",
}


@dataclass
class SectionNode:
    section_id: str
    section_number: str
    title: str
    level: int
    start_offset: int
    end_offset: int
    page_numbers: list[int] = field(default_factory=list)
    chunk_ids: list[str] = field(default_factory=list)
    children: list[SectionNode] = field(default_factory=list)
    parent: Optional[SectionNode] = None
    legal_domain: Optional[str] = None


@dataclass
class SectionHierarchy:
    sections: list[SectionNode] = field(default_factory=list)
    flat_index: dict[str, SectionNode] = field(default_factory=dict)

    def get(self, section_id: str) -> Optional[SectionNode]:
        return self.flat_index.get(section_id)

    def get_by_major(self, major: int) -> list[SectionNode]:
        return [s for s in self.flat_index.values()
                if s.section_number.split(".")[0] == str(major)]

    def nearest_preceding(self, section_id: str) -> Optional[SectionNode]:
        ordered = sorted(self.flat_index.values(), key=lambda s: _section_sort_key(s.section_number))
        target_key = _section_sort_key(section_id)
        for i, s in enumerate(ordered):
            if _section_sort_key(s.section_number) >= target_key:
                return ordered[i - 1] if i > 0 else None
        return ordered[-1] if ordered else None

    def nearest_following(self, section_id: str) -> Optional[SectionNode]:
        ordered = sorted(self.flat_index.values(), key=lambda s: _section_sort_key(s.section_number))
        target_key = _section_sort_key(section_id)
        for i, s in enumerate(ordered):
            if _section_sort_key(s.section_number) > target_key:
                return s
        return None

    def max_major(self) -> int:
        if not self.flat_index:
            return 0
        return max(int(s.section_number.split(".")[0]) for s in self.flat_index.values()
                   if s.section_number.split(".")[0].isdigit())

    def find_by_domain(self, domain: str) -> list[SectionNode]:
        return [s for s in self.flat_index.values() if s.legal_domain == domain]


def _section_sort_key(section_id: str) -> tuple:
    parts = section_id.replace("§", "").split(".")
    key = []
    for p in parts:
        try:
            key.append((0, int(p)))
        except ValueError:
            key.append((1, p))
    return tuple(key)


@dataclass
class LocatorResult:
    status: LocatorStatus
    anchor_type: AnchorType
    confidence: float
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    insert_position: Optional[InsertPosition] = None
    matched_text: Optional[str] = None
    chunk_id: Optional[str] = None
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    display_numbering: bool = True
    legal_domain: Optional[str] = None
    risk_type: Optional[str] = None
    recommendation_type: Optional[str] = None
    clause_operation_type: Optional[str] = None
    rationale_bullets: list[str] = field(default_factory=list)
    related_risks: list[str] = field(default_factory=list)
    impact_accepted: Optional[str] = None
    impact_rejected: Optional[str] = None
    summary_title: Optional[str] = None     # Compact one-line title for card header
    summary_impact: Optional[str] = None    # One-line impact for card header
    action_label: Optional[str] = None      # Display label for operation badge
    group_key: Optional[str] = None         # For grouping by risk type (e.g. "financial", "litigation")

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "anchor_type": self.anchor_type.value,
            "confidence": self.confidence,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "insert_position": self.insert_position.value if self.insert_position else None,
            "matched_text": self.matched_text,
            "chunk_id": self.chunk_id,
            "offset_start": self.offset_start,
            "offset_end": self.offset_end,
            "reason": self.reason,
            "suggestion": self.suggestion,
            "display_numbering": self.display_numbering,
            "legal_domain": self.legal_domain,
            "risk_type": self.risk_type,
            "recommendation_type": self.recommendation_type,
            "clause_operation_type": self.clause_operation_type,
            "rationale_bullets": self.rationale_bullets,
            "related_risks": self.related_risks,
            "impact_accepted": self.impact_accepted,
            "impact_rejected": self.impact_rejected,
            "summary_title": self.summary_title,
            "summary_impact": self.summary_impact,
            "action_label": self.action_label,
            "group_key": self.group_key,
        }
