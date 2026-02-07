"""Security utilities for authentication and authorization.

Provides JWT token creation/verification and password hashing using industry standards.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Bcrypt hashed password from database.

    Returns:
        bool: True if password matches, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a plain password using bcrypt.

    Args:
        password: Plain text password to hash.

    Returns:
        str: Bcrypt hashed password safe to store in database.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token (e.g., {"sub": user_id}).
        expires_delta: Optional custom expiration time.
            Defaults to ACCESS_TOKEN_EXPIRE_MINUTES from settings.

    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string to verify.

    Returns:
        dict[str, Any] | None: Decoded token payload if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def create_password_reset_token(email: str) -> str:
    """Create a short-lived JWT token for password reset.

    Args:
        email: User email address to include in token.

    Returns:
        str: JWT token valid for 30 minutes.
    """
    delta = timedelta(minutes=30)
    return create_access_token(data={"sub": email, "type": "password_reset"}, expires_delta=delta)


def verify_password_reset_token(token: str) -> str | None:
    """Verify a password reset token and extract email.

    Args:
        token: Password reset JWT token.

    Returns:
        str | None: Email address if token is valid, None otherwise.
    """
    payload = verify_token(token)
    if payload is None:
        return None

    if payload.get("type") != "password_reset":
        return None

    email = payload.get("sub")
    if not isinstance(email, str):
        return None

    return email
