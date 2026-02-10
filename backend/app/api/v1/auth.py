"""Authentication API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.auth import AuthService

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autentizace"])

_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 60
_LOGIN_KEY_PREFIX = "login_attempts"


def _get_redis():
    """Get Redis client for login rate limiting."""
    from redis import Redis
    from app.core.config import get_settings
    settings = get_settings()
    return Redis.from_url(str(settings.REDIS_URL), decode_responses=True)


def _check_login_rate(client_ip: str) -> None:
    """Check login rate limit for a given IP using Redis. Raises 429 if exceeded."""
    try:
        redis = _get_redis()
        key = f"{_LOGIN_KEY_PREFIX}:{client_ip}"
        current = int(redis.get(key) or 0)
        if current >= _MAX_LOGIN_ATTEMPTS:
            _logger.warning("login_rate_limit_exceeded ip=%s attempts=%d", client_ip, current)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Příliš mnoho pokusů o přihlášení. Zkuste to za minutu.",
            )
    except HTTPException:
        raise
    except Exception:
        _logger.warning("redis_unavailable_for_rate_limit ip=%s", client_ip)


def _record_failed_login(client_ip: str) -> None:
    """Record a failed login attempt in Redis."""
    try:
        redis = _get_redis()
        key = f"{_LOGIN_KEY_PREFIX}:{client_ip}"
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, _LOGIN_WINDOW_SECONDS)
        pipe.execute()
    except Exception:
        _logger.warning("redis_unavailable_for_rate_limit ip=%s", client_ip)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Přihlášení uživatele.

    Vrací JWT token pro autentizaci dalších požadavků.
    Rate limited: max 5 pokusů za 60 sekund na IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate(client_ip)

    service = AuthService(db)
    user = await service.authenticate(data.email, data.password)
    if user is None:
        _record_failed_login(client_ip)
        _logger.warning("login_failed email=%s ip=%s", data.email, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nesprávný email nebo heslo",
        )

    token = service.create_token(user)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
) -> UserResponse:
    """Vrátí profil přihlášeného uživatele."""
    return UserResponse.model_validate(user)


@router.put("/me/password")
async def change_my_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Změna hesla přihlášeného uživatele."""
    from app.core.security import verify_password

    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stávající heslo je nesprávné",
        )

    service = AuthService(db)
    await service.change_password(user, data.new_password)
    return {"message": "Heslo bylo změněno"}


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    _admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Vytvoření nového uživatele (pouze admin)."""
    service = AuthService(db)

    existing = await service.get_by_email(data.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Uživatel s emailem {data.email} již existuje",
        )

    user = await service.create_user(data)
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    _admin: User = Depends(require_role(UserRole.ADMIN, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """Seznam uživatelů (admin a vedení)."""
    service = AuthService(db)
    users = await service.get_all(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    _admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Aktualizace uživatele (pouze admin)."""
    service = AuthService(db)
    user = await service.update_user(user_id, data)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uživatel nenalezen",
        )
    return UserResponse.model_validate(user)
