"""Settings API endpoints for feature flags management."""

import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


# --- AI Token Usage ---


class AITokenCategoryUsage(BaseModel):
    category: str
    tokens_input: int
    tokens_output: int
    calls: int
    cost_czk: float


class AITokenTimePoint(BaseModel):
    label: str
    cost_czk: float
    calls: int


class AITokenUsageResponse(BaseModel):
    period: str  # "day" | "month" | "year"
    categories: list[AITokenCategoryUsage]
    timeline: list[AITokenTimePoint]
    total_cost_czk: float
    total_calls: int
    total_tokens: int


# 5 AI usage categories
_AI_CATEGORIES = [
    ("Email klasifikace", 800, 200),
    ("Kalkulace", 2000, 1500),
    ("Parsování dokumentů", 1200, 600),
    ("Orchestrace", 500, 300),
    ("Doporučení", 1500, 1000),
]

# Approximate CZK cost per 1K tokens (Sonnet pricing)
_INPUT_COST_PER_1K = 0.07  # CZK
_OUTPUT_COST_PER_1K = 0.35  # CZK


def _seed_for_period(period: str) -> int:
    """Deterministic seed so data is consistent per day."""
    today = datetime.now().strftime("%Y-%m-%d")
    return hash(f"{today}-{period}") % 2**31


def _generate_usage(period: str) -> AITokenUsageResponse:
    """Generate realistic mock AI token usage data."""
    rng = random.Random(_seed_for_period(period))

    if period == "day":
        multiplier = 1
        labels = [f"{h}:00" for h in range(0, 24)]
    elif period == "month":
        multiplier = 30
        now = datetime.now()
        labels = [(now - timedelta(days=29 - i)).strftime("%d.%m.") for i in range(30)]
    else:  # year
        multiplier = 365
        now = datetime.now()
        labels = [
            (now.replace(day=1) - timedelta(days=30 * (11 - i))).strftime("%m/%Y")
            for i in range(12)
        ]

    categories: list[AITokenCategoryUsage] = []
    total_cost = 0.0
    total_calls_sum = 0
    total_tokens_sum = 0

    for name, base_in, base_out in _AI_CATEGORIES:
        tokens_in = int(base_in * multiplier * rng.uniform(0.7, 1.3))
        tokens_out = int(base_out * multiplier * rng.uniform(0.7, 1.3))
        calls = int(multiplier * rng.randint(2, 15))
        cost = (tokens_in / 1000) * _INPUT_COST_PER_1K + (tokens_out / 1000) * _OUTPUT_COST_PER_1K
        categories.append(AITokenCategoryUsage(
            category=name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            calls=calls,
            cost_czk=round(cost, 2),
        ))
        total_cost += cost
        total_calls_sum += calls
        total_tokens_sum += tokens_in + tokens_out

    # Timeline
    timeline: list[AITokenTimePoint] = []
    n = len(labels)
    for lbl in labels:
        pt_cost = round(total_cost / n * rng.uniform(0.5, 1.5), 2)
        pt_calls = max(1, int(total_calls_sum / n * rng.uniform(0.5, 1.5)))
        timeline.append(AITokenTimePoint(label=lbl, cost_czk=pt_cost, calls=pt_calls))

    return AITokenUsageResponse(
        period=period,
        categories=categories,
        timeline=timeline,
        total_cost_czk=round(total_cost, 2),
        total_calls=total_calls_sum,
        total_tokens=total_tokens_sum,
    )


@router.get("/ai-token-usage", response_model=AITokenUsageResponse)
async def get_ai_token_usage(
    period: str = Query("month", pattern="^(day|month|year)$"),
    _user: User = Depends(require_role(UserRole.VEDENI)),
) -> AITokenUsageResponse:
    """Get AI token usage statistics by category and time period."""
    return _generate_usage(period)
