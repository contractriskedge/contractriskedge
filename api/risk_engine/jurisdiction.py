"""Jurisdictional risk context layer — US / EU / UK / APAC rules.

Provides jurisdiction-specific risk assessment rules, regulatory
references, and risk modifiers for the four major legal frameworks:
US (various state laws), EU (GDPR, etc.), UK (post-Brexit), and
APAC (various country-specific regulations).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .output_schema import JurisdictionalConsideration

logger = logging.getLogger(__name__)


@dataclass
class JurisdictionRule:
    """A jurisdiction-specific legal rule affecting risk assessment."""

    jurisdiction_code: str  # US, EU, UK, APAC
    rule_id: str
    rule_name: str
    description: str
    applies_to_categories: List[str]
    risk_modifier: float  # -2.0 to +2.0 modifier to severity
    citation: str  # Legal citation or reference


class JurisdictionalRiskLayer:
    """Jurisdiction-specific risk context layer.

    Provides:
    1. Predefined rules for US / EU / UK / APAC jurisdictions.
    2. Risk modifiers based on applicable jurisdiction rules.
    3. Jurisdiction-specific regulatory references.
    4. Integration with risk analysis output schema.

    Usage:
        jrl = JurisdictionalRiskLayer()
        considerations = jrl.evaluate_clause(
            clause_text="...",
            category="indemnification",
            jurisdictions=["US", "EU"],
            governing_law="New York, USA",
        )
        modifier = jrl.get_risk_modifier("indemnification", "US")
    """

    def __init__(self) -> None:
        """Initialize the jurisdictional risk layer with predefined rules."""
        self._rules: Dict[str, List[JurisdictionRule]] = {}
        self._initialize_rules()

    def _initialize_rules(self) -> None:
        """Initialize jurisdiction-specific rules."""
        # ── US Rules ──
        self._rules["US"] = [
            JurisdictionRule(
                jurisdiction_code="US",
                rule_id="US-001",
                rule_name="UCC Article 2 — Indemnification",
                description="UCC Article 2 governs sales of goods. Indemnification "
                "clauses must be explicit; broad form indemnity may be restricted.",
                applies_to_categories=["indemnification", "liability_limitation"],
                risk_modifier=0.5,
                citation="UCC Article 2 §§ 2-101 to 2-725",
            ),
            JurisdictionRule(
                jurisdiction_code="US",
                rule_id="US-002",
                rule_name="State Anti-Indemnity Statutes",
                description="Many states (e.g., Texas, Louisiana, New York) have "
                "anti-indemnity statutes that limit or void certain indemnity provisions.",
                applies_to_categories=["indemnification"],
                risk_modifier=1.0,
                citation="Various state statutes (e.g., Texas Civil Practice & Remedies Code § 151.101)",
            ),
            JurisdictionRule(
                jurisdiction_code="US",
                rule_id="US-003",
                rule_name="UCC Implied Warranties",
                description="Implied warranties of merchantability and fitness may "
                "apply unless specifically disclaimed in writing.",
                applies_to_categories=["liability_limitation", "compliance"],
                risk_modifier=0.5,
                citation="UCC §§ 2-314, 2-315",
            ),
            JurisdictionRule(
                jurisdiction_code="US",
                rule_id="US-004",
                rule_name="State Data Breach Notification Laws",
                description="All 50 states have data breach notification laws with "
                "varying requirements. Multi-state contracts face compliance complexity.",
                applies_to_categories=["data_privacy", "compliance"],
                risk_modifier=0.8,
                citation="Various state statutes (e.g., CA Civil Code § 1798.82)",
            ),
            JurisdictionRule(
                jurisdiction_code="US",
                rule_id="US-005",
                rule_name="New York General Obligations Law",
                description="NY GOL § 5-1401 allows parties to choose New York law "
                "for agreements over $250K. Certain indemnity provisions restricted.",
                applies_to_categories=["indemnification", "governing_law"],
                risk_modifier=0.3,
                citation="NY General Obligations Law § 5-1401",
            ),
        ]

        # ── EU Rules ──
        self._rules["EU"] = [
            JurisdictionRule(
                jurisdiction_code="EU",
                rule_id="EU-001",
                rule_name="GDPR — Data Processing Restrictions",
                description="GDPR imposes strict requirements on data processing, "
                "cross-border data transfers, and data protection clauses.",
                applies_to_categories=["data_privacy", "compliance"],
                risk_modifier=1.5,
                citation="GDPR (Regulation (EU) 2016/679), Articles 44-49",
            ),
            JurisdictionRule(
                jurisdiction_code="EU",
                rule_id="EU-002",
                rule_name="EU Unfair Contract Terms Directive",
                description="Unfair terms in B2B and B2C contracts may be "
                "unenforceable. Indemnity and liability limitations are scrutinized.",
                applies_to_categories=["indemnification", "liability_limitation"],
                risk_modifier=1.2,
                citation="Council Directive 93/13/EEC",
            ),
            JurisdictionRule(
                jurisdiction_code="EU",
                rule_id="EU-003",
                rule_name="EU Digital Markets Act",
                description="DMA imposes obligations on gatekeeper platforms "
                "affecting termination, data access, and interoperability clauses.",
                applies_to_categories=["termination", "data_privacy", "compliance"],
                risk_modifier=0.8,
                citation="Regulation (EU) 2022/1925 (Digital Markets Act)",
            ),
            JurisdictionRule(
                jurisdiction_code="EU",
                rule_id="EU-004",
                rule_name="EU AI Act",
                description="AI Act imposes requirements on AI system providers "
                "affecting liability and compliance clauses.",
                applies_to_categories=["compliance", "liability_limitation"],
                risk_modifier=1.0,
                citation="Regulation (EU) 2024/1689 (AI Act)",
            ),
            JurisdictionRule(
                jurisdiction_code="EU",
                rule_id="EU-005",
                rule_name="Rome I Regulation — Governing Law",
                description="Rome I governs choice of law in EU contracts. "
                "Consumer protections cannot be waived by law selection.",
                applies_to_categories=["governing_law", "compliance"],
                risk_modifier=0.5,
                citation="Regulation (EC) No 593/2008 (Rome I)",
            ),
        ]

        # ── UK Rules ──
        self._rules["UK"] = [
            JurisdictionRule(
                jurisdiction_code="UK",
                rule_id="UK-001",
                rule_name="UK GDPR — Post-Brexit Data Protection",
                description="UK GDPR (as retained post-Brexit) largely mirrors EU "
                "GDPR but with independent enforcement by the ICO.",
                applies_to_categories=["data_privacy", "compliance"],
                risk_modifier=1.3,
                citation="UK GDPR (SI 2019/419), Data Protection Act 2018",
            ),
            JurisdictionRule(
                jurisdiction_code="UK",
                rule_id="UK-002",
                rule_name="Unfair Contract Terms Act 1977",
                description="UCTA 1977 restricts exclusion and limitation of "
                "liability for breach of contract and negligence.",
                applies_to_categories=["liability_limitation", "indemnification"],
                risk_modifier=1.2,
                citation="Unfair Contract Terms Act 1977, §§ 2-3",
            ),
            JurisdictionRule(
                jurisdiction_code="UK",
                rule_id="UK-003",
                rule_name="Consumer Rights Act 2015",
                description="CRA 2015 provides consumer protections affecting "
                "unfair terms, implied terms, and remedies.",
                applies_to_categories=["liability_limitation", "termination"],
                risk_modifier=0.8,
                citation="Consumer Rights Act 2015, Part 2",
            ),
            JurisdictionRule(
                jurisdiction_code="UK",
                rule_id="UK-004",
                rule_name="Late Payment of Commercial Debts Act",
                description="Statutory interest and compensation for late payment "
                "in business-to-business contracts.",
                applies_to_categories=["payment_terms", "termination"],
                risk_modifier=0.5,
                citation="Late Payment of Commercial Debts (Interest) Act 1998",
            ),
        ]

        # ── APAC Rules ──
        self._rules["APAC"] = [
            JurisdictionRule(
                jurisdiction_code="APAC",
                rule_id="APAC-001",
                rule_name="China — Civil Code Contract Provisions",
                description="China's Civil Code governs contract formation, "
                "performance, and remedies. Liquidated damages limited to 30% of loss.",
                applies_to_categories=["indemnification", "liability_limitation", "payment_terms"],
                risk_modifier=1.0,
                citation="PRC Civil Code (2021), Book 3 — Contracts",
            ),
            JurisdictionRule(
                jurisdiction_code="APAC",
                rule_id="APAC-002",
                rule_name="China — PIPL Data Privacy",
                description="Personal Information Protection Law imposes strict "
                "requirements on data processing and cross-border transfers.",
                applies_to_categories=["data_privacy", "compliance"],
                risk_modifier=1.5,
                citation="PRC Personal Information Protection Law (2021)",
            ),
            JurisdictionRule(
                jurisdiction_code="APAC",
                rule_id="APAC-003",
                rule_name="Japan — Civil Code Amendments",
                description="2020 Civil Code amendments affected contract formation, "
                "warranties, and limitation periods.",
                applies_to_categories=["indemnification", "liability_limitation"],
                risk_modifier=0.5,
                citation="Japan Civil Code (Act No. 89 of 1896, as amended 2020)",
            ),
            JurisdictionRule(
                jurisdiction_code="APAC",
                rule_id="APAC-004",
                rule_name="Singapore — Unfair Contract Terms Act",
                description="UCTA applies to certain B2B contracts restricting "
                "exclusion of liability for negligence and breach.",
                applies_to_categories=["liability_limitation"],
                risk_modifier=0.5,
                citation="Singapore Unfair Contract Terms Act (Cap. 396)",
            ),
            JurisdictionRule(
                jurisdiction_code="APAC",
                rule_id="APAC-005",
                rule_name="India — Contract Act 1872",
                description="Indian Contract Act governs contract formation, "
                "indemnity, and guarantees. Liquidated damages provisions differ.",
                applies_to_categories=["indemnification", "payment_terms"],
                risk_modifier=0.5,
                citation="Indian Contract Act 1872, §§ 124-127 (Indemnity)",
            ),
            JurisdictionRule(
                jurisdiction_code="APAC",
                rule_id="APAC-006",
                rule_name="Australia — ACL Consumer Guarantees",
                description="Australian Consumer Law provides mandatory consumer "
                "guarantees that cannot be excluded.",
                applies_to_categories=["liability_limitation", "compliance"],
                risk_modifier=0.8,
                citation="Competition and Consumer Act 2010, Schedule 2 (ACL)",
            ),
        ]

    def get_rules_for_jurisdiction(
        self, jurisdiction_code: str
    ) -> List[JurisdictionRule]:
        """Get all rules for a specific jurisdiction.

        Args:
            jurisdiction_code: US, EU, UK, or APAC.

        Returns:
            List of JurisdictionRule for that jurisdiction.
        """
        return self._rules.get(jurisdiction_code.upper(), [])

    def get_rules_for_category(
        self, category_id: str, jurisdiction_code: Optional[str] = None
    ) -> List[JurisdictionRule]:
        """Get rules applicable to a specific risk category.

        Args:
            category_id: The risk category identifier.
            jurisdiction_code: Optional jurisdiction filter.

        Returns:
            List of matching JurisdictionRule.
        """
        matching: List[JurisdictionRule] = []
        jurisdictions = (
            [jurisdiction_code.upper()]
            if jurisdiction_code
            else list(self._rules.keys())
        )
        for j_code in jurisdictions:
            for rule in self._rules.get(j_code, []):
                if category_id in rule.applies_to_categories:
                    matching.append(rule)
        return matching

    def get_risk_modifier(
        self, category_id: str, jurisdiction_code: str
    ) -> float:
        """Get the cumulative risk modifier for a category and jurisdiction.

        Args:
            category_id: The risk category identifier.
            jurisdiction_code: US, EU, UK, or APAC.

        Returns:
            Cumulative risk modifier (sum of all applicable rules).
        """
        rules = self.get_rules_for_category(category_id, jurisdiction_code)
        return sum(rule.risk_modifier for rule in rules)

    def evaluate_clause(
        self,
        clause_text: str,
        category_id: str,
        jurisdictions: List[str],
        governing_law: Optional[str] = None,
    ) -> List[JurisdictionalConsideration]:
        """Evaluate a clause against jurisdiction-specific rules.

        Args:
            clause_text: The clause text to evaluate.
            category_id: The risk category.
            jurisdictions: List of jurisdictions to evaluate (US, EU, UK, APAC).
            governing_law: Optional governing law clause text.

        Returns:
            List of JurisdictionalConsideration with risk modifiers.
        """
        considerations: List[JurisdictionalConsideration] = []

        for j_code in jurisdictions:
            rules = self.get_rules_for_category(category_id, j_code)
            for rule in rules:
                # Check if governing law mentions this jurisdiction
                relevance = 1.0
                if governing_law and j_code == "US":
                    if "new york" in governing_law.lower():
                        relevance = 1.5
                    elif "california" in governing_law.lower():
                        relevance = 1.3

                consideration = JurisdictionalConsideration(
                    jurisdiction=rule.jurisdiction_code,
                    rule_reference=f"{rule.rule_id}: {rule.rule_name}",
                    risk_modifier=round(rule.risk_modifier * relevance, 2),
                    explanation=(
                        f"{rule.description} "
                        f"(Citation: {rule.citation})"
                    ),
                )
                considerations.append(consideration)

        return considerations

    def get_all_jurisdictions(self) -> List[str]:
        """Get all supported jurisdiction codes.

        Returns:
            List of jurisdiction codes (US, EU, UK, APAC).
        """
        return list(self._rules.keys())

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all jurisdiction rules.

        Returns:
            Dict with rule counts per jurisdiction.
        """
        return {
            j_code: {
                "total_rules": len(rules),
                "categories_covered": list(
                    set(
                        cat
                        for rule in rules
                        for cat in rule.applies_to_categories
                    )
                ),
            }
            for j_code, rules in self._rules.items()
        }
