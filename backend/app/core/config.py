"""Application configuration using Pydantic Settings.

All configuration values are loaded from environment variables or .env file.
Singleton pattern ensures config is loaded only once.
"""

from functools import lru_cache
from typing import ClassVar

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All sensitive values (API keys, passwords) should be set via .env file
    or environment variables, never hardcoded.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "INFER FORGE"
    ENVIRONMENT: str = Field(default="development", description="Environment (development, staging, production)")
    DEBUG: bool = False

    # Database
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://infer:infer@localhost:5432/infer_forge",
        description="PostgreSQL connection string with asyncpg driver",
    )

    # Redis
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for Celery and caching",
    )

    # Security
    SECRET_KEY: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_USE_RANDOM_STRING",
        description="Secret key for JWT token signing - must be random in production",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Anthropic Claude API
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic API key for Claude AI agents",
    )

    # Email - IMAP
    IMAP_HOST: str = Field(
        default="",
        description="IMAP server hostname",
    )
    IMAP_PORT: int = Field(
        default=993,
        description="IMAP server port (typically 993 for SSL)",
    )
    IMAP_USER: str = Field(
        default="",
        description="IMAP username/email",
    )
    IMAP_PASSWORD: str = Field(
        default="",
        description="IMAP password",
    )
    IMAP_USE_SSL: bool = True

    # Email - SMTP
    SMTP_HOST: str = Field(
        default="",
        description="SMTP server hostname",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port (typically 587 for STARTTLS, 465 for SSL)",
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP username/email",
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP password",
    )
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = Field(
        default="",
        description="Default sender email address",
    )

    # Pohoda integration
    POHODA_ICO: str = Field(
        default="04856562",
        description="IČO firmy Infer s.r.o. pro Pohoda XML",
    )
    POHODA_MSERVER_URL: str = Field(
        default="",
        description="URL mServer API pro odesílání XML do Pohody",
    )
    POHODA_XML_VERSION: str = "2.0"
    POHODA_APPLICATION: str = "INFER_FORGE"

    # Sentry monitoring (optional)
    SENTRY_DSN: str = Field(
        default="",
        description="Sentry DSN for error tracking (optional)",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings singleton.

    Returns:
        Settings: Application configuration instance.
    """
    return Settings()
