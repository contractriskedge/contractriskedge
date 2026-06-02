"""Autonomous Operations Layer — human-governed autonomous actions for escalation, balancing, recovery, rerouting, prioritization.

NOT full autonomy. Human-governed autonomy. That distinction matters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AutonomyLevel(str, Enum):
    SUGGEST = "suggest"           # Suggest action, human decides
    RECOMMEND = "recommend"       # Recommend with rationale, human approves
    AUTO_IF_SAFE = "auto_if_safe" # Auto-execute if within safe parameters
    AUTO_APPROVED = "auto_approved" # Auto-execute for pre-approved scenarios


class AutonomousActionType(str, Enum):
    ESCALATION = "escalation"
    REVIEWER_BALANCE = "reviewer_balance"
    SLA_RECOVERY = "sla_recovery"
    WORKFLOW_REROUTE = "workflow_reroute"
    RISK_PRIORITIZATION = "risk_prioritization"
    RENEWAL_PREPARATION = "renewal_preparation"
    POLICY_REMEDIATION = "policy_remediation"


@dataclass
class AutonomousAction:
    """An action proposed by the autonomous operations layer."""
    action_id: str
    action_type: AutonomousActionType
    title: str
    description: str
    rationale: str
    autonomy_level: AutonomyLevel
    impact_assessment: str = ""
    risk_level: str = "low"  # low, medium, high
    requires_approval: bool = True
    approved_by: str | None = None
    executed: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    executed_at: str | None = None


@dataclass
class AutonomousOperationsService:
    """Human-governed autonomous operations for enterprise coordination.

    Capabilities:
    - Autonomous escalation recommendations (escalate based on patterns)
    - Autonomous reviewer balancing (redistribute workload)
    - Autonomous SLA recovery actions (reroute when SLA at risk)
    - Autonomous workflow rerouting (optimize workflow paths)
    - Autonomous risk prioritization (reorder queues by risk)
    - Autonomous renewal preparation (start prep workflows)
    - Autonomous policy remediation suggestions (fix policy gaps)
    """

    _action_history: list[AutonomousAction] = field(default_factory=list)
    _execution_count: int = 0

    def suggest_escalation(self, context: dict[str, Any]) -> AutonomousAction:
        """Suggest autonomous escalation based on patterns."""
        risk_score = context.get("risk_score", 0.5)
        sla_remaining = context.get("sla_remaining_minutes", 60)
        reviewer_load = context.get("reviewer_load", 0.5)

        if risk_score > 0.8 and sla_remaining < 30:
            level = AutonomyLevel.AUTO_IF_SAFE
            risk = "medium"
        elif risk_score > 0.6 or sla_remaining < 60:
            level = AutonomyLevel.RECOMMEND
            risk = "low"
        else:
            level = AutonomyLevel.SUGGEST
            risk = "low"

        action = AutonomousAction(
            action_id=f"esc_{datetime.utcnow().timestamp()}",
            action_type=AutonomousActionType.ESCALATION,
            title="Automatic Escalation Recommended",
            description=f"Escalate to {context.get('target_role', 'senior')} due to risk ({risk_score:.2f}) and SLA pressure",
            rationale=f"Risk score {risk_score:.2f} exceeds threshold, SLA remaining {sla_remaining:.0f}min, reviewer load {reviewer_load:.0%}",
            autonomy_level=level,
            risk_level=risk,
            requires_approval=level in (AutonomyLevel.SUGGEST, AutonomyLevel.RECOMMEND),
        )
        self._action_history.append(action)
        return action

    def suggest_reviewer_balance(self, workloads: list[dict]) -> list[AutonomousAction]:
        """Suggest autonomous reviewer balancing."""
        actions = []
        overloaded = [w for w in workloads if w.get("utilization", 0) > 0.8]
        underloaded = [w for w in workloads if w.get("utilization", 0) < 0.4]

        for over in overloaded:
            if underloaded:
                target = underloaded[0]
                action = AutonomousAction(
                    action_id=f"bal_{over['reviewer_id'][:8]}_{datetime.utcnow().timestamp()}",
                    action_type=AutonomousActionType.REVIEWER_BALANCE,
                    title=f"Rebalance {over['reviewer_id'][:8]} workload",
                    description=f"Move {over.get('overload_count', 1)} items to {target['reviewer_id'][:8]}",
                    rationale=f"Reviewer at {over['utilization']:.0%} capacity, target at {target['utilization']:.0%}",
                    autonomy_level=AutonomyLevel.AUTO_IF_SAFE,
                    risk_level="low",
                    requires_approval=False,
                )
                actions.append(action)
                self._action_history.append(action)
                underloaded.pop(0)

        return actions

    def suggest_sla_recovery(self, at_risk_workflows: list[dict]) -> list[AutonomousAction]:
        """Suggest autonomous SLA recovery actions."""
        actions = []
        for wf in at_risk_workflows:
            remaining_pct = wf.get("sla_remaining_pct", 0)
            if remaining_pct < 10:
                level = AutonomyLevel.AUTO_IF_SAFE
            elif remaining_pct < 25:
                level = AutonomyLevel.RECOMMEND
            else:
                level = AutonomyLevel.SUGGEST

            action = AutonomousAction(
                action_id=f"sla_{wf.get('workflow_id', 'unknown')[:8]}_{datetime.utcnow().timestamp()}",
                action_type=AutonomousActionType.SLA_RECOVERY,
                title=f"SLA Recovery: {wf.get('workflow_name', 'Unknown')}",
                description=f"Only {remaining_pct:.0f}% SLA remaining — prioritize review",
                rationale=f"Workflow {wf.get('workflow_id', 'unknown')[:8]} has {remaining_pct:.0f}% SLA remaining",
                autonomy_level=level,
                risk_level="medium" if remaining_pct < 10 else "low",
                requires_approval=level == AutonomyLevel.SUGGEST,
            )
            actions.append(action)
            self._action_history.append(action)

        return actions

    def suggest_risk_prioritization(self, queue: list[dict]) -> AutonomousAction:
        """Suggest autonomous queue reprioritization by risk."""
        high_risk = [q for q in queue if q.get("risk_score", 0) or 0 > 0.7]
        if not high_risk:
            raise ValueError("No high-risk items to prioritize")

        action = AutonomousAction(
            action_id=f"prio_{datetime.utcnow().timestamp()}",
            action_type=AutonomousActionType.RISK_PRIORITIZATION,
            title=f"Prioritize {len(high_risk)} High-Risk Items",
            description=f"Move {len(high_risk)} high-risk items to top of queue",
            rationale=f"{len(high_risk)} items with risk score > 0.7 need immediate attention",
            autonomy_level=AutonomyLevel.AUTO_IF_SAFE,
            risk_level="low",
            requires_approval=False,
        )
        self._action_history.append(action)
        return action

    def suggest_renewal_preparation(self, renewals: list[dict]) -> list[AutonomousAction]:
        """Suggest autonomous renewal preparation."""
        actions = []
        for renewal in renewals:
            days_until = renewal.get("days_until_renewal", 365)
            risk = renewal.get("risk_score", 0.5)

            if days_until <= 30:
                level = AutonomyLevel.AUTO_IF_SAFE
            elif days_until <= 60 or risk > 0.6:
                level = AutonomyLevel.RECOMMEND
            else:
                level = AutonomyLevel.SUGGEST

            action = AutonomousAction(
                action_id=f"ren_{renewal.get('contract_id', 'unknown')[:8]}_{datetime.utcnow().timestamp()}",
                action_type=AutonomousActionType.RENEWAL_PREPARATION,
                title=f"Prepare {renewal.get('contract_name', 'Unknown')} Renewal",
                description=f"Begin renewal preparation — {days_until} days until renewal",
                rationale=f"Renewal in {days_until} days with risk score {risk:.2f}",
                autonomy_level=level,
                risk_level="medium" if days_until < 30 else "low",
                requires_approval=level == AutonomyLevel.SUGGEST,
            )
            actions.append(action)
            self._action_history.append(action)

        return actions

    def approve_action(self, action_id: str, approved_by: str) -> bool:
        """Approve a proposed autonomous action."""
        for action in self._action_history:
            if action.action_id == action_id and action.requires_approval:
                action.approved_by = approved_by
                action.executed = True
                action.executed_at = datetime.utcnow().isoformat()
                self._execution_count += 1
                return True
        return False

    def get_pending_actions(self) -> list[AutonomousAction]:
        """Get all pending actions requiring approval."""
        return [a for a in self._action_history if a.requires_approval and not a.executed]

    def get_executed_actions(self) -> list[AutonomousAction]:
        """Get all executed actions."""
        return [a for a in self._action_history if a.executed]

    def get_autonomy_report(self) -> dict[str, Any]:
        """Get autonomous operations report."""
        total = len(self._action_history)
        executed = self._execution_count
        return {
            "total_actions_proposed": total,
            "actions_executed": executed,
            "execution_rate": round(executed / max(total, 1) * 100, 1),
            "by_type": {
                t.value: sum(1 for a in self._action_history if a.action_type == t)
                for t in AutonomousActionType
            },
            "pending_approvals": len(self.get_pending_actions()),
        }


# ── Global singleton ───────────────────────────────────────────────

autonomous_ops = AutonomousOperationsService()
