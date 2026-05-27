"""Batch upload service — orchestrates multi-file upload operations.

Manages the BatchUpload lifecycle: create, track per-file progress,
compute aggregate status, and handle cancellation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ingestion.batch_models import BatchUpload, BatchStatus
from app.domains.ingestion.models import UploadSession, IngestionState


class BatchUploadService:
    """Service layer for batch upload operations."""

    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self._db = db
        self._tenant_id = tenant_id
        self._user_id = user_id

    async def create_batch(self, name: Optional[str] = None) -> BatchUpload:
        """Create a new batch upload container."""
        batch = BatchUpload(
            batch_id=uuid.uuid4(),
            tenant_id=uuid.UUID(self._tenant_id),
            user_id=self._user_id,
            name=name or f"Batch upload {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            status=BatchStatus.PENDING,
            total_files=0,
            completed_files=0,
            failed_files=0,
            total_bytes=0,
        )
        self._db.add(batch)
        await self._db.flush()
        return batch

    async def get_batch(self, batch_id: uuid.UUID) -> Optional[BatchUpload]:
        """Get a batch by ID (scoped to tenant)."""
        result = await self._db.execute(
            select(BatchUpload).where(
                BatchUpload.batch_id == batch_id,
                BatchUpload.tenant_id == uuid.UUID(self._tenant_id),
            )
        )
        return result.scalar_one_or_none()

    async def list_batches(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[BatchStatus] = None,
    ) -> tuple[list[BatchUpload], int]:
        """List batches for the tenant with pagination."""
        query = select(BatchUpload).where(
            BatchUpload.tenant_id == uuid.UUID(self._tenant_id),
        )
        count_query = select(func.count()).select_from(BatchUpload).where(
            BatchUpload.tenant_id == uuid.UUID(self._tenant_id),
        )

        if status_filter:
            query = query.where(BatchUpload.status == status_filter)
            count_query = count_query.where(BatchUpload.status == status_filter)

        # Get total count
        total_result = await self._db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        result = await self._db.execute(
            query.order_by(BatchUpload.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        batches = list(result.scalars().all())
        return batches, total

    async def get_batch_files(self, batch_id: uuid.UUID) -> list[UploadSession]:
        """Get all upload sessions associated with a batch."""
        result = await self._db.execute(
            select(UploadSession).where(
                UploadSession.batch_id == batch_id,
                UploadSession.tenant_id == uuid.UUID(self._tenant_id),
            ).order_by(UploadSession.created_at)
        )
        return list(result.scalars().all())

    async def link_upload_to_batch(
        self, upload_id: uuid.UUID, batch_id: uuid.UUID, file_size: int
    ) -> None:
        """Associate an upload session with a batch and update counters."""
        # Update the upload session with batch_id
        await self._db.execute(
            update(UploadSession).where(
                UploadSession.upload_id == upload_id,
            ).values(batch_id=batch_id)
        )
        # Update batch counters
        await self._db.execute(
            update(BatchUpload).where(
                BatchUpload.batch_id == batch_id,
            ).values(
                total_files=BatchUpload.total_files + 1,
                total_bytes=BatchUpload.total_bytes + file_size,
                status=BatchStatus.UPLOADING,
            )
        )

    async def update_file_status(
        self, upload_id: uuid.UUID, new_state: IngestionState, error: Optional[str] = None
    ) -> None:
        """Update per-file status and recalculate batch aggregate status."""
        # Get the upload to find its batch
        result = await self._db.execute(
            select(UploadSession).where(UploadSession.upload_id == upload_id)
        )
        upload = result.scalar_one_or_none()
        if not upload or not upload.batch_id:
            return

        batch_id = upload.batch_id
        is_terminal = new_state in (
            IngestionState.REVIEW_READY, IngestionState.FAILED,
            IngestionState.CANCELLED, IngestionState.QUARANTINED,
        )
        is_success = new_state == IngestionState.REVIEW_READY
        is_failure = new_state in (IngestionState.FAILED, IngestionState.CANCELLED, IngestionState.QUARANTINED)

        if is_terminal:
            if is_success:
                await self._db.execute(
                    update(BatchUpload).where(BatchUpload.batch_id == batch_id).values(
                        completed_files=BatchUpload.completed_files + 1,
                    )
                )
            elif is_failure:
                await self._db.execute(
                    update(BatchUpload).where(BatchUpload.batch_id == batch_id).values(
                        failed_files=BatchUpload.failed_files + 1,
                    )
                )

            # Recalculate overall batch status
            await self._recalculate_batch_status(batch_id)

    async def _recalculate_batch_status(self, batch_id: uuid.UUID) -> None:
        """Recalculate aggregate batch status based on all file states."""
        result = await self._db.execute(
            select(BatchUpload).where(BatchUpload.batch_id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if not batch:
            return

        total = batch.total_files
        completed = batch.completed_files
        failed = batch.failed_files

        if total == 0:
            new_status = BatchStatus.PENDING
        elif completed == total:
            new_status = BatchStatus.COMPLETED
        elif failed == total:
            new_status = BatchStatus.FAILED
        elif completed + failed >= total:
            new_status = BatchStatus.PARTIAL
        else:
            new_status = BatchStatus.PROCESSING

        values = {"status": new_status}
        if new_status in (BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.PARTIAL):
            values["completed_at"] = datetime.now(timezone.utc)

        await self._db.execute(
            update(BatchUpload).where(BatchUpload.batch_id == batch_id).values(**values)
        )

    async def cancel_batch(self, batch_id: uuid.UUID) -> bool:
        """Cancel a batch and all pending uploads within it."""
        batch = await self.get_batch(batch_id)
        if not batch or batch.status in (BatchStatus.COMPLETED, BatchStatus.CANCELLED):
            return False

        await self._db.execute(
            update(BatchUpload).where(BatchUpload.batch_id == batch_id).values(
                status=BatchStatus.CANCELLED,
                completed_at=datetime.now(timezone.utc),
            )
        )
        # Cancel all non-terminal uploads in the batch
        await self._db.execute(
            update(UploadSession).where(
                UploadSession.batch_id == batch_id,
                UploadSession.ingestion_state == IngestionState.UPLOADED,
            ).values(ingestion_state=IngestionState.CANCELLED)
        )
        return True
