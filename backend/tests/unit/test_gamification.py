"""Unit tests for gamification service."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrderStatus, PointsAction, PointsPeriod, User, UserPoints, UserRole
from app.services.gamification import GamificationService


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test user."""
    import bcrypt

    user = User(
        email="test@infer.cz",
        full_name="Test User",
        hashed_password=bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(),
        role=UserRole.OBCHODNIK,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_user2(test_db: AsyncSession) -> User:
    """Create a second test user."""
    import bcrypt

    user = User(
        email="test2@infer.cz",
        full_name="Test User 2",
        hashed_password=bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(),
        role=UserRole.OBCHODNIK,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


class TestGamificationService:
    """Tests for GamificationService."""

    async def test_award_points(self, test_db: AsyncSession, test_user: User) -> None:
        """Test awarding points to a user."""
        service = GamificationService(test_db)
        points_record = await service.award_points(
            user_id=test_user.id,
            action=PointsAction.ORDER_STATUS_CHANGE,
            points=10,
            description="Test points",
            entity_type="order",
            entity_id=uuid.uuid4(),
        )

        assert points_record.id is not None
        assert points_record.user_id == test_user.id
        assert points_record.action == PointsAction.ORDER_STATUS_CHANGE
        assert points_record.points == 10
        assert points_record.description == "Test points"
        assert points_record.entity_type == "order"
        assert points_record.earned_at is not None

    async def test_calculate_order_points(self, test_db: AsyncSession) -> None:
        """Test calculating points for order status transitions."""
        service = GamificationService(test_db)

        # Test all valid transitions
        assert (
            service.calculate_order_points(OrderStatus.POPTAVKA, OrderStatus.NABIDKA) == 5
        )
        assert (
            service.calculate_order_points(OrderStatus.NABIDKA, OrderStatus.OBJEDNAVKA)
            == 10
        )
        assert (
            service.calculate_order_points(OrderStatus.OBJEDNAVKA, OrderStatus.VYROBA) == 5
        )
        assert (
            service.calculate_order_points(OrderStatus.VYROBA, OrderStatus.EXPEDICE) == 10
        )
        assert (
            service.calculate_order_points(OrderStatus.EXPEDICE, OrderStatus.FAKTURACE) == 5
        )
        assert (
            service.calculate_order_points(OrderStatus.FAKTURACE, OrderStatus.DOKONCENO)
            == 20
        )

        # Test invalid transition (should return 0)
        assert (
            service.calculate_order_points(OrderStatus.POPTAVKA, OrderStatus.DOKONCENO) == 0
        )

    async def test_get_leaderboard_all_time(
        self, test_db: AsyncSession, test_user: User, test_user2: User
    ) -> None:
        """Test getting all-time leaderboard."""
        service = GamificationService(test_db)

        # Award points to users
        await service.award_points(
            user_id=test_user.id,
            action=PointsAction.ORDER_STATUS_CHANGE,
            points=50,
            description="User 1 points",
        )
        await service.award_points(
            user_id=test_user.id,
            action=PointsAction.CALCULATION_COMPLETE,
            points=30,
            description="User 1 more points",
        )
        await service.award_points(
            user_id=test_user2.id,
            action=PointsAction.DOCUMENT_UPLOAD,
            points=40,
            description="User 2 points",
        )

        # Get leaderboard
        leaderboard = await service.get_leaderboard(period=PointsPeriod.ALL_TIME, limit=10)

        assert leaderboard.period == "all_time"
        assert leaderboard.total_users == 2
        assert len(leaderboard.entries) == 2

        # Check ranking (user 1 should be first with 80 points)
        first_entry = leaderboard.entries[0]
        assert first_entry.rank == 1
        assert first_entry.user_id == str(test_user.id)
        assert first_entry.total_points == 80
        assert first_entry.tasks_completed == 2

        second_entry = leaderboard.entries[1]
        assert second_entry.rank == 2
        assert second_entry.user_id == str(test_user2.id)
        assert second_entry.total_points == 40
        assert second_entry.tasks_completed == 1

    async def test_get_leaderboard_empty(self, test_db: AsyncSession) -> None:
        """Test getting leaderboard when no points exist."""
        service = GamificationService(test_db)

        leaderboard = await service.get_leaderboard(period=PointsPeriod.ALL_TIME, limit=10)

        assert leaderboard.period == "all_time"
        assert leaderboard.total_users == 0
        assert len(leaderboard.entries) == 0

    async def test_get_user_stats(self, test_db: AsyncSession, test_user: User) -> None:
        """Test getting user statistics."""
        service = GamificationService(test_db)

        # Award various types of points
        await service.award_points(
            user_id=test_user.id,
            action=PointsAction.ORDER_COMPLETE,
            points=20,
            description="Order complete",
        )
        await service.award_points(
            user_id=test_user.id,
            action=PointsAction.CALCULATION_COMPLETE,
            points=15,
            description="Calculation done",
        )
        await service.award_points(
            user_id=test_user.id,
            action=PointsAction.DOCUMENT_UPLOAD,
            points=5,
            description="Document uploaded",
        )

        # Get stats
        stats = await service.get_user_stats(user_id=test_user.id)

        assert stats.user_id == str(test_user.id)
        assert stats.user_name == "Test User"
        assert stats.total_points == 40
        assert stats.rank == 1
        assert stats.orders_completed == 1
        assert stats.calculations_done == 1
        assert stats.documents_uploaded == 1
        assert len(stats.recent_points) == 3

    async def test_points_model_creation(self, test_db: AsyncSession, test_user: User) -> None:
        """Test UserPoints model instantiation."""
        points = UserPoints(
            user_id=test_user.id,
            action=PointsAction.ORDER_STATUS_CHANGE,
            points=10,
            description="Test points",
            entity_type="order",
            entity_id=uuid.uuid4(),
            earned_at=datetime.now(UTC),
        )

        test_db.add(points)
        await test_db.flush()
        await test_db.refresh(points)

        assert points.id is not None
        assert points.user_id == test_user.id
        assert points.action == PointsAction.ORDER_STATUS_CHANGE
        assert points.points == 10
        assert points.created_at is not None
        assert points.updated_at is not None
