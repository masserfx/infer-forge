"""Settings API endpoints for feature flags management."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/nastaveni", tags=["Nastavení"])


class FeatureFlagsResponse(BaseModel):
    ORCHESTRATION_ENABLED: bool
    ORCHESTRATION_AUTO_CREATE_ORDERS: bool
    ORCHESTRATION_AUTO_CALCULATE: bool
    ORCHESTRATION_AUTO_OFFER: bool
    POHODA_AUTO_SYNC: bool


class FeatureFlagsUpdate(BaseModel):
    ORCHESTRATION_ENABLED: bool | None = None
    ORCHESTRATION_AUTO_CREATE_ORDERS: bool | None = None
    ORCHESTRATION_AUTO_CALCULATE: bool | None = None
    ORCHESTRATION_AUTO_OFFER: bool | None = None
    POHODA_AUTO_SYNC: bool | None = None


class IntegrationStatus(BaseModel):
    name: str
    status: str  # "connected" | "disconnected" | "configured"
    details: str | None = None


@router.get("/flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    _user: User = Depends(require_role(UserRole.VEDENI)),
) -> FeatureFlagsResponse:
    """Get current feature flags configuration."""
    from app.core.config import get_settings
    settings = get_settings()

    return FeatureFlagsResponse(
        ORCHESTRATION_ENABLED=settings.ORCHESTRATION_ENABLED,
        ORCHESTRATION_AUTO_CREATE_ORDERS=settings.ORCHESTRATION_AUTO_CREATE_ORDERS,
        ORCHESTRATION_AUTO_CALCULATE=settings.ORCHESTRATION_AUTO_CALCULATE,
        ORCHESTRATION_AUTO_OFFER=settings.ORCHESTRATION_AUTO_OFFER,
        POHODA_AUTO_SYNC=getattr(settings, "POHODA_AUTO_SYNC", False),
    )


@router.patch("/flags", response_model=FeatureFlagsResponse)
async def update_feature_flags(
    data: FeatureFlagsUpdate,
    _user: User = Depends(require_role(UserRole.VEDENI)),
) -> FeatureFlagsResponse:
    """Update feature flags (admin/vedeni only).

    Note: Changes are stored in Redis for persistence across restarts.
    Environment variables take precedence on initial load.
    """
    import redis

    from app.core.config import get_settings

    settings = get_settings()

    # Store in Redis for persistence
    try:
        redis_url = str(settings.REDIS_URL)
        r = redis.from_url(redis_url)  # type: ignore[no-untyped-call]

        update_data = data.model_dump(exclude_none=True)
        for key, value in update_data.items():
            r.set(f"feature_flag:{key}", str(int(value)))
            # Also update the settings singleton
            object.__setattr__(settings, key, value)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update flags: {str(e)}",
        ) from e

    return FeatureFlagsResponse(
        ORCHESTRATION_ENABLED=settings.ORCHESTRATION_ENABLED,
        ORCHESTRATION_AUTO_CREATE_ORDERS=settings.ORCHESTRATION_AUTO_CREATE_ORDERS,
        ORCHESTRATION_AUTO_CALCULATE=settings.ORCHESTRATION_AUTO_CALCULATE,
        ORCHESTRATION_AUTO_OFFER=settings.ORCHESTRATION_AUTO_OFFER,
        POHODA_AUTO_SYNC=getattr(settings, "POHODA_AUTO_SYNC", False),
    )


@router.get("/integrations", response_model=list[IntegrationStatus])
async def get_integration_status(
    _user: User = Depends(require_role(UserRole.VEDENI)),
) -> list[IntegrationStatus]:
    """Get status of all integrations."""
    from app.core.config import get_settings
    settings = get_settings()

    integrations = []

    # Pohoda
    pohoda_status = "configured" if settings.POHODA_MSERVER_URL else "disconnected"
    integrations.append(IntegrationStatus(
        name="Pohoda XML API",
        status=pohoda_status,
        details=settings.POHODA_MSERVER_URL or None,
    ))

    # Email
    email_status = "configured" if settings.IMAP_HOST and settings.SMTP_HOST else "disconnected"
    integrations.append(IntegrationStatus(
        name="E-mail (IMAP/SMTP)",
        status=email_status,
        details=settings.IMAP_HOST or None,
    ))

    # AI (Anthropic)
    ai_status = "connected" if settings.ANTHROPIC_API_KEY else "disconnected"
    integrations.append(IntegrationStatus(
        name="AI Claude (Anthropic)",
        status=ai_status,
    ))

    # Redis
    try:
        from app.core.health import check_redis
        redis_result = await check_redis()
        redis_status = "connected" if redis_result.get("healthy") else "disconnected"
    except Exception:
        redis_status = "disconnected"
    integrations.append(IntegrationStatus(
        name="Redis",
        status=redis_status,
    ))

    return integrations
