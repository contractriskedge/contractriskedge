"""Contract management API endpoints.

Provides endpoints for searching, retrieving, and managing
contract documents and their extracted content.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


async def _get_repo(request: Request):
    """Get the database repository from the app's state.

    Uses request.app.state to access the shared application state,
    avoiding circular import issues with the main module.
    """
    db_repo = getattr(request.app.state, "db_repo", None)
    if db_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available",
        )
    return db_repo


@router.get("/{contract_id}")
async def get_contract(
    request: Request,
    contract_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get a contract by its ID.

    Args:
        request: FastAPI request (used to access app state).
        contract_id: The contract document identifier.
        user: Authenticated user.

    Returns:
        Contract details including metadata and extraction status.

    Raises:
        HTTPException: If contract not found.
    """
    repo = await _get_repo(request)
    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    return contract


@router.get("")
@router.get("/")
async def list_contracts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """List all contracts for the current tenant.

    Args:
        request: FastAPI request (used to access app state).
        page: Page number.
        page_size: Items per page.
        user: Authenticated user.

    Returns:
        Dict with contracts list and pagination.
    """
    repo = await _get_repo(request)
    tenant_id = user.tenant_id or "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    contracts = await repo.list_contracts(tenant_id, limit=page_size, offset=(page - 1) * page_size)
    return {
        "contracts": contracts,
        "total": len(contracts),
        "page": page,
        "page_size": page_size,
    }


@router.post("/search")
async def search_contracts(
    request: Request,
    query: str = Query("", description="Search query"),
    tenant_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Search contracts by query text.

    Args:
        request: FastAPI request (used to access app state).
        query: Full-text search query.
        status_filter: Filter by ingestion status.
        page: Page number for pagination.
        page_size: Items per page.
        user: Authenticated user.

    Returns:
        Dict with matching contracts and pagination info.
    """
    repo = await _get_repo(request)
    current_tenant = user.tenant_id or "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    contracts = await repo.list_contracts(current_tenant, limit=100, offset=0)

    results = contracts
    if query:
        query_lower = query.lower()
        results = [c for c in results if query_lower in c.get("filename", "").lower()]
    if status_filter:
        results = [c for c in results if c.get("status") == status_filter]

    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "results": results[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{contract_id}/clauses")
async def get_contract_clauses(
    request: Request,
    contract_id: str,
    clause_type: Optional[str] = None,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get extracted clauses for a contract.

    Args:
        request: FastAPI request (used to access app state).
        contract_id: The contract identifier.
        clause_type: Optional filter by clause type.
        user: Authenticated user.

    Returns:
        Dict with clauses list.
    """
    repo = await _get_repo(request)
    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )
    return {"contract_id": contract_id, "clauses": []}


@router.get("/{contract_id}/chunks")
async def get_contract_chunks(
    request: Request,
    contract_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get semantic chunks for a contract.

    Args:
        request: FastAPI request (used to access app state).
        contract_id: The contract identifier.
        page: Page number.
        page_size: Items per page.
        user: Authenticated user.

    Returns:
        Dict with chunks list and pagination.
    """
    repo = await _get_repo(request)
    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )
    return {"contract_id": contract_id, "total_chunks": 0, "chunks": []}


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    request: Request,
    contract_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.DELETE_CONTRACTS)),
) -> None:
    """Delete a contract and its extracted data.

    Args:
        request: FastAPI request (used to access app state).
        contract_id: The contract to delete.
        user: Authenticated user.

    Raises:
        HTTPException: If contract not found or access denied.
    """
    repo = await _get_repo(request)
    deleted = await repo.delete_contract(contract_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )
    logger.info("Contract %s deleted by user %s", contract_id, user.sub)


# ── Obligation Inheritance (V2-012) ─────────────────────────────────────────


@router.get("/{contract_id}/obligations")
async def get_contract_obligations(
    request: Request,
    contract_id: str,
    include_inherited: bool = True,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get obligations for a contract, with inheritance tracking.

    Args:
        request: FastAPI request.
        contract_id: The contract identifier.
        include_inherited: Whether to include inherited obligations.
        user: Authenticated user.

    Returns:
        Dict with obligations and summary.
    """
    repo = await _get_repo(request)
    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    from risk_engine.obligation_tracker import ObligationTracker
    tracker = ObligationTracker(repo)
    summary = await tracker.get_obligation_summary(contract_id)

    return summary


# ── Regression Detection (V2-015) ───────────────────────────────────────────


@router.get("/{contract_id}/regressions")
async def get_contract_regressions(
    request: Request,
    contract_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Detect regressions for a contract.

    Compares the contract with related amendments and addenda
    to find term changes that increase risk.

    Args:
        request: FastAPI request.
        contract_id: The contract identifier.
        user: Authenticated user.

    Returns:
        Dict with regression analysis.
    """
    repo = await _get_repo(request)
    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    from risk_engine.regression import RegressionDetector
    detector = RegressionDetector(repo)
    regressions = await detector.detect_regressions(contract_id)

    return {
        "contract_id": contract_id,
        "regressions": regressions,
        "total": len(regressions),
        "critical_count": sum(1 for r in regressions if r.get("severity") == "critical"),
        "high_count": sum(1 for r in regressions if r.get("severity") == "high"),
        "medium_count": sum(1 for r in regressions if r.get("severity") == "medium"),
    }


# ── Exposure Propagation (V2-014) ───────────────────────────────────────────


@router.post("/{contract_id}/propagate-risk")
async def propagate_contract_risk(
    request: Request,
    contract_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Propagate risk scores through a contract's family tree.

    Rolls up child contract risks to the parent contract.

    Args:
        request: FastAPI request.
        contract_id: The contract to propagate risk for.
        user: Authenticated user.

    Returns:
        Dict with propagation results.
    """
    repo = await _get_repo(request)
    contract = await repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    from risk_engine.exposure_propagator import ExposurePropagator
    propagator = ExposurePropagator(repo)
    result = await propagator.propagate_for_contract(contract_id)

    # Update the contract's risk score
    await repo.update_contract_risk_score(contract_id, result.total_risk_score)

    return {
        "contract_id": contract_id,
        "propagation": result.to_dict(),
    }


@router.post("/propagate-risk/all")
async def propagate_all_risks(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Propagate risk scores for all contracts.

    Runs full propagation across all contract families.

    Args:
        request: FastAPI request.
        user: Authenticated user.

    Returns:
        Dict with propagation results for all contracts.
    """
    repo = await _get_repo(request)

    from risk_engine.exposure_propagator import ExposurePropagator
    propagator = ExposurePropagator(repo)
    results = await propagator.propagate_all()

    return {
        "total_contracts": len(results),
        "results": [r.to_dict() for r in results],
    }
