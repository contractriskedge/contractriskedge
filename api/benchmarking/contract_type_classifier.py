"""Map contract text to 15 standard contract types.

Classifies contracts into one of 15 standardized types based on
text analysis of the contract content and structure.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .models import ContractType

logger = logging.getLogger(__name__)

# Keywords and patterns for each contract type
CONTRACT_TYPE_SIGNALS: Dict[ContractType, Dict[str, Any]] = {
    ContractType.SaaS_AGREEMENT: {
        "keywords": [
            "saas", "software as a service", "subscription", "cloud service",
            "platform service", "hosted service", "online service",
            "service level agreement", "uptime", "service credit",
        ],
        "patterns": [
            r'(?i)subscription\s+(?:fee|service|plan|term)',
            r'(?i)monthly\s+(?:recurring|subscription)\s+(?:fee|revenue|charge)',
            r'(?i)service\s+level\s+(?:agreement|objective|credit)',
        ],
        "weight": 1.0,
    },
    ContractType.SOFTWARE_LICENSE: {
        "keywords": [
            "license", "licensed", "end user", "perpetual", "seat",
            "concurrent user", "named user", "license fee", "deployment",
            "on-premise", "on premises", "installation",
        ],
        "patterns": [
            r'(?i)license\s+(?:grant|term|fee|agreement)',
            r'(?i)perpetual\s+license',
            r'(?i)concurrent\s+user',
            r'(?i)named\s+user\s+license',
        ],
        "weight": 1.0,
    },
    ContractType.PROFESSIONAL_SERVICES: {
        "keywords": [
            "professional services", "consulting", "statement of work",
            "time and materials", "fixed fee", "deliverable", "milestone",
            "project", "engagement", "work order", "resource",
        ],
        "patterns": [
            r'(?i)professional\s+services\s+(?:agreement|contract)',
            r'(?i)time\s+and\s+(?:materials|expenses)',
            r'(?i)statement\s+of\s+work',
        ],
        "weight": 1.0,
    },
    ContractType.EMPLOYMENT_AGREEMENT: {
        "keywords": [
            "employee", "employment", "compensation", "salary", "bonus",
            "benefits", "vacation", "termination", "notice period",
            "non-compete", "non-solicit", "at-will", "hire",
        ],
        "patterns": [
            r'(?i)at-will\s+employment',
            r'(?i)base\s+(?:salary|compensation)',
            r'(?i)employee\s+(?:benefits|stock\s+options)',
        ],
        "weight": 1.0,
    },
    ContractType.NON_DISCLOSURE: {
        "keywords": [
            "non-disclosure", "nondisclosure", "confidential information",
            "confidentiality", "nda", "proprietary information",
            "trade secret", "disclosing party", "receiving party",
        ],
        "patterns": [
            r'(?i)non[- ]disclosure\s+(?:agreement|contract)',
            r'(?i)confidential\s+information\s+(?:means|includes)',
        ],
        "weight": 1.0,
    },
    ContractType.SUPPLY_AGREEMENT: {
        "keywords": [
            "supply", "supplier", "vendor", "purchase order", "procurement",
            "inventory", "delivery", "shipment", "goods", "product",
            "raw material", "component", "manufacturing",
        ],
        "patterns": [
            r'(?i)supply\s+(?:agreement|contract|chain)',
            r'(?i)purchase\s+order\s+(?:terms|conditions)',
        ],
        "weight": 1.0,
    },
    ContractType.DISTRIBUTION_AGREEMENT: {
        "keywords": [
            "distributor", "distribution", "reseller", "channel partner",
            "territory", "exclusive", "non-exclusive", "minimum purchase",
            "resale", "wholesale", "dealer",
        ],
        "patterns": [
            r'(?i)distribution\s+(?:agreement|rights|channel)',
            r'(?i)reseller\s+(?:agreement|program)',
            r'(?i)channel\s+partner',
        ],
        "weight": 1.0,
    },
    ContractType.PARTNERSHIP_AGREEMENT: {
        "keywords": [
            "partnership", "partner", "joint venture", "strategic alliance",
            "collaboration", "cooperation", "mutual", "profit sharing",
            "joint marketing", "co-marketing",
        ],
        "patterns": [
            r'(?i)partnership\s+(?:agreement|contract)',
            r'(?i)joint\s+venture\s+(?:agreement|contract)',
        ],
        "weight": 1.0,
    },
    ContractType.JOINT_VENTURE: {
        "keywords": [
            "joint venture", "jointly", "co-venture", "special purpose vehicle",
            "spv", "consortium", "collaboration agreement",
        ],
        "patterns": [
            r'(?i)joint\s+venture\s+(?:agreement|company|entity)',
            r'(?i)special\s+purpose\s+(?:vehicle|entity)',
        ],
        "weight": 1.0,
    },
    ContractType.LOAN_AGREEMENT: {
        "keywords": [
            "loan", "borrower", "lender", "principal", "interest", "repayment",
            "amortization", "maturity", "covenant", "default", "security",
            "collateral", "promissory", "credit facility",
        ],
        "patterns": [
            r'(?i)loan\s+(?:agreement|contract|facility)',
            r'(?i)promissory\s+note',
            r'(?i)credit\s+(?:facility|agreement)',
        ],
        "weight": 1.0,
    },
    ContractType.LEASE_AGREEMENT: {
        "keywords": [
            "lease", "lessor", "lessee", "rent", "premises", "tenant",
            "landlord", "security deposit", "maintenance", "sublease",
            "rental", "property",
        ],
        "patterns": [
            r'(?i)lease\s+(?:agreement|contract|term)',
            r'(?i)rental\s+(?:agreement|contract)',
        ],
        "weight": 1.0,
    },
    ContractType.MERGER_AGREEMENT: {
        "keywords": [
            "merger", "acquisition", "acquire", "purchase", "share exchange",
            "stock", "equity", "closing", "representation", "warranty",
            "indemnification", "escrow", "earn-out",
        ],
        "patterns": [
            r'(?i)merger\s+(?:agreement|contract)',
            r'(?i)share\s+(?:purchase|exchange)\s+(?:agreement|contract)',
            r'(?i)asset\s+purchase\s+(?:agreement|contract)',
        ],
        "weight": 1.0,
    },
    ContractType.SERVICE_LEVEL: {
        "keywords": [
            "service level", "sla", "uptime", "availability", "response time",
            "resolution time", "service credit", "penalty", "performance metric",
            "kpi", "service standard",
        ],
        "patterns": [
            r'(?i)service\s+level\s+(?:agreement|objective|commitment|target)',
            r'(?i)service\s+credit',
        ],
        "weight": 1.0,
    },
    ContractType.MASTER_SERVICES: {
        "keywords": [
            "master services", "msa", "master agreement", "statement of work",
            "work order", "service provider", "services",
        ],
        "patterns": [
            r'(?i)master\s+services\s+(?:agreement|contract)',
            r'(?i)master\s+(?:agreement|services)\s+agreement',
        ],
        "weight": 1.0,
    },
    ContractType.STATEMENT_OF_WORK: {
        "keywords": [
            "statement of work", "sow", "scope of work", "deliverable",
            "timeline", "milestone", "acceptance criteria", "project plan",
        ],
        "patterns": [
            r'(?i)statement\s+of\s+work',
            r'(?i)scope\s+of\s+work',
            r'(?i)work\s+order\s+(?:number|#)',
        ],
        "weight": 1.0,
    },
    ContractType.OTHER: {
        "keywords": [],
        "patterns": [],
        "weight": 0.1,
    },
}


class ContractTypeClassifier:
    """Classifies contracts into 15 standardized types.

    Uses keyword matching and pattern detection to identify the
    contract type from the document text.

    Usage:
        classifier = ContractTypeClassifier()
        ctype, confidence = classifier.classify(contract_text)
    """

    def classify(
        self, text: str
    ) -> Tuple[ContractType, float]:
        """Classify a contract into a standard type.

        Args:
            text: The contract text to classify.

        Returns:
            Tuple of (ContractType, confidence_score).
        """
        if not text.strip():
            return ContractType.OTHER, 0.0

        text_lower = text.lower()
        scores: Dict[ContractType, float] = {}

        for ctype, signals in CONTRACT_TYPE_SIGNALS.items():
            score = 0.0

            # Keyword matches
            for keyword in signals["keywords"]:
                occurrences = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                score += occurrences * signals["weight"]

            # Pattern matches
            for pattern in signals["patterns"]:
                if re.search(pattern, text):
                    score += 3.0 * signals["weight"]  # Higher weight for patterns

            if score > 0:
                scores[ctype] = score

        if not scores:
            return ContractType.OTHER, 0.2

        best_type = max(scores, key=scores.get)
        total_score = sum(scores.values())

        # Normalize confidence
        confidence = min(0.95, scores[best_type] / max(1.0, total_score))

        return best_type, round(confidence, 4)

    def classify_with_distribution(
        self, text: str
    ) -> Dict[str, float]:
        """Get confidence scores for all contract types.

        Args:
            text: The contract text.

        Returns:
            Dict mapping contract type names to confidence scores.
        """
        text_lower = text.lower()
        raw_scores: Dict[str, float] = {}

        for ctype, signals in CONTRACT_TYPE_SIGNALS.items():
            score = 0.0

            for keyword in signals["keywords"]:
                occurrences = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                score += occurrences * signals["weight"]

            for pattern in signals["patterns"]:
                if re.search(pattern, text):
                    score += 3.0 * signals["weight"]

            raw_scores[ctype.value] = score

        # Normalize
        total = sum(raw_scores.values())
        if total > 0:
            return {
                ct: round(score / total, 4)
                for ct, score in raw_scores.items()
            }
        else:
            return {ct.value: 1.0 / len(ContractType) for ct in ContractType}

    def get_supported_types(self) -> List[str]:
        """Get the list of supported contract types.

        Returns:
            List of contract type name strings.
        """
        return [ct.value for ct in ContractType]
