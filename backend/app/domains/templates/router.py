"""Template Library API router — enterprise CLM endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

from .repository import TemplateRepository
from .service import TemplateService
from .schemas import (
    TemplateCreate, TemplateUpdate, TemplateVersionCreate,
    TemplateCategoryCreate, TemplateCategoryUpdate,
    TemplateClauseCreate, TemplateClauseUpdate,
    GenerateContractRequest,
    TemplateDetail, TemplateListItem, TemplateCategoryResponse,
    TemplateVersionResponse, TemplateClauseResponse,
    TemplateMetrics, TemplateValidationResult, TemplateDependencyInfo,
    GenerateContractResponse, PaginatedTemplateList,
    PaginatedCategoryList, PaginatedClauseList,
    ClauseAnalytics, ClauseDependencyInfo,
    TemplatePackageCreate, TemplatePackageUpdate, TemplatePackageResponse,
    PackageItemCreate, PaginatedPackageList,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Template Library"])


# ── Dependencies ──────────────────────────────────────────────────

async def get_repo(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> TemplateRepository:
    return TemplateRepository(session, tenant_id)


async def get_service(
    repo: TemplateRepository = Depends(get_repo),
    user: UserContext = Depends(get_current_user),
) -> TemplateService:
    return TemplateService(repo, actor_id=user.id)


# ── Categories ────────────────────────────────────────────────────

@router.get("/categories", response_model=PaginatedCategoryList)
async def list_categories(
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all template categories."""
    categories = await service.list_categories()
    return PaginatedCategoryList(data=categories, total=len(categories))


