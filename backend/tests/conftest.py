"""Pytest configuration and shared fixtures.

Provides test database, async client, and mock settings.
"""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import all models so they register with Base.metadata
import app.models  # noqa: F401
from app.core.config import Settings
from app.api.deps import get_db
from app.core.database import Base

# Test database URL (use in-memory SQLite with shared cache for fast tests)
# file::memory:?cache=shared allows multiple connections to share the same in-memory DB
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with in-memory SQLite.

    Uses StaticPool to share a single connection for in-memory SQLite,
    ensuring tables created in create_all are visible to sessions.

    Yields:
        AsyncSession: Test database session.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create a single session for the test
    async with async_session_maker() as session:
        yield session
        # Note: No explicit commit here - test controls transactions

    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with test database.

    Args:
        test_db: Test database session.

    Yields:
        AsyncClient: httpx async client for testing FastAPI.
    """
    from app.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        # Return the same test_db session without commit/rollback
        # This allows test to control transactions
        try:
            yield test_db
        except Exception:
            # Don't rollback - let test handle it
            raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _mock_rate_limiter_and_circuit_breaker() -> Generator[None, None, None]:
    """Mock rate limiter and circuit breaker so tests don't need Redis."""
    mock_limiter = MagicMock()
    mock_limiter.acquire.return_value = True
    mock_limiter.release.return_value = None
    mock_limiter.record_usage.return_value = None

    with (
        patch("app.core.rate_limiter.get_rate_limiter", return_value=mock_limiter),
        patch("app.core.circuit_breaker.anthropic_breaker") as mock_breaker,
    ):
        mock_breaker.can_execute.return_value = True
        mock_breaker.record_success.return_value = None
        mock_breaker.record_failure.return_value = None
        yield


@pytest.fixture(scope="function")
def test_settings() -> Settings:
    """Create test settings with safe defaults.

    Returns:
        Settings: Test configuration.
    """
    return Settings(
        DEBUG=True,
        DATABASE_URL=TEST_DATABASE_URL,  # type: ignore[arg-type]
        REDIS_URL="redis://localhost:6379/15",  # type: ignore[arg-type]
        SECRET_KEY="test_secret_key_not_for_production",
        ANTHROPIC_API_KEY="test_key",
    )
