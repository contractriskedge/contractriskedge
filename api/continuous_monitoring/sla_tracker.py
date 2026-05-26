"""SLA obligation deadline tracker (V2-018).

Tracks SLA obligations extracted from contracts, computes breach risk
scores, and manages escalation routing when deadlines are at risk or
breached. Integrates with the obligation event bus.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .event_bus import ObligationEventBus, ObligationEvent, EventType, EventPriority

logger = logging.getLogger(__name__)


@dataclass
class SLAObligation:
    """Represents a single SLA obligation from a contract."""

    sla_id: str
    contract_id: str
    tenant_id: str
    title: str
    description: str
    category: str  # uptime, response_time, resolution_time, data_retention, etc.
    target_value: str  # e.g., "99.9%", "4 hours", "24 hours"
    due_date: Optional[str] = None
    status: str = "active"  # active, at_risk, breached, fulfilled, waived
    breach_risk_score: float = 0.0  # 0-10
    severity: str = "medium"  # low, medium, high, critical
    assigned_to: Optional[str] = None
    escalation_level: int = 0
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "sla_id": self.sla_id,
            "contract_id": self.contract_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "target_value": self.target_value,
            "due_date": self.due_date,
            "status": self.status,
            "breach_risk_score": round(self.breach_risk_score, 2),
            "severity": self.severity,
            "assigned_to": self.assigned_to,
            "escalation_level": self.escalation_level,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SLATracker:
    """Tracks SLA obligations and computes breach risk.

    Monitors SLA deadlines, computes risk scores based on time
    remaining and obligation severity, and manages escalation routing.

    Usage:
        tracker = SLATracker(event_bus)
        await tracker.register_obligation(sla)
        await tracker.check_deadlines()
        breaches = await tracker.get_breach_risk_report("tenant-123")
    """

    def __init__(
        self,
        event_bus: ObligationEventBus,
        db_pool: Optional[Any] = None,
    ) -> None:
        """Initialize the SLA tracker.

        Args:
            event_bus: The obligation event bus.
            db_pool: Optional database pool.
        """
        self._event_bus = event_bus
        self._db_pool = db_pool
        self._obligations: Dict[str, SLAObligation] = {}
        self._escalation_matrix = {
            "critical": {"warning_days": 7, "breach_risk_threshold": 7.0},
            "high": {"warning_days": 14, "breach_risk_threshold": 6.0},
            "medium": {"warning_days": 30, "breach_risk_threshold": 5.0},
            "low": {"warning_days": 60, "breach_risk_threshold": 4.0},
        }

    async def register_obligation(self, sla: SLAObligation) -> str:
        """Register a new SLA obligation for tracking.

        Args:
            sla: The SLA obligation to track.

        Returns:
            The SLA ID.
        """
        self._obligations[sla.sla_id] = sla
        logger.info("Registered SLA %s: %s (category=%s, severity=%s)",
                     sla.sla_id, sla.title, sla.category, sla.severity)
        return sla.sla_id

    async def register_obligations_batch(self, slas: List[SLAObligation]) -> List[str]:
        """Register multiple SLA obligations at once.

        Args:
            slas: List of SLA obligations.

        Returns:
            List of SLA IDs.
        """
        ids = []
        for sla in slas:
            ids.append(await self.register_obligation(sla))
        return ids

    async def update_status(
        self,
        sla_id: str,
        status: str,
        notes: Optional[str] = None,
    ) -> Optional[SLAObligation]:
        """Update the status of an SLA obligation.

        Args:
            sla_id: The SLA to update.
            status: New status (active, at_risk, breached, fulfilled, waived).
            notes: Optional update notes.

        Returns:
            Updated SLA or None if not found.
        """
        sla = self._obligations.get(sla_id)
        if not sla:
            logger.warning("SLA %s not found", sla_id)
            return None

        sla.status = status
        sla.updated_at = datetime.utcnow().isoformat()
        if notes:
            sla.notes = notes

        # Emit event for status changes
        if status == "breached":
            event = ObligationEventBus.create_event(
                event_type=EventType.SLA_BREACHED,
                contract_id=sla.contract_id,
                tenant_id=sla.tenant_id,
                title=f"SLA breached: {sla.title}",
                description=f"SLA obligation '{sla.title}' (target: {sla.target_value}) has been breached.",
                priority=EventPriority.CRITICAL if sla.severity in ("critical", "high") else EventPriority.HIGH,
                risk_score=sla.breach_risk_score,
                metadata={"sla_id": sla_id, "category": sla.category, "target_value": sla.target_value},
            )
            await self._event_bus.emit(event)
        elif status == "at_risk":
            event = ObligationEventBus.create_event(
                event_type=EventType.SLA_DEADLINE_APPROACHING,
                contract_id=sla.contract_id,
                tenant_id=sla.tenant_id,
                title=f"SLA at risk: {sla.title}",
                description=f"SLA obligation '{sla.title}' is at risk of breach.",
                priority=EventPriority.HIGH,
                risk_score=sla.breach_risk_score,
                metadata={"sla_id": sla_id, "category": sla.category},
            )
            await self._event_bus.emit(event)

        return sla

    async def check_deadlines(self) -> List[Dict[str, Any]]:
        """Check all SLA obligations for approaching deadlines.

        Computes breach risk scores and emits events for SLAs
        that are approaching their deadlines.

        Returns:
            List of SLA status dicts that triggered alerts.
        """
        today = datetime.utcnow()
        alerts: List[Dict[str, Any]] = []

        for sla in self._obligations.values():
            if sla.status in ("fulfilled", "waived"):
                continue

            if not sla.due_date:
                continue

            try:
                due = datetime.fromisoformat(sla.due_date)
            except (ValueError, TypeError):
                continue

            days_remaining = (due - today).days
            severity_config = self._escalation_matrix.get(sla.severity, self._escalation_matrix["medium"])
            warning_days = severity_config["warning_days"]

            # Compute breach risk score
            if days_remaining <= 0:
                # Already past due
                sla.breach_risk_score = min(10.0, 7.0 + abs(days_remaining) * 0.2)
                sla.status = "breached"
                await self.update_status(sla.sla_id, "breached")
                alerts.append({
                    "sla_id": sla.sla_id,
                    "contract_id": sla.contract_id,
                    "status": "breached",
                    "breach_risk_score": sla.breach_risk_score,
                    "days_overdue": abs(days_remaining),
                })
            elif days_remaining <= warning_days:
                # At risk
                risk = max(3.0, 10.0 - (days_remaining / warning_days) * 10.0)
                sla.breach_risk_score = round(risk, 2)
                if sla.status != "at_risk":
                    sla.status = "at_risk"
                    sla.escalation_level = min(3, sla.escalation_level + 1)
                    await self.update_status(sla.sla_id, "at_risk")
                    alerts.append({
                        "sla_id": sla.sla_id,
                        "contract_id": sla.contract_id,
                        "status": "at_risk",
                        "breach_risk_score": sla.breach_risk_score,
                        "days_remaining": days_remaining,
                        "escalation_level": sla.escalation_level,
                    })
            else:
                # Active - compute baseline risk
                sla.breach_risk_score = round(max(0.0, 3.0 - (days_remaining / 365) * 3.0), 2)
                sla.status = "active"

        if alerts:
            logger.info("SLA deadline check: %d alerts generated", len(alerts))

        return alerts

    async def get_breach_risk_report(self, tenant_id: str) -> Dict[str, Any]:
        """Generate a breach risk report for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with breach risk summary and details.
        """
        tenant_slas = [s for s in self._obligations.values() if s.tenant_id == tenant_id]

        active = sum(1 for s in tenant_slas if s.status == "active")
        at_risk = sum(1 for s in tenant_slas if s.status == "at_risk")
        breached = sum(1 for s in tenant_slas if s.status == "breached")
        fulfilled = sum(1 for s in tenant_slas if s.status == "fulfilled")

        high_risk = sum(1 for s in tenant_slas if s.breach_risk_score >= 7.0)
        medium_risk = sum(1 for s in tenant_slas if 4.0 <= s.breach_risk_score < 7.0)

        by_category: Dict[str, int] = {}
        for s in tenant_slas:
            by_category[s.category] = by_category.get(s.category, 0) + 1

        return {
            "tenant_id": tenant_id,
            "total_obligations": len(tenant_slas),
            "status_breakdown": {
                "active": active,
                "at_risk": at_risk,
                "breached": breached,
                "fulfilled": fulfilled,
            },
            "risk_breakdown": {
                "high_risk": high_risk,
                "medium_risk": medium_risk,
                "low_risk": len(tenant_slas) - high_risk - medium_risk,
            },
            "by_category": by_category,
            "overall_breach_risk_score": round(
                sum(s.breach_risk_score for s in tenant_slas) / max(len(tenant_slas), 1), 2
            ),
        }

    async def get_escalation_path(
        self,
        sla_id: str,
    ) -> Dict[str, Any]:
        """Get the escalation path for an SLA obligation.

        Args:
            sla_id: The SLA identifier.

        Returns:
            Dict with escalation details.
        """
        sla = self._obligations.get(sla_id)
        if not sla:
            return {"error": "SLA not found"}

        escalation_levels = {
            0: {"name": "Assigned Party", "action": "Notify assigned resource"},
            1: {"name": "Team Lead", "action": "Notify team lead for review"},
            2: {"name": "Department Manager", "action": "Escalate to department management"},
            3: {"name": "Executive", "action": "Executive-level escalation required"},
        }

        return {
            "sla_id": sla_id,
            "current_level": sla.escalation_level,
            "current_assignee": sla.assigned_to,
            "severity": sla.severity,
            "breach_risk_score": sla.breach_risk_score,
            "escalation_path": [
                {"level": level, **info}
                for level, info in escalation_levels.items()
                if level >= sla.escalation_level
            ],
        }
