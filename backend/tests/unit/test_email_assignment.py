"""Tests for automatic email-to-order assignment."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models import Customer, InboxMessage, Order, OrderStatus
from app.services.inbox import match_email_to_order


@pytest.mark.asyncio
class TestEmailOrderMatching:
    """Test email-to-order matching logic."""

    async def test_match_by_order_number_in_subject(self, test_db):
        """Test matching when order number is in email subject."""
        # Create customer and order
        customer = Customer(
            company_name="Test Company",
            ico="12345678",
            contact_name="John Doe",
            email="customer@example.com",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="ZAK-2024-001",
            status=OrderStatus.VYROBA,
        )
        test_db.add(order)
        await test_db.flush()

        # Create inbox message with order number in subject
        inbox_msg = InboxMessage(
            message_id="<test1@example.com>",
            from_email="customer@example.com",
            subject="Re: Dotaz k zakázce ZAK-2024-001",
            body_text="Dobrý den, chtěl bych se zeptat...",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        # Match email to order
        matched_order_id = await match_email_to_order(test_db, inbox_msg)

        assert matched_order_id == order.id

    async def test_match_by_order_number_in_body(self, test_db):
        """Test matching when order number is in email body."""
        customer = Customer(
            company_name="Test Company",
            ico="12345678",
            contact_name="John Doe",
            email="customer@example.com",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="NAB-2025-042",
            status=OrderStatus.NABIDKA,
        )
        test_db.add(order)
        await test_db.flush()

        inbox_msg = InboxMessage(
            message_id="<test2@example.com>",
            from_email="customer@example.com",
            subject="Dotaz",
            body_text="Dobrý den, týká se to nabídky NAB-2025-042.",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        matched_order_id = await match_email_to_order(test_db, inbox_msg)

        assert matched_order_id == order.id

    async def test_match_custom_prefix_order_number(self, test_db):
        """Test matching with custom order number prefix."""
        customer = Customer(
            company_name="Test Company",
            ico="12345678",
            contact_name="John Doe",
            email="customer@example.com",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="OBJ-2024-100",
            status=OrderStatus.OBJEDNAVKA,
        )
        test_db.add(order)
        await test_db.flush()

        inbox_msg = InboxMessage(
            message_id="<test3@example.com>",
            from_email="customer@example.com",
            subject="Objednávka OBJ-2024-100",
            body_text="Potvrzuji objednávku.",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        matched_order_id = await match_email_to_order(test_db, inbox_msg)

        assert matched_order_id == order.id

    async def test_match_by_customer_email(self, test_db):
        """Test matching by customer email when no order number is found."""
        customer = Customer(
            company_name="Test Company",
            ico="12345678",
            contact_name="Jane Smith",
            email="jane@example.com",
        )
        test_db.add(customer)
        await test_db.flush()

        # Create multiple orders - should match the most recent active one
        old_order = Order(
            customer_id=customer.id,
            number="ZAK-2024-001",
            status=OrderStatus.VYROBA,
        )
        test_db.add(old_order)

        recent_order = Order(
            customer_id=customer.id,
            number="ZAK-2024-010",
            status=OrderStatus.NABIDKA,
        )
        test_db.add(recent_order)
        await test_db.flush()

        inbox_msg = InboxMessage(
            message_id="<test4@example.com>",
            from_email="jane@example.com",
            subject="General inquiry",
            body_text="Hello, I have a question.",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        matched_order_id = await match_email_to_order(test_db, inbox_msg)

        # Should match the most recent order
        assert matched_order_id == recent_order.id

    async def test_no_match_for_completed_orders(self, test_db):
        """Test that completed orders are not matched by email."""
        customer = Customer(
            company_name="Test Company",
            ico="12345678",
            contact_name="John Doe",
            email="john@example.com",
        )
        test_db.add(customer)
        await test_db.flush()

        # Only completed order
        completed_order = Order(
            customer_id=customer.id,
            number="ZAK-2024-001",
            status=OrderStatus.DOKONCENO,
        )
        test_db.add(completed_order)
        await test_db.flush()

        inbox_msg = InboxMessage(
            message_id="<test5@example.com>",
            from_email="john@example.com",
            subject="New inquiry",
            body_text="Hello",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        matched_order_id = await match_email_to_order(test_db, inbox_msg)

        # Should not match completed orders
        assert matched_order_id is None

    async def test_no_match_when_order_not_found(self, test_db):
        """Test no match when referenced order doesn't exist."""
        inbox_msg = InboxMessage(
            message_id="<test6@example.com>",
            from_email="unknown@example.com",
            subject="Question about ZAK-9999-999",
            body_text="Where is my order?",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        matched_order_id = await match_email_to_order(test_db, inbox_msg)

        assert matched_order_id is None

    async def test_no_match_for_unknown_customer(self, test_db):
        """Test no match when customer email is not in database."""
        inbox_msg = InboxMessage(
            message_id="<test7@example.com>",
            from_email="unknown@example.com",
            subject="Hello",
            body_text="I'm a new customer.",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        matched_order_id = await match_email_to_order(test_db, inbox_msg)

        assert matched_order_id is None

    async def test_priority_order_number_over_email(self, test_db):
        """Test that order number match takes priority over email match."""
        # Customer A with active order
        customer_a = Customer(
            company_name="Company A",
            ico="11111111",
            contact_name="Alice",
            email="alice@companya.com",
        )
        test_db.add(customer_a)
        await test_db.flush()

        order_a = Order(
            customer_id=customer_a.id,
            number="ZAK-2024-100",
            status=OrderStatus.VYROBA,
        )
        test_db.add(order_a)

        # Customer B with different order
        customer_b = Customer(
            company_name="Company B",
            ico="22222222",
            contact_name="Bob",
            email="bob@companyb.com",
        )
        test_db.add(customer_b)
        await test_db.flush()

        order_b = Order(
            customer_id=customer_b.id,
            number="ZAK-2024-200",
            status=OrderStatus.NABIDKA,
        )
        test_db.add(order_b)
        await test_db.flush()

        # Email from Customer A asking about Customer B's order
        inbox_msg = InboxMessage(
            message_id="<test8@example.com>",
            from_email="alice@companya.com",
            subject="Question about ZAK-2024-200",
            body_text="I need information about this order.",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        matched_order_id = await match_email_to_order(test_db, inbox_msg)

        # Should match order_b (by order number), not order_a (by email)
        assert matched_order_id == order_b.id


@pytest.mark.asyncio
class TestEmailAssignmentIntegration:
    """Integration test for email assignment in poll_inbox workflow."""

    async def test_inbox_message_gets_order_id_assigned(self, test_db):
        """Test that InboxMessage.order_id gets populated after matching."""
        customer = Customer(
            company_name="Test Co",
            ico="12345678",
            contact_name="Test User",
            email="test@example.com",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="ZAK-2024-555",
            status=OrderStatus.VYROBA,
        )
        test_db.add(order)
        await test_db.flush()

        inbox_msg = InboxMessage(
            message_id="<integration_test@example.com>",
            from_email="test@example.com",
            subject="Re: ZAK-2024-555",
            body_text="Status update?",
            received_at=datetime.now(UTC),
        )
        test_db.add(inbox_msg)
        await test_db.flush()

        # Simulate assignment
        matched_order_id = await match_email_to_order(test_db, inbox_msg)
        inbox_msg.order_id = matched_order_id
        await test_db.commit()

        # Verify assignment
        result = await test_db.execute(
            select(InboxMessage).where(InboxMessage.id == inbox_msg.id)
        )
        updated_msg = result.scalar_one()

        assert updated_msg.order_id == order.id
