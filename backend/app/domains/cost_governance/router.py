"""Cost & Resource Governance API router — budgets, quotas, model routing, throttling."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.cost_governance.schemas import (
    BudgetPeriod, BudgetAlertLevel, ModelTier, RoutingStrategy, ResourceType,
    TokenBudgetConfig, TokenBudgetUsage, BudgetAlert,
    BudgetConfigCreate, BudgetConfigUpdate,
    TenantQuota, QuotaUsage, QuotaCheckResult,
    InferenceSummary,
    ModelRoute, RoutingDecision, RoutingRule,
    CacheROIMetrics,
    ThrottleRule, ThrottleDecision,
    CostGovernanceDashboard,
)
from app.domains.cost_governance.service import (
    TokenBudgetService,
    QuotaEnforcementService,
    ModelRouter,
    InferenceAccountingService,
    CostGovernanceService,
)

router = APIRouter(prefix="/cost-governance", tags=["Cost & Resource Governance"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_budget_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> TokenBudgetService:
    return TokenBudgetService(session=db, tenant_id=tenant_id)


async def get_quota_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> QuotaEnforcementService:
    return QuotaEnforcementService(session=db, tenant_id=tenant_id)


async def get_accounting_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> InferenceAccountingService:
    return InferenceAccountingService(session=db, tenant_id=tenant_id)


async def get_cost_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> CostGovernanceService:
    return CostGovernanceService(session=db, tenant_id=tenant_id)


# ── Token Budgets ───────────────────────────────────────────────────


@router.get("/budgets", response_model=TokenBudgetUsage)
async def get_budget_usage(
    service: TokenBudgetService = Depends(get_budget_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get current token/cost budget usage for the tenant."""
    return await service.get_current_usage()


@router.put("/budgets", response_model=TokenBudgetConfig)
async def update_budget_config(
    config: BudgetConfigUpdate,
    service: TokenBudgetService = Depends(get_budget_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Update token budget configuration."""
    return await service.update_config(config)


@router.post("/budgets/check", response_model=BudgetAlertLevel)
async def check_budget(
    estimated_tokens: int = Query(0, ge=0),
    estimated_cost: float = Query(0.0, ge=0.0),
    service: TokenBudgetService = Depends(get_budget_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Check if an operation would exceed the budget. Call BEFORE inference."""
    return await service.check_budget(
        estimated_tokens=estimated_tokens,
        estimated_cost=estimated_cost,
    )


# ── Tenant Quotas ───────────────────────────────────────────────────


@router.get("/quotas", response_model=TenantQuota)
async def get_tenant_quotas(
    service: QuotaEnforcementService = Depends(get_quota_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get the current quota configuration for the tenant."""
    return await service.get_quotas()


@router.get("/quotas/usage", response_model=QuotaUsage)
async def get_quota_usage(
    service: QuotaEnforcementService = Depends(get_quota_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get current usage against all tenant quotas."""
    return await service.get_usage()


@router.post("/quotas/check", response_model=QuotaCheckResult)
async def check_quota(
    resource: ResourceType,
    estimated_cost: float = Query(0.0, ge=0.0),
    service: QuotaEnforcementService = Depends(get_quota_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Check if a specific operation is allowed under current quotas."""
    return await service.check_operation(resource=resource, estimated_cost=estimated_cost)


# ── Model Routing ───────────────────────────────────────────────────


@router.get("/models", response_model=list[ModelRoute])
async def list_available_models(
    tier: Optional[ModelTier] = Query(None),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """List available models, optionally filtered by tier."""
    router = ModelRouter()
    return router.get_models(tier=tier)


@router.post("/models/route", response_model=RoutingDecision)
async def route_inference_request(
    prompt_key: str = Query(...),
    tenant_tier: ModelTier = Query(ModelTier.STANDARD),
    strategy: RoutingStrategy = Query(RoutingStrategy.BALANCED),
    max_cost: Optional[float] = Query(None),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Route an inference request to the optimal model based on cost, quality, and constraints."""
    router = ModelRouter()
    return router.route(
        prompt_key=prompt_key,
        tenant_tier=tenant_tier,
        strategy=strategy,
        max_cost=max_cost,
    )


# ── Inference Accounting ────────────────────────────────────────────


@router.get("/inferences/summary", response_model=InferenceSummary)
async def get_inference_summary(
    period_days: int = Query(30, ge=1, le=365),
    service: InferenceAccountingService = Depends(get_accounting_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get inference usage summary for a period, broken down by model and prompt."""
    return await service.get_summary(period_days=period_days)


# ── Dashboard ───────────────────────────────────────────────────────


@router.get("/dashboard", response_model=CostGovernanceDashboard)
async def get_cost_governance_dashboard(
    service: CostGovernanceService = Depends(get_cost_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get the complete cost governance dashboard with budgets, quotas, and cost drivers."""
    return await service.get_dashboard()
