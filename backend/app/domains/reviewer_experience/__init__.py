"""Reviewer Experience System — reviewer inbox, AI confidence triage, grouped findings, bulk resolution, evidence-first review.

Enterprise adoption depends heavily on reviewer efficiency and experience.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TriageLevel(str, Enum):
    HIGH_CONFIDENCE = "high_confidence"     # AI is very sure, quick review
    MEDIUM_CONFIDENCE = "medium_confidence" # AI is moderately sure, careful review
    LOW_CONFIDENCE = "low_confidence"       # AI is unsure, detailed review
    FLAGGED = "flagged"                     # Needs immediate attention


@dataclass
class ReviewerInboxItem:
    """An item in a reviewer's inbox."""
    item_id: str
    review_id: str
    title: str
    priority: str  # critical, high, medium, low
    triage_level: TriageLevel
    ai_confidence: float
    stage: str
    assigned_at: str
    sla_deadline: str
    contract_name: str = ""
    contract_type: str = ""
    risk_score: float = 0.0


@dataclass
class FindingGroup:
    """A group of related findings for bulk resolution."""
    group_id: str
    group_type: str  # same_clause_type, same_severity, same_vendor
    label: str
    finding_count: int
    ai_confidence_avg: float
    can_bulk_resolve: bool = True
    findings: list[dict] = field(default_factory=list)


@dataclass
class EvidenceChunk:
    """An evidence chunk for evidence-first review mode."""
    chunk_id: str
    text: str
    page_numbers: list[int] = field(default_factory=list)
    section_heading: str = ""
    clause_type: str = ""
    relevance_score: float = 0.0


@dataclass
class ReviewerExperienceService:
    """Reviewer experience optimization — making reviewers efficient and effective.

    Capabilities:
    - Reviewer inbox with AI-powered triage
    - AI confidence triage (sort by AI certainty)
    - Grouped findings for bulk resolution
    - Bulk resolution workflows
    - Evidence-first review mode (show evidence before AI conclusion)
    - Clause comparison workspace
    - Replay-aware debugging UI
    """

    _inbox: dict[str, list[ReviewerInboxItem]] = field(default_factory=dict)

    def add_to_inbox(self, reviewer_id: str, item: ReviewerInboxItem) -> None:
        """Add an item to a reviewer's inbox."""
        if reviewer_id not in self._inbox:
            self._inbox[reviewer_id] = []
        self._inbox[reviewer_id].append(item)

    def get_inbox(self, reviewer_id: str, triage_filter: TriageLevel | None = None, priority: str | None = None) -> list[ReviewerInboxItem]:
        """Get a reviewer's inbox, sorted by priority then SLA."""
        items = self._inbox.get(reviewer_id, [])
        if triage_filter:
            items = [i for i in items if i.triage_level == triage_filter]
        if priority:
            items = [i for i in items if i.priority == priority]

        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda i: (priority_order.get(i.priority, 99), i.sla_deadline))
        return items

    def get_inbox_summary(self, reviewer_id: str) -> dict[str, Any]:
        """Get a summary of the reviewer's inbox."""
        items = self._inbox.get(reviewer_id, [])
        return {
            "total": len(items),
            "by_triage": {
                level.value: sum(1 for i in items if i.triage_level == level)
                for level in TriageLevel
            },
            "by_priority": {
                p: sum(1 for i in items if i.priority == p)
                for p in ["critical", "high", "medium", "low"]
            },
            "sla_breached": sum(1 for i in items if i.sla_deadline < datetime.utcnow().isoformat()),
            "high_confidence_items": sum(1 for i in items if i.triage_level == TriageLevel.HIGH_CONFIDENCE),
        }

    def triage_findings(self, findings: list[dict]) -> list[dict]:
        """Triage findings by AI confidence and risk score.

        Returns findings sorted by review priority (lowest confidence first).
        """
        def triage_score(finding: dict) -> float:
            confidence = finding.get("confidence", 0.5) or 0.5
            risk_score = finding.get("risk_score", 0.5) or 0.5
            # Low confidence + high risk = highest priority
            return (1.0 - confidence) * risk_score

        sorted_findings = sorted(findings, key=triage_score, reverse=True)
        for finding in sorted_findings:
            confidence = finding.get("confidence", 0.5) or 0.5
            if confidence >= 0.9:
                finding["triage"] = TriageLevel.HIGH_CONFIDENCE.value
            elif confidence >= 0.7:
                finding["triage"] = TriageLevel.MEDIUM_CONFIDENCE.value
            elif confidence >= 0.5:
                finding["triage"] = TriageLevel.LOW_CONFIDENCE.value
            else:
                finding["triage"] = TriageLevel.FLAGGED.value

        return sorted_findings

    def group_findings(self, findings: list[dict]) -> list[FindingGroup]:
        """Group findings for bulk resolution."""
        groups: dict[str, list[dict]] = {}

        for finding in findings:
            # Group by clause type
            clause_type = finding.get("clause_type", "other")
            key = f"clause:{clause_type}"
            if key not in groups:
                groups[key] = []
            groups[key].append(finding)

        result = []
        for key, group_findings in groups.items():
            if len(group_findings) < 2:
                continue
            clause_type = key.split(":")[1]
            avg_conf = sum(f.get("confidence", 0.5) or 0.5 for f in group_findings) / len(group_findings)
            result.append(FindingGroup(
                group_id=f"group_{key}",
                group_type="same_clause_type",
                label=f"{len(group_findings)} {clause_type} findings",
                finding_count=len(group_findings),
                ai_confidence_avg=round(avg_conf, 4),
                can_bulk_resolve=avg_conf > 0.8,
                findings=group_findings,
            ))

        return sorted(result, key=lambda g: g.finding_count, reverse=True)

    def get_evidence_context(self, chunk_text: str, surrounding_chunks: list[dict] | None = None) -> list[EvidenceChunk]:
        """Get evidence context for evidence-first review mode."""
        evidence = []

        # Primary chunk
        evidence.append(EvidenceChunk(
            chunk_id="primary",
            text=chunk_text[:500],
            relevance_score=1.0,
        ))

        # Surrounding context
        if surrounding_chunks:
            for i, chunk in enumerate(surrounding_chunks):
                evidence.append(EvidenceChunk(
                    chunk_id=f"context_{i}",
                    text=(chunk.get("text", "") or "")[:500],
                    page_numbers=chunk.get("page_numbers", []),
                    section_heading=chunk.get("section_heading", ""),
                    clause_type=chunk.get("clause_type", ""),
                    relevance_score=0.5,
                ))

        return evidence

    def get_experience_status(self) -> dict[str, Any]:
        """Get reviewer experience system status."""
        total_items = sum(len(items) for items in self._inbox.values())
        return {
            "active_reviewers": len(self._inbox),
            "total_inbox_items": total_items,
            "avg_per_reviewer": round(total_items / max(len(self._inbox), 1), 1),
        }