@router.post("/categories", response_model=TemplateCategoryResponse, status_code=201)
async def create_category(
    body: TemplateCategoryCreate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new template category."""
    return await service.create_category(body)


@router.put("/categories/{category_id}", response_model=TemplateCategoryResponse)
async def update_category(
    category_id: str,
    body: TemplateCategoryUpdate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a template category."""
    result = await service.update_category(category_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    return result


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Delete (deactivate) a template category."""
    result = await service.delete_category(category_id)
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")


# ── Static Collection Routes (must be before /{template_id}) ─────
# These are mounted on a sub-router to ensure they take priority over
# the /{template_id} parameterized routes below.

_static_router = APIRouter()


@_static_router.get("/search", response_model=PaginatedTemplateList)
async def search_templates(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search templates by name, description, or tags."""
    items, total = await service.list_templates(
        search=q, page=page, page_size=page_size,
    )
    return PaginatedTemplateList(data=items, total=total, page=page, page_size=page_size)


@_static_router.get("/favorites", response_model=PaginatedTemplateList)
async def list_favorite_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List favorite templates for the current user."""
    items, total = await service.list_templates(page=page, page_size=page_size)
    items = [i for i in items if i.is_favorite]
    return PaginatedTemplateList(data=items, total=len(items), page=page, page_size=page_size)


@_static_router.get("/metrics", response_model=TemplateMetrics)
async def get_template_metrics(
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get template library dashboard metrics."""
    return await service.get_metrics()


# ── Clauses ───────────────────────────────────────────────────────

@_static_router.get("/clauses", response_model=PaginatedClauseList)
async def list_clauses(
    clause_type: Optional[str] = Query(None, description="Filter by clause type"),
    template_id: Optional[str] = Query(None, description="Filter by template"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List reusable clauses."""
    clauses, total = await service.list_clauses(
        clause_type=clause_type, template_id=template_id,
        page=page, page_size=page_size,
    )
    return PaginatedClauseList(data=clauses, total=total)


@_static_router.post("/clauses", response_model=TemplateClauseResponse, status_code=201)
async def create_clause(
    body: TemplateClauseCreate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a reusable clause."""
    return await service.create_clause(body)


@_static_router.get("/clauses/analytics", response_model=ClauseAnalytics)
async def get_clause_analytics(
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get clause library analytics."""
    return await service.get_clause_analytics()


@_static_router.get("/clauses/search", response_model=PaginatedClauseList)
async def search_clauses_global(
    q: str = Query(..., min_length=1, description="Search query"),
    clause_type: Optional[str] = Query(None, description="Filter by clause type"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search clauses by name, content, tags, risk, and category."""
    clauses, total = await service.search_clauses_global(
        query=q, clause_type=clause_type,
        risk_level=risk_level, page=page, page_size=page_size,
    )
    return PaginatedClauseList(data=clauses, total=total)


@_static_router.get("/clauses/{clause_id}", response_model=TemplateClauseResponse)
async def get_clause(
    clause_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a clause by ID."""
    result = await service.get_clause(clause_id)
    if not result:
        raise HTTPException(status_code=404, detail="Clause not found")
    return result


@_static_router.put("/clauses/{clause_id}", response_model=TemplateClauseResponse)
async def update_clause(
    clause_id: str,
    body: TemplateClauseUpdate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a clause."""
    result = await service.update_clause(clause_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Clause not found")
    return result


@_static_router.delete("/clauses/{clause_id}", status_code=204)
async def delete_clause(
    clause_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Delete a clause."""
    result = await service.delete_clause(clause_id)
    if not result:
        raise HTTPException(status_code=404, detail="Clause not found")


@_static_router.post("/clauses/{clause_id}/submit", response_model=TemplateClauseResponse)
async def submit_clause_for_review(
    clause_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Submit a clause for legal review (draft → legal_review)."""
    try:
        result = await service.submit_clause_for_review(clause_id)
        if not result:
            raise HTTPException(status_code=404, detail="Clause not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@_static_router.post("/clauses/{clause_id}/approve", response_model=TemplateClauseResponse)
async def approve_clause(
    clause_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Approve a clause (legal_review → approved)."""
    try:
        result = await service.approve_clause(clause_id)
        if not result:
            raise HTTPException(status_code=404, detail="Clause not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@_static_router.post("/clauses/{clause_id}/publish", response_model=TemplateClauseResponse)
async def publish_clause(
    clause_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Publish a clause (approved → published)."""
    try:
        result = await service.publish_clause(clause_id)
        if not result:
            raise HTTPException(status_code=404, detail="Clause not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@_static_router.post("/clauses/{clause_id}/reject", response_model=TemplateClauseResponse)
async def reject_clause(
    clause_id: str,
    reason: str = Query("", description="Reason for rejection"),
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Reject a clause — return to draft with feedback."""
    try:
        result = await service.reject_clause(clause_id, reason)
        if not result:
            raise HTTPException(status_code=404, detail="Clause not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@_static_router.get("/clauses/{clause_id}/dependencies", response_model=ClauseDependencyInfo)
async def check_clause_dependencies(
    clause_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Check how many templates and contracts reference a clause."""
    result = await service.check_clause_dependencies(clause_id)
    if not result:
        raise HTTPException(status_code=404, detail="Clause not found")
    return result


# ── Drafts ────────────────────────────────────────────────────────

@_static_router.post("/drafts", response_model=GenerateContractResponse, status_code=201)
async def save_draft(
    body: GenerateContractRequest,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Save a draft contract for later resume."""
    result = await service.save_draft(body, step=1)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@_static_router.get("/drafts")
async def list_drafts(
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all draft contracts for the current user."""
    return await service.list_drafts()


@_static_router.get("/drafts/{draft_id}")
async def get_draft(
    draft_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a draft by ID for resume."""
    result = await service.get_draft(draft_id)
    if not result:
        raise HTTPException(status_code=404, detail="Draft not found")
    return result


# ── Versions (static paths) ───────────────────────────────────────

@_static_router.get("/versions/{version_id}", response_model=TemplateVersionResponse)
async def get_version(
    version_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a specific version."""
    result = await service.get_version(version_id)
    if not result:
        raise HTTPException(status_code=404, detail="Version not found")
    return result


@_static_router.get("/versions/{version_id}/clause-refs")
async def get_template_clause_refs(
    version_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get clause references for a template version with clause details."""
    return await service.get_template_clause_refs(version_id)


@_static_router.put("/versions/{version_id}/clause-refs")
async def set_template_clause_refs(
    version_id: str,
    refs: list[dict],
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Set clause references for a template version, pinning clause versions."""
    try:
        return await service.set_template_clause_refs(version_id, refs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Packages ──────────────────────────────────────────────────────

@_static_router.get("/packages", response_model=PaginatedPackageList)
async def list_packages(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List template packages — industry starter packs."""
    items, total = await service.list_packages(
        industry=industry, page=page, page_size=page_size,
    )
    return PaginatedPackageList(data=items, total=total)


@_static_router.post("/packages", response_model=TemplatePackageResponse, status_code=201)
async def create_package(
    body: TemplatePackageCreate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a template package with optional items."""
    return await service.create_package(body)


@_static_router.get("/packages/{package_id}", response_model=TemplatePackageResponse)
async def get_package(
    package_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a template package with its items."""
    result = await service.get_package(package_id)
    if not result:
        raise HTTPException(status_code=404, detail="Package not found")
    return result


@_static_router.put("/packages/{package_id}", response_model=TemplatePackageResponse)
async def update_package(
    package_id: str,
    body: TemplatePackageUpdate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a template package."""
    result = await service.update_package(package_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Package not found")
    return result


@_static_router.delete("/packages/{package_id}", status_code=204)
async def delete_package(
    package_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Delete a template package."""
    result = await service.delete_package(package_id)
    if not result:
        raise HTTPException(status_code=404, detail="Package not found")


@_static_router.post("/packages/{package_id}/publish", response_model=TemplatePackageResponse)
async def publish_package(
    package_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Publish a template package."""
    result = await service.publish_package(package_id)
    if not result:
        raise HTTPException(status_code=404, detail="Package not found")
    return result


@_static_router.put("/packages/{package_id}/items")
async def set_package_items(
    package_id: str,
    items: list[PackageItemCreate],
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Set the items (templates) in a package."""
    result = await service.set_package_items(package_id, items)
    if not result:
        raise HTTPException(status_code=404, detail="Package not found")
    return result


# Include the static router into the main router with no prefix
router.include_router(_static_router)


# ── Templates ─────────────────────────────────────────────────────

@router.get("", response_model=PaginatedTemplateList)
async def list_templates(
    status: Optional[str] = Query(None, description="Filter by status"),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name/description/tags"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List templates with filtering and search."""
    items, total = await service.list_templates(
        status=status, category_id=category_id,
        search=search, page=page, page_size=page_size,
    )
    return PaginatedTemplateList(data=items, total=total, page=page, page_size=page_size)


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get template detail with versions."""
    result = await service.get_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.post("", response_model=TemplateDetail, status_code=201)
async def create_template(
    body: TemplateCreate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new template."""
    return await service.create_template(body)


@router.put("/{template_id}", response_model=TemplateDetail)
async def update_template(
    template_id: str,
    body: TemplateUpdate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a template."""
    result = await service.update_template(template_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Delete a template."""
    result = await service.delete_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")


# ── Template Actions ──────────────────────────────────────────────

@router.post("/{template_id}/publish", response_model=TemplateDetail)
async def publish_template(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Publish a template (set status to approved)."""
    result = await service.publish_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.post("/{template_id}/archive", response_model=TemplateDetail)
async def archive_template(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Archive a template."""
    result = await service.archive_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.post("/{template_id}/duplicate", response_model=TemplateDetail, status_code=201)
async def duplicate_template(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Duplicate a template with its current version."""
    original = await service.get_template(template_id)
    if not original:
        raise HTTPException(status_code=404, detail="Template not found")
    dup_body = TemplateCreate(
        name=f"{original.name} (Copy)",
        description=original.description,
        category_id=original.category.id if original.category else None,
        tags=original.tags,
        owner=original.owner,
        department=original.department,
        business_unit=original.business_unit,
    )
    return await service.create_template(dup_body)


@router.post("/{template_id}/favorite")
async def toggle_favorite(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Toggle favorite status for a template."""
    return await service.toggle_favorite(template_id)


# ── Versions ──────────────────────────────────────────────────────

@router.get("/{template_id}/versions", response_model=list[TemplateVersionResponse])
async def list_versions(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List all versions of a template."""
    detail = await service.get_template(template_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Template not found")
    return detail.versions


@router.post("/{template_id}/versions", response_model=TemplateDetail, status_code=201)
async def create_version(
    template_id: str,
    body: TemplateVersionCreate,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new version for a template."""
    result = await service.create_version(template_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


# ── Variable Extraction ───────────────────────────────────────────

@router.get("/{template_id}/variables")
async def extract_template_variables(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Extract all {{variables}} from the current version of a template."""
    variables = await service.extract_variables_from_template(template_id)
    if variables is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"variables": variables}


# ── Contract Generation ───────────────────────────────────────────

@router.post("/{template_id}/generate", response_model=GenerateContractResponse)
async def generate_contract(
    template_id: str,
    body: GenerateContractRequest,
    request: Request,
    service: TemplateService = Depends(get_service),
    repo: TemplateRepository = Depends(get_repo),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Generate a contract from a template.
    
    Supports version pinning (template_version_id), idempotency (idempotency_key),
    and draft status (status='draft').
    """
    body.template_id = template_id
    try:
        result = await service.generate_contract(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")

    pending = service.pop_pending_ingestion()
    if pending:
        upload_id, tenant_id, user_id = pending
        # Commit before Celery so workers see upload/review rows (same as upload API).
        await repo.session.commit()

        from app.domains.ingestion.post_upload_dispatch import (
            dispatch_ingestion_pipeline,
            new_correlation_id,
        )

        correlation_id = new_correlation_id()
        inline_runner = None
        if settings.environment == "development":
            from app.domains.ingestion.router import _schedule_inline_ingestion

            db_factory = request.app.state.db_factory

            def inline_runner() -> None:
                _schedule_inline_ingestion(
                    upload_id=upload_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    db_factory=db_factory,
                    correlation_id=correlation_id,
                )

        queued = dispatch_ingestion_pipeline(
            upload_id,
            tenant_id,
            user_id or user.id,
            schedule_inline=inline_runner,
        )
        if not queued:
            logger.warning(
                "Template contract saved but ingestion not started for upload %s",
                upload_id,
            )

    return result


# ── Generate Preview ──────────────────────────────────────────────

@router.post("/{template_id}/preview", response_model=GenerateContractResponse)
async def preview_contract(
    template_id: str,
    body: GenerateContractRequest,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Preview a contract from a template without creating any records."""
    body.template_id = template_id
    body.preview_only = True
    result = await service.generate_contract(body)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


# ── Available Clauses for Generation ──────────────────────────────

@router.get("/{template_id}/available-clauses")
async def get_available_clauses(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get all clauses available for a template when generating a contract."""
    return await service.get_available_clauses(template_id)


# ── Template Validation ───────────────────────────────────────────

@router.get("/{template_id}/validate", response_model=TemplateValidationResult)
async def validate_template(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Validate a template before publishing."""
    try:
        return await service.validate_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Dependency Check ──────────────────────────────────────────────

@router.get("/{template_id}/dependencies", response_model=TemplateDependencyInfo)
async def check_template_dependencies(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Check if a template can be archived or deleted."""
    try:
        return await service.check_dependencies(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Usage History ─────────────────────────────────────────────────

@router.get("/{template_id}/history")
async def get_template_history(
    template_id: str,
    service: TemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get usage history for a template."""
    return await service.get_usage_history(template_id)
