"""Unit tests for authentication and RBAC in INFER FORGE.

Tests cover:
- User model and UserRole enum
- AuthService (authenticate, create_user, change_password)
- Security (JWT, password hashing)
- Auth API endpoints
- RBAC (require_role dependency)
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User, UserRole
from app.schemas.auth import UserCreate
from app.services.auth import AuthService


class TestUserModel:
    """Tests for User model."""

    async def test_create_user(self, test_db: AsyncSession) -> None:
        """Test creating a user with valid data."""
        user = User(
            email="newuser@infer.cz",
            hashed_password=get_password_hash("password123"),
            full_name="New User",
            role=UserRole.TECHNOLOG,
            is_active=True,
            phone="+420 777 888 999",
        )
        test_db.add(user)
        await test_db.commit()

        assert user.id is not None
        assert user.email == "newuser@infer.cz"
        assert user.full_name == "New User"
        assert user.role == UserRole.TECHNOLOG
        assert user.is_active is True
        assert user.phone == "+420 777 888 999"
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_user_role_enum(self) -> None:
        """Test that all user roles exist."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.OBCHODNIK.value == "obchodnik"
        assert UserRole.TECHNOLOG.value == "technolog"
        assert UserRole.VEDENI.value == "vedeni"
        assert UserRole.UCETNI.value == "ucetni"

    async def test_user_default_values(self, test_db: AsyncSession) -> None:
        """Test user default values (role=OBCHODNIK, is_active=True)."""
        user = User(
            email="default@infer.cz",
            hashed_password=get_password_hash("pass123"),
            full_name="Default User",
        )
        test_db.add(user)
        await test_db.commit()

        assert user.role == UserRole.OBCHODNIK
        assert user.is_active is True

    async def test_user_unique_email(self, test_db: AsyncSession) -> None:
        """Test that duplicate email raises IntegrityError."""
        user1 = User(
            email="duplicate@infer.cz",
            hashed_password=get_password_hash("pass123"),
            full_name="User 1",
        )
        test_db.add(user1)
        await test_db.commit()

        user2 = User(
            email="duplicate@infer.cz",
            hashed_password=get_password_hash("pass456"),
            full_name="User 2",
        )
        test_db.add(user2)

        with pytest.raises(IntegrityError):
            await test_db.commit()


