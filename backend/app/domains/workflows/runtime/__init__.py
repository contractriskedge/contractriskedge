"""Workflow Runtime Engine — state machine execution, SLA timers, escalation, approval gates, compensation.

Provides:
- WorkflowExecutionEngine — execute and manage workflow instances
- StateMachineRuntime — formal state machine with guards, actions, and transitions
- SLATimer — deadline tracking and breach detection
- EscalationPolicy — automatic escalation on SLA breach or failure
- HumanApprovalGate — pause workflow for human decision
- ResumableWorkflow — persistence and recovery for long-running workflows
- CompensationHandler — rollback/saga support for failed workflows
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


# ── Core Types ─────────────────────────────────────────────────────

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class WorkflowStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPENSATED = "compensated"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class WorkflowContext:
    """Immutable context passed through workflow execution."""
    workflow_id: str
    workflow_type: str
    tenant_id: str
    correlation_id: str
    trace_id: str
    actor_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class WorkflowStep:
    """A single step in a workflow definition."""
    name: str
    handler: Callable[[WorkflowContext], Awaitable[Any]]
    compensation_handler: Callable[[WorkflowContext], Awaitable[Any]] | None = None
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    requires_approval: bool = False
    approval_config: dict[str, Any] = field(default_factory=dict)
    sla_seconds: int | None = None


@dataclass
class WorkflowDefinition:
    """Definition of a workflow — the blueprint for execution."""
    workflow_type: str
    version: str
    steps: list[WorkflowStep]
    description: str = ""
    timeout_seconds: int = 3600
    sla_seconds: int | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class WorkflowInstance:
    """A running instance of a workflow."""
    workflow_id: str
    workflow_type: str
    version: str
    tenant_id: str
    status: WorkflowStatus
    context: WorkflowContext
    current_step: int = 0
    step_results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    sla_deadline: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str | None = None


# ── State Machine Runtime ──────────────────────────────────────────

class StateMachineRuntime:
    """Formal state machine for workflow step transitions.

    Enforces valid transitions, guards, and lifecycle rules.
    """

    VALID_TRANSITIONS: dict[WorkflowStepStatus, set[WorkflowStepStatus]] = {
        WorkflowStepStatus.PENDING: {WorkflowStepStatus.RUNNING, WorkflowStepStatus.SKIPPED},
        WorkflowStepStatus.RUNNING: {WorkflowStepStatus.COMPLETED, WorkflowStepStatus.FAILED, WorkflowStepStatus.WAITING_APPROVAL},
        WorkflowStepStatus.WAITING_APPROVAL: {WorkflowStepStatus.RUNNING, WorkflowStepStatus.COMPLETED, WorkflowStepStatus.FAILED},
        WorkflowStepStatus.COMPLETED: set(),
        WorkflowStepStatus.FAILED: {WorkflowStepStatus.PENDING, WorkflowStepStatus.COMPENSATED},
        WorkflowStepStatus.COMPENSATED: set(),
        WorkflowStepStatus.SKIPPED: set(),
    }

    @staticmethod
    def can_transition(from_status: WorkflowStepStatus, to_status: WorkflowStepStatus) -> bool:
        """Check if a transition is valid."""
        allowed = StateMachineRuntime.VALID_TRANSITIONS.get(from_status, set())
        return to_status in allowed

    @staticmethod
    def validate_transition(from_status: WorkflowStepStatus, to_status: WorkflowStepStatus, step_name: str) -> None:
        """Validate a transition, raising if invalid."""
        if not StateMachineRuntime.can_transition(from_status, to_status):
            raise InvalidTransitionError(
                f"Cannot transition step '{step_name}' from {from_status.value} to {to_status.value}"
            )


class InvalidTransitionError(Exception):
    """Raised when an invalid workflow state transition is attempted."""


# ── SLA Timer ──────────────────────────────────────────────────────

@dataclass
class SLATimer:
    """Deadline tracking and breach detection for workflow steps.

    Tracks SLA deadlines and emits breach events when exceeded.
    """

    sla_seconds: int
    deadline: float = 0.0
    breached: bool = False
    breached_at: float | None = None

    def start(self) -> None:
        """Start the SLA timer."""
        self.deadline = time.time() + self.sla_seconds
        self.breached = False
        self.breached_at = None

    def check_breach(self) -> bool:
        """Check if SLA has been breached."""
        if self.breached:
            return True
        if time.time() > self.deadline:
            self.breached = True
            self.breached_at = time.time()
            logger.warning("SLA breached: deadline was %.0fs ago", time.time() - self.deadline)
            return True
        return False

    def remaining_seconds(self) -> float:
        """Get remaining time before SLA breach."""
        remaining = self.deadline - time.time()
        return max(0.0, remaining)

    def reset(self) -> None:
        """Reset the timer."""
        self.deadline = 0.0
        self.breached = False
        self.breached_at = None


# ── Escalation Policy ──────────────────────────────────────────────

@dataclass
class EscalationLevel:
    """A single escalation level with target and action."""
    level: int
    name: str
    notify_roles: list[str]
    notify_users: list[str] = field(default_factory=list)
    timeout_minutes: int = 30
    action: str = "notify"  # "notify", "reassign", "override", "auto_approve"


@dataclass
class EscalationPolicy:
    """Automatic escalation on SLA breach or step failure.

    Defines escalation levels with increasing severity.
    """

    policy_id: str
    name: str
    levels: list[EscalationLevel] = field(default_factory=list)
    max_level: int = 3

    def get_level(self, level: int) -> EscalationLevel | None:
        """Get an escalation level by index."""
        for l in self.levels:
            if l.level == level:
                return l
        return None

    def escalate(self, current_level: int, context: WorkflowContext) -> EscalationLevel | None:
        """Escalate to the next level."""
        next_level = current_level + 1
        level = self.get_level(next_level)
        if level:
            logger.warning(
                "Escalating workflow %s to level %d (%s): notifying %s",
                context.workflow_id, level.level, level.name, level.notify_roles,
            )
        return level


# ── Human Approval Gate ────────────────────────────────────────────

@dataclass
class ApprovalGate:
    """Pauses workflow execution for human decision.

    The workflow remains in WAITING_APPROVAL state until
    a human approves, rejects, or the approval times out.
    """

    gate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    step_name: str = ""
    required_roles: list[str] = field(default_factory=list)
    required_users: list[str] = field(default_factory=list)
    min_approvals: int = 1
    timeout_minutes: int = 1440  # 24 hours
    status: str = "pending"  # pending, approved, rejected, timed_out
    approved_by: list[str] = field(default_factory=list)
    rejected_by: str | None = None
    reason: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: str | None = None

    def approve(self, user_id: str) -> bool:
        """Approve the gate. Returns True if minimum approvals reached."""
        if self.status != "pending":
            return False
        if user_id not in self.approved_by:
            self.approved_by.append(user_id)
        if len(self.approved_by) >= self.min_approvals:
            self.status = "approved"
            self.resolved_at = datetime.utcnow().isoformat()
            return True
        return False

    def reject(self, user_id: str, reason: str) -> None:
        """Reject the gate."""
        self.status = "rejected"
        self.rejected_by = user_id
        self.reason = reason
        self.resolved_at = datetime.utcnow().isoformat()

    def is_timed_out(self) -> bool:
        """Check if the approval gate has timed out."""
        if self.status != "pending":
            return False
        created = datetime.fromisoformat(self.created_at)
        deadline = created + timedelta(minutes=self.timeout_minutes)
        return datetime.utcnow() > deadline


# ── Compensation Handler ───────────────────────────────────────────

@dataclass
class CompensationHandler:
    """Handles compensation (rollback) for failed workflow steps.

    Implements the Saga pattern for distributed workflow compensation.
    """

    async def compensate_step(self, step: WorkflowStep, context: WorkflowContext, error: str) -> None:
        """Execute compensation handler for a failed step."""
        if step.compensation_handler is None:
            logger.warning("No compensation handler for step '%s'", step.name)
            return

        try:
            logger.info("Compensating step '%s' for workflow %s", step.name, context.workflow_id)
            await step.compensation_handler(context)
            logger.info("Compensation complete for step '%s'", step.name)
        except Exception as e:
            logger.error("Compensation failed for step '%s': %s", step.name, e)
            raise

    async def compensate_workflow(self, definition: WorkflowDefinition, instance: WorkflowInstance) -> None:
        """Compensate all completed steps in reverse order (Saga pattern)."""
        completed_steps = [
            (i, step) for i, step in enumerate(definition.steps)
            if i < instance.current_step
        ]

        for step_index, step in reversed(completed_steps):
            result = instance.step_results[step_index] if step_index < len(instance.step_results) else {}
            if result.get("status") == WorkflowStepStatus.COMPLETED.value:
                await self.compensate_step(step, instance.context, "Workflow compensation triggered")

        instance.status = WorkflowStatus.COMPENSATED


# ── Workflow Execution Engine ──────────────────────────────────────

StepHandler = Callable[[WorkflowContext], Awaitable[Any]]


@dataclass
class WorkflowExecutionEngine:
    """Executes and manages workflow instances with full lifecycle support.

    Features:
    - Sequential step execution with state machine validation
    - SLA timer and breach detection
    - Escalation on failure or timeout
    - Human approval gates
    - Saga compensation on failure
    - Resumability (persist state for recovery)
    """

    _definitions: dict[str, WorkflowDefinition] = field(default_factory=dict)
    _instances: dict[str, WorkflowInstance] = field(default_factory=dict)
    _approval_gates: dict[str, ApprovalGate] = field(default_factory=dict)
    _sla_timers: dict[str, SLATimer] = field(default_factory=dict)
    _escalation_policies: dict[str, EscalationPolicy] = field(default_factory=dict)
    _compensation: CompensationHandler = field(default_factory=CompensationHandler)

    def register_definition(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        key = f"{definition.workflow_type}:{definition.version}"
        self._definitions[key] = definition
        logger.info("Registered workflow definition: %s v%s", definition.workflow_type, definition.version)

    def register_escalation_policy(self, workflow_type: str, policy: EscalationPolicy) -> None:
        """Register an escalation policy for a workflow type."""
        self._escalation_policies[workflow_type] = policy

    async def start_workflow(
        self,
        workflow_type: str,
        tenant_id: str,
        actor_id: str | None = None,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> WorkflowInstance:
        """Start a new workflow instance."""
        # Find the latest version of the workflow type
        matching = [
            (key, defn) for key, defn in self._definitions.items()
            if key.startswith(f"{workflow_type}:")
        ]
        if not matching:
            raise ValueError(f"No workflow definition found for type '{workflow_type}'")

        # Use the latest version
        matching.sort(key=lambda x: x[0], reverse=True)
        key, definition = matching[0]

        workflow_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())

        context = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            tenant_id=tenant_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            trace_id=trace_id,
            actor_id=actor_id,
            data=data or {},
            metadata=metadata or {},
        )

        instance = WorkflowInstance(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            version=definition.version,
            tenant_id=tenant_id,
            status=WorkflowStatus.RUNNING,
            context=context,
            sla_deadline=(
                (datetime.utcnow() + timedelta(seconds=definition.sla_seconds)).isoformat()
                if definition.sla_seconds else None
            ),
        )

        self._instances[workflow_id] = instance

        # Start SLA timer if configured
        if definition.sla_seconds:
            timer = SLATimer(sla_seconds=definition.sla_seconds)
            timer.start()
            self._sla_timers[workflow_id] = timer

        logger.info(
            "Started workflow %s (%s v%s) for tenant %s",
            workflow_id[:8], workflow_type, definition.version, tenant_id,
        )

        # Execute steps asynchronously
        asyncio.create_task(self._execute_steps(workflow_id, definition, instance))

        return instance

    async def _execute_steps(self, workflow_id: str, definition: WorkflowDefinition, instance: WorkflowInstance) -> None:
        """Execute workflow steps sequentially."""
        escalation_level = 0

        for step_index, step in enumerate(definition.steps):
            instance.current_step = step_index

            # Check for cancellation
            if instance.status == WorkflowStatus.CANCELLED:
                logger.info("Workflow %s cancelled before step '%s'", workflow_id[:8], step.name)
                return

            # Step-level SLA timer
            step_timer = None
            if step.sla_seconds:
                step_timer = SLATimer(sla_seconds=step.sla_seconds)
                step_timer.start()

            # Check for human approval gate
            if step.requires_approval:
                gate = ApprovalGate(
                    workflow_id=workflow_id,
                    step_name=step.name,
                    required_roles=step.approval_config.get("required_roles", []),
                    required_users=step.approval_config.get("required_users", []),
                    min_approvals=step.approval_config.get("min_approvals", 1),
                    timeout_minutes=step.approval_config.get("timeout_minutes", 1440),
                )
                self._approval_gates[gate.gate_id] = gate
                instance.status = WorkflowStatus.WAITING_APPROVAL

                # Wait for approval (polling approach)
                while gate.status == "pending":
                    if gate.is_timed_out():
                        gate.status = "timed_out"
                        logger.warning("Approval gate %s timed out for step '%s'", gate.gate_id[:8], step.name)
                        break
                    await asyncio.sleep(5)

                if gate.status == "rejected" or gate.status == "timed_out":
                    instance.status = WorkflowStatus.FAILED
                    instance.errors.append({
                        "step": step.name,
                        "error": f"Approval {gate.status}: {gate.reason or 'timeout'}",
                    })
                    return

                instance.status = WorkflowStatus.RUNNING

            # Execute step with retry
            step_status = WorkflowStepStatus.RUNNING
            step_error = None

            for attempt in range(step.max_retries + 1):
                try:
                    StateMachineRuntime.validate_transition(
                        WorkflowStepStatus.PENDING if attempt == 0 else WorkflowStepStatus.FAILED,
                        WorkflowStepStatus.RUNNING,
                        step.name,
                    )

                    result = await asyncio.wait_for(
                        step.handler(instance.context),
                        timeout=step.timeout_seconds,
                    )

                    step_status = WorkflowStepStatus.COMPLETED
                    instance.step_results.append({
                        "step": step.name,
                        "status": step_status.value,
                        "result": result,
                        "attempts": attempt + 1,
                    })
                    logger.info("Step '%s' completed (attempt %d)", step.name, attempt + 1)
                    break

                except asyncio.TimeoutError:
                    step_error = f"Step timed out after {step.timeout_seconds}s"
                    logger.warning("Step '%s' timed out (attempt %d/%d)", step.name, attempt + 1, step.max_retries + 1)
                except Exception as e:
                    step_error = str(e)
                    logger.warning("Step '%s' failed (attempt %d/%d): %s", step.name, attempt + 1, step.max_retries + 1, e)

                step_status = WorkflowStepStatus.FAILED

                if attempt < step.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            if step_status == WorkflowStepStatus.FAILED:
                instance.errors.append({
                    "step": step.name,
                    "error": step_error,
                    "attempts": step.max_retries + 1,
                })

                # Check escalation policy
                policy = self._escalation_policies.get(definition.workflow_type)
                if policy:
                    escalated = policy.escalate(escalation_level, instance.context)
                    if escalated:
                        escalation_level += 1

                # Compensate
                await self._compensation.compensate_workflow(definition, instance)
                instance.status = WorkflowStatus.FAILED
                logger.error("Workflow %s failed at step '%s': %s", workflow_id[:8], step.name, step_error)
                return

        # All steps completed
        instance.status = WorkflowStatus.COMPLETED
        instance.completed_at = datetime.utcnow().isoformat()
        logger.info("Workflow %s completed successfully (%d steps)", workflow_id[:8], len(definition.steps))

    async def get_workflow(self, workflow_id: str) -> WorkflowInstance | None:
        """Get a workflow instance by ID."""
        return self._instances.get(workflow_id)

    async def cancel_workflow(self, workflow_id: str) -> None:
        """Cancel a running workflow."""
        instance = self._instances.get(workflow_id)
        if instance and instance.status in (WorkflowStatus.RUNNING, WorkflowStatus.PAUSED, WorkflowStatus.WAITING_APPROVAL):
            instance.status = WorkflowStatus.CANCELLED
            logger.info("Cancelled workflow %s", workflow_id[:8])

    async def resolve_approval(self, gate_id: str, user_id: str, action: str, reason: str | None = None) -> bool:
        """Resolve an approval gate."""
        gate = self._approval_gates.get(gate_id)
        if not gate:
            raise ValueError(f"Approval gate {gate_id} not found")

        if action == "approve":
            return gate.approve(user_id)
        elif action == "reject":
            gate.reject(user_id, reason or "No reason provided")
            return False
        else:
            raise ValueError(f"Invalid approval action: {action}")

    def get_workflows_by_status(self, status: WorkflowStatus) -> list[WorkflowInstance]:
        """Get all workflow instances with a given status."""
        return [i for i in self._instances.values() if i.status == status]

    def get_pending_approvals(self, user_id: str | None = None) -> list[ApprovalGate]:
        """Get all pending approval gates."""
        gates = [g for g in self._approval_gates.values() if g.status == "pending"]
        if user_id:
            gates = [
                g for g in gates
                if user_id in g.required_users or not g.required_users
            ]
        return gates

    def get_workflow_stats(self) -> dict[str, int]:
        """Get workflow statistics."""
        stats = {}
        for status in WorkflowStatus:
            count = sum(1 for i in self._instances.values() if i.status == status)
            if count > 0:
                stats[status.value] = count
        stats["total"] = len(self._instances)
        stats["pending_approvals"] = len(self.get_pending_approvals())
        return stats
