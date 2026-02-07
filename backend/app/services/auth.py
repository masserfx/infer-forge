"""Authentication and user management service."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and user management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate user by email and password.

        Returns the user if credentials are valid, None otherwise.
        """
        user = await self.get_by_email(email)
        if user is None:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        logger.info("user_authenticated email=%s", email)
        return user

    def create_token(self, user: User) -> str:
        """Create JWT access token for user."""
        return create_access_token(
            data={"sub": str(user.id), "role": user.role.value},
        )

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email),
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id),
        )
        return result.scalar_one_or_none()

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            role=data.role,
            phone=data.phone,
        )
        self.db.add(user)
        await self.db.flush()
        logger.info("user_created email=%s role=%s", data.email, data.role.value)
        return user

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User | None:
        """Update user fields."""
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        logger.info("user_updated user_id=%s fields=%s", user_id, list(update_data.keys()))
        return user

    async def change_password(self, user: User, new_password: str) -> None:
        """Change user password."""
        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
        logger.info("password_changed user_id=%s", user.id)

    async def get_all(self, skip: int = 0, limit: int = 50) -> list[User]:
        """List all users."""
        result = await self.db.execute(
            select(User).order_by(User.full_name).offset(skip).limit(limit),
        )
        return list(result.scalars().all())
