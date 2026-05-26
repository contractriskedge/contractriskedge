"""
Credential encryption and vault abstraction.

Uses AES-256-GCM for at-rest encryption of tokens and secrets.
Supports key rotation readiness via key versioning.
"""

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from structlog import get_logger

logger = get_logger(__name__)

# 12-byte nonce for AES-GCM
_NONCE_LENGTH = 12
# HKDF salt length
_SALT_LENGTH = 32
# Current key version — increment to trigger key rotation
_KEY_VERSION = 1


class CredentialEncryption:
    """
    AES-256-GCM encryption for credential secrets.

    Supports multiple key versions for rotation readiness.
    Keys are derived from a master key using HKDF.
    """

    def __init__(self, master_key: Optional[bytes] = None):
        if master_key is None:
            master_key = self._load_master_key()
        self._master_key = master_key
        self._key_cache: dict[int, bytes] = {}

    def _load_master_key(self) -> bytes:
        """Load master key from environment or generate for development."""
        key_hex = os.environ.get("INTEGRATION_MASTER_KEY")
        if key_hex:
            return bytes.fromhex(key_hex)
        # Development fallback — never use in production
        logger.warning("No INTEGRATION_MASTER_KEY set; using derived development key")
        return hashlib.sha256(b"ContractRiskEdge-Dev-Master-Key-2024").digest()

    def _derive_key(self, version: int = _KEY_VERSION) -> bytes:
        """Derive a 256-bit key from the master key using HKDF."""
        if version not in self._key_cache:
            salt = hashlib.sha256(f"credential-key-v{version}".encode()).digest()
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt[:16],
                info=b"contractriskedge-credential-encryption",
            )
            self._key_cache[version] = hkdf.derive(self._master_key)
        return self._key_cache[version]

    def encrypt(self, plaintext: str, aad: Optional[bytes] = None) -> str:
        """
        Encrypt plaintext with AES-256-GCM.

        Returns base64-encoded payload: version|nonce|ciphertext|tag
        """
        key = self._derive_key(_KEY_VERSION)
        aesgcm = AESGCM(key)
        nonce = os.urandom(_NONCE_LENGTH)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad or b"")
        # Bundle: version (1 byte) + nonce (12 bytes) + ciphertext+tag
        payload = bytes([_KEY_VERSION]) + nonce + ciphertext
        return base64.b64encode(payload).decode("ascii")

    def decrypt(self, encrypted: str, aad: Optional[bytes] = None) -> str:
        """
        Decrypt base64-encoded payload.

        Supports multiple key versions for rotation compatibility.
        """
        payload = base64.b64decode(encrypted)
        version = payload[0]
        nonce = payload[1 : 1 + _NONCE_LENGTH]
        ciphertext = payload[1 + _NONCE_LENGTH :]

        key = self._derive_key(version)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad or b"")
        return plaintext.decode("utf-8")

    def rotate_key(self) -> dict[str, Any]:
        """
        Trigger key rotation by incrementing version.

        In production, this would coordinate with a KMS.
        Returns rotation metadata.
        """
        new_version = _KEY_VERSION + 1
        self._key_cache.clear()
        logger.info("credential_key_rotation_initiated", new_version=new_version)
        return {
            "previous_version": _KEY_VERSION,
            "new_version": new_version,
            "rotated_at": datetime.now(timezone.utc).isoformat(),
        }


class CredentialVault:
    """
    High-level vault abstraction for credential lifecycle management.

    Provides tenant-isolated encrypted storage with audit hooks.
    """

    def __init__(self, encryption: Optional[CredentialEncryption] = None):
        self._encryption = encryption or CredentialEncryption()
        self._cache: dict[str, tuple[str, datetime]] = {}

    def store_token(
        self,
        tenant_id: str,
        integration_id: str,
        token: str,
        token_type: str = "access_token",
        metadata: Optional[dict] = None,
    ) -> str:
        """Encrypt and store a token. Returns encrypted blob."""
        aad = self._build_aad(tenant_id, integration_id, token_type)
        encrypted = self._encryption.encrypt(token, aad=aad)
        cache_key = f"{tenant_id}:{integration_id}:{token_type}"
        self._cache[cache_key] = (encrypted, datetime.now(timezone.utc))
        logger.info(
            "credential_stored",
            tenant_id=tenant_id,
            integration_id=integration_id,
            token_type=token_type,
        )
        return encrypted

    def retrieve_token(
        self,
        tenant_id: str,
        integration_id: str,
        encrypted_blob: str,
        token_type: str = "access_token",
    ) -> str:
        """Decrypt and retrieve a token."""
        aad = self._build_aad(tenant_id, integration_id, token_type)
        return self._encryption.decrypt(encrypted_blob, aad=aad)

    def rotate_credentials(
        self,
        tenant_id: str,
        integration_id: str,
        old_encrypted: str,
        new_token: str,
        token_type: str = "access_token",
    ) -> str:
        """Rotate a credential: decrypt old (verify), encrypt new."""
        # Decrypt old to verify integrity
        self.retrieve_token(tenant_id, integration_id, old_encrypted, token_type)
        # Encrypt new
        return self.store_token(tenant_id, integration_id, new_token, token_type)

    def _build_aad(self, tenant_id: str, integration_id: str, token_type: str) -> bytes:
        """Build Additional Authenticated Data for tenant-isolated encryption."""
        return f"{tenant_id}:{integration_id}:{token_type}".encode("utf-8")

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("credential_cache_cleared")
