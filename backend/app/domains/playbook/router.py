"""Legal Playbook + Policy Engine API router.

Endpoints:
- Playbook CRUD + versioning + publishing
- Clause standard management
- Policy rule management
- Approval threshold management
- Policy evaluation
- Policy override request/review workflow
- Governance audit trail
- AI policy context injection
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission, require_any_permission
from app.kernel.security.permissions import Permissions
from app.kernel.web.pagination import PaginatedResponse, PaginationMeta
from app.kernel.web.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.domains.playbook.schemas import (
    PlaybookCreate, PlaybookUpdate, PlaybookDetail, PlaybookSummary,
    PlaybookVersionCreate, PlaybookVersionSummary,
    ClauseStandardCreate, ClauseStandardUpdate, ClauseStandardItem,
    FallbackRecommendation, FallbackRecommendationResponse,
    PolicyRuleCreate, PolicyRuleUpdate, PolicyRuleItem, PolicyRuleWithPlaybook,
    TraceabilityResponse,
    ApprovalThresholdCreate, ApprovalThresholdUpdate, ApprovalThresholdItem,
    PolicyEvaluationSummary, PolicyEvaluationDetail,
    OverrideRequest, OverrideReview, OverrideItem,
    GovernanceAuditEventItem,
    PlaybookFilterParams, ClauseFilterParams, RuleFilterParams,
    EvaluationFilterParams, OverrideFilterParams, AuditFilterParams,
    PolicyContextInject, PolicyContextResult
)
from app.domains.playbook.service import PlaybookService, AIPolicyInjectionService
from app.domains.playbook.repository import PlaybookRepository
from app.kernel.events.bus import EventBus

router = APIRouter(prefix="/playbooks", tags=["Legal Playbook & Policy Engine"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_playbook_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
) -> PlaybookService:
    return PlaybookService(
        repo=PlaybookRepository(db, tenant_id=tenant_id),
        event_bus=EventBus(),
        user=user,
        tenant_id=tenant_id
)


async def get_policy_injection_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
) -> AIPolicyInjectionService:
    return AIPolicyInjectionService(
        repo=PlaybookRepository(db, tenant_id=tenant_id),
        tenant_id=tenant_id
)


# ── Playbook Management ─────────────────────────────────────────────


@router.post("/", response_model=PlaybookDetail, status_code=201)
async def create_playbook(
    data: PlaybookCreate,
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new legal playbook with initial draft version."""
    return await service.create_playbook(data
)


