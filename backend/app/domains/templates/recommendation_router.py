"""Clause Recommendation Engine — REST API endpoints.

Provides:
- CRUD for recommendation rules (admin/settings)
- Evaluate endpoint (used by the wizard)
- Audit trail query
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_tenant_id, get_db
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.kernel.web.exceptions import NotFoundError, ConflictError
from app.domains.templates.recommendation_models import ClauseRecommendationRule
from app.domains.templates.recommendation_schemas import (
    RecommendationRuleCreate,
    RecommendationRuleUpdate,
    RecommendationRuleResponse,
    PaginatedRuleResponse,
    RecommendationContext,
    RecommendationResult,
    AcceptRejectClauses,
)
from app.domains.templates.recommendation_repository import RecommendationRuleRepository
from app.domains.templates.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates/recommendation-rules", tags=["clause-recommendations"])


# ── Dependency ───────────────────────────────────────────────────

async def get_repo(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> RecommendationRuleRepository:
    return RecommendationRuleRepository(db, tenant_id)


async def get_engine(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> RecommendationEngine:
    return RecommendationEngine(db, tenant_id)


# ── CRUD Endpoints ───────────────────────────────────────────────

@router.post("", response_model=RecommendationRuleResponse, status_code=201)
async def create_rule(
    body: RecommendationRuleCreate,
    repo: RecommendationRuleRepository = Depends(get_repo),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Create a new clause recommendation rule."""
    rule = ClauseRecommendationRule(
        tenant_id=repo.tenant_id,
        name=body.name,
        description=body.description,
        priority=body.priority,
        is_active=body.is_active,
        clause_id=body.clause_id,
        clause_version=body.clause_version,
        recommendation_type=body.recommendation_type,
        variable_key=body.variable_key,
        operator=body.operator,
        condition_value=body.condition_value,
        template_id=body.template_id,
        business_unit=body.business_unit,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        created_by=user.id,
    )
    rule = await repo.create(rule)
    return RecommendationRuleResponse.model_validate(rule)


@router.get("", response_model=PaginatedRuleResponse)
async def list_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    variable_key: Optional[str] = None,
    clause_id: Optional[str] = None,
    template_id: Optional[str] = None,
    search: Optional[str] = None,
    repo: RecommendationRuleRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """List recommendation rules with filtering and pagination."""
    rules, total = await repo.list(
        page=page, page_size=page_size,
        is_active=is_active,
        variable_key=variable_key,
        clause_id=clause_id,
        template_id=template_id,
        search=search,
    )
    return PaginatedRuleResponse(
        data=[RecommendationRuleResponse.model_validate(r) for r in rules],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{rule_id}", response_model=RecommendationRuleResponse)
async def get_rule(
    rule_id: str,
    repo: RecommendationRuleRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Get a single recommendation rule."""
    rule = await repo.get(rule_id)
    if not rule:
        raise NotFoundError(f"Recommendation rule {rule_id} not found")
    return RecommendationRuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=RecommendationRuleResponse)
async def update_rule(
    rule_id: str,
    body: RecommendationRuleUpdate,
    repo: RecommendationRuleRepository = Depends(get_repo),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Update a recommendation rule."""
    updates = body.model_dump(exclude_unset=True)
    updates["updated_by"] = user.id
    rule = await repo.update(rule_id, updates)
    if not rule:
        raise NotFoundError(f"Recommendation rule {rule_id} not found")
    return RecommendationRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: str,
    repo: RecommendationRuleRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.ADMIN_SYSTEM)),
):
    """Delete a recommendation rule."""
    deleted = await repo.delete(rule_id)
    if not deleted:
        raise NotFoundError(f"Recommendation rule {rule_id} not found")


# ── Evaluation Endpoint ──────────────────────────────────────────

@router.post("/evaluate", response_model=RecommendationResult)
async def evaluate_rules(
    context: RecommendationContext,
    engine: RecommendationEngine = Depends(get_engine),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Evaluate recommendation rules against variable values.

    This is the core endpoint used by the Generate Wizard to suggest clauses.
    It's decoupled from templates — pass any variable values and get clause suggestions.
    """
    # Ensure tenant_id is set from auth context
    context.tenant_id = engine.tenant_id
    result = await engine.evaluate(context)
    return result


@router.post("/accept", status_code=200)
async def accept_recommendations(
    body: AcceptRejectClauses,
    engine: RecommendationEngine = Depends(get_engine),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Record user's accept/reject decisions on suggested clauses.

    This creates an audit trail of what was suggested and what the user chose.
    """
    # Build a minimal context for audit (variable values are best-effort)
    context = RecommendationContext(
        variable_values={},
        tenant_id=engine.tenant_id,
    )
    # Reconstruct a result from the submitted data
    from app.domains.templates.recommendation_schemas import SuggestedClause
    result = RecommendationResult(
        suggested_clauses=body.suggested_clauses,
        rules_evaluated=len(body.suggested_clauses),
        rules_matched=len(body.suggested_clauses),
    )
    await engine.record_audit(
        context=context,
        result=result,
        accepted_ids=body.accepted_clause_ids,
        rejected_ids=body.rejected_clause_ids,
        review_id=body.review_id,
        generated_contract_id=body.generated_contract_id,
        created_by=user.id,
    )
    return {"status": "ok", "accepted": len(body.accepted_clause_ids), "rejected": len(body.rejected_clause_ids)}
