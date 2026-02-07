"""FastAPI dependencies for database, auth, and RBAC."""

from collections.abc import AsyncGenerator, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import verify_token
from app.models.user import User, UserRole
from app.services.auth import AuthService

security_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session.

    Yields:
        AsyncSession: Database session that will be automatically closed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate current user from JWT Bearer token.

    Raises:
        HTTPException 401: If token is missing, invalid, or user not found.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Přihlášení je vyžadováno",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatný nebo expirovaný token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatný token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    service = AuthService(db)
    user = await service.get_by_id(UUID(user_id_str))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Uživatel nenalezen nebo deaktivován",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if token is provided, None otherwise.

    Does not raise on missing/invalid token — useful for public endpoints
    that behave differently for authenticated users.
    """
    if credentials is None:
        return None

    payload = verify_token(credentials.credentials)
    if payload is None:
        return None

    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None

    service = AuthService(db)
    user = await service.get_by_id(UUID(user_id_str))
    if user is None or not user.is_active:
        return None

    return user


def require_role(*roles: UserRole) -> Callable[..., User]:
    """Create a dependency that enforces role-based access.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...

    Args:
        *roles: Allowed roles. ADMIN always has access.

    Returns:
        Dependency function that validates user role.
    """
    async def _check_role(
        user: User = Depends(get_current_user),
    ) -> User:
        allowed = set(roles) | {UserRole.ADMIN}
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nedostatečná oprávnění. Vyžadovaná role: "
                f"{', '.join(r.value for r in roles)}",
            )
        return user

    return _check_role
