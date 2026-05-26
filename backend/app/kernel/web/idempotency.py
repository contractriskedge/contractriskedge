"""Idempotency protection middleware and utilities.

Provides Idempotency-Key header support for preventing duplicate request
processing. Uses PostgreSQL for idempotency key storage with TTL-based
expiration and automatic cleanup.

Usage:
    from app.kernel.web.idempotency import IdempotencyGuard, IdempotencyKey

    # In a route handler:
    guard = IdempotencyGuard(db)
    result = await guard.process(
        idempotency_key="uuid-from-header",
        tenant_id="tenant-uuid",
        operation="upload_document",
        handler=lambda: perform_upload(),
        ttl_seconds=86400,  # 24 hours
    )
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Text, func, select, delete
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.database.base import Base

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────

DEFAULT_IDEMPOTENCY_TTL = 86_400  # 24 hours
MAX_IDEMPOTENCY_KEY_LENGTH = 255


# ── ORM Model ──────────────────────────────────────────────────────

class IdempotencyRecord(Base):
    """Stores idempotency keys for deduplication protection."""
    __tablename__ = "idempotency_records"

    record_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(Text, nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    operation = Column(Text, nullable=False)
    resource_id = Column(Text, nullable=True)  # The ID of the created/updated resource
    request_hash = Column(Text, nullable=True)  # SHA-256 of request body for validation
    response_data = Column(JSONB, nullable=True)  # Cached response for replay
    status_code = Column(Text, nullable=False, default="completed")  # 'pending', 'completed', 'failed'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


# ── Idempotency Guard ──────────────────────────────────────────────

class IdempotencyError(Exception):
    """Base error for idempotency violations."""
    pass


class IdempotencyKeyMismatchError(IdempotencyError):
    """Request body differs from original request with same idempotency key."""
    pass


@dataclass
class IdempotencyGuard:
    """Protects against duplicate request processing using Idempotency-Key headers.

    Features:
        - Deduplication: Same key + operation returns cached response
        - Request validation: Detects if same key used with different request body
        - TTL-based expiration: Keys auto-expire after configurable duration
        - Pending detection: Detects concurrent requests with same key
    """

    session: AsyncSession

    async def process(
        self,
        idempotency_key: str,
        tenant_id: str,
        operation: str,
        handler: Callable[[], Any],
        request_body: Optional[dict] = None,
        ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL,
    ) -> dict:
        """Process a request with idempotency protection.

        Args:
            idempotency_key: The Idempotency-Key value from the request header
            tenant_id: Tenant ID for isolation
            operation: Operation name (e.g., 'upload_document', 'analyze_contract')
            handler: Async callable that performs the actual operation
            request_body: Optional request body for hash validation
            ttl_seconds: How long to keep the idempotency record (default 24h)

        Returns:
            dict with 'data' (response from handler or cached) and 'cached' (bool)

        Raises:
            IdempotencyKeyMismatchError: If same key used with different request body
        """
        # Validate key format
        if not idempotency_key or len(idempotency_key) > MAX_IDEMPOTENCY_KEY_LENGTH:
            raise ValueError(f"Invalid idempotency key (max {MAX_IDEMPOTENCY_KEY_LENGTH} chars)")

        # Normalize the key
        normalized_key = self._normalize_key(idempotency_key, tenant_id, operation)

        # Compute request hash if body provided
        request_hash = None
        if request_body:
            request_hash = hashlib.sha256(
                json.dumps(request_body, sort_keys=True).encode()
            ).hexdigest()

        # Check for existing record
        existing = await self._get_record(normalized_key)

        if existing:
            # Check if still pending (concurrent request)
            if existing.status_code == "pending":
                raise IdempotencyError(
                    f"Request with idempotency key {idempotency_key} is still processing"
                )

            # Validate request hash matches
            if existing.request_hash and request_hash and existing.request_hash != request_hash:
                raise IdempotencyKeyMismatchError(
                    f"Idempotency key {idempotency_key} was used with a different request body"
                )

            # Return cached response
            logger.info("Idempotency hit for key=%s operation=%s", idempotency_key, operation)
            return {
                "data": existing.response_data,
                "cached": True,
                "resource_id": existing.resource_id,
            }

        # Create pending record
        record = IdempotencyRecord(
            idempotency_key=normalized_key,
            tenant_id=tenant_id,
            operation=operation,
            request_hash=request_hash,
            status_code="pending",
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        )
        self.session.add(record)
        await self.session.flush()

        try:
            # Execute the handler
            result = await handler() if hasattr(handler, '__await__') else handler()

            # Extract resource_id and response data
            resource_id = None
            response_data = result
            if isinstance(result, dict):
                resource_id = result.get("upload_id") or result.get("review_id") or result.get("run_id") or result.get("id")
                response_data = result

            # Update record with success
            record.status_code = "completed"
            record.resource_id = resource_id
            record.response_data = response_data if isinstance(response_data, dict) else {"result": str(response_data)}
            await self.session.flush()

            return {
                "data": result,
                "cached": False,
                "resource_id": resource_id,
            }

        except Exception as e:
            # Mark as failed
            record.status_code = "failed"
            record.response_data = {"error": str(e)}
            await self.session.flush()
            raise

    async def _get_record(self, normalized_key: str) -> Optional[IdempotencyRecord]:
        """Get an existing idempotency record that hasn't expired."""
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == normalized_key,
            IdempotencyRecord.expires_at > datetime.utcnow(),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _normalize_key(key: str, tenant_id: str, operation: str) -> str:
        """Create a normalized, scoped idempotency key."""
        raw = f"{tenant_id}:{operation}:{key}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def generate_key() -> str:
        """Generate a new idempotency key."""
        return str(uuid.uuid4())


# ── Cleanup ────────────────────────────────────────────────────────

async def cleanup_expired_keys(session: AsyncSession) -> int:
    """Remove expired idempotency records. Returns count of deleted records."""
    stmt = delete(IdempotencyRecord).where(
        IdempotencyRecord.expires_at <= datetime.utcnow()
    )
    result = await session.execute(stmt)
    await session.flush()
    count = result.rowcount if hasattr(result, 'rowcount') else 0
    if count:
        logger.info("Cleaned up %d expired idempotency records", count)
    return count
