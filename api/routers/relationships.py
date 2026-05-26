"""Contract relationship graph API endpoints.

Provides endpoints for managing contract relationship hierarchies,
traversal, and cross-contract conflict queries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts", tags=["Contract Relationships"])


async def _get_repo(request: Request):
    """Get the database repository from the app's state."""
    db_repo = getattr(request.app.state, "db_repo", None)
    if db_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available",
        )
    return db_repo


@router.get("/{contract_id}/relationships")
async def list_relationships(
    request: Request,
    contract_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """List all relationships for a contract.

    Args:
        request: FastAPI request.
        contract_id: The contract identifier.
        user: Authenticated user.

    Returns:
        Dict with relationships list.
    """
    repo = await _get_repo(request)
    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    relationships = await repo.list_relationships(contract_id)
    return {
        "contract_id": contract_id,
        "relationships": relationships,
        "total": len(relationships),
    }


@router.post("/{contract_id}/relationships", status_code=status.HTTP_201_CREATED)
async def create_relationship(
    request: Request,
    contract_id: str,
    body: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Create a relationship between two contracts.

    The contract_id in the URL is the parent. The body must contain
    child_contract_id and relationship_type.

    Args:
        request: FastAPI request.
        contract_id: Parent contract identifier.
        body: Dict with child_contract_id, relationship_type,
              optional effective_date and notes.
        user: Authenticated user.

    Returns:
        Created relationship dict.
    """
    repo = await _get_repo(request)

    # Validate parent contract exists
    parent = await repo.get_contract(contract_id)
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent contract {contract_id} not found",
        )

    # Validate child contract exists
    child_id = body.get("child_contract_id")
    if not child_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="child_contract_id is required",
        )

    child = await repo.get_contract(child_id)
    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Child contract {child_id} not found",
        )

    # Validate relationship type
    valid_types = {"parent", "child", "amendment", "addendum", "dpa"}
    rel_type = body.get("relationship_type", "child")
    if rel_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid relationship_type. Must be one of: {', '.join(sorted(valid_types))}",
        )

    relationship = await repo.create_relationship({
        "parent_contract_id": contract_id,
        "child_contract_id": child_id,
        "relationship_type": rel_type,
        "effective_date": body.get("effective_date"),
        "notes": body.get("notes"),
    })

    logger.info(
        "Relationship %s created: %s -> %s (%s) by user %s",
        relationship["relationship_id"], contract_id, child_id, rel_type, user.sub,
    )

    return relationship


@router.delete("/{contract_id}/relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(
    request: Request,
    contract_id: str,
    rel_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.DELETE_CONTRACTS)),
) -> None:
    """Delete a relationship.

    Args:
        request: FastAPI request.
        contract_id: Contract identifier (for validation).
        rel_id: Relationship identifier.
        user: Authenticated user.

    Raises:
        HTTPException: If relationship not found.
    """
    repo = await _get_repo(request)

    rel = await repo.get_relationship(rel_id)
    if rel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {rel_id} not found",
        )

    # Verify the relationship involves this contract
    if rel["parent_contract_id"] != contract_id and rel["child_contract_id"] != contract_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Relationship does not involve the specified contract",
        )

    deleted = await repo.delete_relationship(rel_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {rel_id} not found",
        )

    logger.info("Relationship %s deleted by user %s", rel_id, user.sub)


@router.get("/{contract_id}/relationship-tree")
async def get_relationship_tree(
    request: Request,
    contract_id: str,
    max_depth: int = Query(5, ge=1, le=20, description="Maximum traversal depth"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get the full relationship tree for a contract.

    Builds a tree by traversing both parent and child relationships.

    Args:
        request: FastAPI request.
        contract_id: The root contract identifier.
        max_depth: Maximum traversal depth.
        user: Authenticated user.

    Returns:
        Dict with tree structure.
    """
    repo = await _get_repo(request)

    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    # Get all relationships
    all_rels = await repo.list_all_relationships()
    from models.relationship_graph import ContractRelationship, RelationshipGraph, RelationshipType

    relationships = [
        ContractRelationship.from_dict(rel) for rel in all_rels
    ]

    graph = RelationshipGraph(relationships)

    # Build contract map for enriching nodes
    all_contract_ids = {contract_id}
    for rel in all_rels:
        all_contract_ids.add(rel["parent_contract_id"])
        all_contract_ids.add(rel["child_contract_id"])

    contract_map = {}
    for cid in all_contract_ids:
        c = await repo.get_contract(cid)
        if c:
            contract_map[cid] = c

    tree = graph.build_tree(contract_id, contract_map, max_depth)

    return {
        "contract_id": contract_id,
        "tree": tree.to_dict(),
        "total_nodes": len(all_contract_ids),
    }


@router.get("/{contract_id}/conflicts")
async def get_contract_conflicts(
    request: Request,
    contract_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Check for cross-contract conflicts.

    Delegates to the conflict detector engine if available, otherwise
    returns basic relationship-level conflict indicators.

    Args:
        request: FastAPI request.
        contract_id: The contract identifier.
        user: Authenticated user.

    Returns:
        Dict with conflict analysis.
    """
    repo = await _get_repo(request)

    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    # Try to use the conflict detector engine
    try:
        from risk_engine.conflict_detector import ConflictDetector
        detector = ConflictDetector(repo)
        conflicts = await detector.detect_conflicts(contract_id)
        return {
            "contract_id": contract_id,
            "conflicts": conflicts,
            "total": len(conflicts),
            "engine": "conflict_detector",
        }
    except ImportError:
        logger.warning("ConflictDetector not available, returning basic checks")

    # Basic conflict detection using relationship data
    relationships = await repo.list_relationships(contract_id)
    basic_conflicts = []

    for rel in relationships:
        # Check for circular references
        if rel["parent_contract_id"] == rel["child_contract_id"]:
            basic_conflicts.append({
                "type": "self_reference",
                "severity": "high",
                "description": f"Contract references itself in relationship {rel['relationship_id']}",
                "relationship_id": rel["relationship_id"],
            })

        # Check for duplicate relationships
        for other in relationships:
            if (
                other["relationship_id"] != rel["relationship_id"]
                and other["parent_contract_id"] == rel["parent_contract_id"]
                and other["child_contract_id"] == rel["child_contract_id"]
            ):
                basic_conflicts.append({
                    "type": "duplicate_relationship",
                    "severity": "medium",
                    "description": f"Duplicate relationship between {rel['parent_contract_id']} and {rel['child_contract_id']}",
                    "relationship_ids": [rel["relationship_id"], other["relationship_id"]],
                })
                break

    return {
        "contract_id": contract_id,
        "conflicts": basic_conflicts,
        "total": len(basic_conflicts),
        "engine": "basic",
    }
