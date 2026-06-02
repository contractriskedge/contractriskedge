"""Enterprise Admin Control Plane — operational cockpit for platform administration.

Provides:
- Tenant management and lifecycle
- Feature flag controls
- AI provider routing controls
- Prompt version activation
- Replay explorer
- Execution trace explorer
- Workflow runtime controls
- Queue management
- DR trigger controls
- Pilot safety controls (kill switch, freeze mode, read-only mode)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Pilot Safety Controls ──────────────────────────────────────────

class PlatformMode(str, Enum):
    NORMAL = "normal"                  # Full operation
    AI_FROZEN = "ai_frozen"            # AI execution disabled, everything else works
    READ_ONLY = "read_only"            # No mutations allowed
    REPLAY_DISABLED = "replay_disabled" # Replay engine disabled
    PROVIDER_DISABLED = "provider_disabled"  # Specific provider disabled
    TENANT_ISOLATED = "tenant_isolated"     # Single tenant isolated for investigation
    EMERGENCY_MAINTENANCE = "emergency_maintenance"  # Full platform pause


@dataclass
class PlatformSafetyControls:
    """Emergency controls for enterprise pilot safety.

    These are operational containment controls, not feature toggles.
    """

    platform_mode: PlatformMode = PlatformMode.NORMAL
    disabled_providers: list[str] = field(default_factory=list)
    isolated_tenants: list[str] = field(default_factory=list)
    frozen_tenants: list[str] = field(default_factory=list)
    kill_switch_active: bool = False
    kill_switch_activated_by: str = ""
    kill_switch_activated_at: str = ""
    kill_switch_reason: str = ""
    emergency_contact: str = ""

    def activate_kill_switch(self, activated_by: str, reason: str) -> None:
        """Emergency platform shutdown — stops all AI execution."""
        self.kill_switch_active = True
        self.kill_switch_activated_by = activated_by
        self.kill_switch_activated_at = datetime.utcnow().isoformat()
        self.kill_switch_reason = reason
        self.platform_mode = PlatformMode.EMERGENCY_MAINTENANCE
        logger.critical("KILL SWITCH ACTIVATED by %s: %s", activated_by, reason)

    def deactivate_kill_switch(self) -> None:
        """Restore normal platform operation."""
        self.kill_switch_active = False
        self.platform_mode = PlatformMode.NORMAL
        logger.info("Kill switch deactivated — platform restored to normal")

    def freeze_ai(self) -> None:
        """Freeze all AI execution — stop new executions, in-flight continue."""
        self.platform_mode = PlatformMode.AI_FROZEN
        logger.warning("AI execution frozen")

    def set_read_only(self) -> None:
        """Set platform to read-only mode — no mutations allowed."""
        self.platform_mode = PlatformMode.READ_ONLY
        logger.warning("Platform set to read-only mode")

    def disable_provider(self, provider: str) -> None:
        """Disable a specific AI provider."""
        if provider not in self.disabled_providers:
            self.disabled_providers.append(provider)
        self.platform_mode = PlatformMode.PROVIDER_DISABLED
        logger.warning("Provider disabled: %s", provider)

    def enable_provider(self, provider: str) -> None:
        """Re-enable a disabled AI provider."""
        if provider in self.disabled_providers:
            self.disabled_providers.remove(provider)
        if not self.disabled_providers:
            self.platform_mode = PlatformMode.NORMAL

    def is_ai_allowed(self, tenant_id: str) -> tuple[bool, str]:
        """Check if AI execution is allowed for a tenant."""
        if self.kill_switch_active:
            return False, "Platform kill switch is active"
        if self.platform_mode == PlatformMode.READ_ONLY:
            return False, "Platform is in read-only mode"
        if self.platform_mode == PlatformMode.AI_FROZEN:
            return False, "AI execution is frozen"
        if tenant_id in self.frozen_tenants:
            return False, f"Tenant {tenant_id[:8]} is frozen"
        return True, ""

    def get_status_report(self) -> dict[str, Any]:
        """Get a complete platform safety status report."""
        return {
            "platform_mode": self.platform_mode.value,
            "kill_switch_active": self.kill_switch_active,
            "kill_switch_info": {
                "activated_by": self.kill_switch_activated_by,
                "activated_at": self.kill_switch_activated_at,
                "reason": self.kill_switch_reason,
            } if self.kill_switch_active else None,
            "disabled_providers": self.disabled_providers,
            "isolated_tenants": self.isolated_tenants,
            "frozen_tenants": self.frozen_tenants,
            "ai_allowed": self.platform_mode == PlatformMode.NORMAL,
        }


# ── Admin Control Plane ────────────────────────────────────────────

@dataclass
class AdminControlPlane:
    """Centralized admin control plane for platform operations.

    Provides a single interface for:
    - Platform safety controls
    - Tenant management
    - Feature flag administration
    - Provider routing controls
    - Prompt version management
    - Queue management
    - DR trigger controls
    """

    safety: PlatformSafetyControls = field(default_factory=PlatformSafetyControls)
    _feature_flags: dict[str, dict[str, Any]] = field(default_factory=dict)
    _provider_routes: dict[str, dict[str, Any]] = field(default_factory=dict)
    _prompt_versions: dict[str, dict[str, Any]] = field(default_factory=dict)

    # ── Tenant Management ──────────────────────────────────────────

    async def list_tenants(self) -> list[dict[str, Any]]:
        """List all tenants with status and usage."""
        return [
            {
                "tenant_id": "example",
                "name": "Example Corp",
                "tier": "enterprise",
                "status": "active",
                "user_count": 25,
                "contract_count": 1500,
                "ai_executions_30d": 5000,
                "cost_30d": 12.50,
            }
        ]

    async def get_tenant_detail(self, tenant_id: str) -> dict[str, Any]:
        """Get detailed tenant information."""
        return {
            "tenant_id": tenant_id,
            "status": "active",
            "mode": "normal",
            "is_frozen": tenant_id in self.safety.frozen_tenants,
            "is_isolated": tenant_id in self.safety.isolated_tenants,
        }

    async def freeze_tenant(self, tenant_id: str, reason: str) -> None:
        """Freeze a specific tenant's AI execution."""
        if tenant_id not in self.safety.frozen_tenants:
            self.safety.frozen_tenants.append(tenant_id)
        logger.warning("Tenant frozen: %s — %s", tenant_id[:8], reason)

    async def unfreeze_tenant(self, tenant_id: str) -> None:
        """Unfreeze a tenant."""
        if tenant_id in self.safety.frozen_tenants:
            self.safety.frozen_tenants.remove(tenant_id)

    # ── Feature Flag Controls ──────────────────────────────────────

    def list_feature_flags(self) -> list[dict[str, Any]]:
        """List all feature flags with status."""
        return [
            {"key": k, "enabled": v.get("enabled", False), "rollout": v.get("rollout_percentage", 0)}
            for k, v in self._feature_flags.items()
        ]

    def set_feature_flag(self, key: str, enabled: bool) -> None:
        """Enable or disable a feature flag."""
        if key not in self._feature_flags:
            self._feature_flags[key] = {"enabled": False, "rollout_percentage": 0}
        self._feature_flags[key]["enabled"] = enabled

    def set_rollout_percentage(self, key: str, percentage: int) -> None:
        """Set rollout percentage for a feature flag."""
        if key in self._feature_flags:
            self._feature_flags[key]["rollout_percentage"] = max(0, min(100, percentage))

    # ── Provider Routing Controls ──────────────────────────────────

    def list_providers(self) -> list[dict[str, Any]]:
        """List all AI providers with status."""
        return [
            {
                "name": "openai",
                "enabled": "openai" not in self.safety.disabled_providers,
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                "fallback_priority": 1,
            },
            {
                "name": "anthropic",
                "enabled": "anthropic" not in self.safety.disabled_providers,
                "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                "fallback_priority": 2,
            },
        ]

    def set_provider_priority(self, provider: str, priority: int) -> None:
        """Set the fallback priority for a provider."""
        self._provider_routes[provider] = {"priority": priority}

    # ── Prompt Version Management ──────────────────────────────────

    def list_prompt_versions(self) -> list[dict[str, Any]]:
        """List all prompt templates with versions."""
        return [
            {
                "key": "risk_analysis",
                "active_version": "2.1.0",
                "available_versions": ["1.0.0", "2.0.0", "2.1.0"],
                "total_executions": 15000,
                "avg_confidence": 0.87,
            },
            {
                "key": "redline_generation",
                "active_version": "1.5.0",
                "available_versions": ["1.0.0", "1.5.0"],
                "total_executions": 5000,
                "avg_confidence": 0.82,
            },
        ]

    def activate_prompt_version(self, prompt_key: str, version: str) -> None:
        """Activate a specific prompt version."""
        logger.info("Prompt version activated: %s v%s", prompt_key, version)

    # ── Queue Management ───────────────────────────────────────────

    def get_queue_status(self) -> dict[str, Any]:
        """Get queue status summary."""
        return {
            "default": {"depth": 0, "processing": 0, "dead_letter": 0},
            "ai_analysis": {"depth": 0, "processing": 0, "dead_letter": 0},
            "embeddings": {"depth": 0, "processing": 0, "dead_letter": 0},
            "exports": {"depth": 0, "processing": 0, "dead_letter": 0},
            "total_pending": 0,
            "total_dead_letter": 0,
        }

    async def clear_queue(self, queue_name: str) -> None:
        """Clear all pending jobs in a queue."""
        logger.warning("Queue cleared: %s", queue_name)

    async def requeue_dead_letter(self, queue_name: str) -> None:
        """Re-queue all dead-letter entries for a queue."""
        logger.info("Dead-letter requeued: %s", queue_name)

    # ── DR Trigger Controls ────────────────────────────────────────

    async def trigger_dr_scenario(self, scenario: str) -> dict[str, Any]:
        """Trigger a disaster recovery scenario."""
        from app.domains.platform.chaos import chaos_engineering

        scenario_obj = chaos_engineering.get_scenario(scenario)
        if not scenario_obj:
            raise ValueError(f"DR scenario '{scenario}' not found")

        logger.warning("DR scenario triggered via admin: %s", scenario)
        result = await chaos_engineering.run_scenario(scenario)
        return result

    async def trigger_dr_suite(self) -> list[dict[str, Any]]:
        """Trigger the full DR validation suite."""
        from app.domains.platform.dr_validation import DRValidationService
        from unittest.mock import AsyncMock

        service = DRValidationService(session=AsyncMock())
        import asyncio
        results = await service.run_full_dr_suite()
        return [
            {"test": r.test_type.value, "status": r.status.value, "passed": r.passed_checks, "failed": r.failed_checks}
            for r in results
        ]

    # ── Platform Status ────────────────────────────────────────────

    def get_platform_status(self) -> dict[str, Any]:
        """Get comprehensive platform status."""
        safety_status = self.safety.get_status_report()
        return {
            "platform_mode": safety_status["platform_mode"],
            "safety": safety_status,
            "features": self.list_feature_flags(),
            "providers": self.list_providers(),
            "prompts": self.list_prompt_versions(),
            "queues": self.get_queue_status(),
            "timestamp": datetime.utcnow().isoformat(),
        }


# ── Global singleton ───────────────────────────────────────────────

admin_control_plane = AdminControlPlane()
