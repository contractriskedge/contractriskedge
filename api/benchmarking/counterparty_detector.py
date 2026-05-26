"""Enterprise vs SMB vs Government vs Non-profit counterparty detection.

Detects the type of counterparty (enterprise, SMB, government, non-profit)
from contract text using keyword patterns and entity recognition.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .models import CounterpartyType

logger = logging.getLogger(__name__)

# Keywords associated with each counterparty type
COUNTERPARTY_KEYWORDS: Dict[CounterpartyType, List[str]] = {
    CounterpartyType.ENTERPRISE: [
        "corporation", "inc", "incorporated", "ltd", "limited", "corp",
        "holdings", "group", "global", "international", "enterprise",
        "fortune 500", "publicly traded", "nyse", "nasdaq", "multinational",
        "subsidiary", "parent company", "board of directors", "shareholder",
        "annual revenue", "market cap", "institutional",
    ],
    CounterpartyType.SMB: [
        "llc", "llp", "small business", "startup", "founder", "entrepreneur",
        "sole proprietor", "dba", "pLLC", "professional corporation",
        "boutique", "independent", "freelancer", "consultant", "agency",
        "family-owned", "locally owned", "small team",
    ],
    CounterpartyType.GOVERNMENT: [
        "government", "federal", "state of", "united states", "agency",
        "department of", "municipal", "county of", "city of", "public entity",
        "government contractor", "rfp", "solicitation", "g sa", "f ar",
        "sovereign", "public sector", "government agency", "regulation",
        "compliance", "public trust", "official", "government-issued",
    ],
    CounterpartyType.NON_PROFIT: [
        "non-profit", "nonprofit", "501(c)", "charity", "charitable",
        "foundation", "endowment", "philanthropic", "tax-exempt",
        "public charity", "ngo", "non-governmental", "social enterprise",
        "mission-driven", "community organization", "volunteer",
        "grant", "donor", "tax deductible",
    ],
}

# High-precision patterns for each type
HIGH_CONFIDENCE_PATTERNS: Dict[CounterpartyType, List[str]] = {
    CounterpartyType.ENTERPRISE: [
        r'\b(?:NYSE|NASDAQ)\s*:',
        r'\bFortune\s+\d{1,3}\b',
        r'\b(?:Annual|Yearly)\s+(?:Revenue|Income|Turnover)\s+(?:of|:)\s*\$[\d,]+[MBK]',
        r'\bPublicly\s+(?:Traded|Held)\b',
    ],
    CounterpartyType.GOVERNMENT: [
        r'\b(?:U\.?S\.?|United\s+States)\s+(?:Government|Federal|Agency)\b',
        r'\bRF[PQ]\s+(?:No\.|Number|#)\s*\d+',
        r'\bFAR\s+(?:Part\s+)?\d+',
        r'\b(?:State|County|City|Town|Village)\s+of\s+[A-Z]',
    ],
    CounterpartyType.NON_PROFIT: [
        r'\b501\(c\)\s*\(?\d{1,2}\)?',
        r'\bSection\s+501\(c\)',
        r'\bTax-Exempt\s+(?:Status|Organization|Entity)\b',
    ],
    CounterpartyType.SMB: [
        r'\bSole\s+(?:Proprietor|Proprietorship)\b',
        r'\bDBA\s+',
        r'\bStartup\s+(?:Company|Venture)\b',
    ],
}


class CounterpartyDetector:
    """Detects counterparty type from contract text.

    Uses keyword matching and high-precision patterns to classify
    counterparties as enterprise, SMB, government, or non-profit.

    Usage:
        detector = CounterpartyDetector()
        ctype, confidence = detector.detect(contract_text)
    """

    def detect(
        self, text: str
    ) -> Tuple[CounterpartyType, float]:
        """Detect the counterparty type from contract text.

        Args:
            text: The contract text to analyze.

        Returns:
            Tuple of (CounterpartyType, confidence_score).
        """
        if not text.strip():
            return CounterpartyType.ENTERPRISE, 0.0

        text_lower = text.lower()
        scores: Dict[CounterpartyType, float] = {}

        for ctype in CounterpartyType:
            score = 0.0

            # High-precision pattern matches
            patterns = HIGH_CONFIDENCE_PATTERNS.get(ctype, [])
            for pattern in patterns:
                if re.search(pattern, text):
                    score += 3.0  # High weight for precise patterns

            # Keyword matches
            keywords = COUNTERPARTY_KEYWORDS.get(ctype, [])
            for keyword in keywords:
                occurrences = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                score += occurrences * 0.5

            if score > 0:
                scores[ctype] = score

        if not scores:
            # Default to enterprise with low confidence
            return CounterpartyType.ENTERPRISE, 0.3

        # Find best match
        best_type = max(scores, key=scores.get)
        total_score = sum(scores.values())

        # Compute confidence
        confidence = min(0.95, scores[best_type] / max(1.0, total_score))

        return best_type, round(confidence, 4)

    def detect_with_distribution(
        self, text: str
    ) -> Dict[str, float]:
        """Get confidence scores for all counterparty types.

        Args:
            text: The contract text.

        Returns:
            Dict mapping counterparty type names to confidence scores.
        """
        result: Dict[str, float] = {}
        text_lower = text.lower()

        for ctype in CounterpartyType:
            score = 0.0

            patterns = HIGH_CONFIDENCE_PATTERNS.get(ctype, [])
            for pattern in patterns:
                if re.search(pattern, text):
                    score += 3.0

            keywords = COUNTERPARTY_KEYWORDS.get(ctype, [])
            for keyword in keywords:
                occurrences = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                score += occurrences * 0.5

            result[ctype.value] = score

        # Normalize
        total = sum(result.values())
        if total > 0:
            result = {k: round(v / total, 4) for k, v in result.items()}
        else:
            result = {ctype.value: 0.25 for ctype in CounterpartyType}

        return result
