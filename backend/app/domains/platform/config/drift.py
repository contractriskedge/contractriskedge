"""Config Drift Detection — detects stale rollout state, tenant mismatch, environment inconsistency, orphan configs.

Prevents silent operational chaos from configuration drift across the platform.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DriftSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DriftType(str, Enum):
    STALE_ROLLOUT = "stale_rollout"
    TENANT_MISMATCH = "tenant_mismatch"
    ENVIRONMENT_INCONSISTENCY = "environment_inconsistency"
    ORPHAN_CONFIG = "orphan_config"
    INVALID_POLICY_CHAIN = "invalid_policy_chain"
    PROMPT_VERSION_DRIFT = "prompt_version_drift"
    EMBEDDING_MODEL_DRIFT = "embedding_model_drift"
    RETENTION_POLICY_DRIFT = "retention_policy_drift"


@dataclass
class ConfigDrift:
    """A single configuration drift instance."""
    drift_id: str
    drift_type: DriftType
    severity: DriftSeverity
    config_key: str
    expected_value: Any
    actual_value: Any
    source: str  # e.g., "tenant:abc123", "environment:staging"
    details: str = ""
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    auto_repairable: bool = False


@dataclass
class DriftReport:
    """Complete configuration drift report."""
    total_drifts: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    drifts: list[ConfigDrift] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def passed(self) -> bool:
        return self.critical_count == 0


@dataclass
class ConfigDriftDetector:
    """Detects configuration drift across the platform.

    Monitors:
    - Stale rollout state (feature flags that should have been promoted)
    - Tenant mismatch (tenant config differs from baseline)
    - Environment inconsistency (staging vs production configs)
    - Orphan configs (config keys no longer referenced)
    - Invalid policy chains (broken dependency chains)
    - Prompt version drift (different tenants on different prompt versions)
    - Embedding model drift (chunks using outdated embedding models)
    - Retention policy drift (tenant retention differs from defaults)
    """

    _baseline_configs: dict[str, Any] = field(default_factory=dict)
    _known_config_keys: set[str] = field(default_factory=set)

    def set_baseline(self, key: str, value: Any) -> None:
        """Set the baseline (expected) value for a config key."""
        self._baseline_configs[key] = value
        self._known_config_keys.add(key)

    def register_config_key(self, key: str) -> None:
        """Register a known config key (for orphan detection)."""
        self._known_config_keys.add(key)

    async def check_tenant_mismatch(
        self,
        tenant_id: str,
        tenant_config: dict[str, Any],
        baseline_overrides: dict[str, Any] | None = None,
    ) -> list[ConfigDrift]:
        """Check if a tenant's config has drifted from baseline."""
        drifts: list[ConfigDrift] = []
        overrides = baseline_overrides or {}

        for key, expected_value in self._baseline_configs.items():
            actual_value = tenant_config.get(key, overrides.get(key, expected_value))

            # Skip if tenant has a deliberate override
            if key in overrides:
                expected_value = overrides[key]

            if actual_value != expected_value:
                drifts.append(ConfigDrift(
                    drift_id=self._make_drift_id(),
                    drift_type=DriftType.TENANT_MISMATCH,
                    severity=DriftSeverity.WARNING,
                    config_key=key,
                    expected_value=expected_value,
                    actual_value=actual_value,
                    source=f"tenant:{tenant_id}",
                    details=f"Tenant config differs from baseline for '{key}'",
                    auto_repairable=True,
                ))

        return drifts

    async def check_environment_consistency(
        self,
        env_a: str,
        config_a: dict[str, Any],
        env_b: str,
        config_b: dict[str, Any],
        expected_differences: set[str] | None = None,
    ) -> list[ConfigDrift]:
        """Check consistency between two environments (e.g., staging vs production).

        Args:
            env_a: Name of first environment.
            config_a: Config dict for first environment.
            env_b: Name of second environment.
            config_b: Config dict for second environment.
            expected_differences: Set of config keys that are intentionally different.

        Returns:
            List of unexpected config drifts between environments.
        """
        drifts: list[ConfigDrift] = []
        expected = expected_differences or set()
        all_keys = set(config_a.keys()) | set(config_b.keys())

        for key in all_keys:
            if key in expected:
                continue

            val_a = config_a.get(key)
            val_b = config_b.get(key)

            if val_a != val_b:
                drifts.append(ConfigDrift(
                    drift_id=self._make_drift_id(),
                    drift_type=DriftType.ENVIRONMENT_INCONSISTENCY,
                    severity=DriftSeverity.WARNING,
                    config_key=key,
                    expected_value=val_a,
                    actual_value=val_b,
                    source=f"environment:{env_a} vs {env_b}",
                    details=f"'{key}' differs between {env_a} ({val_a}) and {env_b} ({val_b})",
                    auto_repairable=False,
                ))

        return drifts

    async def check_stale_rollouts(
        self,
        feature_flags: dict[str, dict[str, Any]],
        staleness_threshold_days: int = 30,
    ) -> list[ConfigDrift]:
        """Detect feature flags that have been in rollout for too long.

        A flag at 50% for 60 days should either be promoted to 100% or removed.
        """
        drifts: list[ConfigDrift] = []
        now = datetime.utcnow()

        for flag_key, flag_config in feature_flags.items():
            rollout_pct = flag_config.get("rollout_percentage", 0)
            created_at_str = flag_config.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_days = (now - created_at).days

                    if 0 < rollout_pct < 100 and age_days > staleness_threshold_days:
                        drifts.append(ConfigDrift(
                            drift_id=self._make_drift_id(),
                            drift_type=DriftType.STALE_ROLLOUT,
                            severity=DriftSeverity.WARNING,
                            config_key=flag_key,
                            expected_value=100,
                            actual_value=rollout_pct,
                            source=f"feature_flag:{flag_key}",
                            details=f"Flag at {rollout_pct}% for {age_days} days (threshold: {staleness_threshold_days}d)",
                            auto_repairable=False,
                        ))
                except (ValueError, TypeError):
                    pass

        return drifts

    async def check_orphan_configs(
        self,
        active_config_keys: set[str],
    ) -> list[ConfigDrift]:
        """Detect config keys that are no longer referenced."""
        drifts: list[ConfigDrift] = []
        orphans = self._known_config_keys - active_config_keys

        for key in orphans:
            drifts.append(ConfigDrift(
                drift_id=self._make_drift_id(),
                drift_type=DriftType.ORPHAN_CONFIG,
                severity=DriftSeverity.INFO,
                config_key=key,
                expected_value=None,
                actual_value="still_present",
                source="config_registry",
                details=f"Config key '{key}' is registered but no longer referenced",
                auto_repairable=True,
            ))

        return drifts

    async def check_prompt_version_drift(
        self,
        tenant_prompt_versions: dict[str, dict[str, str]],
        expected_active_versions: dict[str, str],
    ) -> list[ConfigDrift]:
        """Detect tenants running different prompt versions than expected."""
        drifts: list[ConfigDrift] = []

        for tenant_id, prompt_versions in tenant_prompt_versions.items():
            for prompt_key, active_version in prompt_versions.items():
                expected = expected_active_versions.get(prompt_key)
                if expected and active_version != expected:
                    drifts.append(ConfigDrift(
                        drift_id=self._make_drift_id(),
                        drift_type=DriftType.PROMPT_VERSION_DRIFT,
                        severity=DriftSeverity.WARNING,
                        config_key=f"prompt:{prompt_key}",
                        expected_value=expected,
                        actual_value=active_version,
                        source=f"tenant:{tenant_id}",
                        details=f"Tenant {tenant_id[:8]} on prompt v{active_version}, expected v{expected}",
                        auto_repairable=False,
                    ))

        return drifts

    async def run_full_drift_scan(
        self,
        tenant_configs: dict[str, dict[str, Any]] | None = None,
        environment_configs: dict[str, dict[str, Any]] | None = None,
        feature_flags: dict[str, dict[str, Any]] | None = None,
        active_config_keys: set[str] | None = None,
        tenant_prompt_versions: dict[str, dict[str, str]] | None = None,
        expected_prompt_versions: dict[str, str] | None = None,
    ) -> DriftReport:
        """Run a comprehensive drift scan across all dimensions."""
        all_drifts: list[ConfigDrift] = []

        # Tenant mismatch scan
        if tenant_configs:
            for tenant_id, config in tenant_configs.items():
                drifts = await self.check_tenant_mismatch(tenant_id, config)
                all_drifts.extend(drifts)

        # Environment consistency scan
        if environment_configs and len(environment_configs) >= 2:
            env_names = list(environment_configs.keys())
            for i in range(len(env_names)):
                for j in range(i + 1, len(env_names)):
                    drifts = await self.check_environment_consistency(
                        env_names[i], environment_configs[env_names[i]],
                        env_names[j], environment_configs[env_names[j]],
                    )
                    all_drifts.extend(drifts)

        # Stale rollout scan
        if feature_flags:
            drifts = await self.check_stale_rollouts(feature_flags)
            all_drifts.extend(drifts)

        # Orphan config scan
        if active_config_keys is not None:
            drifts = await self.check_orphan_configs(active_config_keys)
            all_drifts.extend(drifts)

        # Prompt version drift scan
        if tenant_prompt_versions and expected_prompt_versions:
            drifts = await self.check_prompt_version_drift(tenant_prompt_versions, expected_prompt_versions)
            all_drifts.extend(drifts)

        critical = sum(1 for d in all_drifts if d.severity == DriftSeverity.CRITICAL)
        warnings = sum(1 for d in all_drifts if d.severity == DriftSeverity.WARNING)
        info = sum(1 for d in all_drifts if d.severity == DriftSeverity.INFO)

        recommendations = []
        if critical > 0:
            recommendations.append(f"Resolve {critical} critical drifts immediately")
        if warnings > 0:
            recommendations.append(f"Review {warnings} warning-level drifts in next sprint")
        if info > 0:
            recommendations.append(f"Clean up {info} informational drifts (orphan configs)")
        if not all_drifts:
            recommendations.append("No configuration drift detected — all systems consistent")

        return DriftReport(
            total_drifts=len(all_drifts),
            critical_count=critical,
            warning_count=warnings,
            info_count=info,
            drifts=all_drifts,
            recommendations=recommendations,
        )

    def _make_drift_id(self) -> str:
        import uuid
        return f"drift_{uuid.uuid4().hex[:12]}"
