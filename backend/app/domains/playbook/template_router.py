"""Redline Template Coverage & Management API router.

Endpoints:
- GET  /playbook/templates/coverage — template coverage analysis
- POST /playbook/templates/generate — AI-powered template draft generation
- GET  /playbook/templates — list templates with pagination + filtering
- GET  /playbook/templates/{id} — get single template
- POST /playbook/templates — create template
- PUT  /playbook/templates/{id} — update template
- DELETE /playbook/templates/{id} — soft delete (set status=retired)
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.kernel.web.pagination import PaginatedResponse, PaginationMeta
from app.kernel.web.exceptions import NotFoundError, ValidationError
from app.domains.playbook.schemas import (
    RedlineTemplateCreate,
    RedlineTemplateUpdate,
    RedlineTemplateItem,
    TemplateCoverageResponse,
    TemplateGenerateRequest,
    TemplateGenerateResponse,
    TemplateFilterParams,
)
from app.domains.playbook.service import TemplateService
from app.domains.playbook.repository import PlaybookRepository

router = APIRouter(prefix="/playbook/templates", tags=["Redline Templates"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_template_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> TemplateService:
    return TemplateService(
        repo=PlaybookRepository(db, tenant_id=tenant_id),
        tenant_id=tenant_id,
    )


# ── Coverage Analysis ───────────────────────────────────────────────


@router.get("/coverage", response_model=TemplateCoverageResponse)
async def get_template_coverage(
    service: TemplateService = Depends(get_template_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Analyze template coverage across all finding clause_types.

    Queries all review findings grouped by clause_type and compares
    against existing templates to produce coverage statistics.
    """
    return await service.get_coverage()


# ── AI Template Generation ──────────────────────────────────────────


@router.post("/generate", response_model=TemplateGenerateResponse, status_code=200)
async def generate_template(
    data: TemplateGenerateRequest,
    service: TemplateService = Depends(get_template_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Generate a draft clause template using AI.

    Uses DeepSeek (preferred for cost) or falls back to OpenAI.
    The generated text is NOT saved — user must call POST to save.
    """
    try:
        return await service.generate_template(data)
    except RuntimeError as exc:
        raise ValidationError(str(exc))


# ── CRUD ────────────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse[RedlineTemplateItem])
async def list_templates(
    clause_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: TemplateService = Depends(get_template_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List redline templates with filtering and pagination."""
    filters = TemplateFilterParams(
        clause_type=clause_type, category=category,
        jurisdiction=jurisdiction, industry=industry,
        risk_level=risk_level, status=status, search=search,
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order,
    )
    items, total = await service.list_templates(filters)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.get("/{template_id}", response_model=RedlineTemplateItem)
async def get_template(
    template_id: uuid.UUID = Path(..., description="Template ID"),
    service: TemplateService = Depends(get_template_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a redline template by ID."""
    result = await service.get_template(str(template_id))
    if not result:
        raise NotFoundError(f"Template {template_id} not found")
    return result


@router.post("", response_model=RedlineTemplateItem, status_code=201)
async def create_template(
    data: RedlineTemplateCreate,
    service: TemplateService = Depends(get_template_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new redline template."""
    return await service.create_template(data, created_by=user.id)


@router.put("/{template_id}", response_model=RedlineTemplateItem)
async def update_template(
    template_id: uuid.UUID = Path(..., description="Template ID"),
    data: RedlineTemplateUpdate = ...,
    service: TemplateService = Depends(get_template_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a redline template."""
    result = await service.update_template(str(template_id), data)
    if not result:
        raise NotFoundError(f"Template {template_id} not found")
    return result


@router.delete("/{template_id}", response_model=RedlineTemplateItem)
async def delete_template(
    template_id: uuid.UUID = Path(..., description="Template ID"),
    service: TemplateService = Depends(get_template_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Soft-delete a redline template (sets status=retired)."""
    result = await service.delete_template(str(template_id))
    if not result:
        raise NotFoundError(f"Template {template_id} not found")
    return result
