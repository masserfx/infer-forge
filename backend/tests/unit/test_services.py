"""Unit tests for business logic services."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditAction,
    AuditLog,
    Customer,
    Order,
    OrderPriority,
    OrderStatus,
)
from app.schemas import CustomerCreate, CustomerUpdate, OrderCreate, OrderItemCreate
from app.services import CustomerService, OrderService


class TestCustomerService:
    """Tests for CustomerService."""

    async def test_create_customer(self, test_db: AsyncSession) -> None:
        """Test creating a customer via service."""
        service = CustomerService(test_db)
        data = CustomerCreate(
            company_name="Service Test s.r.o.",
            ico="33333333",
            contact_name="Test User",
            email="test@service.cz",
        )
        customer = await service.create(data)

        assert customer.id is not None
        assert customer.company_name == "Service Test s.r.o."
        assert customer.ico == "33333333"

    async def test_get_customer_by_id(self, test_db: AsyncSession) -> None:
        """Test retrieving customer by ID."""
        service = CustomerService(test_db)
        data = CustomerCreate(
            company_name="Get Test s.r.o.",
            ico="44444444",
            contact_name="Get User",
            email="get@test.cz",
        )
        created = await service.create(data)

        found = await service.get_by_id(created.id)
        assert found is not None
        assert found.company_name == "Get Test s.r.o."

    async def test_get_customer_not_found(self, test_db: AsyncSession) -> None:
        """Test retrieving non-existent customer."""
        service = CustomerService(test_db)
        result = await service.get_by_id(uuid.uuid4())
        assert result is None

    async def test_get_all_customers(self, test_db: AsyncSession) -> None:
        """Test listing all customers."""
        service = CustomerService(test_db)
        for i in range(3):
            await service.create(
                CustomerCreate(
                    company_name=f"List Test {i}",
                    ico=f"5555555{i}",
                    contact_name=f"User {i}",
                    email=f"user{i}@test.cz",
                )
            )

        customers = await service.get_all()
        assert len(customers) == 3

    async def test_update_customer(self, test_db: AsyncSession) -> None:
        """Test updating a customer."""
        service = CustomerService(test_db)
        data = CustomerCreate(
            company_name="Update Test",
            ico="66666666",
            contact_name="Before Update",
            email="before@test.cz",
        )
        customer = await service.create(data)

        updated = await service.update(
            customer.id,
            CustomerUpdate(contact_name="After Update"),
        )
        assert updated is not None
        assert updated.contact_name == "After Update"

    async def test_delete_customer(self, test_db: AsyncSession) -> None:
        """Test deleting a customer."""
        service = CustomerService(test_db)
        data = CustomerCreate(
            company_name="Delete Test",
            ico="77777777",
            contact_name="To Delete",
            email="delete@test.cz",
        )
        customer = await service.create(data)

        result = await service.delete(customer.id)
        assert result is True

        found = await service.get_by_id(customer.id)
        assert found is None


class TestOrderService:
    """Tests for OrderService."""

    async def _create_customer(self, db: AsyncSession) -> Customer:
        """Helper to create a test customer."""
        customer = Customer(
            company_name="Order Service Test",
            ico=str(uuid.uuid4().int)[:8],
            contact_name="Test",
            email="test@orderservice.cz",
        )
        db.add(customer)
        await db.flush()
        return customer

    async def test_create_order(self, test_db: AsyncSession) -> None:
        """Test creating an order with items."""
        customer = await self._create_customer(test_db)
        service = OrderService(test_db)

        data = OrderCreate(
            customer_id=customer.id,
            number="ZAK-TEST-001",
            status=OrderStatus.POPTAVKA,
            priority=OrderPriority.NORMAL,
            items=[
                OrderItemCreate(
                    name="Koleno 90°",
                    material="P235GH",
                    quantity=Decimal("50"),
                    unit="ks",
                ),
            ],
        )
        order = await service.create(data)

        assert order.id is not None
        assert order.number == "ZAK-TEST-001"
        assert order.status == OrderStatus.POPTAVKA

    async def test_status_transition_valid(self, test_db: AsyncSession) -> None:
        """Test valid status transition."""
        customer = await self._create_customer(test_db)
        service = OrderService(test_db)

        data = OrderCreate(
            customer_id=customer.id,
            number="ZAK-TEST-002",
            status=OrderStatus.POPTAVKA,
            priority=OrderPriority.NORMAL,
            items=[
                OrderItemCreate(name="Test item", quantity=Decimal("1"), unit="ks"),
            ],
        )
        order = await service.create(data)

        updated = await service.change_status(order.id, OrderStatus.NABIDKA)
        assert updated is not None
        assert updated.status == OrderStatus.NABIDKA

    async def test_status_transition_invalid(self, test_db: AsyncSession) -> None:
        """Test invalid status transition raises ValueError."""
        customer = await self._create_customer(test_db)
        service = OrderService(test_db)

        data = OrderCreate(
            customer_id=customer.id,
            number="ZAK-TEST-003",
            status=OrderStatus.POPTAVKA,
            priority=OrderPriority.NORMAL,
            items=[
                OrderItemCreate(name="Test item", quantity=Decimal("1"), unit="ks"),
            ],
        )
        order = await service.create(data)

        with pytest.raises(ValueError, match="Invalid status transition"):
            await service.change_status(order.id, OrderStatus.DOKONCENO)

    async def test_status_transitions_map(self) -> None:
        """Test that status transitions map is complete."""
        service = OrderService.__new__(OrderService)
        for status in OrderStatus:
            assert status in service.STATUS_TRANSITIONS
