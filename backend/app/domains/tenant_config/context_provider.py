"""Tenant Configuration Context Provider — merges Playbook standards with Policy Pack overrides.

This provider is the bridge between the Playbook (canonical clause standards, policy rules,
approval thresholds) and tenant-specific Policy Pack overrides. It loads both sources and
merges them using UUID-based matching, producing a unified context for the AI pipeline.

Architecture decision (Sprint 24 Task 3.2):
  - Playbook = canonical source of truth
  - Policy Packs = tenant-specific overlays (higher precedence)
  - Merge at query time using UUID key matching

Usage:
    provider = TenantConfigContextProvider(session, tenant_id)
    context = await provider.get_merged_context()
    # context.clause_overrides, context.rule_overrides, context.threshold_overrides
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.playbook.models import ClauseStandard, PolicyRule, ApprovalThreshold

logger = logging.getLogger(__name__)


# ── DTOs ───────────────────────────────────────────────────────────


@dataclass
class ClauseOverrideResult:
    """A clause standard with Policy Pack overrides applied."""
    clause_id: str
    category: str
    clause_type: str
    title: str
    body: str
    risk_level: str
    is_active: bool
    overridden: bool = False
    override_source_pack_id: Optional[str] = None


@dataclass
class RuleOverrideResult:
    """A policy rule with Policy Pack overrides applied."""
    rule_id: str
    name: str
    rule_type: str
    effect: str
    priority: int
    is_active: bool
    is_mandatory: bool
    effect_config: dict[str, Any] = field(default_factory=dict)
    overridden: bool = False
    override_source_pack_id: Optional[str] = None


@dataclass
class ThresholdOverrideResult:
    """An approval threshold with Policy Pack overrides applied."""
    threshold_id: str
    name: str
    threshold_type: str
    operator: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    approval_role: str = ""
    approval_level: int = 1
    is_active: bool = True
    overridden: bool = False
    override_source_pack_id: Optional[str] = None


@dataclass
class MergedPolicyContext:
    """Complete merged context combining Playbook standards with Policy Pack overrides."""
    playbook_id: Optional[str] = None
    playbook_name: str = ""
    clauses: list[ClauseOverrideResult] = field(default_factory=list)
    rules: list[RuleOverrideResult] = field(default_factory=list)
    thresholds: list[ThresholdOverrideResult] = field(default_factory=list)
    total_overrides_applied: int = 0
    total_overrides_skipped: int = 0


# ── Raw JSONB DTOs (mirrors PolicyPackCreate schemas) ──────────────


@dataclass
class RawRuleOverride:
    rule_id: str
    override_effect: Optional[str] = None
    override_priority: Optional[int] = None
    is_active: Optional[bool] = None
    effect_config_overrides: Optional[dict[str, Any]] = None


@dataclass
class RawThresholdOverride:
    threshold_id: str
    override_min_value: Optional[float] = None
    override_max_value: Optional[float] = None
    override_approval_role: Optional[str] = None
    override_approval_level: Optional[int] = None


@dataclass
class RawClauseOverride:
    clause_id: str
    override_body: Optional[str] = None
    override_risk_level: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass
class RawPolicyPack:
    """Mirrors the policy_packs table row for reading JSONB columns."""
    pack_id: str
    name: str
    playbook_id: Optional[str] = None
    is_active: bool = True
    rule_overrides: list[RawRuleOverride] = field(default_factory=list)
    threshold_overrides: list[RawThresholdOverride] = field(default_factory=list)
    clause_overrides: list[RawClauseOverride] = field(default_factory=list)


# ── Provider ───────────────────────────────────────────────────────


class TenantConfigContextProvider:
    """Loads Playbook standards, loads Policy Pack overrides, merges them via UUID matching.

    The merge strategy (validated in Sprint 24 Task 3.4):
      1. Parse override reference as UUID
      2. Look up matching Playbook entity by primary key
      3. If found: apply override values on top of Playbook entity
      4. If not found: log warning, skip override (graceful degradation)
      5. No name-based fallback matching
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def get_merged_context(self) -> MergedPolicyContext:
        """Load Playbook + Policy Packs and return merged context."""
        playbook = await self._load_active_playbook()
        packs = await self._load_active_policy_packs()

        if not playbook and not packs:
            logger.info("No active playbook or policy packs for tenant %s", self.tenant_id)
            return MergedPolicyContext()

        context = MergedPolicyContext(
            playbook_id=str(playbook.playbook_id) if playbook else None,
            playbook_name=playbook.name if playbook else "",
        )

        # Load base entities from Playbook
        clause_standards = await self._load_clause_standards(playbook)
        policy_rules = await self._load_policy_rules(playbook)
        approval_thresholds = await self._load_approval_thresholds(playbook)

        # Apply overrides
        context.clauses = await self._merge_clause_overrides(clause_standards, packs, context)
        context.rules = await self._merge_rule_overrides(policy_rules, packs, context)
        context.thresholds = await self._merge_threshold_overrides(approval_thresholds, packs, context)

        logger.info(
            "Merged policy context for tenant %s: %d clauses, %d rules, %d thresholds, "
            "%d overrides applied, %d skipped",
            self.tenant_id,
            len(context.clauses),
            len(context.rules),
            len(context.thresholds),
            context.total_overrides_applied,
            context.total_overrides_skipped,
        )
        return context

    # ── Data Loading ──────────────────────────────────────────────

    async def _load_active_playbook(self) -> Optional[Any]:
        """Load the first active/published playbook for this tenant."""
        from app.domains.playbook.models import LegalPlaybook, PlaybookStatus

        result = await self.session.execute(
            select(LegalPlaybook).where(
                LegalPlaybook.tenant_id == self.tenant_id,
                LegalPlaybook.status == PlaybookStatus.PUBLISHED,
            ).order_by(LegalPlaybook.updated_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _load_clause_standards(self, playbook: Optional[Any]) -> list[Any]:
        """Load clause standards for a playbook."""
        if not playbook:
            return []
        result = await self.session.execute(
            select(ClauseStandard).where(
                ClauseStandard.playbook_id == playbook.playbook_id,
                ClauseStandard.tenant_id == self.tenant_id,
                ClauseStandard.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def _load_policy_rules(self, playbook: Optional[Any]) -> list[Any]:
        """Load policy rules for a playbook."""
        if not playbook:
            return []
        result = await self.session.execute(
            select(PolicyRule).where(
                PolicyRule.playbook_id == playbook.playbook_id,
                PolicyRule.tenant_id == self.tenant_id,
                PolicyRule.is_active == True,
            ).order_by(PolicyRule.priority)
        )
        return list(result.scalars().all())

    async def _load_approval_thresholds(self, playbook: Optional[Any]) -> list[Any]:
        """Load approval thresholds for a playbook."""
        if not playbook:
            return []
        result = await self.session.execute(
            select(ApprovalThreshold).where(
                ApprovalThreshold.playbook_id == playbook.playbook_id,
                ApprovalThreshold.tenant_id == self.tenant_id,
                ApprovalThreshold.is_active == True,
            ).order_by(ApprovalThreshold.priority)
        )
        return list(result.scalars().all())

    async def _load_active_policy_packs(self) -> list[RawPolicyPack]:
        """Load all active policy packs for this tenant."""
        result = await self.session.execute(
            sa_text("""
                SELECT pack_id, name, playbook_id, is_active,
                       rule_overrides, threshold_overrides, clause_overrides
                FROM policy_packs
                WHERE tenant_id = :tid AND is_active = true
                ORDER BY created_at DESC
            """),
            {"tid": self.tenant_id},
        )
        packs = []
        for row in result.fetchall():
            packs.append(RawPolicyPack(
                pack_id=str(row.pack_id),
                name=row.name,
                playbook_id=str(row.playbook_id) if row.playbook_id else None,
                is_active=row.is_active,
                rule_overrides=[RawRuleOverride(**r) for r in (row.rule_overrides or [])],
                threshold_overrides=[RawThresholdOverride(**t) for t in (row.threshold_overrides or [])],
                clause_overrides=[RawClauseOverride(**c) for c in (row.clause_overrides or [])],
            ))
        return packs

    # ── Merge Logic ───────────────────────────────────────────────

    async def _merge_clause_overrides(
        self,
        standards: list[Any],
        packs: list[RawPolicyPack],
        context: MergedPolicyContext,
    ) -> list[ClauseOverrideResult]:
        """Apply clause overrides from Policy Packs onto Playbook clause standards."""
        # Build lookup map: clause_id (str) → ClauseStandard
        standard_map: dict[str, Any] = {}
        for s in standards:
            standard_map[str(s.clause_id)] = s

        # Start with base standards
        results: list[ClauseOverrideResult] = []
        for s in standards:
            results.append(ClauseOverrideResult(
                clause_id=str(s.clause_id),
                category=str(s.category.value) if hasattr(s.category, "value") else str(s.category),
                clause_type=str(s.clause_type.value) if hasattr(s.clause_type, "value") else str(s.clause_type),
                title=s.title,
                body=s.body,
                risk_level=s.risk_level,
                is_active=s.is_active,
            ))

        # Apply overrides
        for pack in packs:
            for override in pack.clause_overrides:
                target_id = override.clause_id

                # Validate UUID format
                if not self._is_valid_uuid(target_id):
                    logger.warning(
                        "Skipping clause override with non-UUID reference '%s' in pack %s",
                        target_id, pack.pack_id,
                    )
                    context.total_overrides_skipped += 1
                    continue

                # Look up in standard map
                target = standard_map.get(target_id)
                if target is None:
                    logger.warning(
                        "Skipping clause override: clause_id=%s not found in playbook standards (pack=%s)",
                        target_id, pack.pack_id,
                    )
                    context.total_overrides_skipped += 1
                    continue

                # Find and update the result entry
                for result in results:
                    if result.clause_id == target_id:
                        if override.override_body is not None:
                            result.body = override.override_body
                        if override.override_risk_level is not None:
                            result.risk_level = override.override_risk_level
                        if override.is_active is not None:
                            result.is_active = override.is_active
                        result.overridden = True
                        result.override_source_pack_id = pack.pack_id
                        context.total_overrides_applied += 1
                        break

        return results

    async def _merge_rule_overrides(
        self,
        rules: list[Any],
        packs: list[RawPolicyPack],
        context: MergedPolicyContext,
    ) -> list[RuleOverrideResult]:
        """Apply rule overrides from Policy Packs onto Playbook policy rules."""
        rule_map: dict[str, Any] = {}
        for r in rules:
            rule_map[str(r.rule_id)] = r

        results: list[RuleOverrideResult] = []
        for r in rules:
            results.append(RuleOverrideResult(
                rule_id=str(r.rule_id),
                name=r.name,
                rule_type=r.rule_type,
                effect=str(r.effect.value) if hasattr(r.effect, "value") else str(r.effect),
                priority=r.priority,
                is_active=r.is_active,
                is_mandatory=r.is_mandatory,
                effect_config=dict(r.effect_config) if r.effect_config else {},
            ))

        for pack in packs:
            for override in pack.rule_overrides:
                target_id = override.rule_id

                if not self._is_valid_uuid(target_id):
                    logger.warning(
                        "Skipping rule override with non-UUID reference '%s' in pack %s",
                        target_id, pack.pack_id,
                    )
                    context.total_overrides_skipped += 1
                    continue

                target = rule_map.get(target_id)
                if target is None:
                    logger.warning(
                        "Skipping rule override: rule_id=%s not found in playbook rules (pack=%s)",
                        target_id, pack.pack_id,
                    )
                    context.total_overrides_skipped += 1
                    continue

                for result in results:
                    if result.rule_id == target_id:
                        if override.override_effect is not None:
                            result.effect = override.override_effect
                        if override.override_priority is not None:
                            result.priority = override.override_priority
                        if override.is_active is not None:
                            result.is_active = override.is_active
                        if override.effect_config_overrides is not None:
                            result.effect_config.update(override.effect_config_overrides)
                        result.overridden = True
                        result.override_source_pack_id = pack.pack_id
                        context.total_overrides_applied += 1
                        break

        return results

    async def _merge_threshold_overrides(
        self,
        thresholds: list[Any],
        packs: list[RawPolicyPack],
        context: MergedPolicyContext,
    ) -> list[ThresholdOverrideResult]:
        """Apply threshold overrides from Policy Packs onto Playbook approval thresholds."""
        threshold_map: dict[str, Any] = {}
        for t in thresholds:
            threshold_map[str(t.threshold_id)] = t

        results: list[ThresholdOverrideResult] = []
        for t in thresholds:
            results.append(ThresholdOverrideResult(
                threshold_id=str(t.threshold_id),
                name=t.name,
                threshold_type=t.threshold_type,
                operator=t.operator,
                min_value=t.min_value,
                max_value=t.max_value,
                approval_role=t.approval_role,
                approval_level=t.approval_level,
                is_active=t.is_active,
            ))

        for pack in packs:
            for override in pack.threshold_overrides:
                target_id = override.threshold_id

                if not self._is_valid_uuid(target_id):
                    logger.warning(
                        "Skipping threshold override with non-UUID reference '%s' in pack %s",
                        target_id, pack.pack_id,
                    )
                    context.total_overrides_skipped += 1
                    continue

                target = threshold_map.get(target_id)
                if target is None:
                    logger.warning(
                        "Skipping threshold override: threshold_id=%s not found in playbook thresholds (pack=%s)",
                        target_id, pack.pack_id,
                    )
                    context.total_overrides_skipped += 1
                    continue

                for result in results:
                    if result.threshold_id == target_id:
                        if override.override_min_value is not None:
                            result.min_value = override.override_min_value
                        if override.override_max_value is not None:
                            result.max_value = override.override_max_value
                        if override.override_approval_role is not None:
                            result.approval_role = override.override_approval_role
                        if override.override_approval_level is not None:
                            result.approval_level = override.override_approval_level
                        result.overridden = True
                        result.override_source_pack_id = pack.pack_id
                        context.total_overrides_applied += 1
                        break

        return results

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Check if a string is a valid UUID v4."""
        if not value or not isinstance(value, str):
            return False
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
