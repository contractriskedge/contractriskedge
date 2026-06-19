"""Redline Template Management API — CRUD, Coverage, AI Draft Generation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_tenant_id, get_db
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.redline_templates.repository import RedlineTemplateRepository
from app.domains.redline_templates.service import RedlineTemplateService
from app.domains.redline_templates.schemas import (
    RedlineTemplateCreate,
    RedlineTemplateUpdate,
    RedlineTemplateResponse,
    AIDraftRequest,
    AIDraftResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/redline-templates", tags=["Redline Templates"])


async def get_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> RedlineTemplateService:
    return RedlineTemplateService(RedlineTemplateRepository(db, tenant_id=tenant_id))


# ── Coverage Dashboard ─────────────────────────────────────────────


@router.get(
    "/coverage",
    summary="Get template coverage analytics",
    description="Returns coverage stats per clause type — which findings have templates and which don't.",
    responses={200: {"description": "Coverage analytics"}},
)
async def get_coverage(
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get template coverage across all clause types."""
    return await service.get_coverage()


@router.get(
    "/missing",
    summary="Get missing templates ranked by frequency",
    description="Returns clause types with findings but no templates, ordered by frequency.",
)
async def get_missing_templates(
    limit: int = Query(20, ge=1, le=100),
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return await service.get_missing_templates(limit)


# ── AI Draft Generation ────────────────────────────────────────────


@router.post(
    "/generate-draft",
    summary="Generate AI draft for a missing template",
    description="Uses GPT-4o to generate a high-quality clause draft for a missing template.",
    responses={200: {"model": AIDraftResponse}},
)
async def generate_draft(
    request: AIDraftRequest,
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Generate an AI-powered redline draft for a clause type."""
    try:
        result = await service.generate_ai_draft(
            clause_type=request.clause_type,
            finding_title=request.finding_title,
            finding_description=request.finding_description,
            jurisdiction=request.jurisdiction,
            industry=request.industry,
            risk_level=request.risk_level,
        )
        return result
    except Exception as exc:
        logger.error("AI draft generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI draft generation failed: {exc}",
        )


# ── CRUD ───────────────────────────────────────────────────────────


@router.post(
    "",
    summary="Create a redline template",
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: RedlineTemplateCreate,
    service: RedlineTemplateService = Depends(get_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new redline template."""
    create_data = data.model_dump()
    create_data["created_by"] = create_data.get("created_by") or user.id
    return await service.create_template(create_data)


@router.get("")
async def list_templates(
    clause_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return await service.list_templates(clause_type, category, status, limit, offset)


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.patch("/{template_id}")
async def update_template(
    template_id: str,
    data: RedlineTemplateUpdate,
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    template = await service.update_template(template_id, data.model_dump(exclude_unset=True))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_DELETE)),
):
    deleted = await service.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")


@router.post("/{template_id}/use")
async def record_template_usage(
    template_id: str,
    accepted: bool = Query(True),
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Record that a template was used (for analytics)."""
    await service.record_usage(template_id, accepted)
    return {"status": "recorded"}


# ── Batch Operations ──────────────────────────────────────────────


class BatchGenerateRequest(BaseModel):
    items: list[AIDraftRequest]


@router.post(
    "/generate-batch",
    summary="Batch generate AI drafts for multiple clause types",
)
async def batch_generate_drafts(
    request: BatchGenerateRequest,
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Generate AI drafts for multiple missing clause types in one operation."""
    results = []
    errors = []
    for item in request.items:
        try:
            result = await service.generate_ai_draft(
                clause_type=item.clause_type,
                finding_title=item.finding_title,
                finding_description=item.finding_description,
                jurisdiction=item.jurisdiction,
                industry=item.industry,
                risk_level=item.risk_level,
            )
            results.append(result)
        except Exception as exc:
            errors.append({"clause_type": item.clause_type, "error": str(exc)})
    return {"results": results, "errors": errors, "total": len(request.items), "succeeded": len(results), "failed": len(errors)}


@router.post(
    "/promote-ai-template",
    summary="Promote an AI-generated draft to an approved enterprise template",
)
async def promote_ai_template(
    draft_text: str = Body(...),
    name: str = Body(...),
    clause_type: str = Body(...),
    category: str = Body(...),
    jurisdiction: Optional[str] = Body(None),
    industry: Optional[str] = Body(None),
    risk_level: Optional[str] = Body(None),
    created_by: Optional[str] = Body(None),
    service: RedlineTemplateService = Depends(get_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Promote an AI-generated draft to an approved enterprise template."""
    create_data = {
        "name": name,
        "clause_type": clause_type,
        "category": category or clause_type,
        "jurisdiction": jurisdiction,
        "industry": industry,
        "risk_level": risk_level,
        "template_text": draft_text,
        "status": "active",
        "created_by": created_by or user.id,
        "approved_by": user.id,
        "effective_date": datetime.now(timezone.utc).isoformat(),
    }
    return await service.create_template(create_data)


@router.get(
    "/analytics",
    summary="Get template analytics (usage stats, trends)",
)
async def get_analytics(
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get template analytics including usage stats and coverage trends."""
    coverage = await service.get_coverage()
    templates = await service.list_templates(limit=1000)
    total_usage = sum(t.get("usage_count", 0) for t in templates)
    avg_accept = (
        sum(t.get("accept_rate", 0) for t in templates) / max(len(templates), 1)
    )
    return {
        "coverage": coverage,
        "total_templates": len(templates),
        "total_usage": total_usage,
        "avg_accept_rate": round(avg_accept, 2),
        "by_status": {
            "active": sum(1 for t in templates if t.get("status") == "active"),
            "ai_draft": sum(1 for t in templates if t.get("status") == "ai_draft"),
            "draft": sum(1 for t in templates if t.get("status") == "draft"),
            "retired": sum(1 for t in templates if t.get("status") == "retired"),
        },
    }
