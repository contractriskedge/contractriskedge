"""Webhook notification system for ingestion job completion.

Provides HMAC-SHA256 signed webhook callbacks to notify external
services when an ingestion job completes or fails. Includes retry
logic and payload signing for security.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

from ingestion.models import JobRecord, JobStatus

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Base exception for webhook delivery failures."""


class WebhookDeliveryError(WebhookError):
    """Raised when a webhook payload cannot be delivered."""


class WebhookSignatureError(WebhookError):
    """Raised when webhook signing fails."""


class WebhookNotifier:
    """Handles webhook notification delivery for ingestion job completion.

    Delivers signed JSON payloads to registered webhook URLs with
    configurable retry logic and timeout settings.

    Attributes:
        max_retries: Maximum delivery attempts (default 3).
        timeout: HTTP request timeout in seconds (default 30).
        hmac_algorithm: Hash algorithm for signing (default 'sha256').
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout: float = 30.0,
        hmac_algorithm: str = "sha256",
    ) -> None:
        """Initialize the webhook notifier.

        Args:
            max_retries: Number of delivery attempts before giving up.
            timeout: HTTP request timeout in seconds.
            hmac_algorithm: Hash algorithm for HMAC signing.
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.hmac_algorithm = hmac_algorithm

    def _build_payload(self, job: JobRecord) -> Dict[str, Any]:
        """Build the webhook payload from a job record.

        Args:
            job: The completed job record.

        Returns:
            A dictionary with the webhook payload.
        """
        return {
            "event": "ingestion.completed" if job.status == JobStatus.DONE else "ingestion.failed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "job_id": job.job_id,
                "document_id": job.document_id,
                "tenant_id": job.tenant_id,
                "user_id": job.user_id,
                "filename": job.filename,
                "status": job.status.value,
                "progress": job.progress,
                "error_message": job.error_message,
                "total_pages": len(job.extraction_results) if job.extraction_results else 0,
                "total_clauses": len(job.clauses) if job.clauses else 0,
                "total_chunks": len(job.chunks) if job.chunks else 0,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            },
        }

    def _compute_signature(self, payload: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature for a payload.

        Args:
            payload: The serialized JSON payload bytes.
            secret: The shared secret key for HMAC signing.

        Returns:
            The hex-encoded HMAC signature string.
        """
        hash_func = getattr(hashlib, self.hmac_algorithm)
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hash_func,
        )
        return signature.hexdigest()

    def _validate_webhook_url(self, url: str) -> str:
        """Validate and normalize a webhook URL.

        Args:
            url: The webhook URL to validate.

        Returns:
            The validated URL string.

        Raises:
            WebhookError: If the URL is invalid or uses an unsupported scheme.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            raise WebhookError(
                f"Unsupported webhook URL scheme '{parsed.scheme}'; "
                f"must be http or https"
            )
        if not parsed.netloc:
            raise WebhookError(f"Invalid webhook URL: {url}")
        return url

    async def notify(
        self,
        job: JobRecord,
        webhook_url: str,
        webhook_secret: Optional[str] = None,
    ) -> bool:
        """Send a webhook notification for a completed job.

        Signs the payload with HMAC-SHA256 if a secret is provided.
        Retries on transient failures up to max_retries times.

        Args:
            job: The completed job record.
            webhook_url: The target webhook endpoint URL.
            webhook_secret: Optional shared secret for HMAC signing.

        Returns:
            True if the webhook was delivered successfully.

        Raises:
            WebhookDeliveryError: If delivery fails after all retries.
        """
        url = self._validate_webhook_url(webhook_url)
        payload = self._build_payload(job)
        payload_bytes = json.dumps(payload).encode("utf-8")

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "ContractRiskEdge-Webhook/1.0",
        }

        if webhook_secret:
            try:
                signature = self._compute_signature(payload_bytes, webhook_secret)
                headers["X-ContractRisk-Signature"] = (
                    f"{self.hmac_algorithm}={signature}"
                )
                headers["X-ContractRisk-Timestamp"] = str(int(datetime.utcnow().timestamp()))
            except Exception as exc:
                raise WebhookSignatureError(
                    f"Failed to sign webhook payload: {exc}"
                ) from exc

        last_exception: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(
                        url,
                        content=payload_bytes,
                        headers=headers,
                    )

                    if 200 <= response.status_code < 300:
                        logger.info(
                            "Webhook delivered successfully to %s (attempt %d/%d, status %d)",
                            url,
                            attempt,
                            self.max_retries,
                            response.status_code,
                        )
                        return True

                    logger.warning(
                        "Webhook to %s returned status %d (attempt %d/%d)",
                        url,
                        response.status_code,
                        attempt,
                        self.max_retries,
                    )

                    # Non-retryable status codes
                    if response.status_code in (400, 401, 403, 404, 410):
                        raise WebhookDeliveryError(
                            f"Webhook endpoint returned {response.status_code}: "
                            f"{response.text[:200]}"
                        )

                except httpx.TimeoutException as exc:
                    last_exception = exc
                    logger.warning(
                        "Webhook timeout for %s (attempt %d/%d)",
                        url,
                        attempt,
                        self.max_retries,
                    )
                except httpx.RequestError as exc:
                    last_exception = exc
                    logger.warning(
                        "Webhook request failed for %s (attempt %d/%d): %s",
                        url,
                        attempt,
                        self.max_retries,
                        exc,
                    )

                # Exponential backoff between retries
                if attempt < self.max_retries:
                    import asyncio

                    backoff = 2 ** (attempt + 1)
                    logger.info("Retrying webhook in %ds...", backoff)
                    await asyncio.sleep(backoff)

        raise WebhookDeliveryError(
            f"Failed to deliver webhook to {url} after {self.max_retries} attempts. "
            f"Last error: {last_exception}"
        )

    async def notify_from_job_data(
        self,
        job_data: Dict[str, Any],
        webhook_url: str,
        webhook_secret: Optional[str] = None,
    ) -> bool:
        """Send a webhook notification from raw job data.

        Convenience method that constructs a JobRecord from a dict
        before sending.

        Args:
            job_data: Dictionary representation of a JobRecord.
            webhook_url: The target webhook URL.
            webhook_secret: Optional HMAC secret.

        Returns:
            True if delivered successfully.
        """
        job = JobRecord(**job_data)
        return await self.notify(job, webhook_url, webhook_secret)
