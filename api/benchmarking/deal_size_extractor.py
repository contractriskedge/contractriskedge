"""NLP extractor for contract value from text patterns.

Extracts deal size / contract value information from contract text
using regex patterns and NLP-based number extraction.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Regex patterns for deal size extraction
DEAL_SIZE_PATTERNS: List[Tuple[str, str]] = [
    # "Contract Value: $X"
    (r'(?i)(?:contract|deal|transaction|agreement)\s*(?:value|amount|price|size|worth|consideration)\s*(?::|is|of|:)\s*\$?([\d,]+(?:\.\d{2})?)\s*(million|billion|thousand|M|B|K|m|b|k)?', "explicit_value"),
    # "Total consideration of $X"
    (r'(?i)total\s*(?:consideration|contract\s*value|purchase\s*price|fees?)\s*(?::|is|of|:)?\s*\$?([\d,]+(?:\.\d{2})?)\s*(million|billion|thousand|M|B|K|m|b|k)?', "total_consideration"),
    # "Annual fees of $X"
    (r'(?i)annual\s*(?:fees?|subscription|license|payment|revenue)\s*(?::|is|of|:)?\s*\$?([\d,]+(?:\.\d{2})?)\s*(million|billion|thousand|M|B|K|m|b|k)?', "annual_value"),
    # "$X per year/month"
    (r'(?i)\$?([\d,]+(?:\.\d{2})?)\s*(million|billion|thousand|M|B|K|m|b|k)?\s*per\s*(year|annum|month|quarter)', "periodic_value"),
    # "X-year agreement worth $Y"
    (r'(?i)(?:\d+\s*(?:-|to)\s*)?year\s*(?:agreement|contract|term|deal)\s*(?:worth|valued\s*at|with\s*value\s*of)\s*\$?([\d,]+(?:\.\d{2})?)\s*(million|billion|thousand|M|B|K|m|b|k)?', "multi_year_value"),
    # "not to exceed $X"
    (r'(?i)not\s*to\s*exceed\s*\$?([\d,]+(?:\.\d{2})?)\s*(million|billion|thousand|M|B|K|m|b|k)?', "not_to_exceed"),
    # "$X minimum"
    (r'(?i)\$?([\d,]+(?:\.\d{2})?)\s*(million|billion|thousand|M|B|K|m|b|k)?\s*minimum', "minimum_commitment"),
]

# Multipliers for magnitude suffixes
MAGNITUDE_MULTIPLIERS: Dict[str, float] = {
    "thousand": 1_000,
    "k": 1_000,
    "million": 1_000_000,
    "m": 1_000_000,
    "billion": 1_000_000_000,
    "b": 1_000_000_000,
}


@dataclass
class DealSizeResult:
    """Result of deal size extraction."""

    extracted_value: Optional[float]  # In dollars
    deal_size_tier: str  # small, medium, large, enterprise, mega
    confidence: float
    extraction_method: str
    raw_match: str
    range_low: Optional[float] = None
    range_high: Optional[float] = None


class DealSizeExtractor:
    """Extracts deal size/contract value from text patterns.

    Uses regex patterns to find contract value mentions and classifies
    them into deal size tiers.

    Usage:
        extractor = DealSizeExtractor()
        result = extractor.extract(contract_text)
        tier = result.deal_size_tier
    """

    def extract(
        self, text: str
    ) -> Optional[DealSizeResult]:
        """Extract deal size from contract text.

        Args:
            text: The contract text to analyze.

        Returns:
            DealSizeResult if a value is found, None otherwise.
        """
        if not text.strip():
            return None

        best_match: Optional[DealSizeResult] = None
        best_confidence = 0.0

        for pattern, method in DEAL_SIZE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    result = self._parse_match(match, method)
                    if result and result.confidence > best_confidence:
                        best_match = result
                        best_confidence = result.confidence
                except (ValueError, IndexError):
                    continue

        return best_match

    @staticmethod
    def _parse_match(
        match: re.Match,
        method: str,
    ) -> Optional[DealSizeResult]:
        """Parse a regex match into a DealSizeResult.

        Args:
            match: The regex match object.
            method: The extraction method name.

        Returns:
            DealSizeResult or None if parsing fails.
        """
        groups = match.groups()
        if not groups or not groups[0]:
            return None

        try:
            raw_number = groups[0].replace(",", "")
            value = float(raw_number)
        except (ValueError, IndexError):
            return None

        # Apply magnitude multiplier
        magnitude = groups[1].lower() if len(groups) > 1 and groups[1] else ""
        multiplier = MAGNITUDE_MULTIPLIERS.get(magnitude, 1.0)
        total_value = value * multiplier

        # Determine confidence based on extraction method
        confidence_map = {
            "explicit_value": 0.9,
            "total_consideration": 0.85,
            "annual_value": 0.7,
            "periodic_value": 0.65,
            "multi_year_value": 0.75,
            "not_to_exceed": 0.6,
            "minimum_commitment": 0.55,
        }
        confidence = confidence_map.get(method, 0.5)

        # Determine deal size tier
        tier = DealSizeExtractor._classify_tier(total_value)

        return DealSizeResult(
            extracted_value=total_value,
            deal_size_tier=tier,
            confidence=confidence,
            extraction_method=method,
            raw_match=match.group(0),
        )

    @staticmethod
    def _classify_tier(value: float) -> str:
        """Classify a dollar value into a deal size tier.

        Args:
            value: The dollar value.

        Returns:
            Deal size tier string.
        """
        if value < 100_000:
            return "small"
        elif value < 1_000_000:
            return "medium"
        elif value < 10_000_000:
            return "large"
        elif value < 100_000_000:
            return "enterprise"
        else:
            return "mega"

    def extract_all(self, text: str) -> List[DealSizeResult]:
        """Extract all deal size mentions from text.

        Args:
            text: The contract text to analyze.

        Returns:
            List of all DealSizeResult found.
        """
        results: List[DealSizeResult] = []
        if not text.strip():
            return results

        for pattern, method in DEAL_SIZE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    result = self._parse_match(match, method)
                    if result:
                        results.append(result)
                except (ValueError, IndexError):
                    continue

        return results
