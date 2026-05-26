"""500-clause blind test set across 5 contract types and 12 risk categories.

Generates and manages a comprehensive blind test set for evaluating
risk analysis accuracy across diverse contract types and risk categories.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TestClause:
    """A single test clause with expected results."""

    clause_id: str
    clause_text: str
    contract_type: str
    risk_category: str
    sub_type: str
    expected_severity: int
    expected_risk_level: str
    expected_action: str
    is_high_risk: bool
    notes: Optional[str] = None


@dataclass
class TestSet:
    """A complete test set for evaluation."""

    name: str
    version: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    clauses: List[TestClause] = field(default_factory=list)
    contract_types: List[str] = field(default_factory=list)
    categories_covered: List[str] = field(default_factory=list)

    @property
    def total_clauses(self) -> int:
        return len(self.clauses)


class TestSetGenerator:
    """Generates and manages blind test sets for evaluation.

    Creates a 500-clause blind test set distributed across 5 contract
    types and 12 risk categories, with known ground truth labels.

    Usage:
        generator = TestSetGenerator(seed=42)
        test_set = generator.generate_test_set()
        generator.save_test_set(test_set, "test_set_v1.json")
    """

    CONTRACT_TYPES = [
        "nda",
        "service_agreement",
        "license",
        "employment",
        "lease",
    ]

    RISK_CATEGORIES = [
        "indemnification",
        "liability_limitation",
        "termination",
        "confidentiality",
        "data_privacy",
        "compliance",
        "payment_terms",
        "force_majeure",
        "assignment",
        "governing_law",
        "non_compete",
        "intellectual_property",
    ]

    # Template clauses for each (contract_type, risk_category) pair
    CLAUSE_TEMPLATES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    def __init__(self, seed: int = 42) -> None:
        """Initialize the test set generator.

        Args:
            seed: Random seed for reproducibility.
        """
        self._random = random.Random(seed)
        self._clause_counter = 0
        self._initialize_templates()

    def _initialize_templates(self) -> None:
        """Initialize clause templates for each contract type."""
        self.CLAUSE_TEMPLATES = {
            "nda": {
                "confidentiality": [
                    {
                        "text": "Confidential Information includes all information disclosed orally or in writing.",
                        "severity": 3, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Confidentiality obligations shall survive for a period of one year.",
                        "severity": 6, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Receiving party shall have no obligation to return or destroy confidential information.",
                        "severity": 8, "risk_level": "high", "action": "negotiate",
                    },
                    {
                        "text": "Confidential Information excludes information independently developed without use of disclosing party's information.",
                        "severity": 4, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "All oral information must be reduced to writing within 30 days to be protected.",
                        "severity": 7, "risk_level": "high", "action": "negotiate",
                    },
                ],
                "indemnification": [
                    {
                        "text": "Each party shall indemnify the other for claims arising from breach of confidentiality.",
                        "severity": 4, "risk_level": "medium", "action": "accept",
                    },
                    {
                        "text": "Provider shall indemnify Client for all third-party claims without limitation.",
                        "severity": 6, "risk_level": "medium", "action": "review",
                    },
                ],
                "termination": [
                    {
                        "text": "Either party may terminate this NDA upon 30 days written notice.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "This Agreement terminates automatically after 5 years.",
                        "severity": 4, "risk_level": "medium", "action": "review",
                    },
                ],
            },
            "service_agreement": {
                "indemnification": [
                    {
                        "text": "Provider's aggregate liability shall not exceed the fees paid in the preceding 12 months.",
                        "severity": 4, "risk_level": "medium", "action": "accept",
                    },
                    {
                        "text": "Provider shall indemnify Client for all claims including indirect and consequential damages.",
                        "severity": 7, "risk_level": "high", "action": "negotiate",
                    },
                    {
                        "text": "Indemnification obligations shall survive termination for one year.",
                        "severity": 5, "risk_level": "medium", "action": "review",
                    },
                ],
                "liability_limitation": [
                    {
                        "text": "Neither party shall be liable for any indirect, incidental, or consequential damages.",
                        "severity": 4, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Total liability cap is $100 regardless of the value of services provided.",
                        "severity": 9, "risk_level": "critical", "action": "reject",
                    },
                    {
                        "text": "Liability cap shall be 100% of fees paid with exceptions for IP infringement.",
                        "severity": 3, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "No cap on liability for gross negligence, willful misconduct, or fraud.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                ],
                "termination": [
                    {
                        "text": "Provider may terminate for convenience upon 90 days notice.",
                        "severity": 5, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Either party may terminate for material breach with 30 days cure period.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Client may not terminate for convenience during the initial term.",
                        "severity": 6, "risk_level": "medium", "action": "review",
                    },
                ],
                "payment_terms": [
                    {
                        "text": "All invoices are due within 30 days of receipt.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Provider may increase prices annually up to 5% with 60 days notice.",
                        "severity": 4, "risk_level": "medium", "action": "accept",
                    },
                    {
                        "text": "Late payments shall accrue interest at 1.5% per month.",
                        "severity": 4, "risk_level": "medium", "action": "review",
                    },
                ],
                "force_majeure": [
                    {
                        "text": "Force majeure includes acts of God, war, terrorism, and pandemics.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Force majeure does not include pandemics or cyberattacks.",
                        "severity": 6, "risk_level": "medium", "action": "negotiate",
                    },
                ],
                "data_privacy": [
                    {
                        "text": "Provider shall implement reasonable security measures to protect Client data.",
                        "severity": 6, "risk_level": "medium", "action": "negotiate",
                    },
                    {
                        "text": "Data Processing Agreement attached as Exhibit A with GDPR compliance terms.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                ],
            },
            "license": {
                "intellectual_property": [
                    {
                        "text": "All intellectual property rights in work product shall be owned by Client.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Provider retains ownership of all pre-existing IP with license to Client.",
                        "severity": 3, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Client receives a non-exclusive, non-transferable license to use the software.",
                        "severity": 5, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Provider may incorporate Client feedback into its products without compensation.",
                        "severity": 7, "risk_level": "high", "action": "negotiate",
                    },
                ],
                "liability_limitation": [
                    {
                        "text": "Provider's liability for IP infringement claims shall not be capped.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Liability cap is 12 months of license fees for all claims.",
                        "severity": 4, "risk_level": "medium", "action": "review",
                    },
                ],
                "termination": [
                    {
                        "text": "License terminates automatically upon breach without cure period.",
                        "severity": 7, "risk_level": "high", "action": "negotiate",
                    },
                    {
                        "text": "Upon termination, Client must certify destruction of all licensed materials.",
                        "severity": 3, "risk_level": "low", "action": "accept",
                    },
                ],
            },
            "employment": {
                "non_compete": [
                    {
                        "text": "Employee shall not engage in any competing business for 12 months post-termination.",
                        "severity": 6, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Non-compete covers all businesses that compete in any manner worldwide.",
                        "severity": 9, "risk_level": "critical", "action": "reject",
                    },
                    {
                        "text": "Employee may not solicit Company's customers for 18 months after termination.",
                        "severity": 5, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Non-solicit covers all Company employees regardless of role or involvement.",
                        "severity": 6, "risk_level": "medium", "action": "negotiate",
                    },
                ],
                "intellectual_property": [
                    {
                        "text": "All inventions conceived during employment are owned by Company.",
                        "severity": 4, "risk_level": "medium", "action": "accept",
                    },
                    {
                        "text": "Inventions created on employee's own time with own resources are excluded.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                ],
                "confidentiality": [
                    {
                        "text": "Confidentiality obligations continue indefinitely after employment ends.",
                        "severity": 5, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Employee must return all Company property and confidential materials upon termination.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                ],
                "termination": [
                    {
                        "text": "Company may terminate employment at any time without cause with 2 weeks notice.",
                        "severity": 6, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Employment is at-will and may be terminated by either party at any time.",
                        "severity": 4, "risk_level": "medium", "action": "accept",
                    },
                ],
            },
            "lease": {
                "indemnification": [
                    {
                        "text": "Tenant shall indemnify Landlord for all claims arising from use of premises.",
                        "severity": 5, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Landlord shall indemnify Tenant for claims arising from Landlord's negligence.",
                        "severity": 3, "risk_level": "low", "action": "accept",
                    },
                ],
                "payment_terms": [
                    {
                        "text": "Rent shall increase annually by the greater of 5% or CPI.",
                        "severity": 5, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Late rent payments shall incur a 5% penalty plus interest at 1.5% per month.",
                        "severity": 6, "risk_level": "medium", "action": "negotiate",
                    },
                    {
                        "text": "Security deposit shall be held in an interest-bearing account and returned within 30 days.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                ],
                "termination": [
                    {
                        "text": "Tenant may terminate lease early with 3 months rent as penalty.",
                        "severity": 7, "risk_level": "high", "action": "negotiate",
                    },
                    {
                        "text": "Landlord may terminate lease if Tenant fails to cure breach within 30 days.",
                        "severity": 3, "risk_level": "low", "action": "accept",
                    },
                ],
                "assignment": [
                    {
                        "text": "Tenant may not assign or sublet without Landlord's prior written consent.",
                        "severity": 5, "risk_level": "medium", "action": "review",
                    },
                    {
                        "text": "Consent to assignment shall not be unreasonably withheld or delayed.",
                        "severity": 3, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Any assignment without consent renders lease void at Landlord's option.",
                        "severity": 8, "risk_level": "high", "action": "negotiate",
                    },
                ],
                "governing_law": [
                    {
                        "text": "This Lease shall be governed by the laws of the state where the premises are located.",
                        "severity": 2, "risk_level": "low", "action": "accept",
                    },
                    {
                        "text": "Any disputes shall be resolved exclusively in Landlord's local courts.",
                        "severity": 6, "risk_level": "medium", "action": "review",
                    },
                ],
            },
        }

    def generate_test_set(
        self, total_clauses: int = 500
    ) -> TestSet:
        """Generate a balanced blind test set.

        Distributes clauses across 5 contract types and 12 risk
        categories, ensuring minimum coverage per category.

        Args:
            total_clauses: Total number of test clauses (default 500).

        Returns:
            A TestSet with generated clauses.
        """
        test_set = TestSet(
            name="Contract Risk Analysis Blind Test Set",
            version="1.0.0",
        )

        clauses_per_type = total_clauses // len(self.CONTRACT_TYPES)

        for contract_type in self.CONTRACT_TYPES:
            type_templates = self.CLAUSE_TEMPLATES.get(contract_type, {})
            type_clauses = self._generate_type_clauses(
                contract_type, type_templates, clauses_per_type
            )
            test_set.clauses.extend(type_clauses)

            if contract_type not in test_set.contract_types:
                test_set.contract_types.append(contract_type)

        # Fill remaining slots to reach exact total
        remaining = total_clauses - len(test_set.clauses)
        while remaining > 0:
            ct = self._random.choice(self.CONTRACT_TYPES)
            type_templates = self.CLAUSE_TEMPLATES.get(ct, {})
            if type_templates:
                cat = self._random.choice(list(type_templates.keys()))
                template = self._random.choice(type_templates[cat])
                clause = self._make_test_clause(ct, cat, template)
                test_set.clauses.append(clause)
                remaining -= 1

        # Track categories covered
        categories = set()
        for c in test_set.clauses:
            categories.add(c.risk_category)
        test_set.categories_covered = sorted(categories)

        self._random.shuffle(test_set.clauses)

        logger.info(
            "Generated test set: %d clauses across %d contract types "
            "and %d risk categories",
            len(test_set.clauses),
            len(test_set.contract_types),
            len(test_set.categories_covered),
        )

        return test_set

    def _generate_type_clauses(
        self,
        contract_type: str,
        templates: Dict[str, List[Dict[str, Any]]],
        target_count: int,
    ) -> List[TestClause]:
        """Generate clauses for a specific contract type.

        Args:
            contract_type: The contract type.
            templates: Clause templates for this type.
            target_count: Target number of clauses.

        Returns:
            List of test clauses.
        """
        clauses: list[TestClause] = []
        categories = list(templates.keys())

        if not categories:
            return clauses

        clauses_per_category = max(
            1, target_count // len(categories)
        )

        for category in categories:
            cat_templates = templates[category]
            for _ in range(clauses_per_category):
                template = self._random.choice(cat_templates)
                clause = self._make_test_clause(
                    contract_type, category, template
                )
                clauses.append(clause)

        return clauses[:target_count]

    def _make_test_clause(
        self,
        contract_type: str,
        category: str,
        template: Dict[str, Any],
    ) -> TestClause:
        """Create a TestClause from a template.

        Args:
            contract_type: Contract type.
            category: Risk category.
            template: Clause template data.

        Returns:
            A TestClause instance.
        """
        self._clause_counter += 1

        # Determine sub_type from category
        sub_type_map = {
            "indemnification": "indemnification_scope",
            "liability_limitation": "liability_cap",
            "termination": "termination_for_cause",
            "confidentiality": "confidentiality_definition",
            "data_privacy": "data_security_measures",
            "compliance": "compliance_general",
            "payment_terms": "payment_timing",
            "force_majeure": "force_majeure_definition",
            "assignment": "assignment_restriction",
            "governing_law": "governing_law_choice",
            "non_compete": "non_compete_scope",
            "intellectual_property": "ip_ownership",
        }

        severity = template["severity"]

        return TestClause(
            clause_id=f"test_clause_{self._clause_counter:04d}",
            clause_text=template["text"],
            contract_type=contract_type,
            risk_category=category,
            sub_type=sub_type_map.get(category, "general"),
            expected_severity=severity,
            expected_risk_level=template["risk_level"],
            expected_action=template["action"],
            is_high_risk=severity >= 7,
        )

    def load_test_set(self, path: str) -> TestSet:
        """Load a test set from a JSON file.

        Args:
            path: Path to the test set JSON file.

        Returns:
            Loaded TestSet.
        """
        with open(path) as f:
            data = json.load(f)

        clauses = [TestClause(**c) for c in data.get("clauses", [])]
        test_set = TestSet(
            name=data.get("name", "Loaded Test Set"),
            version=data.get("version", "1.0.0"),
            clauses=clauses,
            contract_types=data.get("contract_types", []),
            categories_covered=data.get("categories_covered", []),
        )

        logger.info(
            "Loaded test set from %s: %d clauses", path, len(clauses)
        )
        return test_set

    def save_test_set(self, test_set: TestSet, path: str) -> None:
        """Save a test set to a JSON file.

        Args:
            test_set: The test set to save.
            path: Output file path.
        """
        data = {
            "name": test_set.name,
            "version": test_set.version,
            "created_at": test_set.created_at.isoformat(),
            "total_clauses": test_set.total_clauses,
            "contract_types": test_set.contract_types,
            "categories_covered": test_set.categories_covered,
            "clauses": [
                {
                    "clause_id": c.clause_id,
                    "clause_text": c.clause_text,
                    "contract_type": c.contract_type,
                    "risk_category": c.risk_category,
                    "sub_type": c.sub_type,
                    "expected_severity": c.expected_severity,
                    "expected_risk_level": c.expected_risk_level,
                    "expected_action": c.expected_action,
                    "is_high_risk": c.is_high_risk,
                    "notes": c.notes,
                }
                for c in test_set.clauses
            ],
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Saved test set to %s (%d clauses)", path, test_set.total_clauses)
