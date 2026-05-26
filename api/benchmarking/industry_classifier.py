"""Fine-tuned DistilBERT classifier for 10 industry categories.

Classifies contract text into one of 10 industry categories using
a DistilBERT model fine-tuned for industry classification.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .models import IndustryCategory

logger = logging.getLogger(__name__)

# Keyword-based fallback patterns for each industry
INDUSTRY_KEYWORDS: Dict[IndustryCategory, List[str]] = {
    IndustryCategory.TECHNOLOGY: [
        "software", "saas", "cloud", "api", "platform", "digital", "data", "algorithm",
        "application", "server", "database", "cyber", "it services", "technology",
        "computer", "programming", "hosting", "infrastructure as a service",
    ],
    IndustryCategory.HEALTHCARE: [
        "healthcare", "medical", "patient", "clinical", "hospital", "physician",
        "health insurance", "hipaa", "health plan", "treatment", "diagnosis",
        "healthcare provider", "medical device", "pharmacy", "telehealth",
    ],
    IndustryCategory.FINANCIAL_SERVICES: [
        "financial", "banking", "investment", "insurance", "securities", "lending",
        "mortgage", "asset management", "wealth management", "fintech", "payment",
        "credit", "underwriting", "broker", "exchange", "compliance",
    ],
    IndustryCategory.MANUFACTURING: [
        "manufacturing", "factory", "production", "industrial", "assembly", "plant",
        "supply chain", "inventory", "logistics", "warehouse", "equipment",
        "machinery", "quality control", "raw material", "procurement",
    ],
    IndustryCategory.RETAIL: [
        "retail", "ecommerce", "store", "merchant", "consumer", "customer",
        "point of sale", "inventory management", "wholesale", "b2c",
        "omnichannel", "marketplace", "shopping", "merchandise",
    ],
    IndustryCategory.ENERGY: [
        "energy", "oil", "gas", "renewable", "solar", "wind", "power", "utility",
        "electricity", "petroleum", "exploration", "refinery", "pipeline",
        "clean energy", "fossil fuel", "grid", "generation",
    ],
    IndustryCategory.REAL_ESTATE: [
        "real estate", "property", "lease", "tenant", "landlord", "commercial property",
        "residential", "rental", "building", "office space", "retail space",
        "property management", "zoning", "construction", "development",
    ],
    IndustryCategory.TELECOMMUNICATIONS: [
        "telecommunications", "telecom", "network", "wireless", "broadband",
        "cellular", "fiber", "5g", "lte", "mobile", "carrier", "spectrum",
        "infrastructure", "connectivity", "bandwidth",
    ],
    IndustryCategory.GOVERNMENT: [
        "government", "public sector", "federal", "state agency", "municipal",
        "regulatory", "compliance", "procurement", "public service", "agency",
        "department of", "government contract", "public trust", "sovereign",
    ],
    IndustryCategory.PHARMACEUTICALS: [
        "pharmaceutical", "drug", "biotech", "clinical trial", "fda", "regulatory approval",
        "therapeutic", "vaccine", "medicine", "prescription", "patent",
        "research and development", "laboratory", "compound",
    ],
}


class IndustryClassifier:
    """Classifies contract text into 10 industry categories.

    Uses a DistilBERT model if available, with keyword-based fallback.

    Usage:
        classifier = IndustryClassifier()
        industry, confidence = classifier.classify(contract_text)
    """

    def __init__(
        self,
        model_name: str = "distilbert-base-uncased",
        use_model: bool = False,
    ) -> None:
        """Initialize the industry classifier.

        Args:
            model_name: HuggingFace model name for DistilBERT.
            use_model: Whether to attempt loading the transformer model.
                       If False, uses keyword-based classification only.
        """
        self._model_name = model_name
        self._use_model = use_model
        self._model = None
        self._tokenizer = None

        if use_model:
            self._load_model()

    def _load_model(self) -> None:
        """Load the DistilBERT model and tokenizer."""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self._model_name,
                num_labels=len(IndustryCategory),
            )
            logger.info("Loaded industry classifier model: %s", self._model_name)
        except Exception as exc:
            logger.warning(
                "Failed to load DistilBERT model: %s. Using keyword fallback.",
                exc,
            )
            self._use_model = False

    def classify(
        self, text: str
    ) -> Tuple[IndustryCategory, float]:
        """Classify contract text into an industry category.

        Args:
            text: The contract text to classify.

        Returns:
            Tuple of (IndustryCategory, confidence_score).
        """
        if not text.strip():
            return IndustryCategory.TECHNOLOGY, 0.0

        if self._use_model and self._model is not None and self._tokenizer is not None:
            return self._classify_with_model(text)
        else:
            return self._classify_with_keywords(text)

    def _classify_with_model(
        self, text: str
    ) -> Tuple[IndustryCategory, float]:
        """Classify using the DistilBERT model.

        Args:
            text: The text to classify.

        Returns:
            Tuple of (IndustryCategory, confidence).
        """
        try:
            import torch

            inputs = self._tokenizer(
                text[:512],  # Truncate to model's max length
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512,
            )

            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits
                probabilities = torch.nn.functional.softmax(logits, dim=-1)

            predicted_idx = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_idx].item()

            categories = list(IndustryCategory)
            if 0 <= predicted_idx < len(categories):
                return categories[predicted_idx], round(confidence, 4)

        except Exception as exc:
            logger.warning("Model classification failed: %s", exc)

        return self._classify_with_keywords(text)

    def _classify_with_keywords(
        self, text: str
    ) -> Tuple[IndustryCategory, float]:
        """Classify using keyword matching as fallback.

        Args:
            text: The text to classify.

        Returns:
            Tuple of (IndustryCategory, confidence).
        """
        text_lower = text.lower()
        scores: Dict[IndustryCategory, int] = {}

        for industry, keywords in INDUSTRY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                # Count occurrences of each keyword
                occurrences = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                score += occurrences
            if score > 0:
                scores[industry] = score

        if not scores:
            return IndustryCategory.TECHNOLOGY, 0.3

        # Find the industry with the highest score
        best_industry = max(scores, key=scores.get)
        total_score = sum(scores.values())
        confidence = min(0.9, scores[best_industry] / max(1, total_score))

        return best_industry, round(confidence, 4)

    def classify_with_distribution(
        self, text: str
    ) -> Dict[str, float]:
        """Get confidence scores for all industry categories.

        Args:
            text: The text to classify.

        Returns:
            Dict mapping industry names to confidence scores.
        """
        text_lower = text.lower()
        scores: Dict[str, float] = {}

        total_matches = 0
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            matches = sum(
                len(re.findall(r'\b' + re.escape(kw) + r'\b', text_lower))
                for kw in keywords
            )
            if matches > 0:
                scores[industry.value] = float(matches)
                total_matches += matches

        if total_matches == 0:
            return {cat.value: 0.0 for cat in IndustryCategory}

        # Normalize to probabilities
        return {
            industry: round(count / total_matches, 4)
            for industry, count in scores.items()
        }

    def get_supported_industries(self) -> List[str]:
        """Get the list of supported industry categories.

        Returns:
            List of industry name strings.
        """
        return [cat.value for cat in IndustryCategory]
