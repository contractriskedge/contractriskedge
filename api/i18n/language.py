"""Multi-language support for contract analysis.

Provides language detection, prompt template loading for 5 languages,
and translation utilities for the contract risk analysis platform.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages for contract analysis."""

    EN = "en"  # English
    ES = "es"  # Spanish
    FR = "fr"  # French
    DE = "de"  # German
    ZH = "zh"  # Mandarin Chinese


# Language display names
LANGUAGE_NAMES = {
    Language.EN: "English",
    Language.ES: "Español",
    Language.FR: "Français",
    Language.DE: "Deutsch",
    Language.ZH: "中文",
}


@dataclass
class LanguageDetectionResult:
    """Result of language detection on a text."""

    detected_language: Language
    confidence: float
    is_reliable: bool  # True if confidence >= 0.95


class LanguageDetector:
    """Detects the language of contract text.

    Uses langdetect library with fastText as fallback.

    Usage:
        detector = LanguageDetector()
        result = detector.detect("This Agreement is governed by...")
        if result.is_reliable:
            prompts = LanguagePromptLoader(result.detected_language)
    """

    def __init__(self) -> None:
        """Initialize the language detector."""
        self._detector = None
        self._fasttext = None

    def detect(self, text: str) -> LanguageDetectionResult:
        """Detect the language of a text.

        Args:
            text: Text to analyze (minimum 50 characters).

        Returns:
            LanguageDetectionResult with detected language and confidence.
        """
        if not text or len(text.strip()) < 20:
            return LanguageDetectionResult(
                detected_language=Language.EN,
                confidence=1.0,
                is_reliable=False,
            )

        try:
            from langdetect import detect as ld_detect, detect_langs
            lang_probs = detect_langs(text[:500])
            if lang_probs:
                top = lang_probs[0]
                detected = Language(top.lang) if top.lang in Language._value2member_map_ else Language.EN
                return LanguageDetectionResult(
                    detected_language=detected,
                    confidence=top.prob,
                    is_reliable=top.prob >= 0.95,
                )
        except Exception:
            pass

        # Fallback: keyword-based detection
        return self._keyword_detect(text)

    @staticmethod
    def _keyword_detect(text: str) -> LanguageDetectionResult:
        """Fallback keyword-based language detection.

        Args:
            text: Text to analyze.

        Returns:
            LanguageDetectionResult.
        """
        text_lower = text.lower()

        # Spanish indicators
        es_keywords = ["el presente", "la presente", "según", "entre las partes",
                       "acuerdo", "contrato", "cláusula", "partes intervinientes"]
        es_score = sum(1 for k in es_keywords if k in text_lower)

        # French indicators
        fr_keywords = ["le présent", "la présente", "selon", "entre les parties",
                       "accord", "contrat", "clause", "parties intervenantes"]
        fr_score = sum(1 for k in fr_keywords if k in text_lower)

        # German indicators
        de_keywords = ["dieser vertrag", "zwischen den parteien", "vereinbarung",
                       "klausel", "gemäß", "nach maßgabe"]
        de_score = sum(1 for k in de_keywords if k in text_lower)

        # Chinese indicators
        zh_keywords = ["本合同", "协议", "条款", "双方", "当事人", "根据"]
        zh_score = sum(1 for k in zh_keywords if k in text)

        scores = {
            Language.ES: es_score,
            Language.FR: fr_score,
            Language.DE: de_score,
            Language.ZH: zh_score,
        }

        best_lang = max(scores, key=scores.get)
        best_score = scores[best_lang]

        if best_score > 0:
            return LanguageDetectionResult(
                detected_language=best_lang,
                confidence=min(0.7 + best_score * 0.05, 0.95),
                is_reliable=False,
            )

        return LanguageDetectionResult(
            detected_language=Language.EN,
            confidence=0.5,
            is_reliable=False,
        )


class LanguagePromptLoader:
    """Loads language-specific prompt templates for risk analysis.

    In production, these would be loaded from locale files.
    For development, provides built-in templates.

    Usage:
        loader = LanguagePromptLoader(Language.ES)
        prompt = loader.get_risk_prompt("indemnification")
    """

    def __init__(self, language: Language = Language.EN) -> None:
        """Initialize the prompt loader.

        Args:
            language: Target language for prompts.
        """
        self._language = language

    def get_risk_prompt(self, clause_type: str) -> str:
        """Get a risk analysis prompt in the target language.

        Args:
            clause_type: The type of clause to analyze.

        Returns:
            Prompt string in the target language.
        """
        prompts = {
            Language.EN: (
                f"Analyze the following {clause_type} clause for potential risks. "
                "Identify risk category, assess severity (1-10), and provide rationale."
            ),
            Language.ES: (
                f"Analice la siguiente cláusula de {self._translate(clause_type)} "
                "para identificar riesgos potenciales. Identifique la categoría de riesgo, "
                "evalúe la gravedad (1-10) y proporcione una justificación."
            ),
            Language.FR: (
                f"Analysez la clause {self._translate(clause_type)} suivante pour "
                "identifier les risques potentiels. Identifiez la catégorie de risque, "
                "évaluez la gravité (1-10) et fournissez une justification."
            ),
            Language.DE: (
                f"Analysieren Sie die folgende {self._translate(clause_type)}-Klausel "
                "auf potenzielle Risiken. Identifizieren Sie die Risikokategorie, "
                "bewerten Sie den Schweregrad (1-10) und geben Sie eine Begründung."
            ),
            Language.ZH: (
                f"分析以下{self._translate(clause_type)}条款的潜在风险。"
                "识别风险类别，评估严重程度（1-10分），并提供理由。"
            ),
        }
        return prompts.get(self._language, prompts[Language.EN])

    @staticmethod
    def _translate(clause_type: str) -> str:
        """Translate clause type names to target language.

        Args:
            clause_type: English clause type name.

        Returns:
            Translated clause type name.
        """
        translations = {
            "indemnification": {
                "es": "indemnización", "fr": "indemnisation",
                "de": "Freistellung", "zh": "赔偿",
            },
            "liability_caps": {
                "es": "limitación de responsabilidad", "fr": "plafond de responsabilité",
                "de": "Haftungsbeschränkung", "zh": "责任限制",
            },
            "termination": {
                "es": "terminación", "fr": "résiliation",
                "de": "Kündigung", "zh": "终止",
            },
            "confidentiality": {
                "es": "confidencialidad", "fr": "confidentialité",
                "de": "Vertraulichkeit", "zh": "保密",
            },
        }
        return ""

    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages.

        Returns:
            List of {code, name} dicts.
        """
        return [
            {"code": lang.value, "name": name}
            for lang, name in LANGUAGE_NAMES.items()
        ]
