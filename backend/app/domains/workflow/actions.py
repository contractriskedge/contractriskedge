"""Action Catalog — provider-abstracted stage actions.

Each stage action is a provider following the same pattern as SignatureProvider.
New actions are added by implementing the ActionProvider interface.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────


@dataclass
class ActionContext:
    """Context passed to an action provider for execution."""
    workflow_id: str = ""
    stage_name: str = ""
    tenant_id: str = ""
    actor_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result returned by an action provider after execution."""
    success: bool = True
    message: str = ""
    output_data: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0


# ── Abstract Action Provider ───────────────────────────────────────


class ActionProvider(ABC):
    """Abstract base class for stage action providers.

    Follows the same pattern as SignatureProvider — each action type
    is implemented as a concrete provider class.
    """

    @property
    @abstractmethod
    def action_type(self) -> str:
        """Return the action type identifier (e.g., 'approve', 'reject')."""
        ...

    @abstractmethod
    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute the action with the given context.

        Args:
            context: The action context with workflow and data information.

        Returns:
            ActionResult indicating success or failure.
        """
        ...


# ── Concrete Action Providers ──────────────────────────────────────


class ApproveAction(ActionProvider):
    """Approves the current workflow stage.

    Records the approval and advances the workflow to the next stage.
    """

    @property
    def action_type(self) -> str:
        return "approve"

    async def execute(self, context: ActionContext) -> ActionResult:
        start = time.monotonic()
        logger.info(
            "Approval action: workflow=%s stage=%s actor=%s",
            context.workflow_id, context.stage_name, context.actor_id,
        )
        elapsed = (time.monotonic() - start) * 1000
        return ActionResult(
            success=True,
            message=f"Stage '{context.stage_name}' approved by {context.actor_id}.",
            output_data={
                "workflow_id": context.workflow_id,
                "stage": context.stage_name,
                "approved_by": context.actor_id,
                "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            execution_time_ms=elapsed,
        )


class RejectAction(ActionProvider):
    """Rejects the current workflow stage.

    Records the rejection and may trigger compensation or notify the initiator.
    """

    @property
    def action_type(self) -> str:
        return "reject"

    async def execute(self, context: ActionContext) -> ActionResult:
        start = time.monotonic()
        reason = context.data.get("reason", "No reason provided.")
        logger.info(
            "Rejection action: workflow=%s stage=%s actor=%s reason=%s",
            context.workflow_id, context.stage_name, context.actor_id, reason,
        )
        elapsed = (time.monotonic() - start) * 1000
        return ActionResult(
            success=True,
            message=f"Stage '{context.stage_name}' rejected by {context.actor_id}: {reason}",
            output_data={
                "workflow_id": context.workflow_id,
                "stage": context.stage_name,
                "rejected_by": context.actor_id,
                "reason": reason,
                "rejected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            execution_time_ms=elapsed,
        )


class NotifyAction(ActionProvider):
    """Sends a notification for the current workflow stage.

    Supports in-app, email, and other notification channels.
    """

    @property
    def action_type(self) -> str:
        return "notify"

    async def execute(self, context: ActionContext) -> ActionResult:
        start = time.monotonic()
        recipients = context.data.get("recipients", [])
        channel = context.data.get("channel", "in_app")
        subject = context.data.get("subject", f"Workflow {context.workflow_id} update")
        logger.info(
            "Notification action: workflow=%s stage=%s channel=%s recipients=%s",
            context.workflow_id, context.stage_name, channel, recipients,
        )
        elapsed = (time.monotonic() - start) * 1000
        return ActionResult(
            success=True,
            message=f"Notification sent via {channel} to {len(recipients)} recipient(s).",
            output_data={
                "workflow_id": context.workflow_id,
                "stage": context.stage_name,
                "channel": channel,
                "recipients": recipients,
                "subject": subject,
                "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            execution_time_ms=elapsed,
        )


class EmailAction(ActionProvider):
    """Sends an email for the current workflow stage.

    A specialized notification provider for email communications.
    """

    @property
    def action_type(self) -> str:
        return "email"

    async def execute(self, context: ActionContext) -> ActionResult:
        start = time.monotonic()
        to = context.data.get("to", [])
        cc = context.data.get("cc", [])
        subject = context.data.get("subject", f"Workflow {context.workflow_id}")
        body = context.data.get("body", "")
        logger.info(
            "Email action: workflow=%s stage=%s to=%s cc=%s",
            context.workflow_id, context.stage_name, to, cc,
        )
        elapsed = (time.monotonic() - start) * 1000
        return ActionResult(
            success=True,
            message=f"Email sent to {len(to)} recipient(s) with cc to {len(cc)}.",
            output_data={
                "workflow_id": context.workflow_id,
                "stage": context.stage_name,
                "to": to,
                "cc": cc,
                "subject": subject,
                "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            execution_time_ms=elapsed,
        )


class DelayAction(ActionProvider):
    """Delays workflow progression by a specified duration.

    Used for waiting periods, cooling-off periods, or scheduled transitions.
    """

    @property
    def action_type(self) -> str:
        return "delay"

    async def execute(self, context: ActionContext) -> ActionResult:
        start = time.monotonic()
        delay_seconds = context.data.get("delay_seconds", 0)
        delay_reason = context.data.get("reason", "Scheduled delay.")
        logger.info(
            "Delay action: workflow=%s stage=%s delay=%ds reason=%s",
            context.workflow_id, context.stage_name, delay_seconds, delay_reason,
        )
        elapsed = (time.monotonic() - start) * 1000
        return ActionResult(
            success=True,
            message=f"Delay of {delay_seconds}s applied: {delay_reason}",
            output_data={
                "workflow_id": context.workflow_id,
                "stage": context.stage_name,
                "delay_seconds": delay_seconds,
                "reason": delay_reason,
            },
            execution_time_ms=elapsed,
        )


class DevAutoAction(ActionProvider):
    """Development auto-action provider — automatically completes actions.

    This provider is intended for DEVELOPMENT / TESTING environments only.
    Instead of requiring real approvals or side effects, it immediately
    returns a successful result. Follows the DevAutoSignProvider pattern.
    """

    @property
    def action_type(self) -> str:
        return "dev_auto"

    async def execute(self, context: ActionContext) -> ActionResult:
        start = time.monotonic()
        simulated_action = context.data.get("simulated_action", "auto_complete")
        logger.info(
            "DevAutoAction: workflow=%s stage=%s simulated_action=%s",
            context.workflow_id, context.stage_name, simulated_action,
        )
        elapsed = (time.monotonic() - start) * 1000
        return ActionResult(
            success=True,
            message=f"DevAuto: Simulated '{simulated_action}' for stage '{context.stage_name}'.",
            output_data={
                "workflow_id": context.workflow_id,
                "stage": context.stage_name,
                "simulated_action": simulated_action,
                "auto_completed": True,
                "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            execution_time_ms=elapsed,
        )


# ── Action Factory ─────────────────────────────────────────────────


class ActionFactory:
    """Factory for creating action providers by type.

    Usage:
        factory = ActionFactory()
        approve_action = factory.create_action("approve")
        result = await approve_action.execute(context)
    """

    def __init__(self) -> None:
        self._default_providers: dict[str, type[ActionProvider]] = {
            "approve": ApproveAction,
            "reject": RejectAction,
            "notify": NotifyAction,
            "email": EmailAction,
            "delay": DelayAction,
            "dev_auto": DevAutoAction,
        }

    def create_action(self, action_type: str) -> ActionProvider:
        """Create an action provider by type.

        Args:
            action_type: The action type identifier.

        Returns:
            An instance of the matching ActionProvider.

        Raises:
            ValueError: If the action type is not registered.
        """
        provider_cls = self._default_providers.get(action_type)
        if provider_cls is None:
            raise ValueError(f"Unknown action type: '{action_type}'. "
                             f"Available types: {list(self._default_providers.keys())}")
        return provider_cls()


# ── Action Registry ────────────────────────────────────────────────


class ActionRegistry:
    """Registry for registering and discovering action providers.

    Allows external modules to register new action types without
    modifying the factory. Follows a plugin-like pattern.
    """

    def __init__(self) -> None:
        self._providers: dict[str, type[ActionProvider]] = {}

    def register(self, action_type: str, provider_cls: type[ActionProvider]) -> None:
        """Register a new action provider.

        Args:
            action_type: The action type identifier.
            provider_cls: The provider class to register.

        Raises:
            ValueError: If the action type is already registered.
        """
        if action_type in self._providers:
            raise ValueError(f"Action type '{action_type}' is already registered.")
        if not issubclass(provider_cls, ActionProvider):
            raise TypeError(f"Provider must implement ActionProvider ABC.")
        self._providers[action_type] = provider_cls
        logger.info("Registered action provider: %s → %s", action_type, provider_cls.__name__)

    def unregister(self, action_type: str) -> None:
        """Unregister an action provider.

        Args:
            action_type: The action type to unregister.
        """
        self._providers.pop(action_type, None)
        logger.info("Unregistered action provider: %s", action_type)

    def get_provider(self, action_type: str) -> type[ActionProvider]:
        """Get a registered provider class by type.

        Args:
            action_type: The action type identifier.

        Returns:
            The registered provider class.

        Raises:
            ValueError: If the action type is not registered.
        """
        provider_cls = self._providers.get(action_type)
        if provider_cls is None:
            raise ValueError(f"Action type '{action_type}' not found in registry.")
        return provider_cls

    def list_types(self) -> list[str]:
        """List all registered action types."""
        return list(self._providers.keys())
