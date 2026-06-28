"""Dispatch ingestion pipeline after upload rows are committed to the database."""

from __future__ import annotations

import logging
import uuid
from typing import Callable, Optional

from app.config import settings

logger = logging.getLogger(__name__)


def dispatch_ingestion_pipeline(
    upload_id: str,
    tenant_id: str,
    user_id: str,
    *,
    schedule_inline: Optional[Callable[[], None]] = None,
) -> bool:
    """Queue (or inline-start) ingestion after the upload row is committed.

    Returns True when a worker or inline pipeline was started.
    """
    if settings.environment == "development" and schedule_inline is not None:
        schedule_inline()
        logger.info(
            "Started inline ingestion for upload %s (development)",
            upload_id,
        )
        return True

    try:
        from workers.ingestion_tasks import ingest_document

        ingest_document.apply_async(
            kwargs={
                "upload_id": upload_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
            countdown=2,
        )
        logger.info(
            "Queued ingestion for upload %s tenant=%s",
            upload_id,
            tenant_id,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Failed to queue ingestion for upload %s: %s",
            upload_id,
            exc,
        )
        return False


def new_correlation_id() -> str:
    return str(uuid.uuid4())
