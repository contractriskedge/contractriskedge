"""Export API endpoints for DOCX tracked-changes and PDF markup export.

Provides endpoints for exporting redline suggestions as DOCX with
native Word tracked changes and PDF with highlighted annotations.
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/redlines/{suggestion_id}/docx")
async def export_redline_docx(
    suggestion_id: str,
    include_original: bool = Query(True, description="Include original text"),
    include_rationale: bool = Query(True, description="Include rationale comments"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.EXPORT_DATA)),
):
    """Export a redline suggestion as DOCX with tracked changes.

    Args:
        suggestion_id: The redline suggestion to export.
        include_original: Whether to include original text for comparison.
        include_rationale: Whether to include rationale as comments.
        user: Authenticated user.

    Returns:
        DOCX file with tracked changes.

    Raises:
        HTTPException: If suggestion not found or export fails.
    """
    from redline.models import RedlineSuggestion
    from redline.diff_engine import DiffEngine

    # Get suggestion from in-memory store
    from routers.redlines import _redline_suggestions

    suggestion = _redline_suggestions.get(suggestion_id)
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suggestion {suggestion_id} not found",
        )

    try:
        from export.docx_exporter import DocxExporter

        exporter = DocxExporter()
        result = exporter.export_redline(
            suggestion=suggestion,
            include_original=include_original,
            include_rationale=include_rationale,
        )

        if not result.success or not result.file_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Export failed",
            )

        return StreamingResponse(
            io.BytesIO(result.file_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="redline_{suggestion_id[:8]}.docx"',
            },
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="DOCX export module not available. Install python-docx.",
        )
    except Exception as exc:
        logger.error("DOCX export failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {exc}",
        )


@router.get("/redlines/{suggestion_id}/pdf")
async def export_redline_pdf(
    suggestion_id: str,
    include_summary: bool = Query(True, description="Include executive summary page"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.EXPORT_DATA)),
):
    """Export a redline suggestion as PDF with markup annotations.

    Args:
        suggestion_id: The redline suggestion to export.
        include_summary: Whether to include an executive summary page.
        user: Authenticated user.

    Returns:
        PDF file with highlighted markup.

    Raises:
        HTTPException: If suggestion not found or export fails.
    """
    from redline.models import RedlineSuggestion

    from routers.redlines import _redline_suggestions

    suggestion = _redline_suggestions.get(suggestion_id)
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suggestion {suggestion_id} not found",
        )

    try:
        from export.pdf_exporter import PdfExporter

        exporter = PdfExporter()
        result = exporter.export_redline(
            suggestion=suggestion,
            include_summary=include_summary,
        )

        if not result.success or not result.file_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Export failed",
            )

        return StreamingResponse(
            io.BytesIO(result.file_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="redline_{suggestion_id[:8]}.pdf"',
            },
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF export module not available. Install PyMuPDF.",
        )
    except Exception as exc:
        logger.error("PDF export failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {exc}",
        )


@router.get("/audit/csv")
async def export_audit_csv(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601)"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.EXPORT_AUDIT)),
):
    """Export audit logs as CSV.

    Args:
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        action: Optional action type filter.
        user: Authenticated user.

    Returns:
        CSV file with audit log entries.
    """
    from middleware.audit_log import HashChainedAuditLog

    audit = HashChainedAuditLog()

    entries = audit.query(
        tenant_id=user.tenant_id or "default",
        action=action,
        start_time=start_date,
        end_time=end_date,
        limit=10000,
    )

    csv_content = audit.export_csv(entries)

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="audit_log_{user.tenant_id or "default"}.csv"',
        },
    )


@router.get("/benchmarks/csv")
async def export_benchmarks_csv(
    clause_type: Optional[str] = Query(None, description="Filter by clause type"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.EXPORT_DATA)),
):
    """Export benchmark corpus as CSV.

    Args:
        clause_type: Optional clause type filter.
        user: Authenticated user.

    Returns:
        CSV file with benchmark clauses.
    """
    from benchmarking.corpus_ingestion import CorpusIngestionPipeline

    pipeline = CorpusIngestionPipeline()
    clauses = pipeline.get_clauses_by_type(clause_type) if clause_type else list(pipeline._corpus.values())

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["clause_id", "clause_type", "contract_type", "industry",
                      "counterparty_type", "quality_score", "clause_text"])

    for c in clauses:
        writer.writerow([
            c.clause_id, c.clause_type, c.contract_type.value,
            c.industry.value, c.counterparty_type.value,
            c.quality_score, c.clause_text[:500],
        ])

    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=benchmark_corpus.csv"},
    )


@router.post("/batch")
async def export_batch_redlines(
    suggestion_ids: List[str] = Query(..., description="List of redline suggestion IDs to export (max 20)"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.EXPORT_DATA)),
):
    """Export multiple redline suggestions as a ZIP archive of DOCX files.

    Args:
        suggestion_ids: List of redline suggestion IDs (max 20).
        user: Authenticated user.

    Returns:
        ZIP file containing DOCX files with tracked changes.

    Raises:
        HTTPException: If suggestions not found or batch export fails.
    """
    if not suggestion_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No suggestion IDs provided",
        )

    if len(suggestion_ids) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch export limited to 20 suggestions, got {len(suggestion_ids)}",
        )

    from routers.redlines import _redline_suggestions

    # Group suggestions by document
    contracts: Dict[str, List[Any]] = {}
    for sid in suggestion_ids:
        suggestion = _redline_suggestions.get(sid)
        if suggestion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Suggestion {sid} not found",
            )
        doc_name = getattr(suggestion, "document_name", "unknown") or "unknown"
        if doc_name not in contracts:
            contracts[doc_name] = []
        contracts[doc_name].append(suggestion)

    try:
        from export.batch_exporter import BatchExporter

        exporter = BatchExporter()
        result = exporter.export_batch(contracts)

        if not result.success or not result.zip_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Batch export failed",
            )

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return StreamingResponse(
            io.BytesIO(result.zip_bytes),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="redlines_batch_{ts}.zip"',
            },
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="DOCX export module not available. Install python-docx.",
        )
    except Exception as exc:
        logger.error("Batch export failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch export failed: {exc}",
        )


@router.get("/procurement/csv")
async def export_procurement_csv(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.EXPORT_DATA)),
):
    """Export vendor procurement comparison data as CSV.

    Args:
        user: Authenticated user.

    Returns:
        CSV file with vendor risk comparison data.
    """
    import csv
    import io as io_module
    from datetime import datetime, timezone

    # Fetch contracts with vendor metadata from the database
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev",
    )
    engine = create_async_engine(database_url)
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT contract_id, filename, contract_type, metadata, created_at
                    FROM contracts
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                """),
                {"tenant_id": user.tenant_id or "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
            )
            rows = result.fetchall()
    finally:
        await engine.dispose()

    output = io_module.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Vendor", "Contract", "Type", "Risk Score", "Contract Value", "Created Date", "Status"])

    for row in rows:
        row_dict = dict(row._mapping)
        meta_str = row_dict.get("metadata", "{}")
        try:
            meta = json.loads(meta_str) if isinstance(meta_str, str) else meta_str
        except (json.JSONDecodeError, TypeError):
            meta = {}
        
        vendor = meta.get("vendor") or meta.get("counterparty") or "Unknown"
        value = meta.get("value_usd", 0)
        value_str = f"${value:,}" if value else "N/A"
        
        writer.writerow([
            vendor,
            row_dict.get("filename", ""),
            row_dict.get("contract_type", ""),
            "",  # Risk score placeholder
            value_str,
            str(row_dict.get("created_at", ""))[:10],
            row_dict.get("status", ""),
        ])

    return StreamingResponse(
        io_module.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=procurement_vendors.csv"},
    )
