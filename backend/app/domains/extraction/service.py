"""OCR orchestration service — manages extraction pipeline and state transitions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.domains.extraction.models import ExtractionRun, ExtractionMethod, ExtractionStatus
from app.domains.extraction.parsers import parser_registry, ExtractionResult, ExtractedPage
from app.domains.extraction.quality import quality_evaluator, QualityScore
from app.domains.extraction.normalizer import normalize_text
from app.domains.extraction.repository import ExtractionRepository
from app.domains.ingestion.models import IngestionState
from app.domains.ingestion.repository import IngestionRepository
from app.integrations.storage.s3 import storage_service
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)


@dataclass
class ExtractionService:
    """Orchestrates document extraction, OCR, and quality evaluation."""

    extraction_repo: ExtractionRepository
    ingestion_repo: IngestionRepository
    event_bus: EventBus
    user: UserContext
    tenant_id: str

    async def run_extraction(self, upload_id: str) -> ExtractionResult:
        """Run full extraction pipeline: detect type → parse → normalize → score."""
        upload = await self.ingestion_repo.get_upload(upload_id, self.tenant_id)
        if not upload:
            raise ValueError(f"Upload not found: {upload_id}")

        # Create extraction run record
        run = await self.extraction_repo.create_run(
            upload_id=upload_id, tenant_id=self.tenant_id, method=ExtractionMethod.PYMUPDF_DIRECT,
        )

        # Download file from storage
        file_data = await storage_service.download_fileobj(
            upload.storage_bucket or "contractrisk-documents",
            upload.storage_key or "",
        )

        # Select parser
        parser = parser_registry.get_parser(upload.content_type, file_data)
        if not parser:
            raise ValueError(f"No parser found for content type: {upload.content_type}")

        # Extract text
        result = parser.extract(file_data, upload.filename)

        # Normalize text
        for page in result.pages:
            page.text = normalize_text(page.text)

        # Evaluate quality
        quality = quality_evaluator.evaluate(result)

        # Store pages
        for page in result.pages:
            await self.extraction_repo.store_page(
                upload_id=upload_id,
                tenant_id=self.tenant_id,
                page=page,
                method=result.method,
            )

        # Update run record
        await self.extraction_repo.complete_run(
            run_id=run.run_id,
            result=result,
            quality=quality,
        )

        return result

    async def handle_quality_result(
        self, upload_id: str, result: ExtractionResult, quality: QualityScore,
    ) -> IngestionState:
        """Determine next ingestion state based on extraction quality."""
        if quality.is_acceptable:
            await self.ingestion_repo.update_state(
                upload_id, self.tenant_id, IngestionState.OCR_COMPLETE,
            )
            return IngestionState.OCR_COMPLETE

        # Check if OCR fallback might help
        if result.method in ("pymupdf_direct",) and result.ocr_required is not False:
            await self.ingestion_repo.update_state(
                upload_id, self.tenant_id, IngestionState.OCR_PENDING,
                error=f"Quality below threshold: {quality.rejection_reason}",
            )
            return IngestionState.OCR_PENDING

        # Quarantine if quality is unacceptable and OCR won't help
        await self.ingestion_repo.update_state(
            upload_id, self.tenant_id, IngestionState.QUARANTINED,
            error=f"Extraction quality unacceptable: {quality.rejection_reason}",
        )
        return IngestionState.QUARANTINED
