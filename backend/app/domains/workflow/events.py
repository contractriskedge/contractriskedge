"""Workflow-specific domain events extending the base EventBus.

Every workflow action emits a standard event for downstream consumers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.kernel.events.bus import DomainEvent

logger = logging.getLogger(__name__)


# ── Workflow Lifecycle Events ──────────────────────────────────────


@dataclass
class WorkflowStarted(DomainEvent):
    """Emitted when a new workflow instance starts."""
    workflow_id: str = ""
    pack_id: str = ""
    version_id: str = ""
    workflow_type: str = ""
    correlation_id: str = ""
    contract_id: str = ""
    initiator_id: str = ""


@dataclass
class WorkflowCompleted(DomainEvent):
    """Emitted when a workflow instance completes successfully."""
    workflow_id: str = ""
    pack_id: str = ""
    version_id: str = ""
    workflow_type: str = ""
    total_stages: int = 0
    total_sla_hours: float = 0.0
    sla_breached: bool = False


@dataclass
class WorkflowCancelled(DomainEvent):
    """Emitted when a workflow instance is cancelled."""
    workflow_id: str = ""
    pack_id: str = ""
    reason: str = ""
    cancelled_by: str = ""


# ── Stage Events ───────────────────────────────────────────────────


@dataclass
class StageEntered(DomainEvent):
    """Emitted when a workflow enters a new stage."""
    workflow_id: str = ""
    stage_name: str = ""
    stage_type: str = ""
    step_order: int = 0
    sla_hours: Optional[int] = None
    assigned_to: Optional[str] = None


@dataclass
class StageCompleted(DomainEvent):
    """Emitted when a workflow stage is completed."""
    workflow_id: str = ""
    stage_name: str = ""
    stage_type: str = ""
    step_order: int = 0
    result: str = ""
    completed_by: str = ""


# ── Approval Events ────────────────────────────────────────────────


@dataclass
class ApprovalGranted(DomainEvent):
    """Emitted when an approval is granted for a stage."""
    workflow_id: str = ""
    stage_name: str = ""
    approved_by: str = ""
    approval_reason: str = ""
    approval_type: str = "standard"  # standard, exec_escalation, auto


@dataclass
class ApprovalRejected(DomainEvent):
    """Emitted when an approval is rejected for a stage."""
    workflow_id: str = ""
    stage_name: str = ""
    rejected_by: str = ""
    rejection_reason: str = ""


# ── Signature Events ───────────────────────────────────────────────


@dataclass
class SignatureSent(DomainEvent):
    """Emitted when a signature request is sent."""
    workflow_id: str = ""
    envelope_id: str = ""
    signer_count: int = 0
    provider: str = ""


@dataclass
class SignatureCompleted(DomainEvent):
    """Emitted when all signatures are completed."""
    workflow_id: str = ""
    envelope_id: str = ""
    provider: str = ""
    certificate_url: str = ""


# ── Obligation Events ──────────────────────────────────────────────


@dataclass
class ObligationCreated(DomainEvent):
    """Emitted when an obligation is created from a workflow."""
    workflow_id: str = ""
    obligation_id: str = ""
    obligation_type: str = ""
    due_date: Optional[str] = None
    assigned_to: str = ""


# ── Alert / Escalation Events ──────────────────────────────────────


@dataclass
class WorkflowEscalated(DomainEvent):
    """Emitted when a workflow is escalated to a higher authority."""
    workflow_id: str = ""
    stage_name: str = ""
    escalated_from: str = ""
    escalated_to: str = ""
    reason: str = ""


@dataclass
class WorkflowBreached(DomainEvent):
    """Emitted when a workflow SLA is breached."""
    workflow_id: str = ""
    stage_name: str = ""
    sla_hours: int = 0
    elapsed_hours: float = 0.0
    assigned_to: Optional[str] = None


# ── Rule Evaluation Events ─────────────────────────────────────────


@dataclass
class RuleMatched(DomainEvent):
    """Emitted when a rule condition evaluates to true."""
    workflow_id: str = ""
    rule_id: str = ""
    rule_summary: str = ""
    execution_time_ms: float = 0.0


@dataclass
class RuleSkipped(DomainEvent):
    """Emitted when a rule is skipped (condition false or error)."""
    workflow_id: str = ""
    rule_id: str = ""
    rule_summary: str = ""
    reason: str = ""


# ── Event Registry ─────────────────────────────────────────────────


WORKFLOW_EVENT_TYPES: dict[str, type[DomainEvent]] = {
    "workflow.started": WorkflowStarted,
    "workflow.completed": WorkflowCompleted,
    "workflow.cancelled": WorkflowCancelled,
    "stage.entered": StageEntered,
    "stage.completed": StageCompleted,
    "approval.granted": ApprovalGranted,
    "approval.rejected": ApprovalRejected,
    "signature.sent": SignatureSent,
    "signature.completed": SignatureCompleted,
    "obligation.created": ObligationCreated,
    "workflow.escalated": WorkflowEscalated,
    "workflow.breached": WorkflowBreached,
    "rule.matched": RuleMatched,
    "rule.skipped": RuleSkipped,
}
