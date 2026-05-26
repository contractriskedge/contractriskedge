"""AI-powered redline suggestion engine for contract analysis.

Provides specialized prompt templates, few-shot examples, and quality
constraints for generating attorney-quality redline suggestions across
8 clause types: Liability Caps, Indemnification, IP Ownership, Payment
Terms, Governing Law, Termination Rights, Confidentiality, and Force Majeure.
"""

from __future__ import annotations

from .prompts import RedlinePromptTemplates, RedlinePromptSet
from .templates import TemplateManager, TemplateVersion
from .few_shot import FewShotExamples, FewShotExample
from .quality_constraints import QualityConstraintEngine, QualityCheckResult
from .formatter import RedlineFormatter, FormattedRedline
from .diff_engine import DiffEngine, WordDiff, DiffOperation
from .status_tracker import (
    StatusTracker,
    RedlineStatus,
    StatusChangeEvent,
    StatusSummary,
)
from .models import (
    RedlineSuggestion,
    RedlineRequest,
    RedlineResponse,
    ClauseType,
    ChangeType,
    PartyRole,
    DealSizeTier,
    Industry,
    CounterpartyAggressiveness,
)

__all__ = [
    "RedlinePromptTemplates",
    "RedlinePromptSet",
    "TemplateManager",
    "TemplateVersion",
    "FewShotExamples",
    "FewShotExample",
    "QualityConstraintEngine",
    "QualityCheckResult",
    "RedlineFormatter",
    "FormattedRedline",
    "DiffEngine",
    "WordDiff",
    "DiffOperation",
    "StatusTracker",
    "RedlineStatus",
    "StatusChangeEvent",
    "StatusSummary",
    "RedlineSuggestion",
    "RedlineRequest",
    "RedlineResponse",
    "ClauseType",
    "ChangeType",
    "PartyRole",
    "DealSizeTier",
    "Industry",
    "CounterpartyAggressiveness",
]
