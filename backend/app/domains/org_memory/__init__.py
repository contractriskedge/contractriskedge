"""Organizational Memory System — captures institutional operational knowledge that compounds over time.

Negotiation outcomes, escalation resolutions, reviewer reasoning, policy exceptions, workflow evolution.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MemoryCategory(str, Enum):
    NEGOTIATION_OUTCOME = "negotiation_outcome"
    ESCALATION_RESOLUTION = "escalation_resolution"
    REVIEWER_REASONING = "reviewer_reasoning"
    POLICY_EXCEPTION = "policy_exception"
    WORKFLOW_EVOLUTION = "workflow_evolution"
    OPERATIONAL_DECISION = "operational_decision"
    REMEDIATION_ACTION = "remediation_action"


@dataclass
class MemoryEntry:
    """A single entry in the organizational memory."""
    entry_id: str
    category: MemoryCategory
    title: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    lessons_learned: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    reference_count: int = 0


@dataclass
class OrganizationalMemoryService:
    """Institutional operational memory — knowledge that compounds over time.

    Captures:
    - Negotiation outcomes (what worked, what didn't)
    - Escalation resolutions (how escalations were resolved)
    - Reviewer reasoning (why reviewers made decisions)
    - Policy exceptions (when and why policies were overridden)
    - Workflow evolution (how workflows changed over time)
    - Operational decisions (key operational choices)
    - Historical remediation actions (how issues were fixed)
    """

    _entries: dict[str, MemoryEntry] = field(default_factory=dict)

    def record(self, entry: MemoryEntry) -> MemoryEntry:
        """Record a memory entry."""
        if not entry.entry_id:
            entry.entry_id = str(uuid.uuid4())
        self._entries[entry.entry_id] = entry
        logger.info("Recorded organizational memory: %s (%s)", entry.title[:50], entry.category.value)
        return entry

    def record_negotiation_outcome(self, contract_id: str, strategy: str, outcome: str, lessons: list[str]) -> MemoryEntry:
        """Record a negotiation outcome for future reference."""
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            category=MemoryCategory.NEGOTIATION_OUTCOME,
            title=f"Negotiation: {contract_id[:8]}",
            description=f"Strategy: {strategy}. Outcome: {outcome}",
            context={"contract_id": contract_id, "strategy": strategy},
            outcome=outcome,
            lessons_learned=lessons,
            tags=["negotiation", contract_id[:8]],
        )
        return self.record(entry)

    def record_escalation_resolution(self, review_id: str, reason: str, resolution: str, lessons: list[str]) -> MemoryEntry:
        """Record how an escalation was resolved."""
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            category=MemoryCategory.ESCALATION_RESOLUTION,
            title=f"Escalation: {review_id[:8]}",
            description=f"Reason: {reason}. Resolution: {resolution}",
            context={"review_id": review_id, "reason": reason},
            outcome=resolution,
            lessons_learned=lessons,
            tags=["escalation", review_id[:8]],
        )
        return self.record(entry)

    def record_reviewer_reasoning(self, finding_id: str, reviewer_id: str, decision: str, rationale: str) -> MemoryEntry:
        """Record a reviewer's reasoning for an override decision."""
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            category=MemoryCategory.REVIEWER_REASONING,
            title=f"Reviewer Decision: {finding_id[:8]}",
            description=f"Decision: {decision}. Rationale: {rationale[:200]}",
            context={"finding_id": finding_id, "reviewer_id": reviewer_id, "decision": decision},
            outcome=decision,
            lessons_learned=[f"Reviewer {reviewer_id[:8]} overrode AI: {rationale[:100]}"],
            tags=["reviewer_decision", finding_id[:8]],
        )
        return self.record(entry)

    def record_policy_exception(self, policy_id: str, reason: str, approved_by: str, duration_days: int) -> MemoryEntry:
        """Record a policy exception."""
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            category=MemoryCategory.POLICY_EXCEPTION,
            title=f"Policy Exception: {policy_id}",
            description=f"Approved by {approved_by} for {duration_days} days. Reason: {reason}",
            context={"policy_id": policy_id, "approved_by": approved_by, "duration_days": duration_days},
            outcome="approved",
            tags=["policy_exception", policy_id],
        )
        return self.record(entry)

    def search_memory(self, query: str, category: MemoryCategory | None = None, limit: int = 10) -> list[MemoryEntry]:
        """Search organizational memory."""
        results = []
        for entry in self._entries.values():
            if category and entry.category != category:
                continue
            if query.lower() in entry.title.lower() or query.lower() in entry.description.lower():
                results.append(entry)
            elif any(query.lower() in t.lower() for t in entry.tags):
                results.append(entry)

        results.sort(key=lambda e: e.reference_count, reverse=True)
        return results[:limit]

    def get_memory_by_category(self, category: MemoryCategory) -> list[MemoryEntry]:
        """Get all memory entries in a category."""
        return [e for e in self._entries.values() if e.category == category]

    def get_memory_summary(self) -> dict[str, Any]:
        """Get organizational memory summary."""
        return {
            "total_entries": len(self._entries),
            "by_category": {
                c.value: sum(1 for e in self._entries.values() if e.category == c)
                for c in MemoryCategory
            },
            "total_lessons": sum(len(e.lessons_learned) for e in self._entries.values()),
            "most_referenced": sorted(
                [{"title": e.title[:50], "refs": e.reference_count} for e in self._entries.values()],
                key=lambda x: x["refs"], reverse=True,
            )[:5],
        }


# ── Global singleton ───────────────────────────────────────────────

org_memory = OrganizationalMemoryService()
