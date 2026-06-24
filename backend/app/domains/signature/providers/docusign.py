"""DocuSign eSignature provider implementation — full JWT grant + envelope APIs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from .base import (
    AuditEvent,
    ProviderResponse,
    ProviderStatus,
    SignatureProvider,
    SignerInfo,
    WebhookEvent,
)

logger = logging.getLogger(__name__)

# ── DocuSign API Scopes ─────────────────────────────────────────
# Required for JWT grant: signature (send on behalf of), impersonation
DOCUSIGN_SCOPES = ["signature", "impersonation"]

# Map DocuSign envelope statuses to our internal statuses
DOCUSIGN_STATUS_MAP = {
    "created": "draft",
    "sent": "sent",
    "delivered": "viewed",
    "completed": "completed",
    "declined": "declined",
    "voided": "voided",
    "expired": "expired",
    "signed": "signed",
}


class DocuSignProvider(SignatureProvider):
    """DocuSign eSignature REST API v2.1 provider.

    Uses OAuth2 JWT Grant for application-level authentication.
    No user interaction required after initial consent grant.
    """

    @property
    def provider_name(self) -> str:
        return "docusign"

    def __init__(
        self,
        integration_key: str,
        user_id: str,
        account_id: str,
        private_key: str,
        client_secret: str = "",
        base_url: str = "https://demo.docusign.net/restapi",
        auth_server: str = "account-d.docusign.com",
    ):
        self.integration_key = integration_key
        self.user_id = user_id
        self.account_id = account_id
        self.private_key = private_key
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self.auth_server = auth_server
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    # ── JWT Consent Grant ───────────────────────────────────────

    def get_consent_url(self, redirect_uri: str = "https://www.docusign.com") -> str:
        """Generate the consent URL for initial JWT grant authorization.

        The user (DocuSign admin) must visit this URL once to grant consent.
        After consent is granted, the application can generate tokens via JWT.

        Args:
            redirect_uri: Where DocuSign redirects after consent

        Returns:
            Full consent URL to open in a browser
        """
        params = {
            "response_type": "code",
            "scope": " ".join(DOCUSIGN_SCOPES),
            "client_id": self.integration_key,
            "redirect_uri": redirect_uri,
        }
        qs = urlencode(params)
        return f"https://{self.auth_server}/oauth/auth?{qs}"

    # ── JWT Token Generation ────────────────────────────────────

    def _build_jwt_assertion(self) -> str:
        """Build a JWT assertion for the OAuth2 token request.

        The JWT is signed with the RSA private key and contains:
        - iss: integration key (client ID)
        - sub: user ID (the impersonated user)
        - aud: the auth server URL
        - iat: issued at time
        - exp: expiration (1 hour max)
        - scope: requested scopes
        """
        from jose import jwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        from cryptography.hazmat.backends import default_backend

        now = int(time.time())
        payload = {
            "iss": self.integration_key,
            "sub": self.user_id,
            "aud": self.auth_server,
            "iat": now,
            "exp": now + 3600,  # 1 hour
            "scope": " ".join(DOCUSIGN_SCOPES),
        }
        # Normalize the private key — handle various formats:
        key = self.private_key
        if "\\n" in key:
            key = key.replace("\\n", "\n")
        key = key.strip()
        if not key.startswith("-----BEGIN"):
            key = f"-----BEGIN RSA PRIVATE KEY-----\n{key}\n-----END RSA PRIVATE KEY-----"

        # python-jose requires PKCS#8 format for RSA private keys.
        # Convert from traditional PEM to PKCS#8.
        rsa_key = load_pem_private_key(key.encode("utf-8"), password=None, backend=default_backend())
        pkcs8_key = rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        return jwt.encode(payload, pkcs8_key, algorithm="RS256")

    async def _ensure_authenticated(self) -> str:
        """Get or refresh OAuth2 JWT access token.

        Uses the JWT grant flow:
        1. Build a JWT assertion signed with the RSA private key
        2. Exchange it for an access token via POST /oauth/token
        3. Cache the token until it expires

        Returns:
            Bearer access token string
        """
        now = time.time()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        assertion = self._build_jwt_assertion()
        token_url = f"https://{self.auth_server}/oauth/token"

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code == 401:
            error_body = response.text
            if "consent_required" in error_body:
                raise PermissionError(
                    "DocuSign consent not granted. "
                    "An admin must visit the consent URL first. "
                    f"Generate it via GET /api/v1/signatures/docusign/consent-url"
                )
            raise PermissionError(
                f"DocuSign authentication failed (401): {error_body}"
            )

        response.raise_for_status()
        token_data = response.json()

        self._access_token = token_data["access_token"]
        self._token_expires_at = now + token_data.get("expires_in", 3600)

        logger.info("DocuSign JWT token obtained (expires in %ss)", token_data.get("expires_in", 3600))
        return self._access_token

    # ── Envelope API ────────────────────────────────────────────

    async def send_envelope(
        self,
        document_bytes: bytes,
        document_name: str,
        signers: list[SignerInfo],
        email_subject: str,
        email_body: str,
        expires_at: Optional[datetime] = None,
        signing_order_enabled: bool = True,
    ) -> ProviderResponse:
        """Create and send a DocuSign envelope.

        Args:
            document_bytes: The PDF document content
            document_name: Name for the document in the envelope
            signers: List of recipients
            email_subject: Subject line for signature emails
            email_body: Body text for signature emails
            expires_at: When the envelope expires
            signing_order_enabled: If True, signers must sign in order

        Returns:
            ProviderResponse with envelope ID and signing URLs
        """
        token = await self._ensure_authenticated()

        # Encode document as base64
        doc_base64 = base64.b64encode(document_bytes).decode("utf-8")

        # Build document definition
        document = {
            "documentBase64": doc_base64,
            "name": document_name,
            "fileExtension": "pdf",
            "documentId": "1",
        }

        # Build recipients
        recipients = {
            "signers": [
                {
                    "email": s.email,
                    "name": s.name,
                    "recipientId": str(i + 1),
                    "routingOrder": str(s.signing_order) if signing_order_enabled else "1",
                    "deliveryMethod": "email",
                    "roleName": s.role,
                    # If client_user_id is set, enable embedded/captive signing.
                    # DocuSign will NOT email the signer — the app must present
                    # the signing URL via _get_recipient_view_url.
                    **({"clientUserId": s.client_user_id} if s.client_user_id else {}),
                }
                for i, s in enumerate(signers)
            ]
        }

        # Build event notifications for webhooks
        # TODO: Configure webhook URL from settings
        event_notifications = {
            "url": "",  # Will be set when webhook endpoint is configured
            "loggingEnabled": True,
            "requireAcknowledgment": True,
            "useSoapInterface": False,
            "includeCertificateWithSoap": False,
            "includeDocumentFields": True,
            "includeEnvelopeVoidReason": True,
            "includeTimeZone": True,
            "includeSenderAccountAsCustomField": True,
            "envelopeEvents": [
                {"envelopeEventStatusCode": "sent"},
                {"envelopeEventStatusCode": "delivered"},
                {"envelopeEventStatusCode": "completed"},
                {"envelopeEventStatusCode": "declined"},
                {"envelopeEventStatusCode": "voided"},
            ],
            "recipientEvents": [
                {"recipientEventStatusCode": "Sent"},
                {"recipientEventStatusCode": "Delivered"},
                {"recipientEventStatusCode": "Completed"},
                {"recipientEventStatusCode": "Declined"},
            ],
        }

        # Build envelope definition
        envelope = {
            "emailSubject": email_subject,
            "emailBlurb": email_body,
            "status": "sent",
            "documents": [document],
            "recipients": recipients,
            "eventNotifications": [event_notifications],
        }

        if expires_at:
            envelope["expireEnabled"] = "true"
            envelope["expireAfter"] = str(int((expires_at - datetime.now(timezone.utc)).days))
            envelope["expireWarn"] = str(max(1, int((expires_at - datetime.now(timezone.utc)).days) - 5))

        # Send to DocuSign
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=envelope,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code == 401:
            # Token may have expired — clear and retry once
            self._access_token = None
            token = await self._ensure_authenticated()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=envelope,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )

        response.raise_for_status()
        result = response.json()

        envelope_id = result["envelopeId"]
        logger.info("DocuSign envelope created: %s", envelope_id)

        # Get signing URLs for each recipient
        signing_urls: dict[str, str] = {}
        for signer in signers:
            try:
                url = await self._get_recipient_view_url(envelope_id, signer, token)
                signing_urls[signer.email] = url
            except Exception as e:
                logger.warning("Could not get signing URL for %s: %s", signer.email, e)

        return ProviderResponse(
            envelope_id=envelope_id,
            status="sent",
            signing_urls=signing_urls,
            expires_at=expires_at,
            raw_response=result,
        )

    async def _get_recipient_view_url(
        self, envelope_id: str, signer: SignerInfo, token: str
    ) -> str:
        """Get the embedded signing URL for a recipient.

        Requires that the signer was created with a ``clientUserId`` in the
        envelope definition.  If the envelope was sent without ``clientUserId``
        (email delivery), DocuSign returns 400 — callers should fall back to
        the email invitation link from the envelope status.
        """
        # The clientUserId MUST match what was set on the recipient at
        # envelope creation time.  If it was not set, embedded signing is
        # not available for this recipient.
        if not signer.client_user_id:
            raise ValueError(
                f"Signer {signer.email} has no client_user_id — "
                "embedded signing URL unavailable. "
                "Use email delivery instead."
            )

        view_request = {
            "returnUrl": "https://www.docusign.com",
            "authenticationMethod": "email",
            "email": signer.email,
            "userName": signer.name,
            "clientUserId": signer.client_user_id,
            "recipientId": signer.recipient_id or "1",
        }
        url = (
            f"{self.base_url}/v2.1/accounts/{self.account_id}"
            f"/envelopes/{envelope_id}/views/recipient"
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=view_request,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        response.raise_for_status()
        return response.json().get("url", "")

    # ── Envelope Status ─────────────────────────────────────────

    async def get_envelope_status(self, envelope_id: str) -> ProviderStatus:
        """Get the current status of a DocuSign envelope."""
        token = await self._ensure_authenticated()
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        data = response.json()

        status = DOCUSIGN_STATUS_MAP.get(data.get("status", ""), data.get("status", "unknown"))

        # Get recipient statuses
        signers = []
        recipients = data.get("recipients", {}).get("signers", [])
        for r in recipients:
            signers.append({
                "email": r.get("email", ""),
                "name": r.get("name", ""),
                "status": DOCUSIGN_STATUS_MAP.get(r.get("status", ""), r.get("status", "unknown")),
                "signed_at": r.get("signedDateTime"),
            })

        return ProviderStatus(
            envelope_id=envelope_id,
            status=status,
            signers=signers,
            last_updated=datetime.now(timezone.utc),
            raw_status=data,
        )

    # ── Void Envelope ───────────────────────────────────────────

    async def void_envelope(self, envelope_id: str, reason: str) -> bool:
        """Void a DocuSign envelope."""
        token = await self._ensure_authenticated()
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}"
        body = {
            "voidedReason": reason,
            "status": "voided",
        }
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        response.raise_for_status()
        logger.info("DocuSign envelope voided: %s", envelope_id)
        return True

    # ── Signing URL ─────────────────────────────────────────────

    async def get_signing_url(self, envelope_id: str, recipient_id: str) -> str:
        """Get the embedded signing URL for a recipient.

        Args:
            envelope_id: The DocuSign envelope ID
            recipient_id: The recipient's email address (used as clientUserId)

        Returns:
            The signing URL to redirect the user to
        """
        token = await self._ensure_authenticated()
        # We need the recipient info — fetch it from the envelope
        status = await self.get_envelope_status(envelope_id)
        signer_info = next(
            (s for s in status.signers if s.get("email") == recipient_id),
            None,
        )
        if not signer_info:
            raise ValueError(f"Recipient {recipient_id} not found in envelope {envelope_id}")

        signer = SignerInfo(
            email=signer_info["email"],
            name=signer_info["name"],
        )
        return await self._get_recipient_view_url(envelope_id, signer, token)

    # ── Certificate ─────────────────────────────────────────────

    async def get_certificate(self, envelope_id: str) -> bytes:
        """Get the DocuSign completion certificate as PDF."""
        token = await self._ensure_authenticated()
        url = (
            f"{self.base_url}/v2.1/accounts/{self.account_id}"
            f"/envelopes/{envelope_id}/documents/certificate"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        return response.content

    # ── Audit Trail ─────────────────────────────────────────────

    async def get_audit_trail(self, envelope_id: str) -> list[AuditEvent]:
        """Get the DocuSign audit trail events."""
        token = await self._ensure_authenticated()
        url = (
            f"{self.base_url}/v2.1/accounts/{self.account_id}"
            f"/envelopes/{envelope_id}/audit_events"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        data = response.json()

        events = []
        for event in data.get("auditEvents", []):
            events.append(AuditEvent(
                event_type=event.get("eventType", "unknown"),
                actor_email=event.get("userEmail"),
                actor_name=event.get("userName"),
                action=event.get("eventType", ""),
                timestamp=datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00")) if "eventDate" in event else datetime.now(timezone.utc),
                ip_address=event.get("ipAddress"),
                details=event,
            ))
        return events

    # ── Webhook Validation ──────────────────────────────────────

    def validate_webhook(self, headers: dict, body: bytes) -> WebhookEvent:
        """Validate and parse a DocuSign Connect webhook.

        Validates the HMAC signature in the X-DocuSign-Signature-1 header
        using the Connect HMAC key.

        Args:
            headers: Request headers (must include X-DocuSign-Signature-1)
            body: Raw request body

        Returns:
            Parsed WebhookEvent
        """
        # Validate HMAC signature
        signature = headers.get("x-docusign-signature-1", "")
        if signature:
            # Compute expected HMAC
            secret = self.client_secret.encode("utf-8")
            expected = base64.b64encode(
                hmac.new(secret, body, hashlib.sha256).digest()
            ).decode("utf-8")
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Invalid DocuSign webhook HMAC signature")

        # Parse the webhook payload
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid DocuSign webhook payload: {e}")

        # Extract envelope info from the payload
        envelope_data = {}
        try:
            envelope_data = payload["event"]["envelope"]
        except (KeyError, TypeError):
            try:
                # Alternative payload format
                envelope_data = payload.get("envelopeSummary", {}).get("envelope", {})
            except (KeyError, TypeError):
                pass

        envelope_id = envelope_data.get("envelopeId", "")
        status = DOCUSIGN_STATUS_MAP.get(
            envelope_data.get("status", ""), envelope_data.get("status", "unknown")
        )

        # Extract recipient info
        recipient_email = None
        recipient_name = None
        try:
            recipients = (
                payload.get("event", {})
                .get("envelope", {})
                .get("recipients", {})
                .get("signers", [])
            ) or (
                payload.get("envelopeSummary", {})
                .get("envelope", {})
                .get("recipients", {})
                .get("signers", [])
            ) or []
            if recipients:
                recipient_email = recipients[0].get("email")
                recipient_name = recipients[0].get("userName")
        except (KeyError, IndexError):
            pass

        return WebhookEvent(
            event_type=f"envelope_{status}",
            envelope_id=envelope_id,
            status=status,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            event_timestamp=datetime.now(timezone.utc),
            raw_event=payload,
        )
