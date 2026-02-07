"""Unit tests for SQLAlchemy models."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditAction,
    AuditLog,
    Customer,
    InboxClassification,
    InboxMessage,
    InboxStatus,
    Order,
    OrderItem,
    OrderPriority,
    OrderStatus,
)


class TestCustomerModel:
    """Tests for Customer model."""

    async def test_create_customer(self, test_db: AsyncSession) -> None:
        """Test creating a customer record."""
        customer = Customer(
            company_name="Test Steel s.r.o.",
            ico="12345678",
            dic="CZ12345678",
            contact_name="Jan Novak",
            email="jan@test-steel.cz",
            phone="+420 123 456 789",
            address="Brno, Czech Republic",
        )
        test_db.add(customer)
        await test_db.flush()

        assert customer.id is not None
        assert isinstance(customer.id, uuid.UUID)
        assert customer.company_name == "Test Steel s.r.o."
        assert customer.ico == "12345678"

    async def test_customer_repr(self, test_db: AsyncSession) -> None:
        """Test Customer string representation."""
        customer = Customer(
            company_name="Infer s.r.o.",
            ico="04856562",
            contact_name="Test",
            email="test@infer.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        repr_str = repr(customer)
        assert "Infer s.r.o." in repr_str
        assert "04856562" in repr_str

    async def test_customer_timestamps(self, test_db: AsyncSession) -> None:
        """Test that timestamps are set automatically."""
        customer = Customer(
            company_name="Timestamp Test",
            ico="99999999",
            contact_name="Test",
            email="test@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        assert customer.created_at is not None
        assert customer.updated_at is not None


class TestOrderModel:
    """Tests for Order model."""

    async def test_create_order(self, test_db: AsyncSession) -> None:
        """Test creating an order with items."""
        customer = Customer(
            company_name="Order Test s.r.o.",
            ico="11111111",
            contact_name="Test",
            email="test@order.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="ZAK-2024-001",
            status=OrderStatus.POPTAVKA,
            priority=OrderPriority.NORMAL,
            due_date=date(2024, 12, 31),
            note="Test order",
        )
        test_db.add(order)
        await test_db.flush()

        assert order.id is not None
        assert order.number == "ZAK-2024-001"
        assert order.status == OrderStatus.POPTAVKA
        assert order.priority == OrderPriority.NORMAL

    async def test_order_item(self, test_db: AsyncSession) -> None:
        """Test creating order items."""
        customer = Customer(
            company_name="Item Test s.r.o.",
            ico="22222222",
            contact_name="Test",
            email="test@item.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="ZAK-2024-002",
            status=OrderStatus.POPTAVKA,
            priority=OrderPriority.HIGH,
        )
        test_db.add(order)
        await test_db.flush()

        item = OrderItem(
            order_id=order.id,
            name="Koleno 90° DN200 PN16",
            material="P235GH",
            quantity=Decimal("50"),
            unit="ks",
            dn="DN200",
            pn="PN16",
        )
        test_db.add(item)
        await test_db.flush()

        assert item.id is not None
        assert item.name == "Koleno 90° DN200 PN16"
        assert item.material == "P235GH"
        assert item.quantity == Decimal("50")

    async def test_order_status_enum(self) -> None:
        """Test OrderStatus enum values."""
        assert OrderStatus.POPTAVKA.value == "poptavka"
        assert OrderStatus.NABIDKA.value == "nabidka"
        assert OrderStatus.OBJEDNAVKA.value == "objednavka"
        assert OrderStatus.VYROBA.value == "vyroba"
        assert OrderStatus.EXPEDICE.value == "expedice"
        assert OrderStatus.FAKTURACE.value == "fakturace"
        assert OrderStatus.DOKONCENO.value == "dokonceno"

    async def test_order_priority_enum(self) -> None:
        """Test OrderPriority enum values."""
        assert OrderPriority.LOW.value == "low"
        assert OrderPriority.NORMAL.value == "normal"
        assert OrderPriority.HIGH.value == "high"
        assert OrderPriority.URGENT.value == "urgent"


class TestInboxMessageModel:
    """Tests for InboxMessage model."""

    async def test_create_inbox_message(self, test_db: AsyncSession) -> None:
        """Test creating an inbox message."""
        msg = InboxMessage(
            message_id="<test-123@mail.example.com>",
            from_email="zakaznik@firma.cz",
            subject="Poptavka - kolena DN200 PN16",
            body_text="Dobry den, prosim o cenovou nabidku...",
            received_at=datetime.now(UTC),
            classification=InboxClassification.POPTAVKA,
            confidence=0.95,
            status=InboxStatus.NEW,
        )
        test_db.add(msg)
        await test_db.flush()

        assert msg.id is not None
        assert msg.classification == InboxClassification.POPTAVKA
        assert msg.confidence == 0.95
        assert msg.status == InboxStatus.NEW

    async def test_inbox_classification_enum(self) -> None:
        """Test InboxClassification enum values."""
        assert InboxClassification.POPTAVKA.value == "poptavka"
        assert InboxClassification.OBJEDNAVKA.value == "objednavka"
        assert InboxClassification.REKLAMACE.value == "reklamace"
        assert InboxClassification.DOTAZ.value == "dotaz"
        assert InboxClassification.PRILOHA.value == "priloha"


class TestAuditLogModel:
    """Tests for AuditLog model."""

    async def test_create_audit_log(self, test_db: AsyncSession) -> None:
        """Test creating an audit log entry."""
        entity_id = uuid.uuid4()
        log = AuditLog(
            user_id=None,
            action=AuditAction.CREATE,
            entity_type="customer",
            entity_id=entity_id,
            changes={"created": {"company_name": "Test"}},
            timestamp=datetime.now(UTC),
        )
        test_db.add(log)
        await test_db.flush()

        assert log.id is not None
        assert log.action == AuditAction.CREATE
        assert log.entity_type == "customer"
        assert log.changes is not None
