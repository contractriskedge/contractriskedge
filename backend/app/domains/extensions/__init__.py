"""Marketplace & Extensibility Foundation — plugin SDK, workflow hooks, event subscriptions, custom evaluators.

Future-proofs the platform for ecosystem expansion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ExtensionType(str, Enum):
    WORKFLOW_HOOK = "workflow_hook"           # Hook into workflow stages
    AI_EVALUATOR = "ai_evaluator"             # Custom AI evaluation logic
    POLICY_PACK = "policy_pack"               # Custom governance policies
    EVENT_SUBSCRIBER = "event_subscriber"     # Subscribe to platform events
    EXTERNAL_ACTION = "external_action"       # Trigger external actions
    DATA_TRANSFORMER = "data_transformer"     # Transform data between systems
    UI_WIDGET = "ui_widget"                   # Custom UI components


@dataclass
class ExtensionManifest:
    """Manifest for a platform extension/plugin."""
    extension_id: str
    name: str
    description: str
    version: str
    extension_type: ExtensionType
    author: str = ""
    website: str = ""
    min_platform_version: str = "1.0.0"
    permissions: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtensionInstance:
    """A running instance of an extension."""
    instance_id: str
    extension_id: str
    tenant_id: str
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    installed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_active: str = ""


# Type aliases for extension hooks
WorkflowHookHandler = Callable[..., Any]
AIEvaluatorFunction = Callable[..., dict[str, Any]]
PolicyFunction = Callable[..., bool]


@dataclass
class ExtensionRegistry:
    """Registry for platform extensions and plugins.

    Provides:
    - Plugin SDK for extension developers
    - Workflow extension hooks (before/after stages)
    - Event subscription management
    - Custom policy pack registration
    - Custom AI evaluator registration
    - External action trigger management
    """

    _manifests: dict[str, ExtensionManifest] = field(default_factory=dict)
    _instances: dict[str, ExtensionInstance] = field(default_factory=dict)
    _workflow_hooks: dict[str, list[tuple[str, WorkflowHookHandler]]] = field(default_factory=dict)
    _ai_evaluators: dict[str, AIEvaluatorFunction] = field(default_factory=dict)
    _policy_packs: dict[str, PolicyFunction] = field(default_factory=dict)
    _event_subscribers: dict[str, list[tuple[str, Callable]]] = field(default_factory=dict)

    # ── Extension Lifecycle ────────────────────────────────────────

    def register_extension(self, manifest: ExtensionManifest) -> None:
        """Register an extension manifest."""
        self._manifests[manifest.extension_id] = manifest
        logger.info("Registered extension: %s v%s (%s)", manifest.name, manifest.version, manifest.extension_type.value)

    def install_extension(self, extension_id: str, tenant_id: str, config: dict[str, Any] | None = None) -> ExtensionInstance:
        """Install an extension for a tenant."""
        manifest = self._manifests.get(extension_id)
        if not manifest:
            raise ValueError(f"Extension '{extension_id}' not found")

        import uuid
        instance = ExtensionInstance(
            instance_id=str(uuid.uuid4()),
            extension_id=extension_id,
            tenant_id=tenant_id,
            config=config or {},
        )
        self._instances[instance.instance_id] = instance
        logger.info("Installed extension %s for tenant %s", extension_id, tenant_id[:8])
        return instance

    def uninstall_extension(self, instance_id: str) -> None:
        """Uninstall an extension instance."""
        instance = self._instances.pop(instance_id, None)
        if instance:
            logger.info("Uninstalled extension %s", instance.extension_id)

    def get_installed(self, tenant_id: str) -> list[ExtensionInstance]:
        """Get all installed extensions for a tenant."""
        return [i for i in self._instances.values() if i.tenant_id == tenant_id]

    # ── Workflow Hooks ─────────────────────────────────────────────

    def register_workflow_hook(self, hook_point: str, extension_id: str, handler: WorkflowHookHandler) -> None:
        """Register a workflow hook handler."""
        if hook_point not in self._workflow_hooks:
            self._workflow_hooks[hook_point] = []
        self._workflow_hooks[hook_point].append((extension_id, handler))
        logger.info("Registered workflow hook '%s' for extension %s", hook_point, extension_id)

    def execute_workflow_hooks(self, hook_point: str, context: dict[str, Any]) -> list[Any]:
        """Execute all handlers for a workflow hook point."""
        results = []
        for ext_id, handler in self._workflow_hooks.get(hook_point, []):
            try:
                result = handler(context)
                results.append({"extension": ext_id, "result": result})
            except Exception as e:
                logger.error("Workflow hook '%s' failed for extension %s: %s", hook_point, ext_id, e)
                results.append({"extension": ext_id, "error": str(e)})
        return results

    # ── Custom AI Evaluators ───────────────────────────────────────

    def register_ai_evaluator(self, name: str, evaluator: AIEvaluatorFunction) -> None:
        """Register a custom AI evaluator."""
        self._ai_evaluators[name] = evaluator
        logger.info("Registered AI evaluator: %s", name)

    def run_evaluator(self, name: str, context: dict[str, Any]) -> dict[str, Any]:
        """Run a custom AI evaluator."""
        evaluator = self._ai_evaluators.get(name)
        if not evaluator:
            raise ValueError(f"AI evaluator '{name}' not found")
        return evaluator(context)

    # ── Custom Policy Packs ────────────────────────────────────────

    def register_policy_pack(self, name: str, policy_fn: PolicyFunction) -> None:
        """Register a custom policy pack."""
        self._policy_packs[name] = policy_fn
        logger.info("Registered policy pack: %s", name)

    def evaluate_policy(self, name: str, context: dict[str, Any]) -> bool:
        """Evaluate a custom policy."""
        policy = self._policy_packs.get(name)
        if not policy:
            raise ValueError(f"Policy pack '{name}' not found")
        return policy(context)

    # ── Event Subscriptions ────────────────────────────────────────

    def subscribe_to_event(self, event_type: str, extension_id: str, handler: Callable) -> None:
        """Subscribe an extension to a platform event."""
        if event_type not in self._event_subscribers:
            self._event_subscribers[event_type] = []
        self._event_subscribers[event_type].append((extension_id, handler))

    def publish_event(self, event_type: str, payload: dict[str, Any]) -> list[Any]:
        """Publish an event to all subscribers."""
        results = []
        for ext_id, handler in self._event_subscribers.get(event_type, []):
            try:
                result = handler(payload)
                results.append({"extension": ext_id, "result": result})
            except Exception as e:
                results.append({"extension": ext_id, "error": str(e)})
        return results

    # ── Registry Status ────────────────────────────────────────────

    def get_registry_status(self) -> dict[str, Any]:
        """Get extension registry status."""
        return {
            "registered_extensions": len(self._manifests),
            "installed_instances": len(self._instances),
            "workflow_hooks": {k: len(v) for k, v in self._workflow_hooks.items()},
            "ai_evaluators": list(self._ai_evaluators.keys()),
            "policy_packs": list(self._policy_packs.keys()),
            "event_subscribers": {k: len(v) for k, v in self._event_subscribers.items()},
        }


# ── Global singleton ───────────────────────────────────────────────

extension_registry = ExtensionRegistry()
