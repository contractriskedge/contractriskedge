"""Email intake plugin for Gmail and Outlook auto-ingestion.

Detects contract attachments in emails and triggers ingestion
via the platform API. Supports Gmail API and Microsoft Graph.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmailProvider(str, Enum):
    """Supported email providers."""

    GMAIL = "gmail"
    OUTLOOK = "outlook"
    IMAP = "imap"


@dataclass
class EmailAttachment:
    """An email attachment detected as a contract document."""

    filename: str
    content_type: str
    size_bytes: int
    content_base64: str
    is_contract: bool = False
    detection_confidence: float = 0.0


@dataclass
class InboundEmail:
    """An inbound email that may contain contract attachments."""

    message_id: str
    from_address: str
    from_name: str
    subject: str
    body_text: str
    attachments: List[EmailAttachment] = field(default_factory=list)
    provider: EmailProvider = EmailProvider.GMAIL


class ContractEmailDetector:
    """Detects contract-related emails and attachments.

    Uses keyword matching and file extension analysis to identify
    contract documents in email attachments.

    Usage:
        detector = ContractEmailDetector()
        email = InboundEmail(...)
        if detector.should_process(email):
            # Trigger ingestion
    """

    # File extensions that are likely contracts
    CONTRACT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".rtf"}

    # Email subject keywords suggesting contract content
    CONTRACT_SUBJECT_KEYWORDS = [
        "contract", "agreement", "msa", "nda", "sow", "eula",
        "license", "addendum", "amendment", "terms", "order form",
        "statement of work", "proposal", "renewal", "signature",
        "contrato", "acuerdo", "vertrag", "vereinbarung",
    ]

    # Sender domains that are pre-approved (configurable per tenant)
    APPROVED_SENDER_DOMAINS: List[str] = []

    def __init__(self) -> None:
        """Initialize the email detector."""
        pass

    def should_process(self, email: InboundEmail) -> bool:
        """Determine if an email should trigger ingestion.

        Args:
            email: The inbound email to check.

        Returns:
            True if the email should be processed.
        """
        # Check subject for contract keywords
        subject_lower = email.subject.lower()
        has_keyword = any(kw in subject_lower for kw in self.CONTRACT_SUBJECT_KEYWORDS)

        # Check for contract attachments
        has_contract_attachment = any(
            self._is_contract_file(att.filename)
            for att in email.attachments
        )

        return has_keyword or has_contract_attachment

    def detect_attachments(self, email: InboundEmail) -> List[EmailAttachment]:
        """Detect and mark contract attachments in an email.

        Args:
            email: The inbound email.

        Returns:
            List of attachments marked as contracts.
        """
        for att in email.attachments:
            att.is_contract = self._is_contract_file(att.filename)
            att.detection_confidence = 0.9 if att.is_contract else 0.0
        return [att for att in email.attachments if att.is_contract]

    @staticmethod
    def _is_contract_file(filename: str) -> bool:
        """Check if a filename suggests a contract document.

        Args:
            filename: The attachment filename.

        Returns:
            True if it looks like a contract document.
        """
        ext = os.path.splitext(filename)[1].lower()
        return ext in ContractEmailDetector.CONTRACT_EXTENSIONS

    @staticmethod
    def extract_sender_domain(email_address: str) -> str:
        """Extract the domain from an email address.

        Args:
            email_address: Email address.

        Returns:
            Domain portion of the email.
        """
        match = re.search(r'@([\w.-]+)', email_address)
        return match.group(1) if match else ""


class EmailIntakeAPI:
    """API for email-based contract intake.

    Provides endpoints for Gmail/Outlook plugins to submit
    emails for contract detection and ingestion.

    Usage:
        intake = EmailIntakeAPI()
        result = await intake.process_inbound_email(email_data)
    """

    def __init__(self) -> None:
        """Initialize the email intake API."""
        self._detector = ContractEmailDetector()
        self._processed: Dict[str, Dict[str, Any]] = {}

    async def process_inbound_email(
        self,
        email_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process an inbound email for contract ingestion.

        Args:
            email_data: Email data from Gmail/Outlook plugin.

        Returns:
            Processing result with detected contracts.
        """
        import uuid

        # Parse email
        email = InboundEmail(
            message_id=email_data.get("message_id", str(uuid.uuid4())),
            from_address=email_data.get("from_address", ""),
            from_name=email_data.get("from_name", ""),
            subject=email_data.get("subject", ""),
            body_text=email_data.get("body_text", ""),
            provider=EmailProvider(email_data.get("provider", "gmail")),
        )

        # Parse attachments
        for att_data in email_data.get("attachments", []):
            email.attachments.append(EmailAttachment(
                filename=att_data.get("filename", ""),
                content_type=att_data.get("content_type", ""),
                size_bytes=att_data.get("size_bytes", 0),
                content_base64=att_data.get("content_base64", ""),
            ))

        # Detect contracts
        contract_attachments = self._detector.detect_attachments(email)
        should_process = self._detector.should_process(email)

        result = {
            "message_id": email.message_id,
            "should_process": should_process,
            "contracts_detected": len(contract_attachments),
            "attachments": [
                {
                    "filename": att.filename,
                    "is_contract": att.is_contract,
                    "confidence": att.detection_confidence,
                    "size_bytes": att.size_bytes,
                }
                for att in email.attachments
            ],
            "sender_domain": ContractEmailDetector.extract_sender_domain(email.from_address),
        }

        self._processed[email.message_id] = result
        return result
