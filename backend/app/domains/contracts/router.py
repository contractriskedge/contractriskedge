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
from datetime import datetime, timedelta, timezone
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

    The frontend Repository view relies on this mapping to surface
    *meaningful* contract identity (vendor, contract number, type,
    financial value, owner, etc.) drawn from `document_metadata`,
    not the raw upload filename.  The filename is kept as a fallback
    for legacy data and is also exposed as `originalFilename`.
    """
    def __init__(self, review, filename: str = "") -> None:
        # Support both dict and object access patterns
        def _get(key: str, default=None):
            if isinstance(review, dict):
                return review.get(key, default)
            return getattr(review, key, default)

        # Pull structured metadata (vendor, contract name, etc.)
        doc_md = _get('document_metadata', None) or _get('metadata', None) or {}
        if not isinstance(doc_md, dict):
            doc_md = {}

        # Identity
        self.id = str(_get('review_id', ''))
        meta_name = (doc_md.get('name') or '').strip()
        self.name = meta_name or (filename or _get('document_name', '') or 'Untitled Contract')
        self.originalFilename = filename or _get('document_name', '') or ''
        # Contract number: prefer stored value, fall back to auto-generate from review_id
        self.contractNumber = (doc_md.get('contract_number') or '').strip()
        if not self.contractNumber:
            # Generate a fallback number from the upload date and review_id suffix
            created = _get('created_at', None)
            date_part = created[:10].replace('-', '')[:6] if created else '000000'
            suffix = str(_get('review_id', ''))[-4:] or '0000'
            self.contractNumber = f"C{date_part}-{suffix}"
        self.contractType = (doc_md.get('contract_type') or 'contract').strip()
        self.vendor = (doc_md.get('vendor') or '').strip()
        self.businessUnit = (doc_md.get('business_unit') or '').strip()
        self.geography = (doc_md.get('geography') or '').strip()
        self.department = (doc_md.get('department') or self.businessUnit or '').strip()
        self.description = (doc_md.get('description') or '').strip()
        self.tags = doc_md.get('tags') or []

        # risk_score is a top-level field in the review response (0-1 float)
        raw_risk = _get('risk_score', None)
        if raw_risk is None:
            raw_risk = doc_md.get('risk_score', None)
        self.riskScore = min(10, round((raw_risk or 0) * 10))
        self.riskLevel = _risk_level(self.riskScore)

        # Financials
        fv = doc_md.get('financial_value', 0) or 0
        try:
            fv = float(fv)
        except (TypeError, ValueError):
            fv = 0
        self.financialValue = fv
        self.currency = (doc_md.get('currency') or 'USD').strip() or 'USD'

        # Status / workflow
        status = _get('status', None)
        status_str = status.value if hasattr(status, 'value') else str(status or 'draft')
        self.reviewStatus = status_str
        self.status = _map_status(status_str)
        self.expiryDate = (doc_md.get('expiration_date') or '')[:10]
        self.renewalDate = (doc_md.get('renewal_date') or '')[:10]
        self.effectiveDate = (doc_md.get('effective_date') or '')[:10]
        self.lastReviewDate = (doc_md.get('last_review_date') or '')[:10]
        self.autoRenew = bool(doc_md.get('auto_renew', False))

        # Top risk / AI
        self.topRisk = _get('rejection_reason', '') or doc_md.get('top_risk', '') or ''
        self.aiConfidence = min(
            100, max(0, round((raw_risk or 0) * 100 if raw_risk else (doc_md.get('ai_confidence', 0) or 0) * 100))
        )

        # Owner / workflow
        owner_name = (doc_md.get('owner') or '').strip()
        owner_id = (doc_md.get('owner_id') or '').strip()
        assignee = _get('assigned_to', None)
        self.owner = owner_name or assignee or _get('created_by', '') or ""
        self.ownerId = owner_id or (assignee or "")
        self.workflowStage = _get('workflow_stage', None) or _map_workflow(status_str)
        self.lastModified = _fmt_date(_get('updated_at', None))
        self.createdAt = _fmt_date(_get('created_at', None))

        # Counts
        self.clauseCount = _get('finding_count', 0) or 0
        self.aiFindingsCount = _get('finding_count', 0) or 0
        self.openFindings = _get('open_finding_count', 0) or 0
        self.missingClauses = []
        self.aiFlags = _derive_flags(raw_risk)
        self.obligationsDue = 0
        self.slaCompliant = _get('sla_breached', False) is not True
        self.slaStatus = _get('sla_status', 'on_track') or 'on_track'
        self.slaDeadline = _fmt_date(_get('sla_deadline', None))
        self.hasRedlines = bool(_get('redline_count', 0))

        # Health bucket — what the Repository uses to color-code rows
        self.health = _derive_health(doc_md, self.riskScore, self.expiryDate, self.slaCompliant)

        # AI summary
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

        self.hasDpa = bool(doc_md.get('has_dpa', False))
        self.totalPages = _get('total_pages', 0) or doc_md.get('total_pages', 0) or 0


def _derive_health(doc_md: dict, risk_score: int, expiry_date: str, sla_compliant: bool) -> str:
    """Bucket a contract's overall health for the Repository row indicator.

    Returns one of: 'healthy', 'needs_review', 'high_risk', 'expired', 'expiring_soon'.
    """
    # Expired / expiring soon check
    today = datetime.now(timezone.utc).date().isoformat()
    if expiry_date and expiry_date < today:
        return "expired"
    if expiry_date:
        try:
            exp = datetime.fromisoformat(expiry_date).date()
            days = (exp - datetime.now(timezone.utc).date()).days
            if 0 <= days <= 90:
                return "expiring_soon"
        except (TypeError, ValueError):
            pass

    if risk_score >= 8:
        return "high_risk"
    if risk_score >= 5:
        return "needs_review"
    if not sla_compliant:
        return "needs_review"
    return "healthy"


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
        "closed": "closed",
        "archived": "archived",
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
        "closed": "closed",
        "archived": "archived",
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

    # Apply client-side search across name, vendor, contract number, and filename
    if search:
        q = search.lower()
        def _matches(r) -> bool:
            md = getattr(r, 'document_metadata', None) or {}
            if not isinstance(md, dict):
                md = {}
            haystacks = [
                (md.get('name') or ''),
                (md.get('vendor') or ''),
                (md.get('contract_number') or ''),
                (md.get('contract_type') or ''),
                (getattr(r, '_document_filename', '') or ''),
                (getattr(r, 'document_name', '') or ''),
            ]
            return any(q in s.lower() for s in haystacks if s)
        items = [r for r in items if _matches(r)]
        # Search is post-pagination; the total reflects the filtered set
        # so the front-end's "X of N" stays accurate.
        total = len(items)

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

    # Expiring within 90 days
    today = datetime.now(timezone.utc).date()
    horizon = today + timedelta(days=90)
    expiring_soon = 0
    total_value = 0.0
    total_value_at_risk = 0.0
    for r in items:
        md = getattr(r, 'document_metadata', None) or {}
        if not isinstance(md, dict):
            md = {}
        fv = float(md.get('financial_value', 0) or 0)
        total_value += fv
        if _get_risk(r) >= 0.7:
            total_value_at_risk += fv
        exp = md.get('expiration_date') or ''
        if exp:
            try:
                exp_d = datetime.fromisoformat(exp[:10]).date()
                if today <= exp_d <= horizon:
                    expiring_soon += 1
            except (TypeError, ValueError):
                pass

    return {
        "total_contracts": total,
        "active_reviews": active_reviews,
        "pending_reviews": pending,
        "high_risk_count": high_risk,
        "expiring_soon": expiring_soon,
        "avg_risk_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "total_value_at_risk": total_value_at_risk,
        "total_portfolio_value": total_value,
    }


@router.get("/views", response_model=None)
async def list_saved_views(
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Placeholder for saved views — returns empty list until feature is backend-backed."""
    return []


