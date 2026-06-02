"""Runtime Configuration Platform — dynamic config registry, feature rollout, audit trail, tenant overrides.

Prevents configuration from becoming scattered chaos across the platform.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ConfigValueType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"


class ConfigStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    DEPRECATED = "deprecated"


@dataclass
class ConfigDefinition:
    """A registered configuration key with metadata."""
    key: str
    description: str
    value_type: ConfigValueType
    default_value: Any = None
    status: ConfigStatus = ConfigStatus.ACTIVE
    validation_regex: str | None = None
    validation_fn: str | None = None  # Name of a registered validation function
    environment_overrides: dict[str, Any] = field(default_factory=dict)
    tenant_overrides: dict[str, Any] = field(default_factory=dict)
    requires_restart: bool = False
    changed_at: str = ""
    changed_by: str = ""


@dataclass
class ConfigChangeLog:
    """An audit trail entry for configuration changes."""
    key: str
    previous_value: Any
    new_value: Any
    changed_by: str
    changed_at: str
    reason: str = ""
    environment: str = ""
    tenant_id: str = ""


@dataclass
class FeatureFlag:
    """A feature flag with rollout configuration."""
    flag_key: str
    name: str
    description: str
    enabled: bool = False
    rollout_percentage: int = 0
    tenant_ids: list[str] = field(default_factory=list)
    environment: str = "production"
    dependencies: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


ConfigChangeHandler = Callable[[str, Any, Any], None]


@dataclass
class RuntimeConfigService:
    """Centralized runtime configuration with dynamic reload and audit trail.

    Provides:
    - Dynamic config registry with type-safe values
    - Feature rollout engine with percentage-based rollouts
    - Configuration audit trail
    - Environment-specific overrides
    - Tenant-specific overrides
    - Runtime reload support (no restart required)
    - Change notification hooks
    """

    _configs: dict[str, ConfigDefinition] = field(default_factory=dict)
    _feature_flags: dict[str, FeatureFlag] = field(default_factory=dict)
    _change_log: list[ConfigChangeLog] = field(default_factory=list)
    _change_handlers: dict[str, list[ConfigChangeHandler]] = field(default_factory=dict)
    _environment: str = "production"

    # ── Config Registry ────────────────────────────────────────────

    def register(self, config: ConfigDefinition) -> None:
        """Register a configuration key."""
        self._configs[config.key] = config
        logger.info("Registered config key: %s (type=%s)", config.key, config.value_type.value)

    def get(self, key: str, environment: str | None = None, tenant_id: str | None = None) -> Any:
        """Get a configuration value with override resolution.

        Resolution order:
        1. Tenant-specific override
        2. Environment-specific override
        3. Default value
        """
        config = self._configs.get(key)
        if not config:
            raise KeyError(f"Configuration key '{key}' not registered")

        # Tenant override
        if tenant_id and tenant_id in config.tenant_overrides:
            return config.tenant_overrides[tenant_id]

        # Environment override
        env = environment or self._environment
        if env in config.environment_overrides:
            return config.environment_overrides[env]

        return config.default_value

    def set(
        self,
        key: str,
        value: Any,
        changed_by: str = "system",
        reason: str = "",
        environment: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Set a configuration value with audit logging."""
        config = self._configs.get(key)
        if not config:
            raise KeyError(f"Configuration key '{key}' not registered")

        previous = self.get(key, environment, tenant_id)

        if tenant_id:
            config.tenant_overrides[tenant_id] = value
        elif environment:
            config.environment_overrides[environment] = value
        else:
            config.default_value = value

        config.changed_at = datetime.utcnow().isoformat()
        config.changed_by = changed_by

        # Audit log
        self._change_log.append(ConfigChangeLog(
            key=key,
            previous_value=previous,
            new_value=value,
            changed_by=changed_by,
            changed_at=datetime.utcnow().isoformat(),
            reason=reason,
            environment=environment or self._environment,
            tenant_id=tenant_id or "",
        ))

        # Notify handlers
        handlers = self._change_handlers.get(key, [])
        for handler in handlers:
            try:
                handler(key, previous, value)
            except Exception as e:
                logger.error("Config change handler failed for '%s': %s", key, e)

        logger.info("Config '%s' changed: %s -> %s (by=%s, reason=%s)", key, previous, value, changed_by, reason)

    def on_change(self, key: str, handler: ConfigChangeHandler) -> None:
        """Register a change notification handler for a config key."""
        if key not in self._change_handlers:
            self._change_handlers[key] = []
        self._change_handlers[key].append(handler)

    # ── Feature Flags ──────────────────────────────────────────────

    def register_feature_flag(self, flag: FeatureFlag) -> None:
        """Register a feature flag."""
        self._feature_flags[flag.flag_key] = flag

    def is_feature_enabled(self, flag_key: str, tenant_id: str | None = None, user_id: str | None = None) -> bool:
        """Check if a feature flag is enabled for a given context."""
        flag = self._feature_flags.get(flag_key)
        if not flag:
            return False

        if not flag.enabled:
            return False

        # Check dependencies
        for dep in flag.dependencies:
            if not self.is_feature_enabled(dep, tenant_id, user_id):
                return False

        # Tenant-specific enablement
        if tenant_id and tenant_id in flag.tenant_ids:
            return True

        # Percentage rollout
        if flag.rollout_percentage < 100 and user_id:
            import hashlib
            hash_val = int(hashlib.sha256(f"{flag_key}:{user_id}".encode()).hexdigest(), 16) % 100
            return hash_val < flag.rollout_percentage

        return flag.enabled

    def enable_feature(self, flag_key: str, enabled: bool = True) -> None:
        """Enable or disable a feature flag."""
        flag = self._feature_flags.get(flag_key)
        if flag:
            flag.enabled = enabled
            logger.info("Feature flag '%s' %s", flag_key, "enabled" if enabled else "disabled")

    def set_rollout_percentage(self, flag_key: str, percentage: int) -> None:
        """Set rollout percentage for a feature flag."""
        flag = self._feature_flags.get(flag_key)
        if flag:
            flag.rollout_percentage = max(0, min(100, percentage))

    # ── Audit Trail ────────────────────────────────────────────────

    def get_change_log(self, key: str | None = None, limit: int = 100) -> list[ConfigChangeLog]:
        """Get configuration change history."""
        if key:
            return [c for c in self._change_log if c.key == key][-limit:]
        return list(self._change_log[-limit:])

    def get_config_report(self) -> dict[str, Any]:
        """Get a comprehensive configuration report."""
        return {
            "registered_keys": len(self._configs),
            "feature_flags": {
                key: {
                    "enabled": flag.enabled,
                    "rollout": flag.rollout_percentage,
                    "dependencies": flag.dependencies,
                }
                for key, flag in self._feature_flags.items()
            },
            "recent_changes": [
                {"key": c.key, "changed_by": c.changed_by, "changed_at": c.changed_at, "reason": c.reason}
                for c in self._change_log[-20:]
            ],
            "environment": self._environment,
        }


# ── Global singleton ───────────────────────────────────────────────

runtime_config = RuntimeConfigService()
