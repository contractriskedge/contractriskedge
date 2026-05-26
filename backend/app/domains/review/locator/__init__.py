"""Locator module — structural redline location system.

Replaces the old chunk-based fuzzy-locate approach with a structured
system that understands document hierarchy, insertion semantics,
and confidence scoring.
"""

from app.domains.review.locator.models import (
    AnchorType,
    InsertPosition,
    LocatorResult,
    LocatorStatus,
    RedlineAction,
    SectionHierarchy,
    SectionNode,
)
from app.domains.review.locator.parser import SectionParser
from app.domains.review.locator.heuristics import ClausePositionMapper
from app.domains.review.locator.service import LocatorService

__all__ = [
    "AnchorType",
    "InsertPosition",
    "LocatorResult",
    "LocatorStatus",
    "RedlineAction",
    "SectionHierarchy",
    "SectionNode",
    "SectionParser",
    "ClausePositionMapper",
    "LocatorService",
]