@router.get("/search-select", response_model=None)
async def search_contracts_for_select(
    q: str = Query("", min_length=0, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ReviewService = Depends(get_review_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Lightweight contract search for the obligation creation contract selector.

    Returns id, name, contract_number, vendor, risk_level for each match.
    Searches by contract name, contract number, vendor, and counterparty.
    """
    from app.domains.review.schemas import ReviewFilterParams
    filters = ReviewFilterParams(page=1, page_size=100)
    items, total = await service.list_reviews(filters)

    results = []
    q_lower = q.lower() if q else ""
    for r in items:
        md = getattr(r, 'document_metadata', None) or {}
        if not isinstance(md, dict):
            md = {}
        # Use filename from the joined UploadSession, then metadata name, then fallback
        filename = getattr(r, '_document_filename', None) or ''
        name = (md.get('name') or filename or '').strip()
        contract_number = (md.get('contract_number') or '').strip()
        vendor = (md.get('vendor') or '').strip()
        counterparty = (md.get('counterparty') or '').strip()

        # Filter by search query
        if q_lower:
            haystack = f"{name} {contract_number} {vendor} {counterparty}".lower()
            if q_lower not in haystack:
                continue

        review_id = str(getattr(r, 'review_id', ''))
        raw_risk = md.get('risk_score', 0)
        try:
            raw_risk = float(raw_risk) if raw_risk else 0
        except (TypeError, ValueError):
            raw_risk = 0
        risk_score = min(10, round(raw_risk * 10))
        risk_level = "critical" if risk_score >= 8 else "high" if risk_score >= 6 else "medium" if risk_score >= 4 else "low"

        results.append({
            "id": review_id,
            "name": name or f"Contract {review_id[:8]}",
            "contract_number": contract_number,
            "vendor": vendor,
            "counterparty": counterparty,
            "risk_level": risk_level,
            "risk_score": risk_score,
        })

    return {
        "data": results,
        "total": len(results),
    }


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
