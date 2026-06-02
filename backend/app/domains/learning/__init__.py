"""AI Learning Loop — reviewer consensus, false-positive clustering, recommendation tuning, prompt optimization.

Where the AI actually compounds over time through continuous learning.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LearningSignalType(str, Enum):
    REVIEWER_ACCEPTED = "reviewer_accepted"       # Reviewer agreed with AI
    REVIEWER_REJECTED = "reviewer_rejected"       # Reviewer disagreed with AI
    REVIEWER_MODIFIED = "reviewer_modified"       # Reviewer modified AI output
    REPLAY_DRIFT = "replay_drift"                 # Replay detected drift
    CONSENSUS_BUILT = "consensus_built"           # Multiple reviewers agreed
    FALSE_POSITIVE = "false_positive"             # AI flagged incorrectly
    FALSE_NEGATIVE = "false_negative"             # AI missed correctly


@dataclass
class LearningSignal:
    """A signal from the learning loop."""
    signal_id: str
    signal_type: LearningSignalType
    execution_id: str
    tenant_id: str
    finding_id: str | None = None
    confidence: float = 0.0
    reviewer_action: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ConsensusScore:
    """Reviewer consensus score for an AI finding."""
    finding_id: str
    total_reviews: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    modified_count: int = 0
    consensus_rate: float = 0.0  # % of reviewers who agreed
    ai_confidence: float = 0.0
    recommendation: str = ""  # "keep", "retune", "remove"


@dataclass
class PromptOptimizationSuggestion:
    """A suggestion for prompt improvement based on learning signals."""
    prompt_key: str
    current_version: str
    suggested_changes: list[str] = field(default_factory=list)
    signal_count: int = 0
    impact_score: float = 0.0
    priority: str = "low"


@dataclass
class AILearningLoop:
    """Continuous AI improvement through reviewer feedback and drift analysis.

    Capabilities:
    - Reviewer consensus scoring (how often reviewers agree with AI)
    - False-positive clustering (patterns where AI is consistently wrong)
    - Recommendation tuning based on feedback
    - Reinforcement signal collection
    - Prompt optimization suggestions
    - Model evaluation drift scoring
    """

    _signals: list[LearningSignal] = field(default_factory=list)
    _consensus_scores: dict[str, ConsensusScore] = field(default_factory=dict)

    def record_signal(self, signal: LearningSignal) -> None:
        """Record a learning signal."""
        self._signals.append(signal)
        logger.debug("Learning signal recorded: %s (confidence=%.2f)", signal.signal_type.value, signal.confidence)

    def record_reviewer_feedback(
        self,
        execution_id: str,
        finding_id: str,
        tenant_id: str,
        reviewer_action: str,  # "accepted", "rejected", "modified"
        ai_confidence: float,
    ) -> LearningSignal:
        """Record reviewer feedback as a learning signal."""
        signal_type_map = {
            "accepted": LearningSignalType.REVIEWER_ACCEPTED,
            "rejected": LearningSignalType.REVIEWER_REJECTED,
            "modified": LearningSignalType.REVIEWER_MODIFIED,
        }
        signal_type = signal_type_map.get(reviewer_action, LearningSignalType.REVIEWER_ACCEPTED)

        signal = LearningSignal(
            signal_id=f"sig_{len(self._signals)}_{datetime.utcnow().timestamp()}",
            signal_type=signal_type,
            execution_id=execution_id,
            tenant_id=tenant_id,
            finding_id=finding_id,
            confidence=ai_confidence,
            reviewer_action=reviewer_action,
        )
        self.record_signal(signal)
        self._update_consensus(finding_id, reviewer_action, ai_confidence)
        return signal

    def _update_consensus(self, finding_id: str, action: str, confidence: float) -> None:
        """Update consensus score for a finding."""
        if finding_id not in self._consensus_scores:
            self._consensus_scores[finding_id] = ConsensusScore(finding_id=finding_id, ai_confidence=confidence)

        score = self._consensus_scores[finding_id]
        score.total_reviews += 1
        if action == "accepted":
            score.accepted_count += 1
        elif action == "rejected":
            score.rejected_count += 1
        elif action == "modified":
            score.modified_count += 1

        score.consensus_rate = score.accepted_count / max(score.total_reviews, 1)

        if score.total_reviews >= 5:
            if score.consensus_rate >= 0.8:
                score.recommendation = "keep"
            elif score.consensus_rate >= 0.5:
                score.recommendation = "retune"
            else:
                score.recommendation = "remove"

    def get_consensus_score(self, finding_id: str) -> ConsensusScore | None:
        """Get consensus score for a finding."""
        return self._consensus_scores.get(finding_id)

    def get_false_positive_clusters(self, min_signals: int = 3) -> list[dict[str, Any]]:
        """Find patterns where AI is consistently wrong."""
        rejected = [
            s for s in self._signals
            if s.signal_type == LearningSignalType.REVIEWER_REJECTED
        ]
        if len(rejected) < min_signals:
            return []

        # Group by clause type or pattern
        clusters: dict[str, int] = {}
        for signal in rejected:
            clause_type = signal.details.get("clause_type", "unknown")
            clusters[clause_type] = clusters.get(clause_type, 0) + 1

        return [
            {"pattern": k, "false_positive_count": v, "severity": "high" if v > 10 else "medium" if v > 5 else "low"}
            for k, v in sorted(clusters.items(), key=lambda x: x[1], reverse=True)
            if v >= min_signals
        ]

    def suggest_prompt_optimizations(self) -> list[PromptOptimizationSuggestion]:
        """Generate prompt optimization suggestions based on learning signals."""
        suggestions = []

        # Find findings with low consensus
        low_consensus = [
            s for s in self._consensus_scores.values()
            if s.total_reviews >= 3 and s.consensus_rate < 0.6
        ]

        if low_consensus:
            suggestions.append(PromptOptimizationSuggestion(
                prompt_key="risk_analysis",
                current_version="latest",
                suggested_changes=[
                    "Review clause_type classification accuracy",
                    "Adjust severity calibration for frequently overridden findings",
                    "Add examples for edge cases with low consensus",
                ],
                signal_count=len(low_consensus),
                impact_score=0.7,
                priority="high",
            ))

        return suggestions

    def get_learning_dashboard(self) -> dict[str, Any]:
        """Get the AI learning loop dashboard."""
        total = len(self._signals)
        accepted = sum(1 for s in self._signals if s.signal_type == LearningSignalType.REVIEWER_ACCEPTED)
        rejected = sum(1 for s in self._signals if s.signal_type == LearningSignalType.REVIEWER_REJECTED)
        modified = sum(1 for s in self._signals if s.signal_type == LearningSignalType.REVIEWER_MODIFIED)

        return {
            "total_signals": total,
            "accepted": accepted,
            "rejected": rejected,
            "modified": modified,
            "acceptance_rate": round(accepted / max(total, 1) * 100, 1),
            "findings_with_consensus": len(self._consensus_scores),
            "false_positive_clusters": self.get_false_positive_clusters(),
            "optimization_suggestions": self.suggest_prompt_optimizations(),
        }


# ── Global singleton ───────────────────────────────────────────────

ai_learning_loop = AILearningLoop()
