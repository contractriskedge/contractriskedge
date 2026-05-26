"""Complete 12-category risk taxonomy for contract analysis.

Defines the comprehensive risk taxonomy with 12 categories, each
containing 4-8 sub-types, default severity ranges, benchmark
dimensions, and example language for both high-risk and market-standard
clauses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class RiskSubType:
    """A sub-type within a risk category."""

    id: str
    name: str
    description: str
    default_severity_range: Tuple[int, int]  # (min, max) on 1-10 scale
    example_high_risk_language: List[str]
    example_market_standard_language: List[str]


@dataclass
class RiskCategoryDef:
    """Definition of a single risk category in the taxonomy."""

    id: str
    name: str
    description: str
    sub_types: List[RiskSubType]
    default_severity_range: Tuple[int, int]
    benchmark_dimensions: List[str]
    example_high_risk_language: List[str]
    example_market_standard_language: List[str]


class RiskTaxonomy:
    """Complete 12-category risk taxonomy for contract analysis.

    Provides the authoritative taxonomy definition including category
    metadata, sub-types, severity ranges, and benchmark language examples.
    Used by the prompt chain to classify and assess contract clauses.

    Usage:
        taxonomy = RiskTaxonomy()
        category = taxonomy.get_category("indemnification")
        sub_types = taxonomy.get_sub_types("liability_limitation")
        all_categories = taxonomy.get_all_categories()
    """

    def __init__(self) -> None:
        """Initialize the taxonomy with all 12 risk categories."""
        self._categories: Dict[str, RiskCategoryDef] = {}
        self._initialize_taxonomy()

    def _initialize_taxonomy(self) -> None:
        """Build the complete 12-category taxonomy."""
        categories = [
            self._build_indemnification(),
            self._build_liability_limitation(),
            self._build_termination(),
            self._build_confidentiality(),
            self._build_data_privacy(),
            self._build_compliance(),
            self._build_payment_terms(),
            self._build_force_majeure(),
            self._build_assignment(),
            self._build_governing_law(),
            self._build_non_compete(),
            self._build_intellectual_property(),
        ]
        for cat in categories:
            self._categories[cat.id] = cat

    def _build_indemnification(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="indemnification",
            name="Indemnification",
            description=(
                "Provisions requiring one party to compensate the other for "
                "losses, damages, or liabilities arising from specified events. "
                "Includes scope of indemnity, defense obligations, and limitations."
            ),
            sub_types=[
                RiskSubType(
                    id="indemnification_scope",
                    name="Scope of Indemnity",
                    description="Breadth of covered losses including direct, indirect, consequential, and third-party claims.",
                    default_severity_range=(4, 9),
                    example_high_risk_language=[
                        "indemnify for all losses including indirect, consequential, incidental, special, or punitive damages",
                        "unlimited indemnification obligation without cap or temporal limitation",
                    ],
                    example_market_standard_language=[
                        "indemnify for third-party claims limited to direct damages",
                        "indemnification capped at contract value with mutual obligations",
                    ],
                ),
                RiskSubType(
                    id="indemnification_defense",
                    name="Defense Obligations",
                    description="Duty to defend, control of defense, and settlement rights.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "indemnifying party has sole control of defense with no input from indemnified party",
                        "indemnified party must reimburse defense costs if claim is unsuccessful",
                    ],
                    example_market_standard_language=[
                        "mutual cooperation in defense with shared control",
                        "indemnifying party controls defense with consent for settlement",
                    ],
                ),
                RiskSubType(
                    id="indemnification_survival",
                    name="Survival Period",
                    description="How long indemnification obligations survive contract termination.",
                    default_severity_range=(3, 7),
                    example_high_risk_language=[
                        "indemnification obligations survive for one year or less",
                        "no survival period specified for indemnification",
                    ],
                    example_market_standard_language=[
                        "indemnification survives for 3 years post-termination",
                        "indefinite survival for third-party IP claims",
                    ],
                ),
                RiskSubType(
                    id="indemnification_carveouts",
                    name="Carve-outs and Exclusions",
                    description="Exceptions to indemnification obligations.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "broad exclusion for indemnification of IP infringement claims",
                        "indemnity excluded for modifications by indemnified party",
                    ],
                    example_market_standard_language=[
                        "standard exclusions for misuse and unauthorized modifications",
                        "proportionate reduction for contributory negligence",
                    ],
                ),
                RiskSubType(
                    id="indemnification_caps",
                    name="Indemnity Caps",
                    description="Monetary limits on indemnification obligations.",
                    default_severity_range=(5, 10),
                    example_high_risk_language=[
                        "no cap on indemnification liability",
                        "indemnification cap is 3x or more of contract value",
                    ],
                    example_market_standard_language=[
                        "indemnification capped at contract value",
                        "separate cap for IP indemnification at 1.5x contract value",
                    ],
                ),
            ],
            default_severity_range=(1, 10),
            benchmark_dimensions=[
                "indemnity_scope_breadth",
                "defense_control_balance",
                "survival_duration",
                "cap_reasonableness",
                "carveout_fairness",
            ],
            example_high_risk_language=[
                "Company shall indemnify and hold harmless Client from any and all claims",
                "unlimited indemnification for all third-party claims",
                "indemnitor shall have sole and absolute control over defense",
            ],
            example_market_standard_language=[
                "Each party shall indemnify the other for claims arising from its gross negligence",
                "indemnification obligations shall be capped at the total fees paid",
                "mutual indemnification with defense cooperation provisions",
            ],
        )

    def _build_liability_limitation(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="liability_limitation",
            name="Limitation of Liability",
            description=(
                "Provisions that cap or exclude a party's liability for damages. "
                "Includes liability caps, exclusions of consequential damages, "
                "and exceptions to limitations."
            ),
            sub_types=[
                RiskSubType(
                    id="liability_cap",
                    name="Liability Cap",
                    description="Monetary cap on total liability.",
                    default_severity_range=(3, 9),
                    example_high_risk_language=[
                        "aggregate liability capped at 50% of fees or less",
                        "liability cap of $10,000 regardless of contract value",
                    ],
                    example_market_standard_language=[
                        "liability cap equal to 100% of fees paid over 12 months",
                        "mutual liability cap at contract value",
                    ],
                ),
                RiskSubType(
                    id="consequential_damages",
                    name="Exclusion of Consequential Damages",
                    description="Whether consequential, indirect, or special damages are excluded.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "broad exclusion of all consequential, indirect, and special damages with no exceptions",
                        "exclusion of lost profits, lost data, and business interruption",
                    ],
                    example_market_standard_language=[
                        "mutual exclusion of consequential damages with exceptions for IP infringement",
                        "consequential damages exclusion with carveback for breach of confidentiality",
                    ],
                ),
                RiskSubType(
                    id="liability_exceptions",
                    name="Exceptions to Limitations",
                    description="What types of claims are not subject to liability caps.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "no exceptions to liability cap, including for gross negligence",
                        "cap applies even to intentional misconduct",
                    ],
                    example_market_standard_language=[
                        "standard exceptions for IP infringement, confidentiality breach, and death/injury",
                        "liability cap does not apply to indemnification obligations",
                    ],
                ),
                RiskSubType(
                    id="liability_aggregation",
                    name="Liability Aggregation",
                    description="How liability is aggregated across affiliates, subsidiaries, and related claims.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "all claims aggregate to a single cap regardless of number of claims",
                        "affiliate claims also subject to same aggregate cap",
                    ],
                    example_market_standard_language=[
                        "separate caps for each claim or series of related claims",
                        "aggregate cap per year with renewal",
                    ],
                ),
            ],
            default_severity_range=(1, 10),
            benchmark_dimensions=[
                "cap_percentage_of_contract_value",
                "consequential_exclusion_breadth",
                "exception_fairness",
                "aggregation_method",
            ],
            example_high_risk_language=[
                "In no event shall either party's aggregate liability exceed the fees paid",
                "neither party shall be liable for any indirect, incidental, or consequential damages",
            ],
            example_market_standard_language=[
                "liability cap of 100% of fees paid with mutual exclusions for consequential damages",
                "standard liability exceptions for IP, confidentiality, and indemnification",
            ],
        )

    def _build_termination(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="termination",
            name="Termination",
            description=(
                "Provisions governing how and when the contract can be terminated, "
                "including termination for convenience, for cause, notice periods, "
                "and post-termination obligations."
            ),
            sub_types=[
                RiskSubType(
                    id="termination_for_convenience",
                    name="Termination for Convenience",
                    description="Right to terminate without cause.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "only one party may terminate for convenience",
                        "no termination for convenience right for either party",
                    ],
                    example_market_standard_language=[
                        "mutual termination for convenience with 30-90 days notice",
                        "termination for convenience with reasonable notice period",
                    ],
                ),
                RiskSubType(
                    id="termination_for_cause",
                    name="Termination for Cause",
                    description="Right to terminate for breach or default.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "termination for cause only after 90 days cure period",
                        "no opportunity to cure before termination for cause",
                    ],
                    example_market_standard_language=[
                        "30-day cure period for non-material breaches",
                        "immediate termination for material breach with notice",
                    ],
                ),
                RiskSubType(
                    id="post_termination_obligations",
                    name="Post-Termination Obligations",
                    description="Obligations that survive termination.",
                    default_severity_range=(3, 7),
                    example_high_risk_language=[
                        "all obligations terminate immediately with no survival",
                        "no obligation to return or destroy confidential information",
                    ],
                    example_market_standard_language=[
                        "survival of confidentiality, indemnification, and payment obligations",
                        "obligation to return/destroy confidential information within 30 days",
                    ],
                ),
                RiskSubType(
                    id="termination_fees",
                    name="Termination Fees and Penalties",
                    description="Fees or penalties payable upon termination.",
                    default_severity_range=(4, 9),
                    example_high_risk_language=[
                        "early termination fee of 100% of remaining contract value",
                        "cancellation penalties that escalate with shorter notice",
                    ],
                    example_market_standard_language=[
                        "termination fee equal to 1-3 months of fees",
                        "no termination fee for convenience termination with 90 days notice",
                    ],
                ),
            ],
            default_severity_range=(1, 9),
            benchmark_dimensions=[
                "convenience_termination_balance",
                "cure_period_reasonableness",
                "survival_comprehensiveness",
                "penalty_reasonableness",
            ],
            example_high_risk_language=[
                "Provider may terminate this agreement at any time without cause",
                "all obligations cease immediately upon termination",
                "early termination penalty of 100% of remaining payments",
            ],
            example_market_standard_language=[
                "either party may terminate for convenience with 60 days written notice",
                "30-day cure period for any non-material breach",
                "standard survival clauses for confidentiality and indemnification",
            ],
        )

    def _build_confidentiality(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="confidentiality",
            name="Confidentiality",
            description=(
                "Provisions protecting confidential information, defining what "
                "constitutes confidential information, permitted uses, disclosure "
                "exceptions, and duration of confidentiality obligations."
            ),
            sub_types=[
                RiskSubType(
                    id="confidentiality_definition",
                    name="Definition of Confidential Information",
                    description="Scope of what is considered confidential.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "confidential information defined so narrowly it excludes key business data",
                        "oral or visual information excluded unless reduced to writing within 5 days",
                    ],
                    example_market_standard_language=[
                        "broad definition covering all information disclosed in connection with the agreement",
                        "includes written, oral, and electronic information with reasonable identification",
                    ],
                ),
                RiskSubType(
                    id="confidentiality_exclusions",
                    name="Exclusions from Confidentiality",
                    description="What information is not protected.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "overly broad exclusion for independently developed information",
                        "information that becomes public through no fault of receiving party",
                    ],
                    example_market_standard_language=[
                        "standard exclusions for publicly known, independently developed, and rightfully received information",
                        "narrowly tailored exclusions with burden of proof on receiving party",
                    ],
                ),
                RiskSubType(
                    id="confidentiality_duration",
                    name="Confidentiality Duration",
                    description="How long confidentiality obligations last.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "confidentiality obligations last only 1-2 years",
                        "perpetual confidentiality with no time limitation",
                    ],
                    example_market_standard_language=[
                        "confidentiality obligations for 3-5 years post-termination",
                        "trade secret protection for as long as information remains a trade secret",
                    ],
                ),
                RiskSubType(
                    id="confidentiality_permitted_disclosures",
                    name="Permitted Disclosures",
                    description="Circumstances where confidential information may be disclosed.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "no exception for disclosures required by law or court order",
                        "receiving party must bear cost of opposing disclosure requests",
                    ],
                    example_market_standard_language=[
                        "permitted disclosure to employees, advisors, and contractors on need-to-know basis",
                        "disclosure required by law with prompt notice and cooperation",
                    ],
                ),
            ],
            default_severity_range=(1, 9),
            benchmark_dimensions=[
                "definition_breadth",
                "exclusion_reasonableness",
                "duration_adequacy",
                "disclosure_flexibility",
            ],
            example_high_risk_language=[
                "Confidential information shall not include information that is independently developed",
                "confidentiality obligations shall survive for one year after termination",
            ],
            example_market_standard_language=[
                "Confidential information means all information disclosed by either party",
                "confidentiality obligations survive for 3 years with trade secret protection",
            ],
        )

    def _build_data_privacy(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="data_privacy",
            name="Data Privacy and Security",
            description=(
                "Provisions governing the collection, processing, storage, and "
                "protection of personal data. Includes GDPR, CCPA, and other "
                "privacy regulation compliance obligations."
            ),
            sub_types=[
                RiskSubType(
                    id="data_processing_terms",
                    name="Data Processing Terms",
                    description="Terms governing how personal data is processed.",
                    default_severity_range=(4, 10),
                    example_high_risk_language=[
                        "no data processing agreement or DPA referenced",
                        "vague data processing terms that don't specify purposes or duration",
                    ],
                    example_market_standard_language=[
                        "comprehensive DPA attached as exhibit with processing purposes, duration, and sub-processors",
                        "GDPR-compliant data processing terms with data subject rights",
                    ],
                ),
                RiskSubType(
                    id="data_security_measures",
                    name="Security Measures",
                    description="Required technical and organizational security measures.",
                    default_severity_range=(4, 9),
                    example_high_risk_language=[
                        "no specific security measures required beyond 'commercially reasonable efforts'",
                        "security measures not documented or auditable",
                    ],
                    example_market_standard_language=[
                        "SOC 2 Type II certification required with annual audits",
                        "ISO 27001 certification with specific technical controls listed",
                    ],
                ),
                RiskSubType(
                    id="data_breach_notification",
                    name="Breach Notification",
                    description="Obligations to notify of data breaches.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "72+ hour notification window or no specific timeline",
                        "notification obligation only for 'material' breaches",
                    ],
                    example_market_standard_language=[
                        "notification within 24-48 hours of confirmed breach",
                        "obligation to notify affected parties and regulators",
                    ],
                ),
                RiskSubType(
                    id="data_transfer",
                    name="Cross-Border Data Transfers",
                    description="Terms governing international data transfers.",
                    default_severity_range=(4, 9),
                    example_high_risk_language=[
                        "no provisions for cross-border data transfers",
                        "data may be stored or processed in any jurisdiction without safeguards",
                    ],
                    example_market_standard_language=[
                        "Standard Contractual Clauses (SCCs) in place for cross-border transfers",
                        "data residency requirements with approved jurisdictions listed",
                    ],
                ),
                RiskSubType(
                    id="data_deletion",
                    name="Data Deletion and Return",
                    description="Obligations to delete or return data upon termination.",
                    default_severity_range=(3, 7),
                    example_high_risk_language=[
                        "no obligation to delete personal data after termination",
                        "30+ day retention of data after termination without deletion",
                    ],
                    example_market_standard_language=[
                        "obligation to delete or return all personal data within 30 days",
                        "certification of deletion with audit right",
                    ],
                ),
            ],
            default_severity_range=(1, 10),
            benchmark_dimensions=[
                "dpa_comprehensiveness",
                "security_standard_rigor",
                "notification_timeliness",
                "transfer_compliance",
                "deletion_assurance",
            ],
            example_high_risk_language=[
                "no data processing agreement referenced in the contract",
                "data may be transferred to any country without safeguards",
            ],
            example_market_standard_language=[
                "DPA attached with SCCs for cross-border transfers",
                "SOC 2 Type II certification with annual audit reports",
            ],
        )

    def _build_compliance(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="compliance",
            name="Regulatory Compliance",
            description=(
                "Provisions requiring compliance with applicable laws, regulations, "
                "and industry standards. Includes anti-corruption, sanctions, export "
                "controls, and industry-specific regulations."
            ),
            sub_types=[
                RiskSubType(
                    id="compliance_general",
                    name="General Compliance Obligation",
                    description="Requirement to comply with applicable laws.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "no general compliance with laws clause",
                        "compliance only with 'material' laws, excluding many regulations",
                    ],
                    example_market_standard_language=[
                        "mutual obligation to comply with all applicable laws and regulations",
                        "specific mention of key regulatory frameworks",
                    ],
                ),
                RiskSubType(
                    id="anti_corruption",
                    name="Anti-Corruption and Anti-Bribery",
                    description="FCPA, UK Bribery Act, and similar compliance.",
                    default_severity_range=(5, 10),
                    example_high_risk_language=[
                        "no anti-corruption provisions",
                        "anti-corruption clause without audit or termination rights",
                    ],
                    example_market_standard_language=[
                        "comprehensive anti-corruption clause with FCPA/UKBA compliance",
                        "right to audit and terminate for corruption violations",
                    ],
                ),
                RiskSubType(
                    id="sanctions_export",
                    name="Sanctions and Export Controls",
                    description="Compliance with trade sanctions and export control laws.",
                    default_severity_range=(4, 9),
                    example_high_risk_language=[
                        "no sanctions or export control provisions",
                        "vague representation of compliance without specifics",
                    ],
                    example_market_standard_language=[
                        "representations of compliance with OFAC sanctions and export controls",
                        "obligation to notify of any sanctions violations",
                    ],
                ),
                RiskSubType(
                    id="industry_regulations",
                    name="Industry-Specific Regulations",
                    description="Compliance with sector-specific regulations (HIPAA, FINRA, FERC, etc.).",
                    default_severity_range=(4, 9),
                    example_high_risk_language=[
                        "no mention of applicable industry regulations",
                        "party disclaims knowledge of industry-specific requirements",
                    ],
                    example_market_standard_language=[
                        "explicit compliance with HIPAA, GLBA, or applicable regulations",
                        "representation of regulatory compliance with audit rights",
                    ],
                ),
            ],
            default_severity_range=(1, 10),
            benchmark_dimensions=[
                "compliance_breadth",
                "anti_corruption_rigor",
                "sanctions_coverage",
                "industry_specificity",
            ],
            example_high_risk_language=[
                "no compliance with laws clause in the agreement",
                "no anti-corruption or anti-bribery provisions",
            ],
            example_market_standard_language=[
                "mutual compliance with all applicable laws and regulations",
                "comprehensive anti-corruption, sanctions, and export control provisions",
            ],
        )

    def _build_payment_terms(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="payment_terms",
            name="Payment Terms and Pricing",
            description=(
                "Provisions governing payment obligations, pricing, invoicing, "
                "late payment penalties, and price adjustment mechanisms."
            ),
            sub_types=[
                RiskSubType(
                    id="payment_timing",
                    name="Payment Timing",
                    description="When payments are due.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "payment due upon receipt of invoice (net 0)",
                        "payment due within 120+ days",
                    ],
                    example_market_standard_language=[
                        "net 30 payment terms",
                        "net 45 with early payment discount",
                    ],
                ),
                RiskSubType(
                    id="late_payment",
                    name="Late Payment Penalties",
                    description="Interest and penalties for late payment.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "late payment interest of 2-5% per month",
                        "suspension of services for any late payment without cure period",
                    ],
                    example_market_standard_language=[
                        "late payment interest of 1-1.5% per month",
                        "reasonable cure period before service suspension",
                    ],
                ),
                RiskSubType(
                    id="price_adjustment",
                    name="Price Adjustment",
                    description="Mechanisms for price changes over time.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "unilateral price increase with no notice or cap",
                        "prices indexed to CPI with no ceiling",
                    ],
                    example_market_standard_language=[
                        "annual price increase capped at CPI or 3-5%",
                        "price adjustment with 60 days notice and mutual agreement",
                    ],
                ),
                RiskSubType(
                    id="invoicing_disputes",
                    name="Invoice Disputes",
                    description="Process for disputing invoices.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "no right to dispute invoices after payment",
                        "disputes must be raised within 5 days of invoice",
                    ],
                    example_market_standard_language=[
                        "30-day period to dispute invoices",
                        "undisputed amounts must be paid while dispute is resolved",
                    ],
                ),
                RiskSubType(
                    id="taxes_and_duties",
                    name="Taxes and Duties",
                    description="Responsibility for taxes, duties, and withholding.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "customer responsible for all taxes including provider's income taxes",
                        "no gross-up for withholding taxes",
                    ],
                    example_market_standard_language=[
                        "each party responsible for its own income taxes",
                        "mutual cooperation for tax treaty benefits with gross-up provision",
                    ],
                ),
            ],
            default_severity_range=(1, 8),
            benchmark_dimensions=[
                "payment_timing_reasonableness",
                "penalty_fairness",
                "price_stability",
                "dispute_process_fairness",
            ],
            example_high_risk_language=[
                "payment due within 10 days of invoice with 3% monthly late fee",
                "provider may increase prices at any time without notice",
            ],
            example_market_standard_language=[
                "net 30 payment terms with 1.5% monthly late fee",
                "annual price increases capped at the greater of CPI or 4%",
            ],
        )

    def _build_force_majeure(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="force_majeure",
            name="Force Majeure",
            description=(
                "Provisions excusing performance when unforeseen events beyond "
                "a party's control occur. Includes definition of covered events, "
                "notice requirements, and mitigation obligations."
            ),
            sub_types=[
                RiskSubType(
                    id="force_majeure_definition",
                    name="Definition of Force Majeure Events",
                    description="What events qualify as force majeure.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "very narrow definition excluding pandemics, cyberattacks, or supply chain disruptions",
                        "vague definition of 'acts of God' without modern contingencies",
                    ],
                    example_market_standard_language=[
                        "comprehensive definition including pandemics, cyberattacks, natural disasters, and supply chain failures",
                        "specific inclusion of modern risks like cloud service failures",
                    ],
                ),
                RiskSubType(
                    id="force_majeure_notice",
                    name="Notice Requirements",
                    description="Timing and form of force majeure notice.",
                    default_severity_range=(2, 5),
                    example_high_risk_language=[
                        "no notice requirement for force majeure events",
                        "notice required within 24 hours which may be impractical",
                    ],
                    example_market_standard_language=[
                        "notice required within 5-10 business days of event",
                        "reasonable notice with ongoing updates on impact",
                    ],
                ),
                RiskSubType(
                    id="force_majeure_mitigation",
                    name="Mitigation Obligations",
                    description="Duty to mitigate effects of force majeure.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "no obligation to mitigate or find alternatives",
                        "suspension of all obligations without mitigation efforts",
                    ],
                    example_market_standard_language=[
                        "obligation to use reasonable efforts to mitigate and resume performance",
                        "alternative performance methods where feasible",
                    ],
                ),
                RiskSubType(
                    id="force_majeure_termination",
                    name="Termination Rights",
                    description="Right to terminate after prolonged force majeure.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "no termination right for prolonged force majeure",
                        "force majeure extends indefinitely without termination option",
                    ],
                    example_market_standard_language=[
                        "either party may terminate if force majeure exceeds 60-90 days",
                        "right to terminate with notice after prolonged event",
                    ],
                ),
            ],
            default_severity_range=(1, 8),
            benchmark_dimensions=[
                "event_coverage_breadth",
                "notice_reasonableness",
                "mitigation_obligation",
                "termination_timeline",
            ],
            example_high_risk_language=[
                "Force majeure shall mean only acts of God, war, and government action",
                "no obligation to mitigate effects of force majeure event",
            ],
            example_market_standard_language=[
                "Force majeure includes pandemics, cyberattacks, natural disasters, and supply chain disruptions",
                "reasonable mitigation obligations with termination after 90 days",
            ],
        )

    def _build_assignment(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="assignment",
            name="Assignment",
            description=(
                "Provisions governing whether and how rights and obligations "
                "under the contract can be assigned or delegated to another party."
            ),
            sub_types=[
                RiskSubType(
                    id="assignment_restriction",
                    name="Assignment Restrictions",
                    description="Whether assignment is restricted or permitted.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "no assignment allowed without consent, consent may be unreasonably withheld",
                        "assignment to affiliates requires prior written consent",
                    ],
                    example_market_standard_language=[
                        "assignment permitted to affiliates without consent",
                        "consent not unreasonably withheld or delayed",
                    ],
                ),
                RiskSubType(
                    id="assignment_change_of_control",
                    name="Change of Control",
                    description="Treatment of assignment upon change of control.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "change of control triggers automatic termination",
                        "change of control deemed assignment requiring consent",
                    ],
                    example_market_standard_language=[
                        "change of control not deemed an assignment",
                        "notice of change of control with no consent required",
                    ],
                ),
                RiskSubType(
                    id="assignment_delegation",
                    name="Delegation of Duties",
                    description="Whether duties can be subcontracted or delegated.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "no right to subcontract any services",
                        "unlimited right to subcontract without approval",
                    ],
                    example_market_standard_language=[
                        "right to subcontract with notice and approval for material functions",
                        "provider remains responsible for subcontractor performance",
                    ],
                ),
            ],
            default_severity_range=(1, 8),
            benchmark_dimensions=[
                "assignment_flexibility",
                "change_of_control_treatment",
                "subcontracting_rights",
            ],
            example_high_risk_language=[
                "Neither party may assign this agreement without the other's written consent",
                "change of control shall be deemed an assignment requiring consent",
            ],
            example_market_standard_language=[
                "Assignment to affiliates permitted without consent",
                "change of control not deemed an assignment with notice",
            ],
        )

    def _build_governing_law(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="governing_law",
            name="Governing Law and Jurisdiction",
            description=(
                "Provisions specifying which jurisdiction's laws govern the "
                "contract and where disputes must be litigated or arbitrated."
            ),
            sub_types=[
                RiskSubType(
                    id="governing_law_choice",
                    name="Choice of Law",
                    description="Which jurisdiction's laws apply.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "governed by laws of a jurisdiction with no connection to either party",
                        "choice of law in a jurisdiction known for unfavorable contract law",
                    ],
                    example_market_standard_language=[
                        "governed by laws of a neutral jurisdiction with connection to parties",
                        "Delaware or New York law for US contracts",
                    ],
                ),
                RiskSubType(
                    id="dispute_venue",
                    name="Dispute Venue",
                    description="Where disputes must be resolved.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "exclusive venue in a remote or expensive jurisdiction",
                        "venue only in the drafting party's location",
                    ],
                    example_market_standard_language=[
                        "mutually agreed venue or neutral location",
                        "courts in either party's jurisdiction with plaintiff filing",
                    ],
                ),
                RiskSubType(
                    id="arbitration",
                    name="Arbitration Provisions",
                    description="Requirements for arbitration vs litigation.",
                    default_severity_range=(2, 7),
                    example_high_risk_language=[
                        "mandatory arbitration with no class action waiver",
                        "arbitration costs borne entirely by one party",
                    ],
                    example_market_standard_language=[
                        "mutual agreement to arbitrate with shared costs",
                        "JAMS or AAA rules with neutral arbitrator selection",
                    ],
                ),
                RiskSubType(
                    id="waiver_jury_trial",
                    name="Waiver of Jury Trial",
                    description="Whether jury trial rights are waived.",
                    default_severity_range=(2, 5),
                    example_high_risk_language=[
                        "unilateral waiver of jury trial for only one party",
                        "buried jury waiver without clear notice",
                    ],
                    example_market_standard_language=[
                        "mutual waiver of jury trial with clear notice",
                        "no jury waiver with preserved rights",
                    ],
                ),
            ],
            default_severity_range=(1, 8),
            benchmark_dimensions=[
                "law_fairness",
                "venue_convenience",
                "arbitration_balance",
                "jury_waiver_fairness",
            ],
            example_high_risk_language=[
                "This agreement shall be governed by the laws of a foreign jurisdiction",
                "exclusive jurisdiction in courts located in the drafting party's home city",
            ],
            example_market_standard_language=[
                "governed by the laws of the state where services are primarily performed",
                "mutual submission to jurisdiction with convenient venue",
            ],
        )

    def _build_non_compete(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="non_compete",
            name="Non-Compete and Non-Solicit",
            description=(
                "Provisions restricting a party's ability to compete, solicit "
                "customers, or hire employees. Includes scope, duration, and "
                "geographic limitations."
            ),
            sub_types=[
                RiskSubType(
                    id="non_compete_scope",
                    name="Non-Compete Scope",
                    description="Activities restricted by non-compete.",
                    default_severity_range=(4, 9),
                    example_high_risk_language=[
                        "broad non-compete covering any business that competes 'in any manner'",
                        "non-compete covering business areas unrelated to contract scope",
                    ],
                    example_market_standard_language=[
                        "narrowly tailored non-compete limited to specific services",
                        "non-compete restricted to the specific business unit involved",
                    ],
                ),
                RiskSubType(
                    id="non_compete_duration",
                    name="Non-Compete Duration",
                    description="How long non-compete lasts.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "non-compete for 2+ years post-termination",
                        "indefinite non-compete with no time limit",
                    ],
                    example_market_standard_language=[
                        "non-compete for 6-12 months post-termination",
                        "reasonable duration based on industry norms",
                    ],
                ),
                RiskSubType(
                    id="non_compete_geography",
                    name="Geographic Scope",
                    description="Geographic area covered by non-compete.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "worldwide non-compete for a local business",
                        "unlimited geographic scope with no nexus to business",
                    ],
                    example_market_standard_language=[
                        "geographic scope limited to territory where services were provided",
                        "reasonable geographic limitation tied to business operations",
                    ],
                ),
                RiskSubType(
                    id="non_solicit",
                    name="Non-Solicitation of Employees",
                    description="Restrictions on hiring each other's employees.",
                    default_severity_range=(2, 6),
                    example_high_risk_language=[
                        "non-solicit covers all employees regardless of involvement",
                        "non-solicit duration of 2+ years",
                    ],
                    example_market_standard_language=[
                        "non-solicit limited to employees directly involved in services",
                        "12-month non-solicit with exception for general advertisements",
                    ],
                ),
                RiskSubType(
                    id="customer_non_solicit",
                    name="Non-Solicitation of Customers",
                    description="Restrictions on soliciting customers.",
                    default_severity_range=(3, 7),
                    example_high_risk_language=[
                        "prohibition on any contact with customers regardless of relationship",
                        "customer non-solicit without time or scope limitations",
                    ],
                    example_market_standard_language=[
                        "limited to solicitation of customers for competing services",
                        "reasonable time-limited restriction with existing relationship exception",
                    ],
                ),
            ],
            default_severity_range=(1, 9),
            benchmark_dimensions=[
                "scope_reasonableness",
                "duration_fairness",
                "geographic_limitation",
                "employee_solicit_breadth",
                "customer_solicit_breadth",
            ],
            example_high_risk_language=[
                "Provider shall not engage in any business that competes with Client",
                "two-year worldwide non-compete covering all related business activities",
            ],
            example_market_standard_language=[
                "12-month non-compete limited to specific services provided under this agreement",
                "reasonable geographic and temporal restrictions aligned with business interests",
            ],
        )

    def _build_intellectual_property(self) -> RiskCategoryDef:
        return RiskCategoryDef(
            id="intellectual_property",
            name="Intellectual Property",
            description=(
                "Provisions governing ownership, licensing, and protection of "
                "intellectual property. Includes IP ownership, license grants, "
                "open source usage, and IP warranties."
            ),
            sub_types=[
                RiskSubType(
                    id="ip_ownership",
                    name="IP Ownership",
                    description="Who owns IP created during the engagement.",
                    default_severity_range=(4, 10),
                    example_high_risk_language=[
                        "all IP created belongs to customer even if provider's pre-existing tools used",
                        "work-made-for-hire clause covering all deliverables without IP definition",
                    ],
                    example_market_standard_language=[
                        "customer owns deliverables, provider retains pre-existing IP",
                        "license grant for pre-existing IP needed for deliverables",
                    ],
                ),
                RiskSubType(
                    id="ip_license_grant",
                    name="License Grants",
                    description="Licenses granted between parties for IP use.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "very narrow license limited to internal use for one year",
                        "no license for pre-existing IP necessary to use deliverables",
                    ],
                    example_market_standard_language=[
                        "perpetual, irrevocable license to use deliverables for intended purpose",
                        "sufficient license to pre-existing IP for deliverable use",
                    ],
                ),
                RiskSubType(
                    id="open_source",
                    name="Open Source Usage",
                    description="Terms governing use of open source software.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "no disclosure of open source components used",
                        "copyleft licenses used without disclosure or compliance plan",
                    ],
                    example_market_standard_language=[
                        "list of open source components provided with license compliance",
                        "copyleft licenses isolated from proprietary code",
                    ],
                ),
                RiskSubType(
                    id="ip_warranties",
                    name="IP Warranties and Infringement",
                    description="Warranties regarding IP ownership and non-infringement.",
                    default_severity_range=(3, 8),
                    example_high_risk_language=[
                        "no warranty of non-infringement",
                        "IP warranty disclaimed 'as is' without remedies",
                    ],
                    example_market_standard_language=[
                        "warranty of non-infringement with standard remedies",
                        "IP infringement indemnification with defense obligations",
                    ],
                ),
                RiskSubType(
                    id="ip_moral_rights",
                    name="Moral Rights",
                    description="Waiver or assignment of moral rights.",
                    default_severity_range=(2, 5),
                    example_high_risk_language=[
                        "unconditional waiver of all moral rights",
                        "no mention of moral rights in jurisdictions that recognize them",
                    ],
                    example_market_standard_language=[
                        "waiver of moral rights to extent permitted by law",
                        "assignment of moral rights with attribution rights",
                    ],
                ),
            ],
            default_severity_range=(1, 10),
            benchmark_dimensions=[
                "ownership_clarity",
                "license_adequacy",
                "open_source_transparency",
                "warranty_strength",
                "moral_rights_handling",
            ],
            example_high_risk_language=[
                "all work product shall be deemed work made for hire owned by Client",
                "no warranty that deliverables do not infringe third-party IP rights",
            ],
            example_market_standard_language=[
                "Customer owns deliverables, Provider retains pre-existing IP with use license",
                "warranty of non-infringement with standard IP indemnification",
            ],
        )

    # ── Public API ───────────────────────────────────────────────────────────

    def get_category(self, category_id: str) -> Optional[RiskCategoryDef]:
        """Get a risk category by its ID.

        Args:
            category_id: The category identifier (e.g., 'indemnification').

        Returns:
            The risk category definition, or None if not found.
        """
        return self._categories.get(category_id)

    def get_sub_types(self, category_id: str) -> List[RiskSubType]:
        """Get all sub-types for a risk category.

        Args:
            category_id: The category identifier.

        Returns:
            List of sub-types for the category, or empty list if not found.
        """
        category = self._categories.get(category_id)
        if category is None:
            return []
        return category.sub_types

    def get_all_categories(self) -> List[RiskCategoryDef]:
        """Get all risk categories in the taxonomy.

        Returns:
            List of all 12 risk category definitions.
        """
        return list(self._categories.values())

    def get_category_ids(self) -> List[str]:
        """Get all category IDs.

        Returns:
            List of all 12 category identifiers.
        """
        return list(self._categories.keys())

    def get_category_names(self) -> List[str]:
        """Get all category display names.

        Returns:
            List of all 12 category names.
        """
        return [cat.name for cat in self._categories.values()]

    def get_all_sub_types(self) -> Dict[str, List[RiskSubType]]:
        """Get all sub-types organized by category.

        Returns:
            Dict mapping category IDs to their sub-types.
        """
        return {
            cat_id: cat.sub_types
            for cat_id, cat in self._categories.items()
        }

    def get_total_sub_type_count(self) -> int:
        """Get the total number of sub-types across all categories.

        Returns:
            Total count of sub-types.
        """
        return sum(len(cat.sub_types) for cat in self._categories.values())

    def find_sub_type(self, sub_type_id: str) -> Optional[Tuple[str, RiskSubType]]:
        """Find a sub-type by its ID across all categories.

        Args:
            sub_type_id: The sub-type identifier.

        Returns:
            Tuple of (category_id, sub_type) if found, None otherwise.
        """
        for cat_id, cat in self._categories.items():
            for sub in cat.sub_types:
                if sub.id == sub_type_id:
                    return (cat_id, sub)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the taxonomy to a dictionary.

        Returns:
            Complete taxonomy as a nested dictionary.
        """
        return {
            "version": "2.0.0",
            "category_count": len(self._categories),
            "sub_type_count": self.get_total_sub_type_count(),
            "categories": {
                cat_id: {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description,
                    "default_severity_range": list(cat.default_severity_range),
                    "benchmark_dimensions": cat.benchmark_dimensions,
                    "sub_types": [
                        {
                            "id": sub.id,
                            "name": sub.name,
                            "description": sub.description,
                            "default_severity_range": list(sub.default_severity_range),
                        }
                        for sub in cat.sub_types
                    ],
                }
                for cat_id, cat in self._categories.items()
            },
        }