@router.get("/", response_model=PaginatedResponse[PlaybookSummary]
)
async def list_playbooks(
    status: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    practice_area: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List legal playbooks with filtering and pagination."""
    filters = PlaybookFilterParams(
        status=status, jurisdiction=jurisdiction, practice_area=practice_area,
        search=search, page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order
)
    items, total = await service.list_playbooks(filters
)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total,
                                   total_pages=max(1, (total + page_size - 1) // page_size))
)


# ── Fixed-path routes (must precede /{playbook_id} to avoid shadowing) ──


@router.get("/fallback", response_model=FallbackRecommendationResponse
)
async def get_fallback_recommendations(
    clause_category: Optional[str] = Query(None, description="Filter by clause category"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    limit: int = Query(5, ge=1, le=20),
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get fallback clause recommendations.

    Returns recommended fallback clauses based on category and jurisdiction.
    Used by the policy engine when clause standards are missing.
    """
    return await service.get_fallback_recommendations(
        clause_category=clause_category,
        jurisdiction=jurisdiction,
        limit=limit,
    )


@router.post("/evaluate", response_model=PolicyEvaluationDetail
)
async def evaluate_contract(
    playbook_id: str = Query(..., description="Playbook ID to evaluate against"),
    upload_id: str = Query(..., description="Upload/contract ID to evaluate"),
    simulation_mode: bool = Query(False, description="Dry-run mode (no persistence)"),
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Evaluate a contract upload against a playbook's policy rules.

    Runs the full PolicyEngine pipeline:
    1. Rule evaluation
    2. Deviation detection
    3. Approval threshold checks
    4. Clause recommendations
    5. Risk scoring

    Returns evaluation results with triggered rules, deviations, and recommendations.
    """
    return await service.evaluate_contract(
        playbook_id=playbook_id,
        upload_id=upload_id,
        simulation_mode=simulation_mode,
    )


@router.get("/rules", response_model=PaginatedResponse[PolicyRuleWithPlaybook])
async def list_tenant_rules(
    rule_type: Optional[str] = Query(None),
    effect: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_mandatory: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    sort_by: str = Query("priority"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all policy rules across playbooks for the tenant."""
    filters = RuleFilterParams(
        rule_type=rule_type, effect=effect, is_active=is_active,
        is_mandatory=is_mandatory, search=search,
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order,
    )
    items, total = await service.list_all_rules(filters)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.get("/traceability", response_model=TraceabilityResponse)
async def get_policy_traceability(
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Policy → Rule → Clause → Finding → Redline traceability aggregates."""
    return await service.get_traceability()


@router.get("/evaluations", response_model=PaginatedResponse[PolicyEvaluationSummary]
)
async def list_evaluations(
    status: Optional[str] = Query(None),
    upload_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List policy evaluations with filtering."""
    filters = EvaluationFilterParams(
        status=status, upload_id=upload_id, risk_level=risk_level,
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order
)
    items, total = await service.list_evaluations(filters
)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total,
                                   total_pages=max(1, (total + page_size - 1) // page_size))
)


@router.get("/evaluations/{evaluation_id}", response_model=PolicyEvaluationDetail
)
async def get_evaluation(
    evaluation_id: str,
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get policy evaluation details."""
    result = await service.get_evaluation(evaluation_id
)
    if not result:
        raise NotFoundError(f"Evaluation {evaluation_id} not found"
)
    return result


@router.get("/evaluations/upload/{upload_id}", response_model=PolicyEvaluationDetail
)
async def get_evaluation_by_upload(
    upload_id: str,
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get the latest policy evaluation for an upload."""
    result = await service.get_evaluation_by_upload(upload_id
)
    if not result:
        raise NotFoundError(f"No evaluation found for upload {upload_id}"
)
    return result


@router.post("/overrides", response_model=OverrideItem, status_code=201
)
async def request_override(
    data: OverrideRequest,
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Request a policy override for a specific evaluation result.

    Overrides allow controlled exceptions to policy rules when
    business justification exists.
    """
    return await service.request_override(data
)


@router.get("/overrides", response_model=PaginatedResponse[OverrideItem]
)
async def list_overrides(
    status: Optional[str] = Query(None),
    override_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List policy override requests with filtering."""
    filters = OverrideFilterParams(
        status=status, override_type=override_type,
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order
)
    items, total = await service.list_overrides(filters
)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total,
                                   total_pages=max(1, (total + page_size - 1) // page_size))
)


@router.get("/audit", response_model=PaginatedResponse[GovernanceAuditEventItem]
)
async def list_audit_events(
    event_type: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: PlaybookService = Depends(get_playbook_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """List governance audit events with filtering."""
    filters = AuditFilterParams(
        event_type=event_type, entity_type=entity_type,
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order
)
    items, total = await service.list_audit_events(filters
)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total,
                                   total_pages=max(1, (total + page_size - 1) // page_size))
)


@router.post("/ai-context", response_model=PolicyContextResult
)
async def build_ai_context(
    data: PolicyContextInject,
    service: AIPolicyInjectionService = Depends(get_policy_injection_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Build structured policy context for AI prompt injection.

    Aggregates relevant policy rules, clause standards, and approval
    thresholds for a given contract context into a single prompt-ready payload.
    """
    return await service.build_context(data
)


@router.get("/{playbook_id}", response_model=PlaybookDetail
)
async def get_playbook(
    playbook_id: uuid.UUID,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get playbook details by ID."""
    result = await service.get_playbook(str(playbook_id)
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} not found"
)
    return result


@router.patch("/{playbook_id}", response_model=PlaybookDetail
)
async def update_playbook(
    playbook_id: uuid.UUID,
    data: PlaybookUpdate,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update playbook metadata."""
    result = await service.update_playbook(str(playbook_id), data
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} not found"
)
    return result


@router.post("/{playbook_id}/publish", response_model=PlaybookVersionSummary
)
async def publish_playbook(
    playbook_id: str,
    data: PlaybookVersionCreate,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_APPROVE)),
):
    """Publish the current draft version of a playbook."""
    result = await service.publish_playbook(playbook_id, data
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} not found"
)
    return result


@router.post("/{playbook_id}/versions/draft", response_model=PlaybookVersionSummary
)
async def create_draft_version(
    playbook_id: str,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new draft version based on the current active version."""
    result = await service.create_draft_version(playbook_id
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} not found"
)
    return result


@router.get("/{playbook_id}/versions", response_model=PaginatedResponse[PlaybookVersionSummary]
)
async def list_playbook_versions(
    playbook_id: str,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all versions of a playbook."""
    items, total = await service.list_versions(playbook_id
)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=1, page_size=total, total=total,
                                   total_pages=1)
)


@router.post("/{playbook_id}/rollback/{version_id}", response_model=PlaybookVersionSummary
)
async def rollback_playbook(
    playbook_id: str,
    version_id: str,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_APPROVE)),
):
    """Rollback playbook to a specific version."""
    result = await service.rollback_playbook(playbook_id, version_id
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} or version {version_id} not found"
)
    return result


@router.post("/{playbook_id}/archive", response_model=PlaybookDetail
)
async def archive_playbook(
    playbook_id: str,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Archive a playbook."""
    result = await service.archive_playbook(playbook_id
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} not found"
)
    return result


# ── Clause Standards ────────────────────────────────────────────────


@router.post("/{playbook_id}/clauses", response_model=ClauseStandardItem, status_code=201
)
async def create_clause(
    playbook_id: str,
    data: ClauseStandardCreate,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new clause standard in a playbook."""
    result = await service.create_clause(playbook_id, data
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} not found"
)
    return result


@router.get("/{playbook_id}/clauses", response_model=PaginatedResponse[ClauseStandardItem]
)
async def list_clauses(
    playbook_id: str,
    category: Optional[str] = Query(None),
    clause_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List clause standards in a playbook with filtering."""
    filters = ClauseFilterParams(
        category=category, clause_type=clause_type, risk_level=risk_level,
        is_active=is_active, search=search, page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order
)
    items, total = await service.list_clauses(playbook_id, filters
)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total,
                                   total_pages=max(1, (total + page_size - 1) // page_size))
)


@router.get("/clauses/{clause_id}", response_model=ClauseStandardItem
)
async def get_clause(
    clause_id: str,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a clause standard by ID."""
    result = await service.get_clause(clause_id
)
    if not result:
        raise NotFoundError(f"Clause {clause_id} not found"
)
    return result


@router.patch("/clauses/{clause_id}", response_model=ClauseStandardItem
)
async def update_clause(
    clause_id: str,
    data: ClauseStandardUpdate,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a clause standard."""
    result = await service.update_clause(clause_id, data
)
    if not result:
        raise NotFoundError(f"Clause {clause_id} not found"
)
    return result


@router.post("/clauses/{clause_id}/deactivate", response_model=ClauseStandardItem
)
async def deactivate_clause(
    clause_id: str,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Deactivate a clause standard."""
    result = await service.deactivate_clause(clause_id
)
    if not result:
        raise NotFoundError(f"Clause {clause_id} not found"
)
    return result


# ── Policy Rules ────────────────────────────────────────────────────


@router.post("/{playbook_id}/rules", response_model=PolicyRuleItem, status_code=201
)
async def create_rule(
    playbook_id: str,
    data: PolicyRuleCreate,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new policy rule in a playbook."""
    result = await service.create_rule(playbook_id, data
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} not found"
)
    return result


@router.get("/{playbook_id}/rules", response_model=PaginatedResponse[PolicyRuleItem]
)
async def list_rules(
    playbook_id: str,
    rule_type: Optional[str] = Query(None),
    effect: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_mandatory: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("priority"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List policy rules in a playbook with filtering."""
    filters = RuleFilterParams(
        rule_type=rule_type, effect=effect, is_active=is_active,
        is_mandatory=is_mandatory, search=search, page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order
)
    items, total = await service.list_rules(playbook_id, filters
)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total,
                                   total_pages=max(1, (total + page_size - 1) // page_size))
)


@router.get("/rules/{rule_id}", response_model=PolicyRuleItem
)
async def get_rule(
    rule_id: str,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a policy rule by ID."""
    result = await service.get_rule(rule_id
)
    if not result:
        raise NotFoundError(f"Rule {rule_id} not found"
)
    return result


@router.patch("/rules/{rule_id}", response_model=PolicyRuleItem
)
async def update_rule(
    rule_id: str,
    data: PolicyRuleUpdate,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a policy rule."""
    result = await service.update_rule(rule_id, data
)
    if not result:
        raise NotFoundError(f"Rule {rule_id} not found"
)
    return result


@router.post("/rules/{rule_id}/toggle", response_model=PolicyRuleItem
)
async def toggle_rule(
    rule_id: str,
    enabled: bool = Query(..., description="True to activate, False to deactivate"),
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Activate or deactivate a policy rule.

    Records a ``rule.activated`` / ``rule.deactivated`` audit event for
    full traceability of rule state changes.
    """
    result = await service.toggle_rule(rule_id, enabled
)
    if not result:
        raise NotFoundError(f"Rule {rule_id} not found"
)
    return result


# ── Approval Thresholds ─────────────────────────────────────────────


@router.post("/{playbook_id}/thresholds", response_model=ApprovalThresholdItem, status_code=201
)
async def create_threshold(
    playbook_id: str,
    data: ApprovalThresholdCreate,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create an approval threshold in a playbook."""
    result = await service.create_threshold(playbook_id, data
)
    if not result:
        raise NotFoundError(f"Playbook {playbook_id} not found"
)
    return result


@router.get("/{playbook_id}/thresholds", response_model=PaginatedResponse[ApprovalThresholdItem]
)
async def list_thresholds(
    playbook_id: str,
    threshold_type: Optional[str] = Query(None),
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List approval thresholds for a playbook."""
    items, total = await service.list_thresholds(playbook_id, threshold_type
)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=1, page_size=total, total=total, total_pages=1)
)


@router.patch("/thresholds/{threshold_id}", response_model=ApprovalThresholdItem
)
async def update_threshold(
    threshold_id: str,
    data: ApprovalThresholdUpdate,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update an approval threshold."""
    result = await service.update_threshold(threshold_id, data
)
    if not result:
        raise NotFoundError(f"Threshold {threshold_id} not found"
)
    return result


# ── Override Detail Routes (must follow /overrides list) ────────────


@router.post("/overrides/{override_id}/review", response_model=OverrideItem
)
async def review_override(
    override_id: str,
    data: OverrideReview,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_APPROVE)),
):
    """Approve or reject a policy override request."""
    try:
        result = await service.review_override(override_id, data
)
        if not result:
            raise NotFoundError(f"Override {override_id} not found"
)
        return result
    except ValueError as exc:
        raise ValidationError(str(exc)
)


@router.get("/overrides/{override_id}", response_model=OverrideItem
)
async def get_override(
    override_id: str,
    service: PlaybookService = Depends(get_playbook_service)
,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get override details by ID."""
    result = await service.get_override(override_id
)
    if not result:
        raise NotFoundError(f"Override {override_id} not found"
)
    return result


# ═══════════════════════════════════════════════════════════════════
# End of router — all routes defined above
# ═══════════════════════════════════════════════════════════════════
