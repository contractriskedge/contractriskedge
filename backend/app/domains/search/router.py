"""Search API router — search, autocomplete, click tracking, and query analytics."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.search.schemas import (
    SearchRequest, SearchResponse, AutocompleteRequest, AutocompleteResponse,
    SearchPulseResponse, SearchClickRequest,
)
from app.domains.search.service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


async def get_search_service(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
) -> SearchService:
    return SearchService(session=db, tenant_id=tenant_id, user=user)


@router.get("/pulse", response_model=SearchPulseResponse)
async def search_pulse(
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get portfolio-level search intelligence for the discovery panel.

    Returns total indexed chunks/contracts, today's query count,
    popular queries, dynamic suggestions from findings DB,
    and portfolio insights. Called on page load to populate the UI.
    """
    return await service.get_pulse(
)


@router.post("", response_model=SearchResponse, include_in_schema=False)
@router.post("/", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Execute a hybrid search across contract chunks.

    Supports vector, keyword, and hybrid strategies.
    All searches are tenant-isolated and permission-filtered.
    """
    return await service.search(body
)


@router.get("", response_model=SearchResponse, include_in_schema=False)
@router.get("/", response_model=SearchResponse)
async def search_get(
    q: str = Query(..., min_length=1, max_length=500),
    strategy: str = Query("hybrid", pattern="^(hybrid|vector|keyword)$"),
    clause_type: Optional[str] = Query(None),
    contract_id: Optional[str] = Query(None),
    entity_types: Optional[str] = Query(None, description="Comma-separated: chunk,finding,obligation"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """GET-based search with query parameter support."""
    types_list = entity_types.split(",") if entity_types else ["chunk"]
    request = SearchRequest(
        query=q, strategy=strategy,
        clause_type=clause_type, contract_id=contract_id,
        entity_types=types_list,
        page=page, page_size=page_size,
    )
    return await service.search(request)


@router.get("/findings")
async def search_findings(
    q: str = Query(..., min_length=1, max_length=500),
    severity: Optional[str] = Query(None, pattern="^(critical|high|medium|low|info)$"),
    clause_type: Optional[str] = Query(None),
    resolution: Optional[str] = Query(None),
    review_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search across AI findings (titles, descriptions, recommendations
).

    Supports filtering by severity, clause type, resolution status, and review.
    Returns matching findings with relevance scoring.
    """
    return await service.search_findings(
        query=q, severity=severity, clause_type=clause_type,
        resolution=resolution, review_id=review_id,
        page=page, page_size=page_size
)


@router.get("/obligations")
async def search_obligations(
    q: str = Query(..., min_length=1, max_length=500),
    status: Optional[str] = Query(None),
    contract_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search across obligations by name, description, vendor, and contract name.

    Supports filtering by status and contract_id.
    Returns matching obligations with relevance scoring.
    """
    return await service.search_obligations(
        query=q, status=status, contract_id=contract_id,
        page=page, page_size=page_size
)


@router.get("/clauses")
async def search_clauses(
    q: str = Query(..., min_length=1, max_length=500),
    clause_type: Optional[str] = Query(None),
    contract_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search across contract clause text and metadata.

    Returns matching chunks with clause type, page numbers, and relevance scores.
    """
    return await service.search_clauses(
        query=q, clause_type=clause_type, contract_id=contract_id,
        page=page, page_size=page_size
)


@router.post("/click")
async def log_click(
    body: SearchClickRequest,
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Log a search result click for ranking quality measurement."""
    await service.log_click_from_request(body)
    return {"status": "logged"}


@router.get("/popular")
async def popular_queries(
    limit: int = Query(20, ge=1, le=100),
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get popular search queries for this tenant."""
    return {"queries": await service.get_popular_queries(limit
)}


@router.get("/zero-results")
async def zero_result_queries(
    limit: int = Query(20, ge=1, le=100),
    service: SearchService = Depends(get_search_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get queries that returned zero results (quality improvement signal
)."""
    return {"queries": await service.get_zero_result_queries(limit
)}
