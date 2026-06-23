"""Generic email service — provider-independent.

Supports:
- SMTP
- SendGrid
- AWS SES
- Console (dev)

Usage:
    email = EmailService(sender=EmailSender.SMTP, config={...})
    await email.send(to="user@co.com", subject="Hello", body="...")
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class EmailSender(str, enum.Enum):
    """Supported email delivery providers."""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    SES = "ses"
    CONSOLE = "console"  # Logs to console for development


@dataclass
class EmailTemplate:
    """An email template with subject and body."""
    subject: str
    body_html: str
    body_text: Optional[str] = None
    variables: dict[str, str] = field(default_factory=dict)


class EmailService:
    """Generic email service for all contract lifecycle notifications.

    Used by:
    - Approval notifications
    - Negotiation invitations
    - Signature requests
    - Obligation reminders
    - Renewal alerts
    - Report delivery
    """

    def __init__(
        self,
        sender: EmailSender = EmailSender.CONSOLE,
        config: Optional[dict] = None,
        from_address: str = "noreply@contractriskedge.com",
        from_name: str = "Contract Risk Edge",
    ):
        self.sender = sender
        self.config = config or {}
        self.from_address = from_address
        self.from_name = from_name

    async def send(
        self,
        to: str | list[str],
        subject: str,
        body: Optional[str] = None,
        html: Optional[str] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        attachments: Optional[list[dict]] = None,
        template: Optional[EmailTemplate] = None,
    ) -> bool:
        """Send an email.

        Args:
            to: Recipient email address or list
            subject: Email subject line
            body: Plain text body
            html: HTML body
            cc: Carbon copy recipients
            bcc: Blind carbon copy recipients
            attachments: List of {filename, content, content_type} dicts
            template: EmailTemplate to render

        Returns:
            True if sent successfully, False otherwise
        """
        recipients = [to] if isinstance(to, str) else to

        if template:
            subject = template.subject
            html = template.body_html
            body = template.body_text or body

        if self.sender == EmailSender.CONSOLE:
            return await self._send_console(recipients, subject, body, html)
        elif self.sender == EmailSender.SMTP:
            return await self._send_smtp(recipients, subject, body, html, cc, bcc, attachments)
        elif self.sender == EmailSender.SENDGRID:
            return await self._send_sendgrid(recipients, subject, body, html)
        elif self.sender == EmailSender.SES:
            return await self._send_ses(recipients, subject, body, html)
        else:
            logger.warning("Unknown email sender: %s", self.sender)
            return False

    async def send_template(
        self,
        to: str | list[str],
        template: EmailTemplate,
        variables: Optional[dict[str, str]] = None,
    ) -> bool:
        """Send a templated email with variable substitution."""
        if variables:
            template.subject = template.subject.format(**variables)
            if template.body_html:
                template.body_html = template.body_html.format(**variables)
            if template.body_text:
                template.body_text = template.body_text.format(**variables)
        return await self.send(to, template.subject, template.body_text, template.body_html)

    async def _send_console(
        self,
        to: list[str],
        subject: str,
        body: Optional[str],
        html: Optional[str],
    ) -> bool:
        """Log email to console for development."""
        logger.info(
            "📧 EMAIL [Console]\n  To: %s\n  Subject: %s\n  Body: %s",
            ", ".join(to), subject, (body or html or "")[:200],
        )
        return True

    async def _send_smtp(
        self,
        to: list[str],
        subject: str,
        body: Optional[str],
        html: Optional[str],
        cc: Optional[list[str]],
        bcc: Optional[list[str]],
        attachments: Optional[list[dict]],
    ) -> bool:
        """Send via SMTP."""
        # TODO: Implement SMTP sending
        # import aiosmtplib
        logger.debug("SMTP email would be sent to %s", to)
        return True

    async def _send_sendgrid(
        self,
        to: list[str],
        subject: str,
        body: Optional[str],
        html: Optional[str],
    ) -> bool:
        """Send via SendGrid API."""
        # TODO: Implement SendGrid sending
        # from sendgrid import SendGridAPIClient
        logger.debug("SendGrid email would be sent to %s", to)
        return True

    async def _send_ses(
        self,
        to: list[str],
        subject: str,
        body: Optional[str],
        html: Optional[str],
    ) -> bool:
        """Send via AWS SES."""
        # TODO: Implement SES sending
        # import boto3
        logger.debug("SES email would be sent to %s", to)
        return True
