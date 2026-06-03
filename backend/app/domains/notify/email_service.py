"""Resend email service — sends transactional emails via Resend API.

Uses the Resend Python SDK. Falls back silently when RESEND_API_KEY is empty
(development mode without email).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Raised when email sending fails after all retries."""


@dataclass
class EmailMessage:
    """Represents an email to be sent via Resend."""
    to: str
    subject: str
    html: str
    from_email: str = ""
    from_name: str = ""


class ResendEmailService:
    """Sends transactional emails via the Resend API.

    Usage:
        svc = ResendEmailService()
        await svc.send(EmailMessage(to="user@example.com", subject="...", html="..."))
    """

    def __init__(self):
        self._api_key = settings.resend_api_key
        self._from_email = settings.resend_from_email
        self._from_name = settings.resend_from_name
        self._client = None

    @property
    def _client_available(self) -> bool:
        return bool(self._api_key)

    async def _get_client(self):
        """Lazy-init Resend client."""
        if self._client is None and self._client_available:
            try:
                import resend
                resend.api_key = self._api_key
                self._client = resend
            except ImportError:
                logger.warning("resend package not installed. Install with: pip install resend")
                return None
        return self._client

    async def send(self, message: EmailMessage) -> Optional[str]:
        """Send an email. Returns provider_message_id on success, None on failure.

        In development mode without RESEND_API_KEY, logs the email instead of sending.
        """
        if not self._client_available:
            logger.warning(
                "[EMAIL NOT SENT] RESEND_API_KEY is not set. "
                "Set RESEND_API_KEY in .env to deliver to %s | Subject: %s",
                message.to,
                message.subject,
            )
            return None

        client = await self._get_client()
        if not client:
            logger.warning("Resend client not available — email not sent to %s", message.to)
            return None

        try:
            params = {
                "from": f"{self._from_name} <{self._from_email}>",
                "to": [message.to],
                "subject": message.subject,
                "html": message.html,
            }
            response = client.Emails.send(params)
            message_id = response.get("id")
            logger.info("Email sent to %s: id=%s", message.to, message_id)
            return message_id
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", message.to, exc)
            raise EmailError(f"Resend API error: {exc}") from exc
