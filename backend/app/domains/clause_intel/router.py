"""Clause Intelligence API router — CRUD, AI analysis, benchmarking, and analytics."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.clause_intel.schemas import (
    ClauseCreate, ClauseUpdate, ClauseResponse, ClauseKpiResponse,
    AiReviewRequest, AiReviewResponse, SimilarityRequest, SimilarityResult,
    DeviationResponse, BenchmarkResponse, FallbackVariantResponse,
    NegotiationHistoryResponse, UsageTrendResponse, MarketComparisonResponse,
    RejectionPatternResponse,
)
from app.domains.clause_intel.service import ClauseService
from app.dependencies import get_db, get_tenant_id
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clauses", tags=["Clause Intelligence"])


async def get_clause_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ClauseService:
    return ClauseService(session, tenant_id)


@router.get("", response_model=None, include_in_schema=False)
@router.get("/", response_model=None)
async def list_clauses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    approval_status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    items, total = await service.list_clauses(page, page_size, category, search, approval_status, risk_level, sort_by, sort_order)
    return {"data": [i.model_dump() for i in items], "pagination": {"page": page, "page_size": page_size, "total": total, "total_pages": max(1, (total + page_size - 1) // page_size)}}


@router.get("/kpis", response_model=None)
async def get_kpis(
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return (await service.get_kpis()).model_dump()


@router.get("/benchmarks", response_model=None)
async def get_benchmarks(
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [b.model_dump() for b in await service.get_benchmarks()]


@router.get("/deviations", response_model=None)
async def get_deviations(
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [d.model_dump() for d in await service.get_deviations()]


@router.post("/ai-review", response_model=None)
async def ai_review(
    req: AiReviewRequest,
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return await service.ai_review(req.clause_text, req.category)


@router.post("/similarity", response_model=None)
async def find_similar(
    req: SimilarityRequest,
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [s.model_dump() for s in await service.find_similar(req.clause_text, req.category, req.limit)]


@router.get("/{clause_id}", response_model=None)
async def get_clause(
    clause_id: str,
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    result = await service.get_clause(clause_id)
    if not result:
        raise HTTPException(status_code=404, detail="Clause not found")
    return result.model_dump()


@router.post("", response_model=None, include_in_schema=False)
@router.post("/", response_model=None)
async def create_clause(
    data: ClauseCreate,
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    return (await service.create_clause(data)).model_dump()


@router.put("/{clause_id}", response_model=None)
async def update_clause(
    clause_id: str,
    data: ClauseUpdate,
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    result = await service.update_clause(clause_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Clause not found")
    return result.model_dump()


@router.delete("/{clause_id}", response_model=None)
async def delete_clause(
    clause_id: str,
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_DELETE)),
):
    if not await service.delete_clause(clause_id):
        raise HTTPException(status_code=404, detail="Clause not found")
    return {"status": "deleted"}


@router.post("/seed", response_model=None, include_in_schema=False)
async def seed_clauses(
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Seed the clause library with sample data for development/demo."""
    from app.domains.clause_intel.seed_data import seed_clause_library
    count = await seed_clause_library(service.session, service.tenant_id)
    return {"status": "seeded", "clauses_created": count}


@router.get("/{clause_id}/fallbacks", response_model=None)
async def get_fallback_variants(
    clause_id: str,
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [v.model_dump() for v in await service.get_fallback_variants(clause_id)]


@router.get("/{clause_id}/negotiations", response_model=None)
async def get_negotiation_history(
    clause_id: str,
    service: ClauseService = Depends(get_clause_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    return [h.model_dump() for h in await service.get_negotiation_history(clause_id)]


@router.get("/usage-trends", response_model=None)
async def get_usage_trends():
    return []


@router.get("/market-comparison", response_model=None)
async def get_market_comparison():
    return []


@router.get("/rejection-patterns", response_model=None)
async def get_rejection_patterns():
    return []
