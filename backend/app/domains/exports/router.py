"""Export API router — generate and download review reports, audit exports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.exports.schemas import ExportFormat
from app.domains.exports.service import ExportService

router = APIRouter(prefix="/exports", tags=["Exports"])


async def get_export_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ExportService:
    return ExportService(session=db, tenant_id=tenant_id)


@router.get("/reviews/{review_id}")
async def export_review_report(
    review_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    include_findings: bool = Query(True),
    include_redlines: bool = Query(True),
    include_evidence: bool = Query(False),
    include_activity: bool = Query(False),
    service: ExportService = Depends(get_export_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Export a review report as PDF or DOCX.

    Generates a comprehensive report including findings, redlines,
    evidence, and activity timeline.
    """
    try:
        fmt = ExportFormat(format)
        file_bytes, filename, content_type = await service.generate_review_report(
            review_id=review_id, fmt=fmt,
            include_findings=include_findings,
            include_redlines=include_redlines,
            include_evidence=include_evidence,
            include_activity=include_activity,
        )
        return Response(
            content=file_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(file_bytes)),
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}")


@router.get("/audit")
async def export_audit_report(
    period_days: int = Query(30, ge=1, le=365),
    service: ExportService = Depends(get_export_service),
    _: None = Depends(require_permission(Permissions.AUDIT_EXPORT)),
):
    """Export an audit report as PDF.

    Includes aggregated event summary and full event listing
    for the specified period.
    """
    try:
        file_bytes, filename, content_type = await service.generate_audit_report(
            period_days=period_days,
        )
        return Response(
            content=file_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(file_bytes)),
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audit export failed: {exc}")
