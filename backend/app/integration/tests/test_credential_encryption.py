"""
Tests for credential encryption and vault abstraction.

Covers:
- AES-256-GCM encryption/decryption
- Tenant-isolated encryption (AAD)
- Key rotation readiness
- Credential vault operations
"""

import base64
import os

import pytest

from app.integration.services.crypto import CredentialEncryption, CredentialVault


class TestCredentialEncryption:
    """Tests for the CredentialEncryption utility."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test basic encrypt/decrypt roundtrip."""
        encryption = CredentialEncryption(master_key=os.urandom(32))
        plaintext = "my-super-secret-api-key-12345"

        encrypted = encryption.encrypt(plaintext)
        assert encrypted != plaintext
        assert isinstance(encrypted, str)

        decrypted = encryption.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertexts(self):
        """Test that same plaintext produces different ciphertexts (nonce)."""
        encryption = CredentialEncryption(master_key=os.urandom(32))
        plaintext = "same-value"

        ct1 = encryption.encrypt(plaintext)
        ct2 = encryption.encrypt(plaintext)

        assert ct1 != ct2

    def test_decrypt_with_wrong_key_fails(self):
        """Test that wrong key cannot decrypt."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)

        encryption1 = CredentialEncryption(master_key=key1)
        encryption2 = CredentialEncryption(master_key=key2)

        encrypted = encryption1.encrypt("secret-data")

        with pytest.raises(Exception):
            encryption2.decrypt(encrypted)

    def test_encrypted_format(self):
        """Test encrypted payload format: version(1) + nonce(12) + ciphertext."""
        encryption = CredentialEncryption(master_key=os.urandom(32))
        encrypted = encryption.encrypt("test")

        payload = base64.b64decode(encrypted)
        assert len(payload) > 13  # version(1) + nonce(12) + ciphertext
        assert payload[0] == 1  # version byte

    def test_aad_integrity(self):
        """Test that AAD mismatch causes decryption failure."""
        encryption = CredentialEncryption(master_key=os.urandom(32))
        plaintext = "tenant-specific-secret"

        encrypted = encryption.encrypt(plaintext, aad=b"tenant-a:int-1")
        decrypted = encryption.decrypt(encrypted, aad=b"tenant-a:int-1")
        assert decrypted == plaintext

        # Wrong AAD
        with pytest.raises(Exception):
            encryption.decrypt(encrypted, aad=b"tenant-b:int-1")

    def test_key_rotation_readiness(self):
        """Test key rotation returns metadata."""
        encryption = CredentialEncryption(master_key=os.urandom(32))
        result = encryption.rotate_key()

        assert "previous_version" in result
        assert "new_version" in result
        assert "rotated_at" in result


class TestCredentialVault:
    """Tests for the CredentialVault abstraction."""

    def test_store_and_retrieve_token(self):
        """Test storing and retrieving tokens via vault."""
        vault = CredentialVault()
        encrypted = vault.store_token(
            tenant_id="tenant-1",
            integration_id="int-1",
            token="my-access-token",
            token_type="access_token",
        )

        assert encrypted is not None
        assert isinstance(encrypted, str)

        decrypted = vault.retrieve_token(
            tenant_id="tenant-1",
            integration_id="int-1",
            encrypted_blob=encrypted,
            token_type="access_token",
        )
        assert decrypted == "my-access-token"

    def test_tenant_isolation(self):
        """Test that tokens are isolated by tenant."""
        vault = CredentialVault()

        encrypted = vault.store_token(
            tenant_id="tenant-a",
            integration_id="int-1",
            token="secret-a",
        )

        # Wrong tenant should fail
        with pytest.raises(Exception):
            vault.retrieve_token(
                tenant_id="tenant-b",
                integration_id="int-1",
                encrypted_blob=encrypted,
            )

    def test_rotate_credentials(self):
        """Test credential rotation."""
        vault = CredentialVault()

        old_encrypted = vault.store_token(
            tenant_id="tenant-1",
            integration_id="int-1",
            token="old-token",
        )

        new_encrypted = vault.rotate_credentials(
            tenant_id="tenant-1",
            integration_id="int-1",
            old_encrypted=old_encrypted,
            new_token="new-token",
        )

        assert old_encrypted != new_encrypted

        # New token is retrievable
        decrypted = vault.retrieve_token(
            tenant_id="tenant-1",
            integration_id="int-1",
            encrypted_blob=new_encrypted,
        )
        assert decrypted == "new-token"

    def test_clear_cache(self):
        """Test cache clearing."""
        vault = CredentialVault()
        vault.store_token("t1", "i1", "token")
        vault.clear_cache()
        # Should not raise
        assert True

    def test_different_token_types(self):
        """Test storing different token types."""
        vault = CredentialVault()

        access = vault.store_token("t1", "i1", "access", token_type="access_token")
        refresh = vault.store_token("t1", "i1", "refresh", token_type="refresh_token")

        # Different types should produce different ciphertexts
        assert access != refresh

        # Each type retrieves correctly
        assert vault.retrieve_token("t1", "i1", access, "access_token") == "access"
        assert vault.retrieve_token("t1", "i1", refresh, "refresh_token") == "refresh"
