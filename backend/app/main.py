"""FastAPI application entry point for INFER FORGE backend.

Configures middleware, routes, and lifecycle events.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db, get_logger, get_settings
from app.core.database import close_db, init_db
from app.core.health import check_database, check_redis, get_version

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Runs on startup and shutdown to manage resources.
    """
    # Startup
    logger.info("application_startup", app_name=settings.APP_NAME)

    # Initialize database (in production, use Alembic migrations instead)
    if settings.DEBUG:
        await init_db()
        logger.info("database_initialized")

    yield

    # Shutdown
    logger.info("application_shutdown")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Automatizační platforma pro strojírenskou firmu Infer s.r.o.",
    version="0.1.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict[str, Any]:
    """Root endpoint with basic app info.

    Returns:
        dict[str, Any]: App name and version.
    """
    return get_version()


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """Health check endpoint for monitoring.

    Checks database and Redis connectivity.

    Returns:
        JSONResponse: Health status of all services.
    """
    # Get database session
    async for db in get_db():
        db_status = await check_database(db)
        break
    else:
        db_status = {"healthy": False, "service": "database", "error": "No session available"}

    redis_status = await check_redis()

    all_healthy = db_status["healthy"] and redis_status["healthy"]
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "services": [db_status, redis_status],
            "version": get_version(),
        },
    )


@app.get("/health/db", status_code=status.HTTP_200_OK)
async def health_check_db() -> dict[str, Any]:
    """Database-only health check.

    Returns:
        dict[str, Any]: Database connectivity status.
    """
    async for db in get_db():
        return await check_database(db)

    return {"healthy": False, "service": "database", "error": "No session available"}


@app.get("/health/redis", status_code=status.HTTP_200_OK)
async def health_check_redis() -> dict[str, Any]:
    """Redis-only health check.

    Returns:
        dict[str, Any]: Redis connectivity status.
    """
    return await check_redis()


# API v1 routes
from app.api.v1 import customers, documents, inbox, orders, pohoda

app.include_router(customers.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(inbox.router, prefix="/api/v1")
app.include_router(pohoda.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
