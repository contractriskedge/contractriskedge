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


class PromoteAITemplateRequest(BaseModel):
    draft_text: str
    name: str
    clause_type: str
    category: str
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    risk_level: Optional[str] = None
    created_by: Optional[str] = None


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
    body: PromoteAITemplateRequest,
    service: RedlineTemplateService = Depends(get_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Promote an AI-generated draft to an approved enterprise template."""
    import uuid
    create_data = {
        "template_id": uuid.uuid4(),
        "name": body.name,
        "clause_type": body.clause_type,
        "category": body.category or body.clause_type,
        "jurisdiction": body.jurisdiction,
        "industry": body.industry,
        "risk_level": body.risk_level,
        "template_text": body.draft_text,
        "language": "en",
        "version": 1,
        "status": "active",
        "usage_count": 0,
        "accept_rate": 0.0,
        "created_by": body.created_by or user.id,
        "approved_by": user.id,
        "effective_date": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    return await service.create_template(create_data)


@router.post(
    "/apply-to-review",
    summary="Apply a template to a review — creates redline and marks finding resolved",
)
async def apply_template_to_review(
    template_id: str = Body(...),
    review_id: str = Body(...),
    finding_id: Optional[str] = Body(None),
    clause_type: str = Body(...),
    service: RedlineTemplateService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Apply a redline template to a review.

    Creates a ReviewRedline from the template text and optionally
    marks the linked finding as resolved.
    """
    # 1. Get the template
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 2. Get the review to find upload_id
    from sqlalchemy import select as sa_select
    from app.domains.review.models import ContractReview
    review_result = await db.execute(
        sa_select(ContractReview).where(
            ContractReview.review_id == review_id,
            ContractReview.tenant_id == tenant_id,
        )
    )
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # 3. Create the redline
    from app.domains.review.repository import ReviewRepository
    from app.domains.review.models import ReviewRedline, RedlineStatus

    review_repo = ReviewRepository(db, tenant_id=tenant_id)
    redline = ReviewRedline(
        review_id=review_id,
        tenant_id=tenant_id,
        upload_id=str(review.upload_id),
        clause_type=clause_type,
        original_text="",
        proposed_text=template["template_text"],
        operation="insert",
        anchor_text=None,
        rationale=f"Applied from template: {template['name']} (v{template['version']})",
        risk_level=template.get("risk_level") or "medium",
        finding_id=finding_id,
        redline_metadata={
            "template_id": template_id,
            "template_name": template["name"],
            "template_version": template["version"],
            "applied_by": user.id,
            "source": "knowledge_center_apply",
        },
        status=RedlineStatus.PROPOSED,
    )
    db.add(redline)
    await db.flush()

    # 4. Mark finding as resolved if finding_id provided
    if finding_id:
        from app.domains.review.models import ReviewFinding
        find_result = await db.execute(
            sa_select(ReviewFinding).where(
                ReviewFinding.finding_id == finding_id,
                ReviewFinding.tenant_id == tenant_id,
            )
        )
        finding = find_result.scalar_one_or_none()
        if finding:
            finding.status = "resolved"
            finding.resolved_by = user.id
            from datetime import datetime, timezone
            finding.resolved_at = datetime.now(timezone.utc)

    # 5. Update review redline count
    from sqlalchemy import func as sa_func
    count_result = await db.execute(
        sa_select(sa_func.count()).select_from(ReviewRedline).where(
            ReviewRedline.review_id == review_id,
        )
    )
    review.redline_count = count_result.scalar() or 0

    # 6. Record template usage
    await service.record_usage(template_id, accepted=True)

    await db.commit()

    return {
        "status": "applied",
        "redline_id": str(redline.redline_id),
        "review_id": review_id,
        "template_name": template["name"],
        "finding_resolved": finding_id is not None,
    }


@router.get(
    "/bundles",
    summary="Get recommended clause bundles",
    description="Returns related clause types that should be applied together as a bundle.",
)
async def get_bundles(
    clause_type: str = Query(..., description="The clause type to find bundles for"),
    service: RedlineTemplateService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get recommended clause bundles for a given clause type.

    For example, requesting bundles for 'gdpr' returns:
    ['data_privacy', 'cross_border_transfer', 'data_breach', 'dpa']
    """
    # Define clause bundles based on legal domain knowledge
    BUNDLES: dict[str, list[dict[str, str]]] = {
        "gdpr": [
            {"clause_type": "gdpr", "label": "GDPR Compliance", "required": True},
            {"clause_type": "cross_border_transfer", "label": "Cross-Border Transfer", "required": True},
            {"clause_type": "data_breach", "label": "Data Breach Notification", "required": True},
            {"clause_type": "dpa", "label": "Data Processing Agreement", "required": False},
            {"clause_type": "scc", "label": "Standard Contractual Clauses", "required": False},
        ],
        "data_privacy": [
            {"clause_type": "gdpr", "label": "GDPR Compliance", "required": True},
            {"clause_type": "cross_border_transfer", "label": "Cross-Border Transfer", "required": True},
            {"clause_type": "data_breach", "label": "Data Breach Notification", "required": True},
        ],
        "confidentiality": [
            {"clause_type": "confidentiality", "label": "Confidentiality", "required": True},
            {"clause_type": "nda", "label": "Non-Disclosure Agreement", "required": True},
            {"clause_type": "return_of_information", "label": "Return of Information", "required": False},
            {"clause_type": "non_compete", "label": "Non-Compete", "required": False},
        ],
        "indemnification": [
            {"clause_type": "indemnification", "label": "Indemnification", "required": True},
            {"clause_type": "liability", "label": "Limitation of Liability", "required": True},
            {"clause_type": "insurance", "label": "Insurance Requirements", "required": False},
        ],
        "liability": [
            {"clause_type": "liability", "label": "Limitation of Liability", "required": True},
            {"clause_type": "indemnification", "label": "Indemnification", "required": True},
            {"clause_type": "consequential_damages", "label": "Consequential Damages", "required": False},
            {"clause_type": "insurance", "label": "Insurance Requirements", "required": False},
        ],
        "termination": [
            {"clause_type": "termination", "label": "Termination", "required": True},
            {"clause_type": "notice_period", "label": "Notice Period", "required": True},
            {"clause_type": "auto_renewal", "label": "Auto-Renewal", "required": False},
            {"clause_type": "for_cause_termination", "label": "For-Cause Termination", "required": False},
        ],
        "intellectual_property": [
            {"clause_type": "intellectual_property", "label": "Intellectual Property", "required": True},
            {"clause_type": "ip_ownership", "label": "IP Ownership", "required": True},
            {"clause_type": "license", "label": "License Grant", "required": True},
            {"clause_type": "non_compete", "label": "Non-Compete", "required": False},
        ],
    }

    # Find matching bundle — exact match or partial match
    bundle = BUNDLES.get(clause_type)
    if not bundle:
        # Try to find a bundle where this clause_type appears
        for key, items in BUNDLES.items():
            if any(item["clause_type"] == clause_type for item in items):
                bundle = items
                break

    if not bundle:
        return {"clause_type": clause_type, "bundle": [], "total": 0}

    # Check which templates exist for each clause type
    enriched = []
    for item in bundle:
        templates = await service.list_templates(clause_type=item["clause_type"], limit=1)
        enriched.append({
            **item,
            "has_template": len(templates) > 0,
            "template_name": templates[0]["name"] if templates else None,
        })

    return {
        "clause_type": clause_type,
        "bundle": enriched,
        "total": len(enriched),
        "applied": sum(1 for b in enriched if b["has_template"]),
        "missing": sum(1 for b in enriched if not b["has_template"]),
    }


@router.get(
    "/analytics",
    summary="Get template analytics (usage stats, trends)",
)
async def get_analytics(
    service: RedlineTemplateService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get template analytics including usage stats and coverage trends."""
    coverage = await service.get_coverage()
    templates = await service.list_templates(limit=1000)
    total_usage = sum(t.get("usage_count", 0) for t in templates)
    avg_accept = (
        sum(t.get("accept_rate", 0) for t in templates) / max(len(templates), 1)
    )

    # Coverage trends from snapshots
    from sqlalchemy import text as sa_text
    trends_result = await db.execute(
        sa_text("""
            SELECT snapshot_date, coverage_pct, total_findings, total_templates
            FROM coverage_snapshots
            WHERE tenant_id = :tenant_id
            ORDER BY snapshot_date DESC
            LIMIT 14
        """),
        {"tenant_id": tenant_id},
    )
    trends = [dict(r._mapping) for r in trends_result.fetchall()]

    # Record today's snapshot (idempotent — one per day)
    from datetime import date, datetime, timezone
    today = date.today()
    await db.execute(
        sa_text("""
            INSERT INTO coverage_snapshots (snapshot_id, tenant_id, total_findings, total_templates, templates_used, templates_missing, coverage_pct, snapshot_date)
            SELECT gen_random_uuid(), :tenant_id, :total_findings, :total_templates, :templates_used, :templates_missing, :coverage_pct, :snapshot_date
            WHERE NOT EXISTS (
                SELECT 1 FROM coverage_snapshots
                WHERE tenant_id = :tenant_id2
                  AND snapshot_date::date = :today
            )
        """),
        {
            "tenant_id": tenant_id,
            "tenant_id2": tenant_id,
            "total_findings": coverage.get("total_findings", 0),
            "total_templates": coverage.get("total_templates", 0),
            "templates_used": coverage.get("templates_used", 0),
            "templates_missing": coverage.get("templates_missing", 0),
            "coverage_pct": coverage.get("coverage_pct", 0),
            "snapshot_date": datetime.now(timezone.utc),
            "today": today,
        },
    )
    await db.commit()

    return {
        "coverage": coverage,
        "total_templates": len(templates),
        "total_usage": total_usage,
        "avg_accept_rate": round(avg_accept, 2),
        "trends": [
            {
                "date": t["snapshot_date"].isoformat() if hasattr(t["snapshot_date"], "isoformat") else str(t["snapshot_date"]),
                "coverage_pct": t["coverage_pct"],
                "total_findings": t["total_findings"],
                "total_templates": t["total_templates"],
            }
            for t in trends
        ],
        "by_status": {
            "active": sum(1 for t in templates if t.get("status") == "active"),
            "ai_draft": sum(1 for t in templates if t.get("status") == "ai_draft"),
            "draft": sum(1 for t in templates if t.get("status") == "draft"),
            "retired": sum(1 for t in templates if t.get("status") == "retired"),
        },
    }
