"""Unit tests for security utilities."""

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    get_password_hash,
    verify_password,
    verify_password_reset_token,
    verify_token,
)

settings = get_settings()


def test_password_hashing() -> None:
    """Test password hashing and verification."""
    password = "test_password_123"
    hashed = get_password_hash(password)

    # Hash should be different from original
    assert hashed != password

    # Verification should work
    assert verify_password(password, hashed) is True

    # Wrong password should fail
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token() -> None:
    """Test JWT access token creation."""
    data = {"sub": "user@example.com", "role": "admin"}
    token = create_access_token(data)

    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0

    # Should be decodable
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "user@example.com"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_verify_token() -> None:
    """Test JWT token verification."""
    data = {"sub": "user@example.com"}
    token = create_access_token(data)

    # Valid token should decode
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "user@example.com"

    # Invalid token should return None
    invalid_payload = verify_token("invalid.token.here")
    assert invalid_payload is None


def test_password_reset_token() -> None:
    """Test password reset token creation and verification."""
    email = "user@example.com"
    token = create_password_reset_token(email)

    # Token should be valid
    assert isinstance(token, str)
    assert len(token) > 0

    # Should extract email correctly
    extracted_email = verify_password_reset_token(token)
    assert extracted_email == email

    # Invalid token should return None
    assert verify_password_reset_token("invalid.token") is None

    # Regular access token should not work as reset token
    regular_token = create_access_token({"sub": email})
    assert verify_password_reset_token(regular_token) is None
