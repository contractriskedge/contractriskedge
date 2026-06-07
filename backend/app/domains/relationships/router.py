"""Relationships Graph API router — endpoints for entity relationship graphs."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_tenant_id
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.relationships.schemas import RelationshipGraph
from app.domains.relationships.service import RelationshipGraphBuilder

router = APIRouter(prefix="/relationships", tags=["Relationships"])

logger = logging.getLogger(__name__)


@router.get("/graph", response_model=RelationshipGraph)
async def get_relationship_graph(
    review_id: Optional[str] = Query(None, description="Center graph on this review"),
    upload_id: Optional[str] = Query(None, description="Center graph on this upload"),
    depth: int = Query(1, ge=1, le=2, description="Traversal depth (1=direct FKs, 2=indirect)"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get an entity relationship graph centered on a review or upload.

    Returns nodes and edges representing the relationships between
    the review, its upload, findings, redlines, negotiations,
    obligations, workflows, and vendors.

    Depth 1: Direct foreign-key relationships only.
    Depth 2: Includes indirect relationships (e.g., AI findings).

    Maximum 200 nodes per response.
    Results are cached for 5 minutes.
    """
    if not review_id and not upload_id:
        raise HTTPException(
            status_code=400,
            detail="Either review_id or upload_id is required",
        )

    builder = RelationshipGraphBuilder(session=db, tenant_id=tenant_id)
    graph = await builder.build_graph(
        review_id=review_id,
        upload_id=upload_id,
        depth=depth,
    )

    if graph.total_nodes == 0:
        raise HTTPException(
            status_code=404,
            detail="No relationship data found for the given review or upload",
        )

    return graph
