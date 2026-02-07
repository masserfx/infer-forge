"""User model for authentication and RBAC."""

import enum

from sqlalchemy import Boolean, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class UserRole(str, enum.Enum):
    """User role enum for RBAC."""

    ADMIN = "admin"
    OBCHODNIK = "obchodnik"
    TECHNOLOG = "technolog"
    VEDENI = "vedeni"
    UCETNI = "ucetni"


class User(Base, UUIDPKMixin, TimestampMixin):
    """Application user with role-based access."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20),
        nullable=False,
        default=UserRole.OBCHODNIK,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role={self.role.value})>"
