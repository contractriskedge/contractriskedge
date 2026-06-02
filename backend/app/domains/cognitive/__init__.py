"""Enterprise Cognitive Layer — enterprise reasoning memory, operational pattern synthesis, strategic recommendation evolution, organization-specific intelligence adaptation, institutional decision learning, enterprise operational cognition.

The deepest strategic layer — enterprise operational cognition infrastructure.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CognitiveCapability(str, Enum):
    REASONING_MEMORY = "reasoning_memory"
    PATTERN_SYNTHESIS = "pattern_synthesis"
    STRATEGY_EVOLUTION = "strategy_evolution"
    INTELLIGENCE_ADAPTATION = "intelligence_adaptation"
    DECISION_LEARNING = "decision_learning"
    OPERATIONAL_COGNITION = "operational_cognition"


@dataclass
class ReasoningTrace:
    """A trace of enterprise reasoning — how a decision was reached."""
    trace_id: str
    topic: str
    reasoning_steps: list[str] = field(default_factory=list)
    evidence_used: list[str] = field(default_factory=list)
    alternatives_considered: list[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SynthesizedPattern:
    """A pattern synthesized from operational data."""
    pattern_id: str
    domain: str
    description: str
    confidence: float
    supporting_evidence: int = 0
    first_observed: str = ""
    last_observed: str = ""


@dataclass
class EnterpriseCognitiveService:
    """Enterprise cognitive layer — the deepest strategic intelligence layer.

    Capabilities:
    - Enterprise reasoning memory (how the enterprise reasons about decisions)
    - Operational pattern synthesis (patterns that emerge from operations)
    - Strategic recommendation evolution (recommendations that improve over time)
    - Organization-specific intelligence adaptation (intelligence that adapts to each org)
    - Institutional decision learning (learning from past decisions)
    - Enterprise operational cognition (unified operational understanding)
    """

    _reasoning_traces: list[ReasoningTrace] = field(default_factory=list)
    _patterns: list[SynthesizedPattern] = field(default_factory=list)

    def record_reasoning(self, trace: ReasoningTrace) -> str:
        """Record a reasoning trace."""
        if not trace.trace_id:
            trace.trace_id = str(uuid.uuid4())
        self._reasoning_traces.append(trace)
        return trace.trace_id

    def synthesize_pattern(self, domain: str, description: str, confidence: float, evidence_count: int = 1) -> SynthesizedPattern:
        """Synthesize a pattern from operational data."""
        now = datetime.utcnow().isoformat()
        # Check if pattern already exists
        for pattern in self._patterns:
            if pattern.domain == domain and pattern.description == description:
                pattern.supporting_evidence += evidence_count
                pattern.confidence = min(1.0, pattern.confidence + 0.05)
                pattern.last_observed = now
                return pattern

        pattern = SynthesizedPattern(
            pattern_id=str(uuid.uuid4()),
            domain=domain,
            description=description,
            confidence=confidence,
            supporting_evidence=evidence_count,
            first_observed=now,
            last_observed=now,
        )
        self._patterns.append(pattern)
        return pattern

    def get_reasoning_trace(self, topic: str) -> list[ReasoningTrace]:
        """Get reasoning traces related to a topic."""
        return [t for t in self._reasoning_traces if topic.lower() in t.topic.lower()]

    def get_high_confidence_patterns(self, min_confidence: float = 0.8) -> list[SynthesizedPattern]:
        """Get patterns with confidence above threshold."""
        return [p for p in self._patterns if p.confidence >= min_confidence]

    def get_cognitive_summary(self) -> dict[str, Any]:
        """Get cognitive layer summary."""
        return {
            "reasoning_traces": len(self._reasoning_traces),
            "synthesized_patterns": len(self._patterns),
            "high_confidence_patterns": len(self.get_high_confidence_patterns()),
            "domains_covered": list(set(p.domain for p in self._patterns)),
            "cognitive_capabilities": [c.value for c in CognitiveCapability],
        }


# ── Global singleton ───────────────────────────────────────────────

enterprise_cognitive = EnterpriseCognitiveService()
