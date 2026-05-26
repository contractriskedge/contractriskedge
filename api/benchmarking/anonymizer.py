"""PII anonymization with confidence scoring for benchmark corpus ingestion.

Uses spaCy NER and regex patterns to detect and anonymize personally
identifiable information in contract clauses before they enter the
benchmark corpus.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Regex patterns for PII detection
PII_PATTERNS: List[Tuple[str, str, str]] = [
    # Email addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', "email", "EMAIL"),
    # Phone numbers (various formats)
    (r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', "phone", "PHONE"),
    # Social Security Numbers
    (r'\b\d{3}-\d{2}-\d{4}\b', "ssn", "SSN"),
    # Credit card numbers (simplified)
    (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', "credit_card", "CREDIT_CARD"),
    # Bank account numbers (simplified patterns)
    (r'\b\d{8,17}\b', "bank_account", "BANK_ACCOUNT"),
    # IP Addresses
    (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', "ip_address", "IP_ADDRESS"),
    # URLs
    (r'\bhttps?://[A-Za-z0-9./?=_-]+\b', "url", "URL"),
    # Dollar amounts (may indicate specific deal terms)
    (r'\$\s*[\d,]+(?:\.\d{2})?\s*(?:million|billion|thousand|M|B|K)?', "dollar_amount", "DOLLAR_AMOUNT"),
    # Dates (specific dates that could be identifying)
    (r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', "date", "DATE"),
    # Company names patterns (Inc., LLC, Corp., Ltd.)
    (r'\b[A-Z][A-Za-z0-9]+(?:,\s*(?:Inc|LLC|Corp|Ltd|PLC|GmbH|SA|Pty)\.?)?\b', "company_name", "COMPANY_NAME"),
    # Street addresses (simplified)
    (r'\b\d{1,5}\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b', "address", "ADDRESS"),
]

# High-confidence patterns (very unlikely to be false positives)
HIGH_CONFIDENCE_PATTERNS: Set[str] = {"email", "ssn", "credit_card", "phone"}


@dataclass
class AnonymizationResult:
    """Result of PII anonymization on a text."""

    anonymized_text: str
    pii_found: bool
    pii_entities: List[Dict[str, Any]]
    confidence: float  # Overall confidence in anonymization (0-1)
    replacements_made: int


class PIIAnonymizer:
    """Anonymizes PII from contract clause text using NER and regex.

    Uses spaCy for named entity recognition of person names, organizations,
    and locations, combined with regex patterns for structured PII like
    emails, phone numbers, and SSNs.

    Usage:
        anonymizer = PIIAnonymizer()
        result = anonymizer.anonymize(
            "John Doe (john@example.com) and Acme Corp agree..."
        )
        clean_text = result.anonymized_text
    """

    def __init__(self, spacy_model: str = "en_core_web_trf") -> None:
        """Initialize the PII anonymizer.

        Args:
            spacy_model: spaCy model to use for NER.
                         Falls back to en_core_web_sm if trf not available.
        """
        self._nlp = None
        self._load_spacy_model(spacy_model)

    def _load_spacy_model(self, model_name: str) -> None:
        """Load the spaCy model with fallback.

        Args:
            model_name: Preferred model name.
        """
        import spacy
        try:
            self._nlp = spacy.load(model_name)
            logger.info("Loaded spaCy model: %s", model_name)
        except OSError:
            try:
                self._nlp = spacy.load("en_core_web_sm")
                logger.info("Fell back to spaCy model: en_core_web_sm")
            except OSError:
                logger.warning(
                    "No spaCy model available. Using regex-only anonymization."
                )

    def anonymize(
        self,
        text: str,
        mask_with: str = "[REDACTED]",
        min_confidence: float = 0.5,
    ) -> AnonymizationResult:
        """Anonymize PII in the given text.

        Args:
            text: The text to anonymize.
            mask_with: Replacement string for PII.
            min_confidence: Minimum confidence threshold for regex matches.

        Returns:
            AnonymizationResult with the cleaned text and metadata.
        """
        if not text.strip():
            return AnonymizationResult(
                anonymized_text=text,
                pii_found=False,
                pii_entities=[],
                confidence=1.0,
                replacements_made=0,
            )

        entities: List[Dict[str, Any]] = []
        anonymized = text
        replacements = 0

        # Step 1: Regex-based PII detection
        anonymized, regex_entities = self._apply_regex(
            anonymized, mask_with, min_confidence
        )
        entities.extend(regex_entities)
        replacements += len(regex_entities)

        # Step 2: spaCy NER-based detection
        if self._nlp is not None:
            anonymized, ner_entities = self._apply_ner(
                anonymized, mask_with
            )
            entities.extend(ner_entities)
            replacements += len(ner_entities)

        # Sort entities by position for consistent output
        entities.sort(key=lambda e: e.get("start", 0))

        # Compute overall confidence
        confidence = self._compute_confidence(entities)

        return AnonymizationResult(
            anonymized_text=anonymized,
            pii_found=len(entities) > 0,
            pii_entities=entities,
            confidence=confidence,
            replacements_made=replacements,
        )

    def _apply_regex(
        self,
        text: str,
        mask_with: str,
        min_confidence: float,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply regex-based PII detection and replacement.

        Args:
            text: The text to process.
            mask_with: Replacement string.
            min_confidence: Minimum confidence threshold.

        Returns:
            Tuple of (anonymized_text, detected_entities).
        """
        entities: List[Dict[str, Any]] = []
        anonymized = text

        for pattern, entity_type, label in PII_PATTERNS:
            confidence = 0.9 if entity_type in HIGH_CONFIDENCE_PATTERNS else 0.7
            if confidence < min_confidence:
                continue

            for match in re.finditer(pattern, anonymized):
                start, end = match.start(), match.end()
                matched_text = match.group()

                # Skip very short number sequences that aren't likely PII
                if entity_type == "bank_account" and len(matched_text) < 9:
                    continue

                entities.append({
                    "type": entity_type,
                    "label": label,
                    "text": matched_text,
                    "start": start,
                    "end": end,
                    "confidence": confidence,
                    "source": "regex",
                })

            # Apply replacement
            replacement_pattern = rf'(?<!\w){pattern}(?!\w)'
            anonymized = re.sub(
                replacement_pattern,
                f"{mask_with}({label})",
                anonymized,
            )

        return anonymized, entities

    def _apply_ner(
        self,
        text: str,
        mask_with: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply spaCy NER-based PII detection.

        Args:
            text: The text to process.
            mask_with: Replacement string.

        Returns:
            Tuple of (anonymized_text, detected_entities).
        """
        entities: List[Dict[str, Any]] = []
        if self._nlp is None:
            return text, entities

        doc = self._nlp(text)

        # Process entities in reverse order to maintain positions
        ner_spans = []
        for ent in doc.ents:
            # Focus on PERSON, ORG, GPE entities
            if ent.label_ in ("PERSON", "ORG", "GPE", "DATE", "MONEY"):
                confidence = 0.8 if ent.label_ == "PERSON" else 0.6
                ner_spans.append({
                    "type": ent.label_.lower(),
                    "label": ent.label_,
                    "text": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": confidence,
                    "source": "ner",
                })

        # Apply replacements (reverse order to preserve positions)
        anonymized = text
        for span in sorted(ner_spans, key=lambda x: x["start"], reverse=True):
            # Check if this span overlaps with already-replaced content
            if mask_with in anonymized[span["start"]:span["end"]]:
                continue
            entities.append(span)
            replacement = f"{mask_with}({span['label']})"
            anonymized = (
                anonymized[:span["start"]]
                + replacement
                + anonymized[span["end"]:]
            )

        return anonymized, entities

    @staticmethod
    def _compute_confidence(
        entities: List[Dict[str, Any]],
    ) -> float:
        """Compute overall anonymization confidence.

        Args:
            entities: List of detected entities.

        Returns:
            Confidence score between 0 and 1.
        """
        if not entities:
            return 1.0

        avg_confidence = sum(
            e.get("confidence", 0.5) for e in entities
        ) / len(entities)

        # Penalize if only low-confidence regex matches
        high_conf = sum(
            1 for e in entities if e.get("confidence", 0) >= 0.8
        )
        ratio = high_conf / len(entities)

        return avg_confidence * (0.5 + 0.5 * ratio)

    def detect_pii(
        self, text: str
    ) -> List[Dict[str, Any]]:
        """Detect PII without performing anonymization.

        Args:
            text: The text to scan.

        Returns:
            List of detected PII entities.
        """
        result = self.anonymize(text)
        return result.pii_entities
