"""Import AI review findings and redlines into a negotiation session."""

from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from app.domains.negotiation.models import (
    NegotiationIssue,
    NegotiationRedline,
)
from app.domains.negotiation.schemas import ClauseContentSchema
from app.domains.review.models import ReviewFinding, ReviewRedline
from app.domains.review.repository import ReviewRepository

_SEVERITY_TO_ISSUE = {
    "critical": "critical",
    "high": "major",
    "medium": "minor",
    "low": "minor",
    "info": "info",
    "blocker": "blocker",
}

_REDLINE_STATUS_MAP = {
    "proposed": "pending",
    "needs_legal_review": "pending",
    "customer_requested": "pending",
    "fallback_language": "pending",
    "modified": "pending",
    "accepted": "accepted",
    "rejected": "rejected",
    "superseded": "superseded",
    "invalid_mapping": "rejected",
}

_OPERATION_TO_TYPE = {
    "insert": "addition",
    "insertion": "addition",
    "add": "addition",
    "addition": "addition",
    "delete": "deletion",
    "deletion": "deletion",
    "remove": "deletion",
    "modification": "modification",
    "modify": "modification",
    "replace": "modification",
    "replacement": "modification",
}


def _clause_id_for_finding(finding: ReviewFinding) -> str:
    return f"finding-{finding.finding_id}"


def _clause_id_for_redline(redline: ReviewRedline, finding: Optional[ReviewFinding]) -> str:
    if finding:
        return _clause_id_for_finding(finding)
    clause_type = (redline.clause_type or "general").strip().lower()
    safe = re.sub(r"[^a-z0-9]+", "-", clause_type).strip("-") or "general"
    return f"clause-{safe}"


def _redline_type(redline: ReviewRedline) -> str:
    op = (redline.operation or "").strip().lower()
    if op in _OPERATION_TO_TYPE:
        return _OPERATION_TO_TYPE[op]
    if not (redline.original_text or "").strip():
        return "addition"
    if not (redline.proposed_text or "").strip():
        return "deletion"
    return "modification"


def _redline_title(redline: ReviewRedline, finding: Optional[ReviewFinding]) -> str:
    if redline.rationale and redline.rationale.strip():
        return redline.rationale.strip()[:500]
    if finding and finding.title:
        return finding.title[:500]
    text = (redline.proposed_text or redline.original_text or "Suggested change").strip()
    return text[:120] + ("…" if len(text) > 120 else "")


def _risk_level(value: Optional[str]) -> str:
    v = (value or "medium").strip().lower()
    if v in {"critical", "high", "medium", "low", "info"}:
        return v
    return "medium"


def build_clauses_from_findings(findings: list[ReviewFinding]) -> list[dict[str, Any]]:
    """Build negotiation clause snapshots from review findings."""
    clauses: list[dict[str, Any]] = []
    seen: set[str] = set()
    for finding in findings:
        clause_id = _clause_id_for_finding(finding)
        if clause_id in seen:
            continue
        seen.add(clause_id)
        section = ""
        if finding.page_numbers:
            section = str(finding.page_numbers[0])
        elif finding.page_number is not None:
            section = str(finding.page_number)
        content = (finding.source_text or finding.description or finding.title or "").strip()
        clauses.append(
            ClauseContentSchema(
                clause_id=clause_id,
                title=finding.title or finding.clause_type or "Clause",
                section_number=section,
                content=content,
                risk_level=_risk_level(finding.severity),
                category=(finding.clause_type or "general").strip().lower(),
            ).model_dump(by_alias=False)
        )
    return clauses


def map_review_redline(
    session_id: str,
    redline: ReviewRedline,
    finding: Optional[ReviewFinding],
    actor_id: str,
) -> NegotiationRedline:
    """Map a review redline row to a negotiation redline."""
    status = _REDLINE_STATUS_MAP.get(str(redline.status), "pending")
    return NegotiationRedline(
        redline_id=str(uuid.uuid4()),
        session_id=session_id,
        clause_id=_clause_id_for_redline(redline, finding),
        type=_redline_type(redline),
        title=_redline_title(redline, finding),
        original_text=redline.original_text or "",
        modified_text=redline.reviewer_modified_text or redline.proposed_text or "",
        author=redline.reviewed_by or actor_id or "AI Review",
        risk_level=_risk_level(redline.risk_level or (finding.severity if finding else None)),
        status=status,
        ai_generated=True,
        ai_confidence=redline.confidence,
    )


def map_finding_to_issue(
    session_id: str,
    finding: ReviewFinding,
    actor_id: str,
) -> NegotiationIssue:
    """Map an open review finding to a negotiation issue."""
    return NegotiationIssue(
        issue_id=str(uuid.uuid4()),
        session_id=session_id,
        clause_id=_clause_id_for_finding(finding),
        title=finding.title or "Review finding",
        description=(finding.description or finding.recommendation or "")[:2000],
        severity=_SEVERITY_TO_ISSUE.get((finding.severity or "major").lower(), "major"),
        status="open",
        created_by=actor_id or "AI Review",
        category=(finding.clause_type or "legal").strip().lower() or "legal",
    )


def build_extra_clauses_from_redlines(
    redlines: list[ReviewRedline],
    existing_clause_ids: set[str],
) -> list[dict[str, Any]]:
    """Add clause stubs for redlines not linked to a finding."""
    clauses: list[dict[str, Any]] = []
    for redline in redlines:
        clause_id = _clause_id_for_redline(redline, None)
        if clause_id in existing_clause_ids:
            continue
        existing_clause_ids.add(clause_id)
        content = (redline.original_text or redline.proposed_text or "").strip()
        clauses.append(
            ClauseContentSchema(
                clause_id=clause_id,
                title=redline.clause_type or "Clause",
                section_number="",
                content=content,
                risk_level=_risk_level(redline.risk_level),
                category=(redline.clause_type or "general").strip().lower(),
            ).model_dump(by_alias=False)
        )
    return clauses


async def load_review_import_data(
    review_repo: ReviewRepository,
    review_id: str,
    tenant_id: str,
) -> tuple[list[ReviewFinding], list[ReviewRedline]]:
    findings, _ = await review_repo.get_findings(review_id, tenant_id, page=1, page_size=500)
    redlines = await review_repo.get_redlines(review_id, tenant_id)
    return list(findings), list(redlines)
