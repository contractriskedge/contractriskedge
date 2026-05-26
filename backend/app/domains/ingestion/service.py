"""Ingestion orchestration service — manages upload lifecycle and pipeline state machine."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.config import settings
from app.domains.ingestion.models import IngestionState, UploadSession
from app.domains.ingestion.repository import IngestionRepository
from app.domains.ingestion.schemas import UploadInitiateRequest
from app.domains.ingestion.security import (
    validate_extension,
    validate_content_type,
    validate_file_size,
    validate_filename_safety,
    FileValidationError,
)
from app.domains.ingestion.exceptions import (
    UploadNotFoundError,
    IngestionStateTransitionError,
    FileTypeNotAllowedError,
    FileTooLargeError,
    IngestionRetryLimitExceededError,
)
from app.domains.ingestion.events import (
    UploadInitiated,
    UploadCompleted,
    UploadFailed,
    UploadCancelled,
    IngestionStatusChanged,
)
from app.integrations.storage.s3 import storage_service, StorageServiceError
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext
from app.kernel.security.events import (
    log_security_event,
    SecurityEventType,
    SecurityEventSeverity,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


@dataclass
class IngestionService:
    """Orchestrates the upload and ingestion lifecycle."""

    repository: IngestionRepository
    event_bus: EventBus
    user: UserContext
    tenant_id: str

    async def initiate_upload(self, request: UploadInitiateRequest) -> dict:
        """Initiate a new upload session with validation and presigned URL generation."""
        # 1. Validate
        safe_filename = validate_filename_safety(request.filename)
        detected_type = validate_extension(safe_filename)
        if detected_type != request.content_type:
            raise FileTypeNotAllowedError(
                f"Declared content type '{request.content_type}' does not match "
                f"detected type '{detected_type}' for extension"
            )
        validate_content_type(request.content_type)
        validate_file_size(request.file_size)

        # 1b. Content-based deduplication: skip if same checksum already processed
        if request.client_checksum_sha256:
            existing = await self.repository.get_upload_by_checksum(
                self.tenant_id, request.client_checksum_sha256,
            )
            if existing and existing.ingestion_state in (
                IngestionState.OCR_COMPLETE,
                IngestionState.CHUNKING_COMPLETE,
                IngestionState.EMBEDDING_COMPLETE,
                IngestionState.ANALYSIS_COMPLETE,
            ):
                logger.info(
                    "Duplicate upload detected (checksum %s): reusing upload %s",
                    request.client_checksum_sha256[:16], existing.upload_id,
                )
                return {
                    "upload_id": str(existing.upload_id),
                    "duplicate": True,
                    "message": "This file has already been uploaded and processed.",
                }

        # 2. Create upload session
        upload = await self.repository.create_upload(
            tenant_id=self.tenant_id,
            user_id=self.user.id,
            filename=safe_filename,
            content_type=request.content_type,
            file_size=request.file_size,
            client_checksum_sha256=request.client_checksum_sha256,
            metadata=request.metadata,
        )

        # 3. Build storage key and generate presigned URL
        bucket = settings.s3_bucket or "contractrisk-documents"
        storage_key = storage_service.build_object_key(self.tenant_id, safe_filename)
        await storage_service.ensure_bucket(bucket)

        presigned_url = await storage_service.generate_presigned_upload_url(
            bucket=bucket,
            key=storage_key,
            content_type=request.content_type,
            expires_in=3600,
        )

        # 4. Store key
        await self.repository.set_storage_key(upload.upload_id, self.tenant_id, storage_key, bucket)

        # 5. Emit event
        await self.event_bus.emit(UploadInitiated(
            tenant_id=self.tenant_id,
            actor_id=self.user.id,
            data={
                "upload_id": str(upload.upload_id),
                "filename": safe_filename,
                "file_size": request.file_size,
            },
        ))

        return {
            "upload_id": str(upload.upload_id),
            "storage_url": presigned_url,
            "expires_in": 3600,
            "allowed_methods": ["PUT"],
            "required_headers": {
                "Content-Type": request.content_type,
            },
        }

    async def complete_upload(self, upload_id: str) -> dict:
        """Confirm upload completion and transition to validation pipeline."""
        upload = await self.repository.get_upload(upload_id, self.tenant_id)
        if not upload:
            raise UploadNotFoundError(upload_id)

        if upload.ingestion_state != IngestionState.UPLOADED:
            raise IngestionStateTransitionError(
                f"Cannot complete upload in state '{upload.ingestion_state.value}'"
            )

        # Verify object exists in storage
        if not await storage_service.object_exists(upload.storage_bucket or "", upload.storage_key or ""):
            raise StorageServiceError("Uploaded file not found in storage")

        # Transition to validation
        await self.repository.update_state(upload_id, self.tenant_id, IngestionState.VALIDATING)

        # Commit before queuing Celery so workers see the state change.
        await self.repository.session.commit()

        # Dispatch validation to worker
        from workers.ingestion import validate_upload_task
        validate_upload_task.delay(
            upload_id=str(upload_id),
            tenant_id=self.tenant_id,
            user_id=self.user.id,
        )

        await self.event_bus.emit(UploadCompleted(
            tenant_id=self.tenant_id,
            actor_id=self.user.id,
            data={"upload_id": str(upload_id)},
        ))

        return {
            "upload_id": str(upload_id),
            "ingestion_state": IngestionState.VALIDATING.value,
            "message": "Upload confirmed. Validation pipeline started.",
        }

    async def cancel_upload(self, upload_id: str) -> dict:
        """Cancel an upload session (only allowed in UPLOADED state)."""
        upload = await self.repository.get_upload(upload_id, self.tenant_id)
        if not upload:
            raise UploadNotFoundError(upload_id)

        if upload.ingestion_state not in (IngestionState.UPLOADED, IngestionState.FAILED):
            raise IngestionStateTransitionError(
                f"Cannot cancel upload in state '{upload.ingestion_state.value}'"
            )

        await self.repository.update_state(upload_id, self.tenant_id, IngestionState.CANCELLED)

        # Clean up storage if object exists
        if upload.storage_key:
            try:
                await storage_service.delete_object(upload.storage_bucket or "", upload.storage_key)
            except Exception as exc:
                logger.warning("Failed to clean up storage for cancelled upload %s: %s", upload_id, exc)

        await self.event_bus.emit(UploadCancelled(
            tenant_id=self.tenant_id,
            actor_id=self.user.id,
            data={"upload_id": str(upload_id)},
        ))

        return {"upload_id": str(upload_id), "status": "cancelled"}

    async def retry_ingestion(self, upload_id: str) -> dict:
        """Retry ingestion from FAILED or re-queue a stuck in-progress upload."""
        upload = await self.repository.get_upload(upload_id, self.tenant_id)
        if not upload:
            raise UploadNotFoundError(upload_id)

        if upload.retry_count >= MAX_RETRIES:
            raise IngestionRetryLimitExceededError(
                f"Maximum retry attempts ({MAX_RETRIES}) exceeded for upload {upload_id}"
            )

        stuck_states = {
            IngestionState.OCR_PENDING,
            IngestionState.OCR_PROCESSING,
            IngestionState.STORAGE_CONFIRMED,
            IngestionState.OCR_COMPLETE,
            IngestionState.CHUNKING_PENDING,
            IngestionState.EMBEDDING_PENDING,
            IngestionState.VALIDATING,
            IngestionState.VALIDATED,
        }

        if upload.ingestion_state in stuck_states:
            from workers.ingestion_dispatch import redispatch_ingestion

            await self.repository.increment_retry(upload_id, self.tenant_id)
            await self.repository.update_state(
                upload_id, self.tenant_id, upload.ingestion_state, error=None,
            )
            await self.repository.session.commit()

            action = redispatch_ingestion(
                str(upload_id),
                self.tenant_id,
                str(upload.user_id),
                upload.ingestion_state,
            )
            if not action:
                raise IngestionStateTransitionError(
                    f"Cannot resume upload in state '{upload.ingestion_state.value}'"
                )
            return {
                "upload_id": str(upload_id),
                "status": "resuming",
                "ingestion_state": upload.ingestion_state.value,
                "retry_count": upload.retry_count + 1,
                "action": action,
            }

        if upload.ingestion_state != IngestionState.FAILED:
            raise IngestionStateTransitionError(
                f"Can only retry from FAILED or stuck pipeline state, "
                f"current: {upload.ingestion_state.value}"
            )

        await self.repository.increment_retry(upload_id, self.tenant_id)
        await self.repository.update_state(upload_id, self.tenant_id, IngestionState.UPLOADED, error=None)

        # Re-dispatch
        await self.complete_upload(upload_id)

        return {"upload_id": str(upload_id), "status": "retrying", "retry_count": upload.retry_count + 1}

    async def get_status(self, upload_id: str) -> Optional[UploadSession]:
        return await self.repository.get_upload(upload_id, self.tenant_id)

    async def list_uploads(self, state: Optional[str] = None, page: int = 1, page_size: int = 20):
        ingestion_state = IngestionState(state) if state else None
        items = await self.repository.list_by_tenant(self.tenant_id, ingestion_state, page_size, (page - 1) * page_size)
        total = await self.repository.count_by_tenant(self.tenant_id, ingestion_state)
        return items, total
