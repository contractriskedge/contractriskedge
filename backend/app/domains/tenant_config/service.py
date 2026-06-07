"""Tenant Configuration Framework service — feature flags, policy packs, scoring overrides, compliance packs."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.tenant_config.schemas import (
    FeatureFlagScope, FeatureFlagState, RolloutStrategy,
    PolicyPackScope, ComplianceRegion,
    FeatureFlagDefinition, FeatureFlagOverride, FeatureFlagEvaluation,
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse,
    FeatureOverrideCreate,
    PolicyPackCreate, PolicyPackResponse, PolicyPackAssignment,
    PolicyPackRuleOverride, PolicyPackThresholdOverride, PolicyPackClauseOverride,
    ScoringOverrideCreate, ScoringOverrideResponse,
    CompliancePackCreate, CompliancePackResponse,
    ComplianceRegulationRef, JurisdictionRule,
    TenantConfigurationSummary,
)

logger = logging.getLogger(__name__)


# ── Built-in Feature Flag Registry ──────────────────────────────────

_BUILTIN_FEATURE_FLAGS: dict[str, FeatureFlagDefinition] = {
    "ai_analysis": FeatureFlagDefinition(
        flag_key="ai_analysis",
        name="AI Analysis",
        description="Enable AI-powered contract analysis",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
    ),
    "redlines": FeatureFlagDefinition(
        flag_key="redlines",
        name="AI Redline Suggestions",
        description="Enable AI-generated redline suggestions",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
        dependencies=["ai_analysis"],
    ),
    "semantic_search": FeatureFlagDefinition(
        flag_key="semantic_search",
        name="Semantic Search",
        description="Enable semantic search across contracts",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
    ),
    "policy_engine": FeatureFlagDefinition(
        flag_key="policy_engine",
        name="Policy Engine",
        description="Enable declarative policy rule evaluation",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
        dependencies=["ai_analysis"],
    ),
    "explainability": FeatureFlagDefinition(
        flag_key="explainability",
        name="AI Explainability",
        description="Enable evidence-chain explainability for AI findings",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
        dependencies=["ai_analysis"],
    ),
    "clause_intelligence": FeatureFlagDefinition(
        flag_key="clause_intelligence",
        name="Clause Intelligence",
        description="Enable clause knowledge graph and negotiation intelligence",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.BETA,
        default_enabled=False,
        dependencies=["ai_analysis"],
    ),
    "executive_analytics": FeatureFlagDefinition(
        flag_key="executive_analytics",
        name="Executive Analytics",
        description="Enable executive dashboard and reporting",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
    ),
    "bulk_operations": FeatureFlagDefinition(
        flag_key="bulk_operations",
        name="Bulk Operations",
        description="Enable batch upload and bulk review operations",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
    ),
    "exports": FeatureFlagDefinition(
        flag_key="exports",
        name="Exports",
        description="Enable document and report exports",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
    ),
    "notifications": FeatureFlagDefinition(
        flag_key="notifications",
        name="Notifications",
        description="Enable in-app and email notifications",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
    ),
    "automation": FeatureFlagDefinition(
        flag_key="automation",
        name="Workflow Automation",
        description="Enable automated workflow actions and triggers",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.BETA,
        default_enabled=False,
    ),
    "tenant_customization": FeatureFlagDefinition(
        flag_key="tenant_customization",
        name="Tenant Customization",
        description="Enable tenant-level configuration overrides",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.BETA,
        default_enabled=False,
    ),
    "benchmarking": FeatureFlagDefinition(
        flag_key="benchmarking",
        name="Benchmarking",
        description="Enable contract clause benchmarking against market data",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.GENERAL_AVAILABILITY,
        default_enabled=True,
    ),
    "ai_governance": FeatureFlagDefinition(
        flag_key="ai_governance",
        name="AI Governance",
        description="Enable AI evaluation, regression testing, and quality governance",
        scope=FeatureFlagScope.GLOBAL,
        state=FeatureFlagState.DEVELOPMENT,
        default_enabled=False,
    ),
}


@dataclass
class FeatureFlagService:
    """Manages feature flag definitions, overrides, and evaluation."""

    session: AsyncSession
    tenant_id: str

    def list_definitions(self) -> list[FeatureFlagDefinition]:
        """List all built-in feature flag definitions."""
        return list(_BUILTIN_FEATURE_FLAGS.values())

    def get_definition(self, flag_key: str) -> Optional[FeatureFlagDefinition]:
        """Get a single feature flag definition."""
        return _BUILTIN_FEATURE_FLAGS.get(flag_key)

    async def evaluate_flag(
        self,
        flag_key: str,
        business_unit: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> FeatureFlagEvaluation:
        """Evaluate a feature flag for the current tenant context."""
        definition = _BUILTIN_FEATURE_FLAGS.get(flag_key)
        if not definition:
            return FeatureFlagEvaluation(
                flag_key=flag_key,
                enabled=False,
                source="default",
                reason=f"Unknown flag: {flag_key}",
                evaluated_at=datetime.now(timezone.utc),
            )

        # 1. Check tenant-level override
        try:
            tenant_override = await self._get_override(flag_key, "tenant", self.tenant_id)
            if tenant_override is not None:
                return FeatureFlagEvaluation(
                    flag_key=flag_key,
                    enabled=tenant_override,
                    source="tenant_override",
                    reason=f"Tenant override: {tenant_override}",
                    evaluated_at=datetime.now(timezone.utc),
                )
        except Exception:
            pass

        # 2. Check business-unit override
        if business_unit:
            try:
                bu_override = await self._get_override(flag_key, "business_unit", business_unit)
                if bu_override is not None:
                    return FeatureFlagEvaluation(
                        flag_key=flag_key,
                        enabled=bu_override,
                        source="business_unit_override",
                        reason=f"Business unit '{business_unit}' override: {bu_override}",
                        evaluated_at=datetime.now(timezone.utc),
                    )
            except Exception:
                pass

        # 3. Check user role override
        if user_role:
            try:
                role_override = await self._get_override(flag_key, "role", user_role)
                if role_override is not None:
                    return FeatureFlagEvaluation(
                        flag_key=flag_key,
                        enabled=role_override,
                        source="role_override",
                        reason=f"Role '{user_role}' override: {role_override}",
                        evaluated_at=datetime.now(timezone.utc),
                    )
            except Exception:
                pass

        # 4. Check rollout strategy
        if definition.rollout_strategy == RolloutStrategy.PLAN_TIER:
            enabled = await self._evaluate_plan_tier(flag_key)
            if enabled is not None:
                return FeatureFlagEvaluation(
                    flag_key=flag_key,
                    enabled=enabled,
                    source="plan_tier",
                    reason=f"Plan tier evaluation: {enabled}",
                    evaluated_at=datetime.now(timezone.utc),
                )

        # 5. Fall back to default
        return FeatureFlagEvaluation(
            flag_key=flag_key,
            enabled=definition.default_enabled,
            source="default",
            reason=f"Default value: {definition.default_enabled}",
            evaluated_at=datetime.now(timezone.utc),
        )

    async def evaluate_bulk(
        self,
        flag_keys: Optional[list[str]] = None,
        business_unit: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> list[FeatureFlagEvaluation]:
        """Evaluate multiple feature flags at once."""
        keys = flag_keys or list(_BUILTIN_FEATURE_FLAGS.keys())
        results: list[FeatureFlagEvaluation] = []
        for key in keys:
            result = await self.evaluate_flag(
                flag_key=key,
                business_unit=business_unit,
                user_role=user_role,
            )
            results.append(result)
        return results

    async def set_override(self, override: FeatureOverrideCreate, actor: str) -> FeatureFlagOverride:
        """Create or update a feature flag override."""
        now = datetime.now(timezone.utc)

        # Upsert logic — table has auto-increment `id`, not `override_id`
        sql = sa_text("""
            INSERT INTO feature_flag_overrides (flag_key, target_type, target_id,
                enabled, expires_at, created_at, updated_at)
            VALUES (:flag_key, :target_type, :target_id,
                :enabled, :expires_at, :created_at, :created_at)
            ON CONFLICT (flag_key, target_type, target_id)
            DO UPDATE SET enabled = :enabled, expires_at = :expires_at, updated_at = :now
            RETURNING id, flag_key, target_type, target_id, enabled,
                expires_at, created_at, updated_at
        """)
        result = await self.session.execute(sql, {
            "flag_key": override.flag_key,
            "target_type": override.target_type,
            "target_id": override.target_id,
            "enabled": override.enabled,
            "expires_at": override.expires_at,
            "created_at": now,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return FeatureFlagOverride(
            override_id=str(row.id),
            flag_key=row.flag_key,
            target_type=row.target_type,
            target_id=row.target_id,
            enabled=row.enabled,
            reason="",
            expires_at=row.expires_at,
            created_by=actor,
            created_at=row.created_at,
        )

    async def remove_override(self, flag_key: str, target_type: str, target_id: str) -> bool:
        """Remove a feature flag override."""
        sql = sa_text("""
            DELETE FROM feature_flag_overrides
            WHERE flag_key = :flag_key AND target_type = :target_type AND target_id = :target_id
        """)
        result = await self.session.execute(sql, {
            "flag_key": flag_key,
            "target_type": target_type,
            "target_id": target_id,
        })
        await self.session.commit()
        return result.rowcount > 0

    async def _get_override(self, flag_key: str, target_type: str, target_id: str) -> Optional[bool]:
        """Get a specific override value."""
        sql = sa_text("""
            SELECT enabled FROM feature_flag_overrides
            WHERE flag_key = :flag_key AND target_type = :target_type AND target_id = :target_id
              AND (expires_at IS NULL OR expires_at > NOW())
        """)
        result = await self.session.execute(sql, {
            "flag_key": flag_key,
            "target_type": target_type,
            "target_id": target_id,
        })
        row = result.fetchone()
        return row.enabled if row else None

    async def _evaluate_plan_tier(self, flag_key: str) -> Optional[bool]:
        """Evaluate flag based on tenant's plan tier."""
        sql = sa_text("""
            SELECT plan FROM tenants WHERE tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        row = result.fetchone()
        if not row:
            return None
        plan = row.plan

        # Plan-based feature availability
        enterprise_only = {"automation", "tenant_customization", "ai_governance", "clause_intelligence"}
        pro_features = {"policy_engine", "explainability", "executive_analytics", "benchmarking"}

        if flag_key in enterprise_only:
            return plan in ("enterprise", "enterprise_plus")
        if flag_key in pro_features:
            return plan in ("pro", "enterprise", "enterprise_plus")
        return True  # available on all plans


@dataclass
class PolicyPackService:
    """Manages tenant policy packs — bundled rule/threshold/clause overrides."""

    session: AsyncSession
    tenant_id: str

    async def create_pack(self, pack: PolicyPackCreate, actor: str) -> PolicyPackResponse:
        """Create a new policy pack."""
        pack_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)

        sql = sa_text("""
            INSERT INTO policy_packs (pack_id, tenant_id, name, description, scope,
                region, industry, jurisdiction, playbook_id,
                rule_overrides, threshold_overrides, clause_overrides,
                is_active, version, created_by, created_at, updated_at)
            VALUES (:pid, :tid, :name, :desc, :scope,
                :region, :industry, :jurisdiction, :playbook_id,
                CAST(:rule_overrides AS jsonb), CAST(:threshold_overrides AS jsonb), CAST(:clause_overrides AS jsonb),
                :is_active, 1, :actor, :now, :now)
            RETURNING pack_id, name, description, scope, region, industry, jurisdiction,
                playbook_id, rule_overrides, threshold_overrides, clause_overrides,
                is_active, version, created_by, created_at, updated_at
        """)
        result = await self.session.execute(sql, {
            "pid": pack_id,
            "tid": self.tenant_id,
            "name": pack.name,
            "desc": pack.description,
            "scope": pack.scope.value if hasattr(pack.scope, 'value') else pack.scope,
            "region": pack.region.value if pack.region and hasattr(pack.region, 'value') else pack.region,
            "industry": pack.industry,
            "jurisdiction": pack.jurisdiction,
            "playbook_id": pack.playbook_id,
            "rule_overrides": json.dumps([r.model_dump() for r in pack.rule_overrides]),
            "threshold_overrides": json.dumps([t.model_dump() for t in pack.threshold_overrides]),
            "clause_overrides": json.dumps([c.model_dump() for c in pack.clause_overrides]),
            "is_active": pack.is_active,
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_pack_response(row)

    async def list_packs(self) -> list[PolicyPackResponse]:
        """List all policy packs for the tenant."""
        sql = sa_text("""
            SELECT * FROM policy_packs
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [self._row_to_pack_response(r) for r in result.fetchall()]

    async def get_pack(self, pack_id: str) -> Optional[PolicyPackResponse]:
        """Get a specific policy pack."""
        sql = sa_text("""
            SELECT * FROM policy_packs WHERE pack_id = :pid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"pid": pack_id, "tid": self.tenant_id})
        row = result.fetchone()
        return self._row_to_pack_response(row) if row else None

    async def delete_pack(self, pack_id: str) -> bool:
        """Delete a policy pack."""
        sql = sa_text("""
            DELETE FROM policy_packs WHERE pack_id = :pid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"pid": pack_id, "tid": self.tenant_id})
        await self.session.commit()
        return result.rowcount > 0

    def _row_to_pack_response(self, row) -> PolicyPackResponse:
        return PolicyPackResponse(
            pack_id=str(row.pack_id),
            name=row.name,
            description=row.description,
            scope=row.scope,
            region=row.region,
            industry=row.industry,
            jurisdiction=row.jurisdiction,
            playbook_id=str(row.playbook_id) if row.playbook_id else None,
            rule_overrides=[PolicyPackRuleOverride(**o) for o in (row.rule_overrides or [])],
            threshold_overrides=[PolicyPackThresholdOverride(**o) for o in (row.threshold_overrides or [])],
            clause_overrides=[PolicyPackClauseOverride(**o) for o in (row.clause_overrides or [])],
            is_active=row.is_active,
            version=row.version,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


@dataclass
class ScoringOverrideService:
    """Manages tenant-level scoring overrides for specific clause types."""

    session: AsyncSession
    tenant_id: str

    async def create_override(self, override: ScoringOverrideCreate, actor: str) -> ScoringOverrideResponse:
        """Create a scoring override."""
        override_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)

        sql = sa_text("""
            INSERT INTO scoring_overrides (override_id, tenant_id, clause_type,
                override_severity, override_risk_weight, override_risk_score,
                is_active, reason, applies_to_business_units, created_by, created_at, updated_at)
            VALUES (:oid, :tid, :clause_type,
                :severity, :weight, :score,
                :is_active, :reason, CAST(:bus AS jsonb), :actor, :now, :now)
            RETURNING override_id, tenant_id, clause_type, override_severity,
                override_risk_weight, override_risk_score, is_active, reason,
                applies_to_business_units, created_by, created_at, updated_at
        """)
        result = await self.session.execute(sql, {
            "oid": override_id,
            "tid": self.tenant_id,
            "clause_type": override.clause_type,
            "severity": override.override_severity,
            "weight": override.override_risk_weight,
            "score": override.override_risk_score,
            "is_active": override.is_active,
            "reason": override.reason,
            "bus": json.dumps(override.applies_to_business_units or []),
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_scoring_response(row)

    async def list_overrides(self) -> list[ScoringOverrideResponse]:
        """List all scoring overrides for the tenant."""
        sql = sa_text("""
            SELECT * FROM scoring_overrides
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [self._row_to_scoring_response(r) for r in result.fetchall()]

    async def delete_override(self, override_id: str) -> bool:
        """Delete a scoring override."""
        sql = sa_text("""
            DELETE FROM scoring_overrides WHERE override_id = :oid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"oid": override_id, "tid": self.tenant_id})
        await self.session.commit()
        return result.rowcount > 0

    def _row_to_scoring_response(self, row) -> ScoringOverrideResponse:
        return ScoringOverrideResponse(
            override_id=str(row.override_id),
            tenant_id=str(row.tenant_id),
            clause_type=row.clause_type,
            override_severity=row.override_severity,
            override_risk_weight=row.override_risk_weight,
            override_risk_score=row.override_risk_score,
            is_active=row.is_active,
            reason=row.reason or "",
            applies_to_business_units=row.applies_to_business_units or [],
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


@dataclass
class CompliancePackService:
    """Manages regional compliance packs — regulation bundles per jurisdiction."""

    session: AsyncSession
    tenant_id: str

    async def create_pack(self, pack: CompliancePackCreate, actor: str) -> CompliancePackResponse:
        """Create a compliance pack for a region."""
        pack_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)

        sql = sa_text("""
            INSERT INTO compliance_packs (pack_id, tenant_id, region, name, description,
                regulations, required_clause_categories, forbidden_clause_categories,
                jurisdiction_rules, is_active, version, created_by, created_at, updated_at)
            VALUES (:pid, :tid, :region, :name, :desc,
                CAST(:regulations AS jsonb), CAST(:required AS jsonb), CAST(:forbidden AS jsonb),
                CAST(:rules AS jsonb), :is_active, 1, :actor, :now, :now)
            RETURNING pack_id, region, name, description, regulations,
                required_clause_categories, forbidden_clause_categories,
                jurisdiction_rules, is_active, version, created_by, created_at, updated_at
        """)
        result = await self.session.execute(sql, {
            "pid": pack_id,
            "tid": self.tenant_id,
            "region": pack.region.value if hasattr(pack.region, 'value') else pack.region,
            "name": pack.name,
            "desc": pack.description,
            "regulations": json.dumps([r.model_dump() for r in pack.regulations]),
            "required": json.dumps(pack.required_clause_categories),
            "forbidden": json.dumps(pack.forbidden_clause_categories),
            "rules": json.dumps([r.model_dump() for r in pack.jurisdiction_rules]),
            "is_active": pack.is_active,
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_compliance_response(row)

    async def list_packs(self, region: Optional[ComplianceRegion] = None) -> list[CompliancePackResponse]:
        """List compliance packs, optionally filtered by region."""
        if region:
            sql = sa_text("""
                SELECT * FROM compliance_packs
                WHERE tenant_id = :tid AND region = :region
                ORDER BY created_at DESC
            """)
            result = await self.session.execute(sql, {"tid": self.tenant_id, "region": region.value if hasattr(region, 'value') else region})
        else:
            sql = sa_text("""
                SELECT * FROM compliance_packs
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """)
            result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [self._row_to_compliance_response(r) for r in result.fetchall()]

    def _row_to_compliance_response(self, row) -> CompliancePackResponse:
        return CompliancePackResponse(
            pack_id=str(row.pack_id),
            region=row.region,
            name=row.name,
            description=row.description,
            regulations=[ComplianceRegulationRef(**r) for r in (row.regulations or [])],
            required_clause_categories=row.required_clause_categories or [],
            forbidden_clause_categories=row.forbidden_clause_categories or [],
            jurisdiction_rules=[JurisdictionRule(**r) for r in (row.jurisdiction_rules or [])],
            is_active=row.is_active,
            version=row.version,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


@dataclass
class TenantConfigurationService:
    """Aggregates full tenant configuration for the admin console."""

    session: AsyncSession
    tenant_id: str

    async def get_full_configuration(self) -> TenantConfigurationSummary:
        """Get the complete configuration summary for a tenant."""
        # Get tenant info
        tenant_sql = sa_text("""
            SELECT name, plan FROM tenants WHERE tenant_id = :tid
        """)
        result = await self.session.execute(tenant_sql, {"tid": self.tenant_id})
        tenant = result.fetchone()
        tenant_name = tenant.name if tenant else ""
        plan = tenant.plan if tenant else "starter"

        # Evaluate all feature flags
        flag_service = FeatureFlagService(self.session, self.tenant_id)
        flags = await flag_service.evaluate_bulk()

        # Get active policy packs
        pack_service = PolicyPackService(self.session, self.tenant_id)
        packs = await pack_service.list_packs()

        # Get scoring overrides
        scoring_service = ScoringOverrideService(self.session, self.tenant_id)
        overrides = await scoring_service.list_overrides()

        # Get compliance packs
        compliance_service = CompliancePackService(self.session, self.tenant_id)
        compliance = await compliance_service.list_packs()

        # Get business units
        bu_sql = sa_text("""
            SELECT DISTINCT business_unit FROM admin_users
            WHERE tenant_id = :tid AND business_unit IS NOT NULL
        """)
        bu_result = await self.session.execute(bu_sql, {"tid": self.tenant_id})
        business_units = [r.business_unit for r in bu_result.fetchall() if r.business_unit]

        return TenantConfigurationSummary(
            tenant_id=self.tenant_id,
            tenant_name=tenant_name,
            plan=plan,
            feature_flags=flags,
            active_policy_packs=[p for p in packs if p.is_active],
            scoring_overrides=overrides,
            compliance_packs=compliance,
            business_units=business_units,
        )
