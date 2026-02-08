"""AES-256-GCM encryption for document storage at rest."""

import base64
import logging
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Nonce size for AES-GCM (96 bits / 12 bytes is standard)
NONCE_SIZE = 12

# Prefix to identify encrypted files
ENCRYPTED_PREFIX = b"ENC1"  # 4 bytes marker


def get_encryption_key() -> bytes | None:
    """Get AES-256 encryption key from settings.

    Returns:
        32-byte key or None if not configured
    """
    settings = get_settings()
    key_str = getattr(settings, "DOCUMENT_ENCRYPTION_KEY", None)
    if not key_str:
        return None

    try:
        key = base64.b64decode(key_str)
        if len(key) != 32:
            logger.error("DOCUMENT_ENCRYPTION_KEY must be 32 bytes (256 bits), got %d bytes", len(key))
            return None
        return key
    except Exception as e:
        logger.error("Invalid DOCUMENT_ENCRYPTION_KEY: %s", str(e))
        return None


def generate_encryption_key() -> str:
    """Generate a new AES-256 key and return as base64 string.

    Returns:
        Base64-encoded 32-byte key
    """
    key = secrets.token_bytes(32)
    return base64.b64encode(key).decode("ascii")


def encrypt_data(plaintext: bytes) -> bytes:
    """Encrypt data with AES-256-GCM.

    If no encryption key is configured, returns plaintext unchanged.

    Format: ENCRYPTED_PREFIX + nonce (12 bytes) + ciphertext + tag (16 bytes)

    Args:
        plaintext: Data to encrypt

    Returns:
        Encrypted data with prefix, nonce, and auth tag
    """
    key = get_encryption_key()
    if key is None:
        return plaintext

    nonce = secrets.token_bytes(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return ENCRYPTED_PREFIX + nonce + ciphertext


def decrypt_data(data: bytes) -> bytes:
    """Decrypt AES-256-GCM encrypted data.

    If data doesn't start with ENCRYPTED_PREFIX, returns as-is (unencrypted file).
    If no encryption key is configured, returns data as-is.

    Args:
        data: Potentially encrypted data

    Returns:
        Decrypted plaintext

    Raises:
        ValueError: If encrypted data is corrupted or key is wrong
    """
    # Check if data is encrypted
    if not data.startswith(ENCRYPTED_PREFIX):
        return data

    key = get_encryption_key()
    if key is None:
        logger.warning("Encrypted file found but DOCUMENT_ENCRYPTION_KEY not set")
        raise ValueError("Cannot decrypt: DOCUMENT_ENCRYPTION_KEY not configured")

    # Strip prefix
    encrypted = data[len(ENCRYPTED_PREFIX):]

    if len(encrypted) < NONCE_SIZE + 16:  # nonce + minimum tag
        raise ValueError("Encrypted data too short")

    nonce = encrypted[:NONCE_SIZE]
    ciphertext = encrypted[NONCE_SIZE:]

    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}") from e


def is_encrypted(data: bytes) -> bool:
    """Check if data has the encryption prefix."""
    return data.startswith(ENCRYPTED_PREFIX)
