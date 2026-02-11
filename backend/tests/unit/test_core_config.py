"""Unit tests for core configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_settings_default_values() -> None:
    """Test that Settings loads with default values."""
    settings = Settings()
    assert settings.APP_NAME == "inferbox"
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 480
    assert settings.POHODA_ICO == "04856562"
    assert settings.POHODA_XML_VERSION == "2.0"
    assert settings.POHODA_APPLICATION == "INFER_FORGE"


def test_settings_singleton() -> None:
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


def test_settings_database_url_validation() -> None:
    """Test that DATABASE_URL must be a valid PostgreSQL URL."""
    # Valid URL
    settings = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db")
    assert "postgresql" in str(settings.DATABASE_URL)

    # Invalid URL should raise ValidationError
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="invalid://url")


def test_settings_redis_url_validation() -> None:
    """Test that REDIS_URL must be a valid Redis URL."""
    # Valid URL
    settings = Settings(REDIS_URL="redis://localhost:6379/0")
    assert "redis" in str(settings.REDIS_URL)

    # Invalid URL should raise ValidationError
    with pytest.raises(ValidationError):
        Settings(REDIS_URL="invalid://url")
