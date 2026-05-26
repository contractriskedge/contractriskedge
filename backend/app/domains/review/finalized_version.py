"""Final Approved Version (v3) — generates immutable final contract packages.

When a review is finalized, this module:
1. Generates a FINAL approved DOCX with all accepted redlines applied
2. Adds approval signature metadata (who approved, when)
3. Creates an immutable snapshot (watermarked, timestamped)
4. Stores the final version with SHA-256 checksum
5. Creates the v3 — Final Approved Contract version record
"""

from __future__ import annotations

import hashlib
import io
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class FinalizedVersionResult:
    """Result of creating a finalized version."""
    version_id: str
    version_number: int
    label: str
    storage_key: str
    file_size_bytes: int
    checksum_sha256: str
    change_summary: str
    created_at: str


async def create_finalized_version(
    session: AsyncSession,
    review_id: str,
    tenant_id: str,
    user_id: str,
    approved_by: Optional[str] = None,
    approved_at: Optional[datetime] = None,
    approval_comments: Optional[str] = None,
    approval_conditions: Optional[dict[str, Any]] = None,
) -> Optional[FinalizedVersionResult]:
    """Generate the final approved contract version (v3 / Final Approved).

    Steps:
    1. Get the latest document version with accepted redlines
    2. Apply all accepted/modified redlines to the original document
    3. Add approval metadata (signature block, timestamp, approver info)
    4. Upload the final document to storage
    5. Create the version record with SHA-256 checksum
    6. Mark previous versions as archived
    """
    from app.domains.review.models import (
        ContractDocumentVersion,
        ContractReview,
        ReviewRedline,
    )
    from app.domains.ingestion.models import UploadSession
    from app.config import settings
    from app.integrations.storage.s3 import storage_service

    # Get the review
    review_result = await session.execute(
        select(ContractReview).where(
            ContractReview.review_id == review_id,
            ContractReview.tenant_id == tenant_id,
        )
    )
    review = review_result.scalar_one_or_none()
    if not review:
        logger.error("Finalized version: review %s not found", review_id)
        return None

    # Get the original upload document
    upload_result = await session.execute(
        select(UploadSession).where(
            UploadSession.upload_id == review.upload_id,
            UploadSession.tenant_id == tenant_id,
        )
    )
    upload = upload_result.scalar_one_or_none()
    if not upload or not upload.storage_key:
        logger.error("Finalized version: original document not found for review %s", review_id)
        return None

    # Get the latest version number
    max_result = await session.execute(
        select(func.max(ContractDocumentVersion.version_number)).where(
            ContractDocumentVersion.review_id == review_id,
            ContractDocumentVersion.tenant_id == tenant_id,
        )
    )
    max_version = max_result.scalar() or 0
    next_version = max_version + 1

    # Get all accepted/modified redlines
    redlines_result = await session.execute(
        select(ReviewRedline).where(
            ReviewRedline.review_id == review_id,
            ReviewRedline.tenant_id == tenant_id,
            ReviewRedline.status.in_(["accepted", "modified"]),
        )
    )
    redlines = redlines_result.scalars().all()

    # Archive previous current versions
    await session.execute(
        update(ContractDocumentVersion).where(
            ContractDocumentVersion.review_id == review_id,
            ContractDocumentVersion.tenant_id == tenant_id,
            ContractDocumentVersion.status == "current",
        ).values(status="archived")
    )

    # Build approval metadata for the document
    approval_metadata = _build_approval_metadata(
        approved_by=approved_by or user_id,
        approved_at=approved_at or datetime.utcnow(),
        approval_comments=approval_comments,
        approval_conditions=approval_conditions,
        review_version=review.version or 1,
    )

    # Generate the final document
    bucket = settings.s3_bucket or "contractrisk-documents"
    storage_key = f"finalized/{tenant_id}/{review_id}/v{next_version}_final_approved.docx"

    try:
        from app.domains.review.document_generation import generate_finalized_document

        doc_data = await generate_finalized_document(
            session=session,
            review_id=review_id,
            tenant_id=tenant_id,
            user_id=user_id,
            original_storage_key=upload.storage_key,
            redlines=redlines,
            approval_metadata=approval_metadata,
        )

        # Upload to storage
        await storage_service.upload_fileobj(
            bucket=bucket,
            key=storage_key,
            data=doc_data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # Compute checksum
        checksum = hashlib.sha256(doc_data).hexdigest()
        file_size = len(doc_data)

    except Exception as exc:
        logger.error(
            "Failed to generate finalized document for review %s: %s",
            review_id, exc, exc_info=True,
        )
        return None

    # Create the finalized version record
    change_summary = (
        f"Final Approved Contract v{next_version} — "
        f"Approved by {approved_by or user_id} on "
        f"{(approved_at or datetime.utcnow()).strftime('%Y-%m-%d %H:%M UTC')}. "
        f"{len(redlines)} accepted redline(s) applied. "
        f"Document is immutable."
    )

    version = ContractDocumentVersion(
        review_id=review_id,
        tenant_id=tenant_id,
        version_number=next_version,
        label=f"v{next_version} — Final Approved",
        status="finalized",
        source_document_id=review.upload_id,
        storage_key=storage_key,
        file_size_bytes=file_size,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        checksum_sha256=checksum,
        change_summary=change_summary,
        accepted_redline_ids=[r.redline_id for r in redlines] if redlines else [],
        created_by=user_id,
    )
    session.add(version)

    # Update the review with approved version reference
    await session.execute(
        update(ContractReview).where(
            ContractReview.review_id == review_id,
            ContractReview.tenant_id == tenant_id,
        ).values(
            approved_version_id=version.version_id,
            completed_at=func.now(),
            updated_at=func.now(),
        )
    )

    await session.flush()

    logger.info(
        "Created finalized version v%s for review %s (storage: %s, size: %d bytes, sha256: %s)",
        next_version, review_id, storage_key, file_size, checksum,
    )

    return FinalizedVersionResult(
        version_id=str(version.version_id),
        version_number=next_version,
        label=version.label,
        storage_key=storage_key,
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        change_summary=change_summary,
        created_at=version.created_at.isoformat() if version.created_at else datetime.utcnow().isoformat(),
    )


def _build_approval_metadata(
    approved_by: str,
    approved_at: datetime,
    approval_comments: Optional[str] = None,
    approval_conditions: Optional[dict[str, Any]] = None,
    review_version: int = 1,
) -> dict[str, Any]:
    """Build approval signature metadata for embedding in the final document."""
    return {
        "approved_by": approved_by,
        "approved_at": approved_at.isoformat(),
        "approval_comments": approval_comments,
        "approval_conditions": approval_conditions or {},
        "review_version": review_version,
        "document_type": "Final Approved Contract",
        "immutable": True,
        "generated_at": datetime.utcnow().isoformat(),
    }
