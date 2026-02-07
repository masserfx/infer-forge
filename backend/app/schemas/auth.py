"""Authentication and user management schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    """Login credentials."""

    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserCreate(BaseModel):
    """Create new user (admin only)."""

    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.OBCHODNIK
    phone: str | None = None


class UserUpdate(BaseModel):
    """Update user."""

    full_name: str | None = None
    role: UserRole | None = None
    phone: str | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    """Change password."""

    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class UserResponse(BaseModel):
    """User response (no password)."""

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    phone: str | None = None

    model_config = {"from_attributes": True}
