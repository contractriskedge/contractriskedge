"""Tenant Configuration API router — feature flags, policy packs, scoring overrides, compliance."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.tenant_config.schemas import (
    FeatureFlagScope, FeatureFlagState, RolloutStrategy,
    FeatureFlagDefinition, FeatureFlagEvaluation,
    FeatureFlagResponse, FeatureFlagCreate, FeatureFlagUpdate,
    FeatureOverrideCreate, FeatureFlagOverride,
    PolicyPackCreate, PolicyPackResponse, PolicyPackAssignment,
    ScoringOverrideCreate, ScoringOverrideResponse,
    CompliancePackCreate, CompliancePackResponse, ComplianceRegion,
    TenantConfigurationSummary,
)
from app.domains.tenant_config.service import (
    FeatureFlagService,
    PolicyPackService,
    ScoringOverrideService,
    CompliancePackService,
    TenantConfigurationService,
)

router = APIRouter(prefix="/tenant-config", tags=["Tenant Configuration"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_flag_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> FeatureFlagService:
    return FeatureFlagService(session=db, tenant_id=tenant_id)


async def get_pack_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> PolicyPackService:
    return PolicyPackService(session=db, tenant_id=tenant_id)


async def get_scoring_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ScoringOverrideService:
    return ScoringOverrideService(session=db, tenant_id=tenant_id)


async def get_compliance_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> CompliancePackService:
    return CompliancePackService(session=db, tenant_id=tenant_id)


async def get_config_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> TenantConfigurationService:
    return TenantConfigurationService(session=db, tenant_id=tenant_id)


# ── Feature Flags ───────────────────────────────────────────────────


@router.get("/features/definitions", response_model=list[FeatureFlagDefinition])
async def list_feature_definitions(
    service: FeatureFlagService = Depends(get_flag_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """List all built-in feature flag definitions."""
    return service.list_definitions()


@router.get("/features/evaluate", response_model=list[FeatureFlagEvaluation])
async def evaluate_feature_flags(
    business_unit: Optional[str] = Query(None),
    user_role: Optional[str] = Query(None),
    service: FeatureFlagService = Depends(get_flag_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Evaluate all feature flags for the current tenant context."""
    return await service.evaluate_bulk(
        business_unit=business_unit,
        user_role=user_role,
    )


@router.get("/features/evaluate/{flag_key}", response_model=FeatureFlagEvaluation)
async def evaluate_single_feature_flag(
    flag_key: str,
    business_unit: Optional[str] = Query(None),
    user_role: Optional[str] = Query(None),
    service: FeatureFlagService = Depends(get_flag_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Evaluate a single feature flag."""
    return await service.evaluate_flag(
        flag_key=flag_key,
        business_unit=business_unit,
        user_role=user_role,
    )


@router.post("/features/overrides", response_model=FeatureFlagOverride, status_code=201)
async def set_feature_override(
    override: FeatureOverrideCreate,
    service: FeatureFlagService = Depends(get_flag_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Set a feature flag override for a tenant, business unit, or role."""
    return await service.set_override(override, actor=user.id)


@router.delete("/features/overrides/{flag_key}/{target_type}/{target_id}")
async def remove_feature_override(
    flag_key: str,
    target_type: str,
    target_id: str,
    service: FeatureFlagService = Depends(get_flag_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Remove a feature flag override."""
    deleted = await service.remove_override(flag_key, target_type, target_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Override not found")
    return {"status": "deleted"}


# ── Policy Packs ────────────────────────────────────────────────────


@router.post("/policy-packs", response_model=PolicyPackResponse, status_code=201)
async def create_policy_pack(
    pack: PolicyPackCreate,
    service: PolicyPackService = Depends(get_pack_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a tenant policy pack with rule, threshold, and clause overrides."""
    return await service.create_pack(pack, actor=user.id)


@router.get("/policy-packs", response_model=list[PolicyPackResponse])
async def list_policy_packs(
    service: PolicyPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all policy packs for the tenant."""
    return await service.list_packs()


@router.get("/policy-packs/{pack_id}", response_model=PolicyPackResponse)
async def get_policy_pack(
    pack_id: str,
    service: PolicyPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a specific policy pack."""
    pack = await service.get_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Policy pack not found")
    return pack


@router.delete("/policy-packs/{pack_id}")
async def delete_policy_pack(
    pack_id: str,
    service: PolicyPackService = Depends(get_pack_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Delete a policy pack."""
    deleted = await service.delete_pack(pack_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Policy pack not found")
    return {"status": "deleted"}


# ── Scoring Overrides ───────────────────────────────────────────────


@router.post("/scoring-overrides", response_model=ScoringOverrideResponse, status_code=201)
async def create_scoring_override(
    override: ScoringOverrideCreate,
    service: ScoringOverrideService = Depends(get_scoring_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Create a scoring override for a specific clause type."""
    return await service.create_override(override, actor=user.id)


@router.get("/scoring-overrides", response_model=list[ScoringOverrideResponse])
async def list_scoring_overrides(
    service: ScoringOverrideService = Depends(get_scoring_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """List all scoring overrides for the tenant."""
    return await service.list_overrides()


@router.delete("/scoring-overrides/{override_id}")
async def delete_scoring_override(
    override_id: str,
    service: ScoringOverrideService = Depends(get_scoring_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Delete a scoring override."""
    deleted = await service.delete_override(override_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scoring override not found")
    return {"status": "deleted"}


# ── Compliance Packs ────────────────────────────────────────────────


@router.post("/compliance-packs", response_model=CompliancePackResponse, status_code=201)
async def create_compliance_pack(
    pack: CompliancePackCreate,
    service: CompliancePackService = Depends(get_compliance_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a regional compliance pack for jurisdiction-specific requirements."""
    return await service.create_pack(pack, actor=user.id)


@router.get("/compliance-packs", response_model=list[CompliancePackResponse])
async def list_compliance_packs(
    region: Optional[ComplianceRegion] = Query(None),
    service: CompliancePackService = Depends(get_compliance_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List compliance packs, optionally filtered by region."""
    return await service.list_packs(region=region)


# ── Configuration Summary ───────────────────────────────────────────


@router.get("/summary", response_model=TenantConfigurationSummary)
async def get_tenant_configuration_summary(
    service: TenantConfigurationService = Depends(get_config_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get the full configuration summary for the current tenant."""
    return await service.get_full_configuration()
