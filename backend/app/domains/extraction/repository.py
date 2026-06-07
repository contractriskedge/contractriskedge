"""Extraction repository — data access for document pages, extraction runs, and failures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.repository.base import BaseRepository
from app.domains.extraction.models import (
    DocumentPage,
    ExtractionRun,
    ExtractionFailure,
    ExtractionMethod,
    ExtractionStatus,
)
from app.domains.extraction.parsers import ExtractionResult, ExtractedPage
from app.domains.extraction.quality import QualityScore


@dataclass
class ExtractionRepository(BaseRepository):

    async def create_run(
        self, upload_id: str, tenant_id: str, method: ExtractionMethod,
    ) -> ExtractionRun:
        run = ExtractionRun(
            upload_id=upload_id,
            tenant_id=tenant_id,
            method=method,
            status=ExtractionStatus.PROCESSING,
            started_at=datetime.utcnow(),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def complete_run(
        self, run_id: str, result: ExtractionResult, quality: QualityScore,
    ) -> None:
        stmt = (
            update(ExtractionRun)
            .where(ExtractionRun.run_id == run_id)
            .values(
                status=ExtractionStatus.COMPLETED,
                total_pages=result.total_pages,
                pages_extracted=len(result.pages),
                total_chars=result.total_chars,
                avg_confidence=result.avg_confidence,
                ocr_required=result.ocr_required,
                ocr_engine_used=result.ocr_engine_used,
                total_processing_time_ms=result.total_processing_time_ms,
                completed_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)

    async def store_page(
        self, upload_id: str, tenant_id: str, page: ExtractedPage, method: str,
    ) -> DocumentPage:
        # Idempotency check: skip if this page already exists for this upload.
        # Prevents IntegrityError from uq_page_per_upload constraint when
        # extraction tasks are accidentally duplicated.
        existing = await self.session.execute(
            select(DocumentPage).where(
                DocumentPage.upload_id == upload_id,
                DocumentPage.tenant_id == tenant_id,
                DocumentPage.page_number == page.page_number,
            )
        )
        existing_page = existing.scalar_one_or_none()
        if existing_page is not None:
            return existing_page

        doc_page = DocumentPage(
            upload_id=upload_id,
            tenant_id=tenant_id,
            page_number=page.page_number,
            text=page.text,
            text_length=len(page.text),
            extraction_method=method,
            extraction_status=ExtractionStatus.COMPLETED,
            ocr_confidence=page.confidence,
            char_count=page.char_count,
            word_count=page.word_count,
            symbol_count=page.symbol_count,
            has_text_layer=page.has_text_layer,
            page_width_pts=page.width_pts,
            page_height_pts=page.height_pts,
            rotation_degrees=page.rotation_degrees,
            processing_time_ms=page.processing_time_ms,
        )
        self.session.add(doc_page)
        await self.session.flush()
        return doc_page

    async def get_pages_by_upload(self, upload_id: str, tenant_id: str):
        stmt = (
            select(DocumentPage)
            .where(DocumentPage.upload_id == upload_id, DocumentPage.tenant_id == tenant_id)
            .order_by(DocumentPage.page_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_pages(self, upload_id: str, tenant_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(DocumentPage)
            .where(DocumentPage.upload_id == upload_id, DocumentPage.tenant_id == tenant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def record_failure(
        self, upload_id: str, tenant_id: str, failure_type: str,
        error_message: str, page_number: Optional[int] = None,
        method_attempted: Optional[str] = None,
    ) -> ExtractionFailure:
        failure = ExtractionFailure(
            upload_id=upload_id,
            tenant_id=tenant_id,
            page_number=page_number,
            failure_type=failure_type,
            error_message=error_message,
            method_attempted=method_attempted,
        )
        self.session.add(failure)
        await self.session.flush()
        return failure
