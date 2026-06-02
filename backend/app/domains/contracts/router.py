"""Contracts API router — wraps the review service to provide a contract-centric view.

This router maps the backend's review-oriented data model into a contract
repository view expected by the frontend ContractsPage.  It delegates all
data access to the existing ReviewService rather than duplicating logic.

Endpoints:
    GET  /contracts/       — List contracts (paginated, filterable, sortable)
    GET  /contracts/kpis   — Aggregate KPI data for the contracts dashboard
    GET  /contracts/{id}   — Single contract detail
    GET  /contracts/views  — Saved views for the contracts repository
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.domains.review.router import get_review_service
from app.domains.review.schemas import ReviewFilterParams
from app.domains.review.service import ReviewService
from app.kernel.security.permissions import Permissions
from app.kernel.security.rbac import require_permission
from app.kernel.web.pagination import PaginatedResponse, PaginationMeta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


# ── Schemas ──────────────────────────────────────────────────────────────


class ContractSummary:
    """Lightweight contract view mapped from review data."""
    def __init__(self, review, filename: str = "") -> None:
        self.id = str(review.review_id)
        self.name = filename or getattr(review, 'document_name', '') or "Untitled"
        self.vendor = getattr(review, 'counterparty', '') or ""
        self.contractType = getattr(review, 'document_type', '') or "contract"
        self.businessUnit = ""
        risk = getattr(review, 'risk_score', None)
        self.riskScore = int(risk) if risk else 0
        self.riskLevel = _risk_level(self.riskScore)
        self.financialValue = 0
        self.currency = "USD"
        status = getattr(review, 'status', 'draft') or 'draft'
        self.status = _map_status(status)
        self.renewalDate = ""
        self.aiConfidence = min(100, max(0, self.riskScore * 10))
        self.owner = getattr(review, 'assigned_to', None) or getattr(review, 'created_by', '') or ""
        self.workflowStage = getattr(review, 'workflow_stage', None) or _map_workflow(status)
        self.lastModified = _fmt_date(getattr(review, 'updated_at', None))
        self.tags = []
        self.geography = ""
        self.counterparty = getattr(review, 'counterparty', '') or ""
        self.description = ""
        self.aiSummary = ""
        self.clauseCount = 0
        self.missingClauses = []
        self.aiFlags = _derive_flags(risk)
        self.obligationsDue = 0
        self.hasRedlines = bool(getattr(review, 'redline_count', 0))
        self.hasDpa = False
        self.autoRenew = False
        self.totalPages = 0
        self.createdAt = _fmt_date(getattr(review, 'created_at', None))


def _risk_level(score: int) -> str:
    if score >= 8: return "critical"
    if score >= 6: return "high"
    if score >= 4: return "medium"
    return "low"


def _map_status(status: str) -> str:
    mapping = {
        "draft": "draft",
        "ai_analyzed": "under_review",
        "in_review": "under_review",
        "approved": "active",
        "rejected": "draft",
        "closed": "expired",
    }
    return mapping.get(status, "draft")


def _map_workflow(status: str) -> str:
    mapping = {
        "draft": "draft",
        "ai_analyzed": "review",
        "in_review": "review",
        "approved": "executed",
        "rejected": "archived",
        "closed": "archived",
    }
    return mapping.get(status, "draft")


def _derive_flags(risk_score) -> list[str]:
    flags = []
    if risk_score and risk_score >= 7:
        flags.append("critical")
    if risk_score and risk_score >= 5:
        flags.append("review_needed")
    return flags


def _fmt_date(dt) -> str:
    if not dt:
        return ""
    if isinstance(dt, str):
        return dt[:10]
    return dt.strftime("%Y-%m-%d")


# ── Endpoints ────────────────────────────────────────────────────────────


@router.get("", response_model=None, include_in_schema=False)
@router.get("/", response_model=None)
async def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List contracts mapped from review data."""
    filters = ReviewFilterParams(
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    items, total = await service.list_reviews(filters)

    # Apply client-side search filter
    if search:
        q = search.lower()
        items = [r for r in items if q in (getattr(r, '_document_filename', None) or getattr(r, 'document_name', '') or "").lower()]

    data = []
    for r in items:
        s = ContractSummary(r, getattr(r, '_document_filename', ''))
        data.append({k: v for k, v in vars(s).items() if not k.startswith('_')})
    return {
        "data": data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.get("/kpis", response_model=None)
async def contract_kpis(
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Aggregate KPI data for the contracts dashboard."""
    items, total = await service.list_reviews(ReviewFilterParams(page=1, page_size=100))

    high_risk = sum(1 for r in items if getattr(r, 'risk_score', None) and r.risk_score >= 7)
    active_reviews = sum(1 for r in items if getattr(r, 'status', None) in ("in_review", "ai_analyzed"))
    pending = sum(1 for r in items if getattr(r, 'status', None) == "draft")
    scores = [r.risk_score for r in items if getattr(r, 'risk_score', None)]

    return {
        "total_contracts": total,
        "active_reviews": active_reviews,
        "pending_reviews": pending,
        "high_risk_count": high_risk,
        "expiring_soon": 0,
        "avg_risk_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "total_value_at_risk": 0,
    }


@router.get("/views", response_model=None)
async def list_saved_views():
    """Placeholder for saved views — returns empty list until feature is backend-backed."""
    return []


@router.get("/{contract_id}", response_model=None)
async def get_contract(
    contract_id: str,
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a single contract by review ID."""
    review = await service.get_review(contract_id)
    if not review:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Contract not found")
    # get_review returns a dict, convert to object for ContractSummary
    from types import SimpleNamespace
    obj = SimpleNamespace(**review)
    return {k: v for k, v in vars(ContractSummary(obj, review.get('original_filename', ''))).items() if not k.startswith('_')}


@router.get("/views", response_model=None)
async def list_saved_views():
    """Placeholder for saved views — returns empty list until feature is backend-backed."""
    return []
