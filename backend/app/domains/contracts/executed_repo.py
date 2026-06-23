"""Executed Document Repository — stores executed PDFs, certificates, and audit logs.

When a contract is fully signed:
1. The executed PDF is stored
2. The completion certificate is stored
3. The audit trail is stored
4. All are linked to the contract record
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.kernel.database.base import Base
from app.kernel.storage import StorageService, StoredFile

logger = logging.getLogger(__name__)


class ExecutedDocument(Base):
    """Stores metadata about executed contract documents."""
    __tablename__ = "executed_documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("contract_reviews.review_id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # executed_pdf, certificate, audit_log
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_exec_doc_contract", "contract_id"),
        Index("idx_exec_doc_type", "document_type"),
    )


class ExecutedDocumentRepository:
    """Repository for executed contract documents.

    When a contract is fully signed, the following are stored:
    - executed_pdf: The fully executed contract PDF
    - certificate: The signature provider's completion certificate
    - audit_log: The complete signature audit trail (JSON)
    """

    def __init__(self, session: AsyncSession, storage: StorageService):
        self.session = session
        self.storage = storage

    async def store_executed_pdf(
        self,
        contract_id: str,
        pdf_data: bytes,
        filename: Optional[str] = None,
    ) -> ExecutedDocument:
        """Store the executed contract PDF."""
        fname = filename or f"executed_{contract_id}.pdf"
        path = f"contracts/executed/{contract_id}/{fname}"

        stored = await self.storage.upload(path, pdf_data, content_type="application/pdf")
        doc = ExecutedDocument(
            id=str(uuid.uuid4()),
            contract_id=contract_id,
            document_type="executed_pdf",
            filename=fname,
            storage_path=path,
            content_type="application/pdf",
            size_bytes=stored.size_bytes,
            provider=stored.provider or "local",
            metadata={"uploaded_at": datetime.now(timezone.utc).isoformat()},
        )
        self.session.add(doc)
        await self.session.flush()
        logger.info("Stored executed PDF for contract %s: %s", contract_id, path)
        return doc

    async def store_certificate(
        self,
        contract_id: str,
        cert_data: bytes,
        filename: Optional[str] = None,
    ) -> ExecutedDocument:
        """Store the signature completion certificate."""
        fname = filename or f"certificate_{contract_id}.pdf"
        path = f"contracts/executed/{contract_id}/{fname}"

        stored = await self.storage.upload(path, cert_data, content_type="application/pdf")
        doc = ExecutedDocument(
            id=str(uuid.uuid4()),
            contract_id=contract_id,
            document_type="certificate",
            filename=fname,
            storage_path=path,
            content_type="application/pdf",
            size_bytes=stored.size_bytes,
            provider=stored.provider or "local",
        )
        self.session.add(doc)
        await self.session.flush()
        logger.info("Stored certificate for contract %s: %s", contract_id, path)
        return doc

    async def store_audit_log(
        self,
        contract_id: str,
        audit_data: dict,
    ) -> ExecutedDocument:
        """Store the signature audit trail as JSON."""
        import json
        data = json.dumps(audit_data, indent=2, default=str).encode("utf-8")
        fname = f"audit_{contract_id}.json"
        path = f"contracts/executed/{contract_id}/{fname}"

        stored = await self.storage.upload(path, data, content_type="application/json")
        doc = ExecutedDocument(
            id=str(uuid.uuid4()),
            contract_id=contract_id,
            document_type="audit_log",
            filename=fname,
            storage_path=path,
            content_type="application/json",
            size_bytes=stored.size_bytes,
            provider=stored.provider or "local",
            metadata=audit_data,
        )
        self.session.add(doc)
        await self.session.flush()
        logger.info("Stored audit log for contract %s: %s", contract_id, path)
        return doc

    async def get_documents(self, contract_id: str) -> list[ExecutedDocument]:
        """Get all stored documents for a contract."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(ExecutedDocument).where(
                ExecutedDocument.contract_id == contract_id
            ).order_by(ExecutedDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document_by_type(
        self, contract_id: str, document_type: str
    ) -> Optional[ExecutedDocument]:
        """Get a specific document type for a contract."""
        from sqlalchemy import select, and_
        result = await self.session.execute(
            select(ExecutedDocument).where(
                and_(
                    ExecutedDocument.contract_id == contract_id,
                    ExecutedDocument.document_type == document_type,
                )
            ).order_by(ExecutedDocument.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def download_document(self, document_id: str) -> Optional[bytes]:
        """Download a stored document's content."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(ExecutedDocument).where(ExecutedDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return None
        return await self.storage.download(doc.storage_path)

    async def get_contract_summary(self, contract_id: str) -> dict:
        """Get a summary of all executed documents for a contract."""
        docs = await self.get_documents(contract_id)
        return {
            "contract_id": contract_id,
            "has_executed_pdf": any(d.document_type == "executed_pdf" for d in docs),
            "has_certificate": any(d.document_type == "certificate" for d in docs),
            "has_audit_log": any(d.document_type == "audit_log" for d in docs),
            "total_documents": len(docs),
            "documents": [
                {
                    "id": d.id,
                    "type": d.document_type,
                    "filename": d.filename,
                    "size_bytes": d.size_bytes,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in docs
            ],
        }
