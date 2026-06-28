"""Signature provider factory — creates provider instances from settings.

All provider instantiation should go through this factory rather than
directly constructing DocuSignProvider, AdobeSignProvider, etc.
This ensures the abstraction is maintained when adding new providers.
"""

from __future__ import annotations

from app.config import settings

from .base import SignatureProvider
from .docusign import DocuSignProvider
from .adobe import AdobeSignProvider
from .dropbox import DropboxSignProvider
from .dev_auto_sign import DevAutoSignProvider


def create_provider(provider_name: str = "docusign") -> SignatureProvider:
    """Create a signature provider instance based on the provider name.

    Args:
        provider_name: One of "docusign", "adobe_sign", "dropbox_sign", "dev_auto_sign"

    Returns:
        A configured SignatureProvider instance

    Raises:
        ValueError: If provider_name is unknown
    """
    if provider_name == "docusign":
        return DocuSignProvider(
            integration_key=settings.docusign_integration_key,
            user_id=settings.docusign_user_id,
            account_id=settings.docusign_account_id,
            private_key=settings.docusign_private_key,
            client_secret=settings.docusign_client_secret,
            base_url=settings.docusign_base_url,
            auth_server=settings.docusign_auth_server,
        )
    elif provider_name == "adobe_sign":
        return AdobeSignProvider()
    elif provider_name == "dropbox_sign":
        return DropboxSignProvider()
    elif provider_name == "dev_auto_sign":
        return DevAutoSignProvider()
    else:
        raise ValueError(
            f"Unknown signature provider: '{provider_name}'. "
            f"Supported providers: docusign, adobe_sign, dropbox_sign, dev_auto_sign"
        )


__all__ = ["create_provider"]
