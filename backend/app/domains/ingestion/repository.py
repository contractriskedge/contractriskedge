"""Ingestion repository — data access for upload sessions and ingestion tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.repository.base import BaseRepository
from app.domains.ingestion.models import UploadSession, IngestionState, coerce_ingestion_state


@dataclass
class IngestionRepository(BaseRepository):
    """Repository for upload session and ingestion pipeline data access."""

    async def create_upload(
        self,
        tenant_id: str,
        user_id: str,
        filename: str,
        content_type: str,
        file_size: int,
        client_checksum_sha256: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UploadSession:
        upload = UploadSession(
            tenant_id=tenant_id,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            client_checksum_sha256=client_checksum_sha256,
            metadata=metadata or {},
            ingestion_state=IngestionState.UPLOADED,
        )
        self.session.add(upload)
        await self.session.flush()
        return upload

    async def get_upload(self, upload_id: str, tenant_id: str) -> Optional[UploadSession]:
        stmt = select(UploadSession).where(
            UploadSession.upload_id == upload_id,
            UploadSession.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, upload_id: str) -> Optional[UploadSession]:
        """Get upload by ID without tenant filter (for cross-domain queries)."""
        stmt = select(UploadSession).where(UploadSession.upload_id == upload_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_state(
        self,
        upload_id: str,
        tenant_id: str,
        new_state: IngestionState,
        error: Optional[str] = None,
    ) -> Optional[UploadSession]:
        upload = await self.get_upload(upload_id, tenant_id)
        if not upload:
            return None

        current_state = coerce_ingestion_state(upload.ingestion_state)
        new_state = coerce_ingestion_state(new_state)

        if not current_state.can_transition_to(new_state):
            raise ValueError(
                f"Cannot transition from {current_state} to {new_state}"
            )

        update_data = {"ingestion_state": new_state.value}
        if error:
            update_data["ingestion_error"] = error
        if new_state == IngestionState.REVIEW_READY:
            update_data["completed_at"] = datetime.utcnow()

        stmt = (
            update(UploadSession)
            .where(UploadSession.upload_id == upload_id)
            .values(**update_data)
        )
        await self.session.execute(stmt)
        await self.session.flush()

        upload.ingestion_state = new_state
        return upload

    async def set_storage_key(
        self, upload_id: str, tenant_id: str, storage_key: str, storage_bucket: str,
    ) -> None:
        stmt = (
            update(UploadSession)
            .where(UploadSession.upload_id == upload_id, UploadSession.tenant_id == tenant_id)
            .values(storage_key=storage_key, storage_bucket=storage_bucket)
        )
        await self.session.execute(stmt)

    async def set_checksum(
        self, upload_id: str, tenant_id: str, server_checksum_sha256: str,
    ) -> None:
        stmt = (
            update(UploadSession)
            .where(UploadSession.upload_id == upload_id, UploadSession.tenant_id == tenant_id)
            .values(server_checksum_sha256=server_checksum_sha256, checksum_validated=func.now())
        )
        await self.session.execute(stmt)

    async def get_upload_by_checksum(
        self, tenant_id: str, checksum_sha256: str,
    ) -> Optional[UploadSession]:
        """Find an existing upload with the same checksum for deduplication."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(UploadSession).where(
                UploadSession.tenant_id == tenant_id,
                UploadSession.client_checksum_sha256 == checksum_sha256,
            ).order_by(UploadSession.created_at.desc())
        )
        return result.scalars().first()

    async def increment_retry(self, upload_id: str, tenant_id: str) -> None:
        stmt = (
            update(UploadSession)
            .where(UploadSession.upload_id == upload_id, UploadSession.tenant_id == tenant_id)
            .values(
                retry_count=UploadSession.retry_count + 1,
                last_retry_at=func.now(),
            )
        )
        await self.session.execute(stmt)

    async def list_by_tenant(
        self, tenant_id: str, state: Optional[IngestionState] = None, limit: int = 50, offset: int = 0,
    ):
        query = select(UploadSession).where(UploadSession.tenant_id == tenant_id)
        if state:
            query = query.where(UploadSession.ingestion_state == state)
        query = query.order_by(UploadSession.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_by_tenant(self, tenant_id: str, state: Optional[IngestionState] = None) -> int:
        query = select(func.count()).select_from(UploadSession).where(UploadSession.tenant_id == tenant_id)
        if state:
            query = query.where(UploadSession.ingestion_state == state)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete_upload(self, upload_id: str, tenant_id: str) -> None:
        """Delete an upload record from the database."""
        from sqlalchemy import delete as sa_delete
        stmt = sa_delete(UploadSession).where(
            UploadSession.upload_id == upload_id,
            UploadSession.tenant_id == tenant_id,
        )
        await self.session.execute(stmt)
