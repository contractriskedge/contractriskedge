"""Risk Delta Engine — tracks how review decisions change risk across versions.

Enterprise semantics:
- Each review decision (accept/reject/modify a redline) produces a RiskDelta
- Deltas accumulate across a review session to show risk progression
- Version transitions capture the net risk change from one version to the next
- The engine supports both point-in-time snapshots and cumulative timelines

Object chain:
  Finding → Suggested Mitigation → Review Decision → RiskDelta → Version Impact
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _uuid_or_none(val: Any) -> Optional[str]:
    """Convert a UUID value to string, or None if it's None/empty.

    This is critical because str(None) produces the string 'None'
    which PostgreSQL cannot parse as a UUID, causing:
        invalid UUID 'None': length must be between 32..36 characters, got 4
    """
    if val is None:
        return None
    s = str(val)
    return s if s and s != "None" else None


class DeltaType(str, PyEnum):
    """Classification of a risk delta event."""
    MITIGATION = "mitigation"           # Risk reduced by accepting a mitigation
    ACCEPTANCE = "acceptance"           # Risk knowingly accepted (acknowledged)
    DISMISSAL = "dismissal"             # Risk dismissed as false positive
    REVERSAL = "reversal"               # Previously mitigated risk re-opened
    ESCALATION = "escalation"           # Risk escalated due to new findings
    VERSION_TRANSITION = "version_transition"  # Net change across versions


@dataclass
class RiskDelta:
    """A single risk delta event — one decision's impact on exposure.

    This is the core unit of the risk timeline. Every review decision
    (accept redline, reject, modify, acknowledge finding, dismiss)
    produces exactly one RiskDelta.
    """
    delta_id: str
    review_id: str
    tenant_id: str

    # What changed
    delta_type: DeltaType
    finding_id: Optional[str] = None
    redline_id: Optional[str] = None

    # The numeric impact
    previous_risk: float = 0.0          # Exposure before this decision
    new_risk: float = 0.0               # Exposure after this decision
    delta_amount: float = 0.0           # new_risk - previous_risk (negative = reduction)
    delta_pct: float = 0.0              # Relative change as percentage

    # Who and when
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    decision: Optional[str] = None      # "accepted", "rejected", "modified", "acknowledged", "dismissed"
    rationale: Optional[str] = None     # User-provided reason

    # Version context
    version_number: Optional[int] = None
    version_id: Optional[str] = None

    # Traceability
    clause_category: Optional[str] = None
    severity: Optional[str] = None
    finding_title: Optional[str] = None
    mitigation_type: Optional[str] = None
    mitigation_effectiveness: Optional[float] = None

    # Metadata
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "delta_id": self.delta_id,
            "review_id": self.review_id,
            "delta_type": self.delta_type.value,
            "finding_id": self.finding_id,
            "redline_id": self.redline_id,
            "previous_risk": round(self.previous_risk, 4),
            "new_risk": round(self.new_risk, 4),
            "delta_amount": round(self.delta_amount, 4),
            "delta_pct": round(self.delta_pct, 2),
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "decision": self.decision,
            "rationale": self.rationale,
            "version_number": self.version_number,
            "version_id": self.version_id,
            "clause_category": self.clause_category,
            "severity": self.severity,
            "finding_title": self.finding_title,
            "mitigation_type": self.mitigation_type,
            "mitigation_effectiveness": self.mitigation_effectiveness,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class VersionImpact:
    """Net risk impact of a version transition.

    Aggregates all RiskDeltas between two versions to show
    the overall effect of a review cycle.
    """
    version_number: int
    version_id: Optional[str] = None
    version_label: Optional[str] = None  # e.g. "v1 — Original", "v2 — Redlined", "v3 — Final"

    # Risk state at this version
    entry_risk: float = 0.0              # Risk when this version was created
    exit_risk: float = 0.0               # Risk after all decisions in this version
    net_delta: float = 0.0               # exit_risk - entry_risk

    # Breakdown of deltas in this version
    total_mitigated: float = 0.0
    total_accepted: float = 0.0
    total_dismissed: float = 0.0
    total_reversed: float = 0.0
    total_escalated: float = 0.0

    # Constituent deltas
    deltas: list[RiskDelta] = field(default_factory=list)

    # Metadata
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    change_summary: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_number": self.version_number,
            "version_id": self.version_id,
            "version_label": self.version_label,
            "entry_risk": round(self.entry_risk, 4),
            "exit_risk": round(self.exit_risk, 4),
            "net_delta": round(self.net_delta, 4),
            "total_mitigated": round(self.total_mitigated, 4),
            "total_accepted": round(self.total_accepted, 4),
            "total_dismissed": round(self.total_dismissed, 4),
            "total_reversed": round(self.total_reversed, 4),
            "total_escalated": round(self.total_escalated, 4),
            "delta_count": len(self.deltas),
            "deltas": [d.to_dict() for d in self.deltas],
            "created_by": self.created_by,
            "created_at": self.created_at,
            "change_summary": self.change_summary,
        }


class RiskDeltaEngine:
    """Computes and tracks risk changes across review decisions and versions.

    Usage:
        engine = RiskDeltaEngine(session, tenant_id)
        delta = await engine.compute_redline_decision_delta(
            review_id, finding, redline, decision="accepted", actor_id=user_id
        )
        await engine.persist_delta(delta)
        timeline = await engine.get_risk_timeline(review_id)
    """

    def __init__(self, session, tenant_id: str) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def compute_redline_decision_delta(
        self,
        review_id: str,
        finding: Any,
        redline: Any,
        decision: str,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None,
        rationale: Optional[str] = None,
        current_risk: Optional[float] = None,
        version_number: Optional[int] = None,
        version_id: Optional[str] = None,
    ) -> RiskDelta:
        """Compute the risk delta for a single redline decision.

        Args:
            review_id: The review this decision belongs to.
            finding: The finding object (must have .risk_score, .severity, .title).
            redline: The redline object (must have .redline_id, .redline_metadata).
            decision: One of "accepted", "rejected", "modified", "acknowledged", "dismissed".
            actor_id: Who made the decision.
            actor_name: Display name of the decision-maker.
            rationale: Why the decision was made.
            current_risk: The current remaining exposure before this decision.
            version_number: Which version this delta belongs to.
            version_id: The specific version record ID.

        Returns:
            A RiskDelta with computed impact.
        """
        from app.domains.review.risk_scoring import SEVERITY_WEIGHTS, normalize_severity

        severity = normalize_severity(getattr(finding, "severity", None))
        severity_weight = SEVERITY_WEIGHTS.get(severity, 0.4)
        finding_risk = getattr(finding, "risk_score", None) or severity_weight

        # Determine delta direction and magnitude based on decision
        if decision in ("accepted", "modified"):
            # Redline accepted → risk is mitigated
            # The mitigation effectiveness varies by clause type
            clause_cat = getattr(finding, "clause_type", None) or ""
            mitigation_effect = self._estimate_mitigation_effect(clause_cat, severity)
            delta_amount = -finding_risk * mitigation_effect
            delta_type = DeltaType.MITIGATION
        elif decision == "acknowledged":
            # Finding acknowledged → risk is knowingly retained
            delta_amount = 0.0  # No change — risk is accepted, not removed
            delta_type = DeltaType.ACCEPTANCE
        elif decision in ("dismissed", "false_positive"):
            # Finding dismissed → risk removed from equation
            delta_amount = -finding_risk
            delta_type = DeltaType.DISMISSAL
        elif decision == "rejected":
            # Redline rejected → risk remains (could increase if mitigation was expected)
            delta_amount = 0.0
            delta_type = DeltaType.ACCEPTANCE
        else:
            delta_amount = 0.0
            delta_type = DeltaType.ACCEPTANCE

        # Extract mitigation type from redline metadata if available
        meta = dict(redline.redline_metadata) if hasattr(redline, "redline_metadata") and redline.redline_metadata else {}
        trace = meta.get("traceability", {}) if isinstance(meta.get("traceability"), dict) else {}
        mitigation_type = trace.get("mitigation_strategy", "") if isinstance(trace, dict) else ""

        previous = current_risk if current_risk is not None else finding_risk
        new_risk_val = max(0.0, previous + delta_amount)
        delta_pct_val = ((new_risk_val - previous) / previous * 100) if previous > 0 else 0.0

        now = datetime.utcnow().isoformat() + "Z"

        return RiskDelta(
            delta_id=str(uuid.uuid4()),
            review_id=review_id,
            tenant_id=self._tenant_id,
            delta_type=delta_type,
            finding_id=_uuid_or_none(getattr(finding, "finding_id", None)),
            redline_id=_uuid_or_none(getattr(redline, "redline_id", None)),
            previous_risk=previous,
            new_risk=new_risk_val,
            delta_amount=round(delta_amount, 4),
            delta_pct=round(delta_pct_val, 2),
            actor_id=actor_id,
            actor_name=actor_name,
            decision=decision,
            rationale=rationale,
            version_number=version_number,
            version_id=version_id,
            clause_category=getattr(finding, "clause_type", None),
            severity=severity,
            finding_title=getattr(finding, "title", ""),
            mitigation_type=mitigation_type if mitigation_type else None,
            mitigation_effectiveness=abs(delta_amount / finding_risk) if finding_risk > 0 else None,
            created_at=now,
        )

    async def compute_version_transition(
        self,
        review_id: str,
        from_version: Optional[int],
        to_version: int,
        deltas: list[RiskDelta],
        entry_risk: float = 0.0,
    ) -> VersionImpact:
        """Aggregate a set of deltas into a version transition impact.

        Args:
            review_id: The review.
            from_version: Previous version number (None for first version).
            to_version: The new version number.
            deltas: All RiskDeltas that occurred in this version.
            entry_risk: Risk score at version entry.

        Returns:
            A VersionImpact aggregating all deltas.
        """
        total_mitigated = sum(d.delta_amount for d in deltas if d.delta_type == DeltaType.MITIGATION)
        total_accepted = sum(d.delta_amount for d in deltas if d.delta_type == DeltaType.ACCEPTANCE)
        total_dismissed = sum(d.delta_amount for d in deltas if d.delta_type == DeltaType.DISMISSAL)
        total_reversed = sum(d.delta_amount for d in deltas if d.delta_type == DeltaType.REVERSAL)
        total_escalated = sum(d.delta_amount for d in deltas if d.delta_type == DeltaType.ESCALATION)

        net_delta = total_mitigated + total_accepted + total_dismissed + total_reversed + total_escalated
        exit_risk = max(0.0, entry_risk + net_delta)

        version_labels = {1: "v1 — Original", 2: "v2 — Redlined", 3: "v3 — Final Approved"}
        version_label = version_labels.get(to_version, f"v{to_version}")

        now = datetime.utcnow().isoformat() + "Z"
        change_summary = self._summarize_changes(total_mitigated, total_accepted, total_dismissed, total_reversed, total_escalated)

        return VersionImpact(
            version_number=to_version,
            version_label=version_label,
            entry_risk=entry_risk,
            exit_risk=round(exit_risk, 4),
            net_delta=round(net_delta, 4),
            total_mitigated=round(abs(total_mitigated), 4),
            total_accepted=round(abs(total_accepted), 4),
            total_dismissed=round(abs(total_dismissed), 4),
            total_reversed=round(abs(total_reversed), 4),
            total_escalated=round(abs(total_escalated), 4),
            deltas=deltas,
            created_at=now,
            change_summary=change_summary,
        )

    async def persist_delta(self, delta: RiskDelta) -> None:
        """Persist a risk delta event to the database."""
        from app.domains.review.models import RiskDeltaEvent

        event = RiskDeltaEvent(
            delta_id=delta.delta_id,
            review_id=delta.review_id,
            tenant_id=self._tenant_id,
            delta_type=delta.delta_type.value,
            finding_id=delta.finding_id,
            redline_id=delta.redline_id,
            previous_risk=delta.previous_risk,
            new_risk=delta.new_risk,
            delta_amount=delta.delta_amount,
            delta_pct=delta.delta_pct,
            actor_id=delta.actor_id,
            actor_name=delta.actor_name,
            decision=delta.decision,
            rationale=delta.rationale,
            version_number=delta.version_number,
            version_id=delta.version_id,
            clause_category=delta.clause_category,
            severity=delta.severity,
            finding_title=delta.finding_title,
            mitigation_type=delta.mitigation_type,
            mitigation_effectiveness=delta.mitigation_effectiveness,
            extra_metadata=delta.metadata,
        )
        self._session.add(event)
        await self._session.flush()

    async def get_risk_timeline(
        self,
        review_id: str,
    ) -> list[RiskDelta]:
        """Get the full ordered timeline of risk deltas for a review.

        Returns deltas ordered by creation time ascending.
        """
        from app.domains.review.models import RiskDeltaEvent
        from sqlalchemy import select

        result = await self._session.execute(
            select(RiskDeltaEvent)
            .where(
                RiskDeltaEvent.review_id == review_id,
                RiskDeltaEvent.tenant_id == self._tenant_id,
            )
            .order_by(RiskDeltaEvent.created_at.asc())
        )
        events = result.scalars().all()
        return [self._event_to_delta(e) for e in events]

    async def get_version_impacts(
        self,
        review_id: str,
    ) -> list[VersionImpact]:
        """Get risk impacts grouped by version for a review.

        Returns a list of VersionImpact objects, one per version,
        ordered by version number ascending.
        """
        from collections import defaultdict

        deltas = await self.get_risk_timeline(review_id)

        # Group deltas by version
        by_version: dict[int, list[RiskDelta]] = defaultdict(list)
        for d in deltas:
            v = d.version_number or 1
            by_version[v].append(d)

        # Compute impacts per version
        impacts = []
        sorted_versions = sorted(by_version.keys())
        running_risk = 0.0

        for i, vnum in enumerate(sorted_versions):
            version_deltas = by_version[vnum]
            # Entry risk is the exit risk of the previous version, or 0
            entry = running_risk
            impact = await self.compute_version_transition(
                review_id=review_id,
                from_version=sorted_versions[i - 1] if i > 0 else None,
                to_version=vnum,
                deltas=version_deltas,
                entry_risk=entry,
            )
            running_risk = impact.exit_risk
            impacts.append(impact)

        return impacts

    async def get_risk_waterfall(
        self,
        review_id: str,
        original_risk: float = 0.0,
    ) -> dict[str, Any]:
        """Build a waterfall chart data structure for the risk timeline.

        Returns:
        {
            "original_risk": 0.85,
            "current_risk": 0.45,
            "segments": [
                {"label": "Original AI Risk", "value": 0.85, "type": "start"},
                {"label": "Mitigated: Indemnification", "value": -0.20, "type": "mitigation"},
                {"label": "Accepted: Liability cap", "value": 0.0, "type": "acceptance"},
                {"label": "Dismissed: Warranty scope", "value": -0.15, "type": "dismissal"},
                {"label": "Remaining Exposure", "value": 0.45, "type": "end"},
            ]
        }
        """
        deltas = await self.get_risk_timeline(review_id)
        segments = [{
            "label": "Original AI Risk",
            "value": round(original_risk, 4),
            "type": "start",
        }]

        running = original_risk
        for d in deltas:
            if d.delta_amount < 0:
                seg_type = "mitigation" if d.delta_type == DeltaType.MITIGATION else "dismissal"
            elif d.delta_amount > 0:
                seg_type = "escalation"
            else:
                seg_type = "acceptance"

            label_parts = [seg_type.title()]
            if d.finding_title:
                label_parts.append(f": {d.finding_title[:60]}")
            elif d.clause_category:
                label_parts.append(f": {d.clause_category.replace('_', ' ').title()}")

            segments.append({
                "label": "".join(label_parts),
                "value": round(d.delta_amount, 4),
                "type": seg_type,
                "delta_id": d.delta_id,
            })
            running += d.delta_amount

        segments.append({
            "label": "Remaining Exposure",
            "value": round(max(0.0, running), 4),
            "type": "end",
        })

        return {
            "original_risk": round(original_risk, 4),
            "current_risk": round(max(0.0, running), 4),
            "segments": segments,
        }

    def _estimate_mitigation_effect(
        self,
        clause_category: Optional[str],
        severity: str,
    ) -> float:
        """Estimate how much a mitigation reduces risk for a clause type."""
        from app.domains.review.risk_scoring import SEVERITY_WEIGHTS

        # Base effectiveness by clause category
        category_base = {
            "liability_indemnity": 0.60,
            "intellectual_property": 0.55,
            "data_privacy": 0.50,
            "commercial_terms": 0.40,
            "termination_renewal": 0.45,
            "governance": 0.35,
            "security": 0.55,
            "compliance": 0.50,
        }
        base = category_base.get(clause_category or "", 0.40)

        # Severity modifier: higher severity = more room for reduction
        severity_modifier = {
            "critical": 1.0,
            "high": 0.85,
            "medium": 0.70,
            "low": 0.50,
            "info": 0.30,
        }
        mod = severity_modifier.get(severity, 0.70)

        return base * mod

    def _summarize_changes(
        self,
        mitigated: float,
        accepted: float,
        dismissed: float,
        reversed_: float,
        escalated: float,
    ) -> str:
        """Build a human-readable summary of changes."""
        parts = []
        if mitigated > 0:
            parts.append(f"Mitigated {mitigated:.1%} risk")
        if dismissed > 0:
            parts.append(f"Dismissed {dismissed:.1%} false positives")
        if accepted > 0:
            parts.append(f"Accepted {accepted:.1%} business risk")
        if reversed_ > 0:
            parts.append(f"Reversed {reversed_:.1%} prior mitigations")
        if escalated > 0:
            parts.append(f"Escalated {escalated:.1%} new risk")
        return "; ".join(parts) if parts else "No material changes"

    @staticmethod
    def _event_to_delta(event) -> RiskDelta:
        """Convert a DB RiskDeltaEvent ORM object to a RiskDelta dataclass."""
        return RiskDelta(
            delta_id=str(event.delta_id),
            review_id=str(event.review_id),
            tenant_id=str(event.tenant_id),
            delta_type=DeltaType(event.delta_type),
            finding_id=str(event.finding_id) if event.finding_id else None,
            redline_id=str(event.redline_id) if event.redline_id else None,
            previous_risk=float(event.previous_risk or 0.0),
            new_risk=float(event.new_risk or 0.0),
            delta_amount=float(event.delta_amount or 0.0),
            delta_pct=float(event.delta_pct or 0.0),
            actor_id=event.actor_id,
            actor_name=event.actor_name,
            decision=event.decision,
            rationale=event.rationale,
            version_number=event.version_number,
            version_id=str(event.version_id) if event.version_id else None,
            clause_category=event.clause_category,
            severity=event.severity,
            finding_title=event.finding_title,
            mitigation_type=event.mitigation_type,
            mitigation_effectiveness=float(event.mitigation_effectiveness) if event.mitigation_effectiveness else None,
            created_at=str(event.created_at) if event.created_at else "",
            metadata=dict(event.extra_metadata) if event.extra_metadata else {},
        )
