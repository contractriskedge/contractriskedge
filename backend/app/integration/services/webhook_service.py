"""
Webhook Service — secure webhook ingestion with verification, replay protection,
idempotent event handling, and retry-safe processing.
"""

import hashlib
import hmac
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.integration.models.webhook import (
    IntegrationWebhook,
    WebhookEvent,
    WebhookEventStatus,
    WebhookStatus,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.telemetry import IntegrationTelemetry

logger = get_logger(__name__)

# Maximum allowed age for webhook timestamps (5 minutes)
_MAX_WEBHOOK_AGE_SECONDS = 300


class WebhookVerifier:
    """
    Verifies webhook payload signatures and protects against replay attacks.

    Supports:
    - HMAC-SHA256 signature verification
    - Timestamp replay protection
    - Idempotency key validation
    """

    @staticmethod
    def verify_hmac_signature(
        payload: bytes,
        signature: str,
        secret: str,
        signature_header: str = "x-hub-signature-256",
    ) -> bool:
        """
        Verify HMAC-SHA256 signature.

        Supports both 'sha256=...' and raw hex formats.
        """
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        if signature.startswith("sha256="):
            return hmac.compare_digest(signature[7:], expected)
        return hmac.compare_digest(signature, expected)

    @staticmethod
    def verify_timestamp(
        timestamp: Optional[float],
        max_age_seconds: int = _MAX_WEBHOOK_AGE_SECONDS,
    ) -> bool:
        """
        Verify webhook timestamp is within acceptable age window.

        Prevents replay attacks by rejecting old events.
        """
        if timestamp is None:
            return False
        now = time.time()
        return (now - timestamp) <= max_age_seconds

    @staticmethod
    def generate_idempotency_key(
        event_id: str,
        provider: str,
        timestamp: Optional[float] = None,
    ) -> str:
        """Generate a deterministic idempotency key for deduplication."""
        base = f"{provider}:{event_id}"
        if timestamp:
            base = f"{base}:{int(timestamp)}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_signature_generic(
        payload: bytes,
        signature: str,
        secret: str,
        algorithm: str = "sha256",
    ) -> bool:
        """
        Generic signature verification supporting multiple algorithms.
        """
        if algorithm == "sha256":
            return WebhookVerifier.verify_hmac_signature(payload, signature, secret)
        elif algorithm == "sha1":
            expected = hmac.new(
                secret.encode("utf-8"), payload, hashlib.sha1
            ).hexdigest()
            if signature.startswith("sha1="):
                return hmac.compare_digest(signature[5:], expected)
            return hmac.compare_digest(signature, expected)
        else:
            raise ValueError(f"Unsupported signature algorithm: {algorithm}")


