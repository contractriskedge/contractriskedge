"""Reviewer Productivity System — bulk resolution, grouped evidence review, AI-assisted actions, smart routing, macros, keyboard-driven workflows, performance coaching.

Enterprise adoption depends heavily on reviewer efficiency and throughput.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BulkAction:
    """A bulk action that can be applied to multiple findings."""
    action_id: str
    name: str
    description: str
    finding_ids: list[str] = field(default_factory=list)
    impact: str = ""  # What happens when applied
    requires_confirmation: bool = True


@dataclass
class ReviewMacro:
    """A reusable review macro/template for common actions."""
    macro_id: str
    name: str
    description: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    shortcut: str = ""  # Keyboard shortcut
    category: str = "general"


@dataclass
class ReviewerProductivityService:
    """Reviewer productivity optimization — maximizing human throughput.

    Capabilities:
    - Bulk resolution workflows (resolve multiple findings at once)
    - Grouped evidence review (review related evidence together)
    - AI-assisted reviewer actions (AI suggests reviewer actions)
    - Smart reviewer routing (route to best available reviewer)
    - Review macros/templates (reusable review patterns)
    - Keyboard-driven workflows (efficiency shortcuts)
    - Reviewer performance coaching (personalized improvement tips)
    """

    _macros: dict[str, ReviewMacro] = field(default_factory=dict)

    def __post_init__(self):
        self._register_default_macros()

    def _register_default_macros(self) -> None:
        """Register default review macros."""
        macros = [
            ReviewMacro(
                macro_id="accept_all_high_conf",
                name="Accept All High Confidence",
                description="Accept all findings with AI confidence > 0.9",
                actions=[{"type": "bulk_accept", "condition": "confidence > 0.9"}],
                shortcut="Ctrl+Shift+A",
                category="bulk_actions",
            ),
            ReviewMacro(
                macro_id="escalate_to_legal",
                name="Escalate to Legal",
                description="Escalate selected findings to legal review",
                actions=[{"type": "escalate", "target_role": "legal", "reason": "Requires legal expertise"}],
                shortcut="Ctrl+Shift+E",
                category="escalation",
            ),
            ReviewMacro(
                macro_id="add_note_and_approve",
                name="Add Note & Approve",
                description="Add a reviewer note and approve the finding",
                actions=[{"type": "add_note"}, {"type": "approve"}],
                shortcut="Ctrl+Shift+N",
                category="review",
            ),
            ReviewMacro(
                macro_id="request_revision",
                name="Request Revision",
                description="Request AI to revise the finding with additional context",
                actions=[{"type": "request_revision", "reason": "Additional context needed"}],
                shortcut="Ctrl+Shift+R",
                category="review",
            ),
            ReviewMacro(
                macro_id="dismiss_false_positive",
                name="Dismiss as False Positive",
                description="Dismiss finding as AI false positive with feedback",
                actions=[{"type": "dismiss", "reason": "False positive", "provide_feedback": True}],
                shortcut="Ctrl+Shift+D",
                category="triage",
            ),
        ]
        for macro in macros:
            self.register_macro(macro)

    def register_macro(self, macro: ReviewMacro) -> None:
        """Register a review macro."""
        self._macros[macro.macro_id] = macro

    def get_macros(self, category: str | None = None) -> list[ReviewMacro]:
        """Get available macros, optionally filtered by category."""
        if category:
            return [m for m in self._macros.values() if m.category == category]
        return list(self._macros.values())

    def suggest_bulk_actions(self, findings: list[dict]) -> list[BulkAction]:
        """Suggest bulk actions based on finding patterns."""
        actions = []

        # Group by confidence
        high_confidence = [f for f in findings if (f.get("confidence", 0) or 0) > 0.9]
        if len(high_confidence) >= 3:
            actions.append(BulkAction(
                action_id="bulk_accept_high_conf",
                name=f"Accept {len(high_confidence)} High-Confidence Findings",
                description=f"AI confidence > 0.9 for all {len(high_confidence)} findings",
                finding_ids=[f.get("finding_id", "") for f in high_confidence],
                impact="Quick resolution of high-confidence findings",
            ))

        # Group by clause type
        by_clause: dict[str, list[dict]] = {}
        for f in findings:
            ct = f.get("clause_type", "other")
            if ct not in by_clause:
                by_clause[ct] = []
            by_clause[ct].append(f)

        for clause_type, group in by_clause.items():
            if len(group) >= 3:
                actions.append(BulkAction(
                    action_id=f"bulk_{clause_type}",
                    name=f"Review {len(group)} {clause_type.title()} Findings",
                    description=f"Grouped by clause type: {clause_type}",
                    finding_ids=[f.get("finding_id", "") for f in group],
                ))

        return actions

    def smart_route_review(self, review_data: dict, available_reviewers: list[dict]) -> str:
        """Route a review to the best available reviewer."""
        required_role = review_data.get("required_role", "reviewer")
        clause_types = review_data.get("clause_types", [])
        risk_score = review_data.get("risk_score", 0.5)

        # Filter by role
        candidates = [r for r in available_reviewers if required_role in r.get("roles", [])]
        if not candidates:
            candidates = available_reviewers

        # Score each reviewer
        scored = []
        for r in candidates:
            score = 0.0
            # Prefer lower current load
            current_load = r.get("current_reviews", 0)
            max_load = r.get("max_concurrent_reviews", 10)
            score += (1.0 - current_load / max_load) * 0.4

            # Prefer matching skills
            reviewer_skills = set(r.get("skills", []))
            required_skills = set(clause_types)
            if required_skills:
                skill_match = len(reviewer_skills & required_skills) / len(required_skills)
                score += skill_match * 0.3

            # Prefer higher accuracy
            accuracy = r.get("accuracy_score", 1.0)
            score += accuracy * 0.3

            scored.append((r["user_id"], score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else ""

    def get_performance_coaching(self, reviewer_stats: dict) -> list[str]:
        """Generate personalized performance coaching tips."""
        tips = []
        avg_hours = reviewer_stats.get("avg_review_time_hours", 0)
        accuracy = reviewer_stats.get("accuracy_score", 1.0)
        reviews_completed = reviewer_stats.get("reviews_completed", 0)
        sla_breaches = reviewer_stats.get("sla_breaches", 0)

        if reviews_completed < 10:
            tips.append("Complete 10 reviews to establish baseline performance metrics")
            return tips

        if avg_hours > 4:
            tips.append(f"Your average review time ({avg_hours:.1f}h) is above team average — try using bulk actions for high-confidence findings")
        if sla_breaches > 2:
            tips.append(f"You've had {sla_breaches} SLA breaches — consider prioritizing items with approaching deadlines")
        if accuracy < 0.9:
            tips.append(f"Your accuracy score ({accuracy:.0%}) suggests reviewing AI recommendations more carefully")
        if avg_hours < 2 and accuracy > 0.95:
            tips.append("Excellent performance! Consider mentoring other reviewers")

        if not tips:
            tips.append("Performance is on track — keep up the good work")

        return tips


# ── Global singleton ───────────────────────────────────────────────

reviewer_productivity = ReviewerProductivityService()
