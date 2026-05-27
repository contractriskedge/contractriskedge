"""Clause Intelligence API router — clause graph, alternatives, negotiation, vendor patterns, graph scaling."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.ai.repository import AIRepository
from app.domains.playbook.repository import PlaybookRepository
from app.domains.review.repository import ReviewRepository
from app.domains.clause_intel.schemas import (
    ClauseGraph, ClauseGraphQuery,
    AlternativeSearchResult,
    NegotiationHistory, NegotiationPattern,
    VendorPatternSummary,
    SemanticSearchResult,
    RiskInheritanceChain,
    ClauseIntelligenceDashboard,
)
from app.domains.clause_intel.graph_schemas import (
    GraphTraversalConfig, TraversalResult,
    GraphExplainabilityRequest, GraphExplainabilityResponse,
    GraphCacheStats, GraphIndexStats,
)
from app.domains.clause_intel.service import ClauseIntelligenceService
from app.domains.clause_intel.graph_service import (
    GraphScoringService, GraphTraversalService,
    GraphExplainabilityService, GraphCacheService,
)

router = APIRouter(prefix="/clause-intel", tags=["Clause Intelligence"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_intel_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ClauseIntelligenceService:
    return ClauseIntelligenceService(
        ai_repo=AIRepository(db, tenant_id=tenant_id),
        review_repo=ReviewRepository(db, tenant_id=tenant_id),
        playbook_repo=PlaybookRepository(db, tenant_id=tenant_id),
    )


# ── Dashboard ───────────────────────────────────────────────────────


@router.get("/dashboard", response_model=ClauseIntelligenceDashboard)
async def get_clause_intelligence_dashboard(
    service: ClauseIntelligenceService = Depends(get_intel_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get executive dashboard for clause intelligence across all contracts."""
    return await service.get_dashboard(tenant_id=tenant_id)


# ── Clause Graph ────────────────────────────────────────────────────


@router.get("/graph", response_model=ClauseGraph)
async def get_clause_graph(
    clause_type: Optional[str] = Query(None, description="Filter by clause type"),
    service: ClauseIntelligenceService = Depends(get_intel_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Build and return the clause knowledge graph."""
    query = ClauseGraphQuery(clause_type=clause_type)
    return await service.graph_builder.query_graph(
        tenant_id=tenant_id,
        query=query,
    )


# ── Approved Alternatives ───────────────────────────────────────────


@router.get("/alternatives", response_model=AlternativeSearchResult)
async def find_approved_alternatives(
    clause_type: str = Query(..., description="Clause type to find alternatives for"),
    text_snippet: Optional[str] = Query(None, description="Optional text snippet for context"),
    limit: int = Query(10, ge=1, le=50),
    service: ClauseIntelligenceService = Depends(get_intel_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Find approved alternative language for a risky clause type."""
    return await service.alternative_finder.find_alternatives(
        clause_type=clause_type,
        tenant_id=tenant_id,
        text_snippet=text_snippet or "",
        limit=limit,
    )


# ── Negotiation History ─────────────────────────────────────────────


@router.get("/negotiations/{upload_id}", response_model=list[NegotiationHistory])
async def get_negotiation_history(
    upload_id: str,
    clause_type: Optional[str] = Query(None),
    service: ClauseIntelligenceService = Depends(get_intel_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get negotiation history for a contract's clauses."""
    return await service.negotiation_tracker.get_negotiation_history(
        upload_id=upload_id,
        clause_type=clause_type,
    )


@router.get("/negotiation-patterns", response_model=list[NegotiationPattern])
async def get_negotiation_patterns(
    clause_type: Optional[str] = Query(None),
    service: ClauseIntelligenceService = Depends(get_intel_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Identify recurring negotiation patterns across all contracts."""
    return await service.negotiation_tracker.get_negotiation_patterns(
        tenant_id=tenant_id,
        clause_type=clause_type,
    )


# ── Vendor Patterns ─────────────────────────────────────────────────


@router.get("/vendors", response_model=list[VendorPatternSummary])
async def get_all_vendor_patterns(
    service: ClauseIntelligenceService = Depends(get_intel_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get clause pattern summaries for all vendors."""
    return await service.vendor_analyzer.get_all_vendor_summaries(tenant_id=tenant_id)


@router.get("/vendors/{vendor_name}", response_model=VendorPatternSummary)
async def get_vendor_pattern(
    vendor_name: str,
    service: ClauseIntelligenceService = Depends(get_intel_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get clause pattern profile for a specific vendor."""
    profile = await service.vendor_analyzer.get_vendor_profile(
        vendor_name=vendor_name,
        tenant_id=tenant_id,
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"No contracts found for vendor '{vendor_name}'")
    return profile


# ── Risk Inheritance ────────────────────────────────────────────────


@router.get("/risk-inheritance/{upload_id}", response_model=list[RiskInheritanceChain])
async def analyze_risk_inheritance(
    upload_id: str,
    service: ClauseIntelligenceService = Depends(get_intel_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Analyze risk inheritance chains across clauses in a contract."""
    return await service.risk_inheritance.analyze_inheritance(upload_id=upload_id)


# ── Graph Traversal ─────────────────────────────────────────────


@router.post("/graph/traverse", response_model=TraversalResult)
async def traverse_clause_graph(
    start_clause_id: str = Query(..., description="Starting clause node ID"),
    max_depth: int = Query(3, ge=1, le=10),
    max_results: int = Query(100, ge=1, le=1000),
    min_edge_strength: float = Query(0.1, ge=0.0, le=1.0),
    service: ClauseIntelligenceService = Depends(get_intel_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Traverse the clause graph from a starting node with configurable limits."""
    graph = await service.graph_builder.build_graph(tenant_id=tenant_id)
    traversal = GraphTraversalService()
    config = GraphTraversalConfig(
        max_depth=max_depth,
        max_results=max_results,
        min_edge_strength=min_edge_strength,
    )
    return traversal.traverse(graph, start_clause_id, config=config)


@router.post("/graph/explain", response_model=GraphExplainabilityResponse)
async def explain_graph_relationships(
    request: GraphExplainabilityRequest,
    service: ClauseIntelligenceService = Depends(get_intel_service),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Explain why clauses are related in the knowledge graph."""
    graph = await service.graph_builder.build_graph(tenant_id=tenant_id)
    scoring = GraphScoringService()
    explainer = GraphExplainabilityService(scoring_service=scoring)
    return await explainer.explain(graph, request)


@router.get("/graph/cache-stats", response_model=GraphCacheStats)
async def get_graph_cache_stats(
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get clause graph cache statistics."""
    cache = GraphCacheService()
    return cache.get_stats()


@router.post("/graph/cache/invalidate")
async def invalidate_graph_cache(
    clause_type: Optional[str] = Query(None),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Invalidate the clause graph cache."""
    cache = GraphCacheService()
    if clause_type:
        cache.invalidate_by_clause_type(clause_type)
    else:
        cache.invalidate()
    return {"status": "invalidated"}
