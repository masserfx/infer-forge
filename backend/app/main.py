"""FastAPI application entry point for INFER FORGE backend.

Configures middleware, routes, and lifecycle events.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core import get_db, get_logger, get_settings
from app.core.database import close_db, init_db
from app.core.health import check_database, check_redis, get_version
from app.core.sentry import init_sentry

# Initialize Sentry (before app creation)
init_sentry()

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

    # Initialize WebSocket manager with Redis pub/sub
    from app.core.websocket import manager

    await manager.initialize()
    logger.info("websocket_manager_initialized")

    yield

    # Shutdown
    logger.info("application_shutdown")
    await manager.close()
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Automatizační platforma pro strojírenskou firmu Infer s.r.o.",
    version="0.1.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
    redirect_slashes=False,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self, request: StarletteRequest, call_next: Any
    ) -> StarletteResponse:
        """Process request and add security headers to response."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Request logging middleware
from app.core.middleware import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)

# Prometheus metrics middleware
from app.core.prometheus_middleware import PrometheusMiddleware

app.add_middleware(PrometheusMiddleware)


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


# Prometheus metrics endpoint
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response as StarletteResponse


@app.get("/metrics")
async def metrics() -> StarletteResponse:
    """Prometheus metrics endpoint."""
    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# API v1 routes
from app.api.v1 import (
    auth,
    calculations,
    customers,
    documents,
    gamification,
    inbox,
    notifications,
    orders,
    pohoda,
    reporting,
    websocket,
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(calculations.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(inbox.router, prefix="/api/v1")
app.include_router(pohoda.router, prefix="/api/v1")
app.include_router(reporting.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(gamification.router, prefix="/api/v1")
app.include_router(websocket.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
