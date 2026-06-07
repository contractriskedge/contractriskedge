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
    """Lightweight contract view mapped from review data.

    Fields align with the frontend PortfolioContract interface.
    Risk scores are stored as 0-1 floats in metadata JSONB
    and converted to 0-10 integers for display.
    """
    def __init__(self, review, filename: str = "") -> None:
        # Support both dict and object access patterns
        def _get(key: str, default=None):
            if isinstance(review, dict):
                return review.get(key, default)
            return getattr(review, key, default)

        self.id = str(_get('review_id', ''))
        self.name = filename or _get('document_name', 'Untitled') or "Untitled"
        self.vendor = ""
        self.contractType = "contract"
        self.businessUnit = ""
        # risk_score is a top-level field in the review response (0-1 float)
        raw_risk = _get('risk_score', None)
        if raw_risk is None:
            # Fallback: check document_metadata JSONB
            doc_md = _get('document_metadata', None) or _get('metadata', None) or {}
            if isinstance(doc_md, dict):
                raw_risk = doc_md.get('risk_score', None)
        self.riskScore = min(10, round((raw_risk or 0) * 10))
        self.riskLevel = _risk_level(self.riskScore)
        self.financialValue = 0
        self.currency = "USD"
        status = _get('status', None)
        status_str = status.value if hasattr(status, 'value') else str(status or 'draft')
        self.status = _map_status(status_str)
        self.expiryDate = ""
        self.topRisk = ""
        self.aiConfidence = min(100, max(0, round((raw_risk or 0) * 100)))
        self.owner = _get('assigned_to', None) or _get('created_by', '') or ""
        self.workflowStage = _get('workflow_stage', None) or _map_workflow(status_str)
        self.lastModified = _fmt_date(_get('updated_at', None))
        self.tags = []
        self.geography = ""
        self.department = ""
        self.description = ""
        self.clauseCount = _get('finding_count', 0) or 0
        self.aiFindingsCount = _get('finding_count', 0) or 0
        self.missingClauses = []
        self.aiFlags = _derive_flags(raw_risk)
        self.obligationsDue = 0
        self.slaCompliant = _get('sla_breached', False) is not True
        self.hasRedlines = bool(_get('redline_count', 0))
        # Compose AI summary from available data
        finding_count = self.clauseCount
        redline_count = _get('redline_count', 0) or 0
        risk_label = self.riskLevel
        score_pct = round((raw_risk or 0) * 100)
        parts = []
        if finding_count > 0:
            parts.append(f"AI analysis identified {finding_count} clause finding{'s' if finding_count != 1 else ''}")
        if redline_count > 0:
            parts.append(f"and generated {redline_count} proposed redline{'s' if redline_count != 1 else ''}")
        if raw_risk and raw_risk > 0:
            parts.append(f"with an overall risk score of {score_pct}% ({risk_label})")
        if parts:
            self.aiSummary = ". ".join(parts) + "."
        else:
            self.aiSummary = "Contract has been uploaded and is pending AI analysis."
        self.hasDpa = False
        self.autoRenew = False
        self.totalPages = _get('total_pages', 0) or 0
        self.createdAt = _fmt_date(_get('created_at', None))


def _risk_level(score: int) -> str:
    if score >= 8: return "critical"
    if score >= 6: return "high"
    if score >= 4: return "medium"
    return "low"


def _map_status(status: str) -> str:
    mapping = {
        "draft": "draft",
        "uploaded": "draft",
        "analyzing": "draft",
        "ai_analyzed": "under_review",
        "ai_reviewed": "under_review",
        "review_ready": "under_review",
        "procurement_review": "under_review",
        "legal_review": "under_review",
        "security_review": "under_review",
        "negotiation": "under_review",
        "in_review": "under_review",
        "changes_requested": "under_review",
        "pending_approval": "pending_review",
        "escalated": "pending_review",
        "legal_approval": "pending_review",
        "exec_approval": "pending_review",
        "approved": "active",
        "rejected": "draft",
        "finalized": "active",
        "executed": "active",
        "archived": "expired",
        "closed": "expired",
    }
    return mapping.get(status, "draft")


def _map_workflow(status: str) -> str:
    mapping = {
        "draft": "draft",
        "uploaded": "intake",
        "analyzing": "ai_review",
        "ai_analyzed": "review",
        "ai_reviewed": "review",
        "review_ready": "review",
        "procurement_review": "procurement",
        "legal_review": "legal_ops",
        "security_review": "security",
        "negotiation": "negotiation",
        "in_review": "review",
        "changes_requested": "review",
        "pending_approval": "pending_approval",
        "escalated": "escalated",
        "legal_approval": "legal_ops",
        "exec_approval": "executive",
        "approved": "executed",
        "rejected": "archived",
        "finalized": "executed",
        "executed": "executed",
        "archived": "archived",
        "closed": "archived",
    }
    return mapping.get(status, "draft")


def _derive_flags(risk_score) -> list[str]:
    """Derive flags from raw risk_score (0-1 float from metadata)."""
    flags = []
    if risk_score and risk_score >= 0.7:
        flags.append("critical")
    if risk_score and risk_score >= 0.5:
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
    """Aggregate KPI data for the contracts dashboard.

    Risk scores are stored as 0-1 floats in document_metadata JSONB.
    High risk threshold: >= 0.7 (maps to >= 7 on 0-10 scale).
    """
    items, total = await service.list_reviews(ReviewFilterParams(page=1, page_size=100))

    def _get_risk(r) -> float:
        md = getattr(r, 'document_metadata', None) or {}
        return float(md.get('risk_score', 0)) if isinstance(md, dict) else 0.0

    def _get_status(r) -> str:
        s = getattr(r, 'status', None)
        return s.value if hasattr(s, 'value') else str(s or '')

    high_risk = sum(1 for r in items if _get_risk(r) >= 0.7)
    active_reviews = sum(1 for r in items if _get_status(r) in ("in_review", "ai_analyzed", "pending_approval", "exec_approval", "legal_approval", "escalated"))
    pending = sum(1 for r in items if _get_status(r) == "draft")
    scores = [_get_risk(r) * 10 for r in items if _get_risk(r) > 0]

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
async def list_saved_views(
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
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
