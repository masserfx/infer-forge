"""Tests for AES-256-GCM document encryption."""

import base64
import os
from unittest.mock import patch

import pytest

from app.core.encryption import (
    ENCRYPTED_PREFIX,
    decrypt_data,
    encrypt_data,
    generate_encryption_key,
    is_encrypted,
)


@pytest.fixture
def encryption_key():
    """Generate a test encryption key."""
    return base64.b64encode(os.urandom(32)).decode("ascii")


@pytest.fixture
def mock_settings_with_key(encryption_key):
    """Mock settings with encryption key."""
    with patch("app.core.encryption.get_settings") as mock:
        mock.return_value.DOCUMENT_ENCRYPTION_KEY = encryption_key
        yield mock


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self, mock_settings_with_key):
        plaintext = b"Tajny dokument s vykresy zakaznika"
        encrypted = encrypt_data(plaintext)

        assert encrypted != plaintext
        assert encrypted.startswith(ENCRYPTED_PREFIX)

        decrypted = decrypt_data(encrypted)
        assert decrypted == plaintext

    def test_encrypt_large_file(self, mock_settings_with_key):
        plaintext = os.urandom(1024 * 1024)  # 1MB
        encrypted = encrypt_data(plaintext)
        decrypted = decrypt_data(encrypted)
        assert decrypted == plaintext

    def test_decrypt_unencrypted_data(self, mock_settings_with_key):
        plaintext = b"Not encrypted data"
        result = decrypt_data(plaintext)
        assert result == plaintext

    def test_is_encrypted(self, mock_settings_with_key):
        plaintext = b"Hello"
        encrypted = encrypt_data(plaintext)
        assert is_encrypted(encrypted) is True
        assert is_encrypted(plaintext) is False

    def test_no_key_passthrough(self):
        with patch("app.core.encryption.get_settings") as mock:
            mock.return_value.DOCUMENT_ENCRYPTION_KEY = ""
            plaintext = b"No encryption"
            result = encrypt_data(plaintext)
            assert result == plaintext

    def test_generate_key(self):
        key = generate_encryption_key()
        decoded = base64.b64decode(key)
        assert len(decoded) == 32

    def test_wrong_key_fails(self, encryption_key):
        # Encrypt with one key
        with patch("app.core.encryption.get_settings") as mock:
            mock.return_value.DOCUMENT_ENCRYPTION_KEY = encryption_key
            encrypted = encrypt_data(b"secret")

        # Try to decrypt with different key
        wrong_key = base64.b64encode(os.urandom(32)).decode("ascii")
        with patch("app.core.encryption.get_settings") as mock:
            mock.return_value.DOCUMENT_ENCRYPTION_KEY = wrong_key
            with pytest.raises(ValueError, match="Decryption failed"):
                decrypt_data(encrypted)

    def test_corrupted_data_fails(self, mock_settings_with_key):
        encrypted = encrypt_data(b"data")
        corrupted = encrypted[:-5] + b"XXXXX"
        with pytest.raises(ValueError):
            decrypt_data(corrupted)