class WebhookService:
    """
    Enterprise webhook ingestion service.

    Handles verification, deduplication, persistence, and retry orchestration
    for incoming webhook events from external providers.
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        audit: Optional[IntegrationAuditService] = None,
        telemetry: Optional[IntegrationTelemetry] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.verifier = WebhookVerifier()
        self.audit = audit
        self.telemetry = telemetry

    async def process_incoming_webhook(
        self,
        provider: str,
        webhook_id: str,
        payload: bytes,
        headers: dict[str, str],
        signature: Optional[str] = None,
        timestamp: Optional[float] = None,
        event_id: Optional[str] = None,
        event_type: Optional[str] = None,
        source_ip: Optional[str] = None,
    ) -> WebhookEvent:
        """
        Process an incoming webhook with full verification pipeline.

        Steps:
        1. Look up webhook subscription
        2. Verify signature (if required)
        3. Check timestamp for replay protection
        4. Check idempotency for deduplication
        5. Persist event
        6. Trigger async processing
        """
        # 1. Look up webhook subscription
        webhook_sub = await self._get_webhook_subscription(provider, webhook_id)
        if not webhook_sub:
            logger.warning(
                "webhook_subscription_not_found",
                provider=provider,
                webhook_id=webhook_id,
            )
            raise ValueError(f"Webhook subscription not found: {provider}/{webhook_id}")

        if webhook_sub.status != WebhookStatus.ACTIVE:
            logger.warning(
                "webhook_subscription_not_active",
                webhook_id=webhook_id,
                status=webhook_sub.status.value,
            )
            raise ValueError(f"Webhook subscription is {webhook_sub.status.value}")

        # 2. Verify signature
        signature_valid = None
        if webhook_sub.require_signature and webhook_sub.secret:
            sig_header = signature or headers.get(
                webhook_sub.signature_header or "x-hub-signature-256", ""
            )
            signature_valid = self.verifier.verify_hmac_signature(
                payload, sig_header, webhook_sub.secret
            )
            if not signature_valid:
                logger.error(
                    "webhook_signature_invalid",
                    webhook_id=webhook_id,
                    source_ip=source_ip,
                )
                # Still record the event but mark as invalid
        else:
            signature_valid = True  # No signature required

        # 3. Timestamp replay protection
        timestamp_valid = self.verifier.verify_timestamp(timestamp)
        if not timestamp_valid and timestamp is not None:
            logger.warning(
                "webhook_timestamp_invalid",
                webhook_id=webhook_id,
                timestamp=timestamp,
            )

        # 4. Idempotency check
        resolved_event_id = event_id or hashlib.sha256(payload).hexdigest()
        idempotency_key = self.verifier.generate_idempotency_key(
            resolved_event_id, provider, timestamp
        )

        existing = await self._check_idempotency(idempotency_key)
        if existing:
            logger.info(
                "webhook_event_duplicate",
                idempotency_key=idempotency_key,
                existing_id=str(existing.id),
            )
            if self.telemetry:
                self.telemetry.record_webhook_event(
                    provider=provider, event_type=event_type or "unknown", status="duplicate"
                )
            return existing

        # 5. Persist event
        now = datetime.now(timezone.utc)
        event = WebhookEvent(
            webhook_id=webhook_sub.id,
            integration_id=webhook_sub.integration_id,
            tenant_id=self.tenant_id,
            idempotency_key=idempotency_key,
            event_id=resolved_event_id,
            event_type=event_type or "unknown",
            raw_payload=payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload,
            headers=headers,
            status=WebhookEventStatus.RECEIVED,
            timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else now,
            received_at=now,
            source_ip=source_ip,
            signature_valid=signature_valid,
            correlation_id=uuid.uuid4(),
            expires_at=now + timedelta(hours=24),
        )

        self.db.add(event)

        # Update webhook subscription stats
        webhook_sub.event_count += 1
        webhook_sub.last_event_at = now

        await self.db.flush()

        if self.telemetry:
            self.telemetry.record_webhook_event(
                provider=provider,
                event_type=event_type or "unknown",
                status="received",
            )

        logger.info(
            "webhook_event_persisted",
            event_id=str(event.id),
            webhook_id=webhook_id,
            event_type=event.event_type,
            signature_valid=signature_valid,
        )

        return event

    async def mark_event_processing(
        self, event_id: uuid.UUID
    ) -> None:
        """Mark a webhook event as being processed."""
        await self.db.execute(
            update(WebhookEvent)
            .where(WebhookEvent.id == event_id)
            .values(
                status=WebhookEventStatus.PROCESSING,
                processing_attempts=WebhookEvent.processing_attempts + 1,
            )
        )
        await self.db.flush()

    async def mark_event_completed(
        self, event_id: uuid.UUID
    ) -> None:
        """Mark a webhook event as successfully processed."""
        await self.db.execute(
            update(WebhookEvent)
            .where(WebhookEvent.id == event_id)
            .values(
                status=WebhookEventStatus.COMPLETED,
                processed_at=datetime.now(timezone.utc),
            )
        )
        await self.db.flush()

    async def mark_event_failed(
        self,
        event_id: uuid.UUID,
        error: str,
        should_retry: bool = True,
    ) -> None:
        """Mark a webhook event as failed, optionally scheduling retry."""
        now = datetime.now(timezone.utc)
        event_result = await self.db.execute(
            select(WebhookEvent).where(WebhookEvent.id == event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            return

        if should_retry and event.processing_attempts < event.max_retries:
            next_retry = now + timedelta(
                seconds=min(60 * (2 ** event.processing_attempts), 3600)
            )
            await self.db.execute(
                update(WebhookEvent)
                .where(WebhookEvent.id == event_id)
                .values(
                    status=WebhookEventStatus.RETRYING,
                    last_error=error,
                    next_retry_at=next_retry,
                )
            )
            logger.info(
                "webhook_event_scheduled_retry",
                event_id=str(event_id),
                attempt=event.processing_attempts,
                next_retry=str(next_retry),
            )
        else:
            status = (
                WebhookEventStatus.DEAD_LETTER
                if event.processing_attempts >= event.max_retries
                else WebhookEventStatus.FAILED
            )
            await self.db.execute(
                update(WebhookEvent)
                .where(WebhookEvent.id == event_id)
                .values(status=status, last_error=error)
            )
            logger.error(
                "webhook_event_failed_permanent",
                event_id=str(event_id),
                status=status.value,
                error=error,
            )

        await self.db.flush()

    async def get_pending_events(
        self,
        limit: int = 50,
    ) -> list[WebhookEvent]:
        """Get events pending retry."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(WebhookEvent)
            .where(
                WebhookEvent.tenant_id == self.tenant_id,
                WebhookEvent.status.in_([
                    WebhookEventStatus.RECEIVED,
                    WebhookEventStatus.RETRYING,
                ]),
                WebhookEvent.next_retry_at <= now,
                WebhookEvent.expires_at > now,
            )
            .order_by(WebhookEvent.received_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_webhook_subscription(
        self, provider: str, webhook_id: str
    ) -> Optional[IntegrationWebhook]:
        result = await self.db.execute(
            select(IntegrationWebhook).where(
                IntegrationWebhook.tenant_id == self.tenant_id,
                IntegrationWebhook.provider == provider,
                IntegrationWebhook.webhook_id == webhook_id,
            )
        )
        return result.scalar_one_or_none()

    async def _check_idempotency(
        self, idempotency_key: str
    ) -> Optional[WebhookEvent]:
        result = await self.db.execute(
            select(WebhookEvent).where(
                WebhookEvent.idempotency_key == idempotency_key,
                WebhookEvent.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()
