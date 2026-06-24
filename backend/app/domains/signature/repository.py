"""E-Signature repository layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.database.base import Base
from .models import SignatureRequest, SignatureSigner, SignatureAuditEvent


class SignatureRepository:
    """Repository for e-signature data access."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    # ── Signature Requests ──────────────────────────────────────

    async def create_request(self, request: SignatureRequest) -> SignatureRequest:
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_request(self, request_id: str) -> Optional[SignatureRequest]:
        result = await self.session.execute(
            select(SignatureRequest).where(
                and_(
                    SignatureRequest.id == request_id,
                    SignatureRequest.tenant_id == self.tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SignatureRequest], int]:
        query = select(SignatureRequest).where(
            SignatureRequest.tenant_id == self.tenant_id
        )
        count_query = select(func.count()).select_from(SignatureRequest).where(
            SignatureRequest.tenant_id == self.tenant_id
        )

        if status:
            query = query.where(SignatureRequest.status == status)
            count_query = count_query.where(SignatureRequest.status == status)

        total = (await self.session.execute(count_query)).scalar() or 0
        query = query.order_by(SignatureRequest.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update_request_status(
        self, request_id: str, status: str, **extra
    ) -> bool:
        request = await self.get_request(request_id)
        if not request:
            return False
        request.status = status
        for key, value in extra.items():
            setattr(request, key, value)
        request.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def find_by_provider_reference(
        self, provider_reference: str
    ) -> Optional[SignatureRequest]:
        """Find a signature request by its provider reference (e.g., DocuSign envelope ID)."""
        result = await self.session.execute(
            select(SignatureRequest).where(
                and_(
                    SignatureRequest.provider_reference == provider_reference,
                    SignatureRequest.tenant_id == self.tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete_request(self, request_id: str) -> bool:
        request = await self.get_request(request_id)
        if not request:
            return False
        await self.session.delete(request)
        await self.session.flush()
        return True

    # ── Signers ─────────────────────────────────────────────────

    async def add_signer(self, signer: SignatureSigner) -> SignatureSigner:
        self.session.add(signer)
        await self.session.flush()
        return signer

    async def get_signers(self, request_id: str) -> list[SignatureSigner]:
        result = await self.session.execute(
            select(SignatureSigner).where(
                SignatureSigner.request_id == request_id
            ).order_by(SignatureSigner.signing_order)
        )
        return list(result.scalars().all())

    async def update_signer_status(
        self, signer_id: str, status: str, **extra
    ) -> bool:
        result = await self.session.execute(
            select(SignatureSigner).where(SignatureSigner.id == signer_id)
        )
        signer = result.scalar_one_or_none()
        if not signer:
            return False
        signer.status = status
        for key, value in extra.items():
            setattr(signer, key, value)
        await self.session.flush()
        return True

    async def remove_signer(self, signer_id: str) -> bool:
        result = await self.session.execute(
            select(SignatureSigner).where(SignatureSigner.id == signer_id)
        )
        signer = result.scalar_one_or_none()
        if not signer:
            return False
        await self.session.delete(signer)
        await self.session.flush()
        return True

    # ── Audit Events ────────────────────────────────────────────

    async def add_audit_event(self, event: SignatureAuditEvent) -> SignatureAuditEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_audit_events(self, request_id: str) -> list[SignatureAuditEvent]:
        result = await self.session.execute(
            select(SignatureAuditEvent).where(
                SignatureAuditEvent.request_id == request_id
            ).order_by(SignatureAuditEvent.created_at.asc())
        )
        return list(result.scalars().all())
