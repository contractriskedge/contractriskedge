"""AI Explainability API router — evidence chains, confidence, benchmarks, regulations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.ai.repository import AIRepository
from app.domains.playbook.repository import PlaybookRepository
from app.domains.review.repository import ReviewRepository
from app.domains.explainability.schemas import (
    ExplainabilityResponse,
    RegulationCheckResult,
    BenchmarkComparison,
)
from app.domains.explainability.service import ExplainabilityService

router = APIRouter(prefix="/explainability", tags=["AI Explainability"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_explainability_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ExplainabilityService:
    return ExplainabilityService(
        ai_repo=AIRepository(db, tenant_id=tenant_id),
        review_repo=ReviewRepository(db, tenant_id=tenant_id),
        playbook_repo=PlaybookRepository(db, tenant_id=tenant_id),
    )


# ── Endpoints ───────────────────────────────────────────────────────


@router.get(
    "/reviews/{review_id}",
    response_model=ExplainabilityResponse,
)
async def get_review_explainability(
    review_id: str,
    upload_id: str,
    service: ExplainabilityService = Depends(get_explainability_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get full explainability for a review's AI analysis — evidence chains, confidence, rationale."""
    return await service.get_explainability(
        review_id=review_id,
        upload_id=upload_id,
        tenant_id=tenant_id,
    )


@router.get(
    "/reviews/{review_id}/regulation-check",
    response_model=RegulationCheckResult,
)
async def check_regulation_compliance(
    review_id: str,
    upload_id: str,
    service: ExplainabilityService = Depends(get_explainability_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Check contract clauses against applicable regulations (GDPR, CCPA, HIPAA, etc.)."""
    return await service.get_regulation_check(
        upload_id=upload_id,
        tenant_id=tenant_id,
    )
