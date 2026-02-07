"""Health check utilities for monitoring application status.

Provides endpoints and functions to verify database, Redis, and service health.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

settings = get_settings()


async def check_database(db: AsyncSession) -> dict[str, Any]:
    """Check database connectivity and basic query execution.

    Args:
        db: Database session to test.

    Returns:
        dict[str, Any]: Status dictionary with 'healthy' boolean and optional error.
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        return {"healthy": True, "service": "database"}
    except Exception as e:
        return {"healthy": False, "service": "database", "error": str(e)}


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity.

    Returns:
        dict[str, Any]: Status dictionary with 'healthy' boolean and optional error.
    """
    try:
        from redis.asyncio import from_url

        redis = await from_url(str(settings.REDIS_URL))
        await redis.ping()
        await redis.close()
        return {"healthy": True, "service": "redis"}
    except Exception as e:
        return {"healthy": False, "service": "redis", "error": str(e)}


def get_version() -> dict[str, str]:
    """Get application version information.

    Returns:
        dict[str, str]: Version and app name.
    """
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
    }