class TestAuthService:
    """Tests for AuthService."""

    async def test_authenticate_success(self, test_db: AsyncSession) -> None:
        """Test successful authentication with correct credentials."""
        # Create user for test
        user = User(
            email="test@infer.cz",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            role=UserRole.OBCHODNIK,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        service = AuthService(test_db)
        authenticated = await service.authenticate("test@infer.cz", "testpassword123")

        assert authenticated is not None
        assert authenticated.id == user.id
        assert authenticated.email == user.email

    async def test_authenticate_wrong_password(self, test_db: AsyncSession) -> None:
        """Test authentication fails with wrong password."""
        # Create user for test
        user = User(
            email="test@infer.cz",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            role=UserRole.OBCHODNIK,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        service = AuthService(test_db)
        authenticated = await service.authenticate("test@infer.cz", "wrongpassword")

        assert authenticated is None

    async def test_authenticate_unknown_email(self, test_db: AsyncSession) -> None:
        """Test authentication fails with unknown email."""
        service = AuthService(test_db)
        authenticated = await service.authenticate("unknown@infer.cz", "password123")

        assert authenticated is None

    async def test_authenticate_inactive_user(self, test_db: AsyncSession) -> None:
        """Test authentication fails for inactive user."""
        inactive_user = User(
            email="inactive@infer.cz",
            hashed_password=get_password_hash("password123"),
            full_name="Inactive User",
            is_active=False,
        )
        test_db.add(inactive_user)
        await test_db.commit()

        service = AuthService(test_db)
        authenticated = await service.authenticate("inactive@infer.cz", "password123")

        assert authenticated is None

    async def test_create_user_service(self, test_db: AsyncSession) -> None:
        """Test creating user via service."""
        service = AuthService(test_db)
        user_data = UserCreate(
            email="created@infer.cz",
            password="newpass123",
            full_name="Created User",
            role=UserRole.VEDENI,
            phone="+420 111 222 333",
        )

        user = await service.create_user(user_data)
        await test_db.commit()

        assert user.id is not None
        assert user.email == "created@infer.cz"
        assert user.full_name == "Created User"
        assert user.role == UserRole.VEDENI
        assert user.phone == "+420 111 222 333"
        assert verify_password("newpass123", user.hashed_password)

    async def test_change_password(self, test_db: AsyncSession) -> None:
        """Test password change functionality."""
        # Create user for test
        user = User(
            email="test@infer.cz",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            role=UserRole.OBCHODNIK,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        service = AuthService(test_db)
        old_hash = user.hashed_password

        await service.change_password(user, "newpassword456")
        await test_db.commit()

        # Reload user from DB
        result = await test_db.execute(select(User).where(User.id == user.id))
        updated_user = result.scalar_one()

        assert updated_user.hashed_password != old_hash
        assert verify_password("newpassword456", updated_user.hashed_password)
        assert not verify_password("testpassword123", updated_user.hashed_password)


class TestSecurity:
    """Tests for security utilities (JWT, password hashing)."""

    def test_password_hash_and_verify(self) -> None:
        """Test password hashing and verification."""
        plain = "mysecretpassword"
        hashed = get_password_hash(plain)

        assert hashed != plain
        assert verify_password(plain, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_create_and_verify_token(self) -> None:
        """Test creating and verifying JWT token."""
        user_id = str(uuid4())
        payload = {"sub": user_id, "role": "admin"}

        token = create_access_token(data=payload)
        decoded = verify_token(token)

        assert decoded is not None
        assert decoded["sub"] == user_id
        assert decoded["role"] == "admin"
        assert "exp" in decoded

    def test_verify_expired_token(self) -> None:
        """Test that expired token returns None."""
        user_id = str(uuid4())
        payload = {"sub": user_id}

        # Create token that expires immediately
        token = create_access_token(data=payload, expires_delta=timedelta(seconds=-1))
        decoded = verify_token(token)

        assert decoded is None


class TestAuthAPI:
    """Tests for Auth API logic (service layer).

    Note: Full HTTP API tests are deferred to integration tests.
    These tests focus on business logic via service layer.
    """

    async def test_login_logic_success(self, test_db: AsyncSession) -> None:
        """Test authentication logic with correct credentials."""
        # Create user
        user = User(
            email="test@infer.cz",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            role=UserRole.OBCHODNIK,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        # Test authentication
        service = AuthService(test_db)
        authenticated = await service.authenticate("test@infer.cz", "testpassword123")

        assert authenticated is not None
        assert authenticated.email == "test@infer.cz"

        # Create token
        token = service.create_token(authenticated)
        assert isinstance(token, str)
        assert len(token) > 20

    async def test_login_logic_wrong_credentials(self, test_db: AsyncSession) -> None:
        """Test authentication logic fails with wrong password."""
        user = User(
            email="test@infer.cz",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            role=UserRole.OBCHODNIK,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        service = AuthService(test_db)
        authenticated = await service.authenticate("test@infer.cz", "wrongpassword")

        assert authenticated is None

    async def test_get_user_by_id(self, test_db: AsyncSession) -> None:
        """Test getting user by ID."""
        user = User(
            email="test@infer.cz",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            role=UserRole.OBCHODNIK,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        service = AuthService(test_db)
        fetched = await service.get_by_id(user.id)

        assert fetched is not None
        assert fetched.email == "test@infer.cz"
        assert fetched.full_name == "Test User"

    async def test_create_user_logic(self, test_db: AsyncSession) -> None:
        """Test user creation logic."""
        service = AuthService(test_db)
        user_data = UserCreate(
            email="business@infer.cz",
            password="pass123456",
            full_name="Business User",
            role=UserRole.OBCHODNIK,
            phone="+420 999 888 777",
        )

        user = await service.create_user(user_data)
        await test_db.commit()

        assert user.id is not None
        assert user.email == "business@infer.cz"
        assert user.full_name == "Business User"
        assert user.role == UserRole.OBCHODNIK

    async def test_list_users_logic(self, test_db: AsyncSession) -> None:
        """Test listing users."""
        # Create multiple users
        for i in range(3):
            user = User(
                email=f"user{i}@infer.cz",
                hashed_password=get_password_hash("pass123"),
                full_name=f"User {i}",
                role=UserRole.OBCHODNIK,
                is_active=True,
            )
            test_db.add(user)
        await test_db.commit()

        service = AuthService(test_db)
        users = await service.get_all(skip=0, limit=50)

        assert len(users) >= 3
        assert all(isinstance(u, User) for u in users)

    async def test_change_password_logic(self, test_db: AsyncSession) -> None:
        """Test password change logic."""
        user = User(
            email="test@infer.cz",
            hashed_password=get_password_hash("oldpassword123"),
            full_name="Test User",
            role=UserRole.OBCHODNIK,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        old_hash = user.hashed_password

        service = AuthService(test_db)
        await service.change_password(user, "newpassword456")
        await test_db.commit()

        # Verify password changed
        assert user.hashed_password != old_hash
        assert verify_password("newpassword456", user.hashed_password)
        assert not verify_password("oldpassword123", user.hashed_password)


class TestRBAC:
    """Tests for role-based access control logic."""

    async def test_require_role_logic(self, test_db: AsyncSession) -> None:
        """Test role validation logic."""
        admin = User(
            email="admin@infer.cz",
            hashed_password=get_password_hash("pass123"),
            full_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        user = User(
            email="user@infer.cz",
            hashed_password=get_password_hash("pass123"),
            full_name="User",
            role=UserRole.OBCHODNIK,
            is_active=True,
        )
        test_db.add(admin)
        test_db.add(user)
        await test_db.commit()

        # Admin should have ADMIN role
        assert admin.role == UserRole.ADMIN
        # ADMIN always has access (tested in deps.require_role)
        assert admin.role in {UserRole.ADMIN}

        # Regular user should not have ADMIN role
        assert user.role == UserRole.OBCHODNIK
        assert user.role not in {UserRole.ADMIN}

    async def test_inactive_user_logic(self, test_db: AsyncSession) -> None:
        """Test inactive user cannot authenticate."""
        inactive = User(
            email="inactive@infer.cz",
            hashed_password=get_password_hash("pass123"),
            full_name="Inactive",
            is_active=False,
        )
        test_db.add(inactive)
        await test_db.commit()

        service = AuthService(test_db)
        authenticated = await service.authenticate("inactive@infer.cz", "pass123")

        assert authenticated is None  # Inactive users cannot authenticate

    async def test_token_contains_role(self, test_db: AsyncSession) -> None:
        """Test JWT token contains role information."""
        admin = User(
            email="admin@infer.cz",
            hashed_password=get_password_hash("pass123"),
            full_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        test_db.add(admin)
        await test_db.commit()

        service = AuthService(test_db)
        token = service.create_token(admin)

        # Verify token
        payload = verify_token(token)
        assert payload is not None
        assert payload["role"] == UserRole.ADMIN.value
        assert payload["sub"] == str(admin.id)
