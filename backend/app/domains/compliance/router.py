"""Compliance domain API router — frameworks, controls, assessments, findings, exceptions, evidence."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.compliance.schemas import (
    ComplianceFrameworkCreate, ComplianceFrameworkResponse,
    ComplianceControlCreate, ComplianceControlResponse,
    ComplianceAssessmentCreate, ComplianceAssessmentResponse,
    ComplianceFindingCreate, ComplianceFindingResponse,
    ComplianceExceptionCreate, ComplianceExceptionResponse,
    ComplianceEvidenceCreate, ComplianceEvidenceResponse,
    PaginatedResponse, PaginationMeta,
)
from app.domains.compliance.service import ComplianceRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["Compliance"])


async def get_repo(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ComplianceRepository:
    return ComplianceRepository(db, tenant_id=tenant_id)


# ── Frameworks ─────────────────────────────────────────────────────


@router.get("/frameworks", response_model=PaginatedResponse)
async def list_frameworks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List compliance frameworks."""
    items, total = await repo.list_frameworks(page=page, page_size=page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.post("/frameworks", response_model=ComplianceFrameworkResponse, status_code=201)
async def create_framework(
    body: ComplianceFrameworkCreate,
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new compliance framework."""
    return await repo.create_framework(body.model_dump())


# ── Controls ───────────────────────────────────────────────────────


@router.get("/controls", response_model=PaginatedResponse)
async def list_controls(
    framework_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List compliance controls, optionally filtered by framework."""
    items, total = await repo.list_controls(framework_id=framework_id, page=page, page_size=page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.post("/controls", response_model=ComplianceControlResponse, status_code=201)
async def create_control(
    body: ComplianceControlCreate,
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new compliance control."""
    return await repo.create_control(body.model_dump())


# ── Assessments ────────────────────────────────────────────────────


@router.get("/assessments", response_model=PaginatedResponse)
async def list_assessments(
    framework_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List compliance assessments."""
    items, total = await repo.list_assessments(framework_id=framework_id, page=page, page_size=page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.post("/assessments", response_model=ComplianceAssessmentResponse, status_code=201)
async def create_assessment(
    body: ComplianceAssessmentCreate,
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new compliance assessment."""
    return await repo.create_assessment(body.model_dump())


# ── Findings ───────────────────────────────────────────────────────


@router.get("/findings", response_model=PaginatedResponse)
async def list_findings(
    assessment_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List compliance findings with optional filters."""
    items, total = await repo.list_findings(
        assessment_id=assessment_id, status=status, severity=severity,
        page=page, page_size=page_size,
    )
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.post("/findings", response_model=ComplianceFindingResponse, status_code=201)
async def create_finding(
    body: ComplianceFindingCreate,
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new compliance finding."""
    return await repo.create_finding(body.model_dump())


# ── Exceptions ─────────────────────────────────────────────────────


@router.get("/exceptions", response_model=PaginatedResponse)
async def list_exceptions(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List compliance exceptions."""
    items, total = await repo.list_exceptions(status=status, page=page, page_size=page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.post("/exceptions", response_model=ComplianceExceptionResponse, status_code=201)
async def create_exception(
    body: ComplianceExceptionCreate,
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new compliance exception."""
    return await repo.create_exception(body.model_dump())


# ── Evidence ───────────────────────────────────────────────────────


@router.get("/evidence", response_model=PaginatedResponse)
async def list_evidence(
    framework: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List compliance evidence."""
    items, total = await repo.list_evidence(framework=framework, page=page, page_size=page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.post("/evidence", response_model=ComplianceEvidenceResponse, status_code=201)
async def create_evidence(
    body: ComplianceEvidenceCreate,
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new compliance evidence record."""
    return await repo.create_evidence(body.model_dump())


# ── Scan ───────────────────────────────────────────────────────────


class ComplianceScanResponse(BaseModel):
    frameworks_scanned: int
    controls_evaluated: int
    new_findings: int
    updated_findings: int
    compliance_score: float
    frameworks: list[dict[str, Any]]


@router.post("/scan", response_model=ComplianceScanResponse)
async def run_compliance_scan(
    repo: ComplianceRepository = Depends(get_repo),
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Run a full compliance scan across all active frameworks.

    Evaluates controls, creates findings for gaps, updates assessments,
    and returns a summary of results.
    """
    result = await repo.run_scan(created_by=current_user.id or "system")
    return ComplianceScanResponse(**result)


# ── Dashboard ──────────────────────────────────────────────────────


@router.get("/dashboard")
async def compliance_dashboard(
    repo: ComplianceRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get compliance dashboard summary with KPIs."""
    frameworks, fw_total = await repo.list_frameworks(page_size=100)
    findings, f_total = await repo.list_findings(page_size=100)
    assessments, a_total = await repo.list_assessments(page_size=100)

    open_findings = sum(1 for f in findings if f["status"] == "open")
    critical_findings = sum(1 for f in findings if f["severity"] == "critical")
    completed_assessments = sum(1 for a in assessments if a["status"] == "completed")
    avg_score = None
    if completed_assessments > 0:
        scores = [a["score"] for a in assessments if a["status"] == "completed" and a["score"] is not None]
        if scores:
            avg_score = sum(scores) / len(scores)

    return {
        "frameworks": fw_total,
        "controls": sum(f.get("control_count", 0) for f in frameworks),
        "open_findings": open_findings,
        "critical_findings": critical_findings,
        "total_findings": f_total,
        "assessments": a_total,
        "completed_assessments": completed_assessments,
        "compliance_score": avg_score,
    }
