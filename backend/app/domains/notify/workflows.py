"""Workflow automation, SLA tracking, and escalation engine services."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.domains.notify.models import WorkflowEvent, WorkflowTimer, EscalationRule, EscalationEvent, SLAPolicy
from app.domains.notify.repository import WorkflowRepository
from app.domains.notify.service import NotificationService
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)


@dataclass
class WorkflowAutomationService:
    """Event-driven workflow automation, SLA tracking, timer management, and escalation engine."""

    repo: WorkflowRepository
    notif_service: NotificationService
    event_bus: EventBus
    tenant_id: str

    # ── Event Processing ───────────────────────────────────────────

    async def process_event(self, event_type: str, source: str, entity_type: str, entity_id: str,
                             actor_id: Optional[str] = None, payload: Optional[dict] = None,
                             correlation_id: Optional[str] = None) -> WorkflowEvent:
        """Record a workflow event and trigger automation rules."""
        event = await self.repo.create_event(
            tenant_id=self.tenant_id, event_type=event_type, source=source,
            entity_type=entity_type, entity_id=entity_id, actor_id=actor_id,
            payload=payload or {}, correlation_id=correlation_id,
        )

        # Evaluate automation rules
        await self._evaluate_rules(event)

        return event

    async def _evaluate_rules(self, event: WorkflowEvent) -> None:
        """Evaluate automation rules for an event."""
        # SLA timer creation for review assignments
        if event.event_type == "review.assigned":
            await self._schedule_sla_timers(event)

        # Escalation rule evaluation
        if event.event_type in ("sla_breach", "overdue", "manual_escalation"):
            await self._evaluate_escalation_rules(event)

    # ── SLA Tracking ───────────────────────────────────────────────

    async def _schedule_sla_timers(self, event: WorkflowEvent) -> None:
        """Schedule SLA warning and overdue timers for a review."""
        # Get SLA policy for this workflow type
        review_id = str(event.entity_id) if event.entity_id else ""
        priority = event.payload.get("priority", "normal")
        policies = await self.repo.get_sla_policies(self.tenant_id, "legal_review", priority)

        if not policies:
            return

        policy = policies[0]
        now = datetime.utcnow()
        warning_minutes = int(policy.target_minutes * policy.warning_threshold_percent)

        # Warning timer
        await self.repo.create_timer(
            tenant_id=self.tenant_id, timer_type="sla_warning",
            entity_type="review", entity_id=review_id,
            target_time=now + timedelta(minutes=warning_minutes),
            action="send_sla_warning",
            action_payload={"review_id": review_id, "policy_id": str(policy.policy_id)},
        )

        # Overdue timer
        await self.repo.create_timer(
            tenant_id=self.tenant_id, timer_type="overdue",
            entity_type="review", entity_id=review_id,
            target_time=now + timedelta(minutes=policy.target_minutes),
            action="mark_overdue",
            action_payload={"review_id": review_id, "policy_id": str(policy.policy_id)},
        )

        # Escalation timer (if configured)
        if policy.escalation_after_minutes:
            await self.repo.create_timer(
                tenant_id=self.tenant_id, timer_type="escalation",
                entity_type="review", entity_id=review_id,
                target_time=now + timedelta(minutes=policy.escalation_after_minutes),
                action="auto_escalate",
                action_payload={"review_id": review_id},
            )

    async def check_sla(self, review_id: str, assignee_id: str, priority: str = "normal") -> Optional[dict]:
        """Check SLA status for a review. Returns warning info if approaching breach."""
        policies = await self.repo.get_sla_policies(self.tenant_id, "legal_review", priority)
        if not policies:
            return None

        policy = policies[0]
        # Find the assignment time from workflow events
        events = await self.repo.get_events_by_entity(self.tenant_id, "review", review_id)
        assigned_event = next((e for e in events if e.event_type == "review.assigned"), None)
        if not assigned_event:
            return None

        elapsed = (datetime.utcnow() - assigned_event.created_at.replace(tzinfo=None)).total_seconds() / 60
        remaining = policy.target_minutes - elapsed
        percent_used = elapsed / policy.target_minutes if policy.target_minutes > 0 else 1.0

        return {
            "elapsed_minutes": round(elapsed, 1),
            "remaining_minutes": round(remaining, 1),
            "target_minutes": policy.target_minutes,
            "percent_used": round(percent_used, 2),
            "is_warning": percent_used >= policy.warning_threshold_percent,
            "is_breached": remaining <= 0,
        }

    # ── Timer Processing ───────────────────────────────────────────

    async def process_due_timers(self) -> int:
        """Process all due timers and dispatch actions. Returns count processed."""
        timers = await self.repo.get_due_timers(self.tenant_id)
        count = 0
        for timer in timers:
            try:
                await self._execute_timer_action(timer)
                await self.repo.mark_timer_fired(timer.timer_id)
                count += 1
            except Exception as exc:
                logger.error("Timer action failed: timer=%s action=%s error=%s",
                             timer.timer_id, timer.action, exc)
        return count

    async def _execute_timer_action(self, timer: WorkflowTimer) -> None:
        """Execute the action associated with a workflow timer."""
        if timer.action == "send_sla_warning":
            assignee_id = timer.action_payload.get("assignee_id", "")
            review_id = timer.action_payload.get("review_id", "")
            remaining = int((timer.target_time - datetime.utcnow()).total_seconds() / 60)
            await self.notif_service.send_sla_warning(review_id, assignee_id, max(remaining, 0))

        elif timer.action == "mark_overdue":
            await self.process_event(
                event_type="overdue", source="sla_tracker",
                entity_type=timer.entity_type, entity_id=str(timer.entity_id),
                payload=timer.action_payload,
            )

        elif timer.action == "auto_escalate":
            await self.process_event(
                event_type="sla_breach", source="sla_tracker",
                entity_type=timer.entity_type, entity_id=str(timer.entity_id),
                payload=timer.action_payload,
            )

    # ── Escalation Engine ──────────────────────────────────────────

    async def _evaluate_escalation_rules(self, event: WorkflowEvent) -> None:
        """Evaluate escalation rules for a triggering event."""
        rules = await self.repo.get_active_escalation_rules(self.tenant_id, event.event_type)
        for rule in rules:
            await self._execute_escalation(rule, event)

    async def _execute_escalation(self, rule: EscalationRule, event: WorkflowEvent) -> EscalationEvent:
        """Execute an escalation rule: determine target and create escalation event."""
        # Determine escalation target from chain
        chain = rule.escalation_chain
        current_level = 1

        # Find current escalation level for this entity
        existing = await self.repo.get_active_escalations(self.tenant_id, event.entity_type, str(event.entity_id) if event.entity_id else "")
        if existing:
            current_level = existing.level + 1

        if current_level > rule.max_escalation_level:
            logger.warning("Max escalation level reached for %s/%s", event.entity_type, event.entity_id)
            return None

        # Find target for this level
        level_config = next((l for l in chain if l.get("level") == current_level), chain[-1])
        escalated_to = level_config.get("assignee", "")

        esc_event = await self.repo.create_escalation(
            tenant_id=self.tenant_id, rule_id=rule.rule_id,
            entity_type=event.entity_type, entity_id=str(event.entity_id) if event.entity_id else "",
            level=current_level, escalated_by=event.actor_id or "system",
            escalated_to=escalated_to, reason=event.payload.get("reason", "Auto-escalation"),
        )

        # Send notification
        await self.notif_service.send_escalation_notification(esc_event, str(event.entity_id) if event.entity_id else "")

        return esc_event

    async def manual_escalate(self, entity_type: str, entity_id: str, reason: str,
                               escalated_by: str, escalated_to: Optional[str] = None) -> EscalationEvent:
        """Trigger a manual escalation."""
        event = await self.process_event(
            event_type="manual_escalation", source="manual",
            entity_type=entity_type, entity_id=entity_id,
            actor_id=escalated_by, payload={"reason": reason, "escalated_to": escalated_to},
        )
        # Return the created escalation from rule evaluation
        rules = await self.repo.get_active_escalation_rules(self.tenant_id, "manual_escalation")
        if rules:
            return await self._execute_escalation(rules[0], event)
        return None

    # ── SLA Policy Management ──────────────────────────────────────

    async def create_sla_policy(self, name: str, workflow_type: str, priority: str,
                                 target_minutes: int, warning_threshold: float = 0.8,
                                 escalation_after_minutes: Optional[int] = None) -> SLAPolicy:
        return await self.repo.create_sla_policy(
            tenant_id=self.tenant_id, name=name, workflow_type=workflow_type,
            priority=priority, target_minutes=target_minutes,
            warning_threshold_percent=warning_threshold,
            escalation_after_minutes=escalation_after_minutes,
        )

    async def list_sla_policies(self, workflow_type: Optional[str] = None):
        return await self.repo.list_sla_policies(self.tenant_id, workflow_type)
