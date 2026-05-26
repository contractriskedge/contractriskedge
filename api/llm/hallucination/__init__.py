"""Hallucination detection and grounding validation modules.

Provides detectors for identifying unsupported claims in LLM output
and validating that AI-generated analysis is grounded in source text.
"""

from __future__ import annotations

from .detector import GroundingValidator, GroundingValidationResult, ClaimVerification

__all__ = [
    "GroundingValidator",
    "GroundingValidationResult",
    "ClaimVerification",
]
