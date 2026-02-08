"""Unit tests for GDPR data deletion functionality."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog, Customer, Order, OrderStatus
from app.services import CustomerService


@pytest.fixture
async def customer_with_orders(test_db: AsyncSession) -> Customer:
    """Create a customer with order history for testing."""
    customer = Customer(
        company_name="Test GDPR Company",
        ico="12345678",
        dic="CZ12345678",
        contact_name="Jan Novák",
        email="jan.novak@test.cz",
        phone="+420123456789",
        address="Praha 1, Václavské náměstí 1",
    )
    test_db.add(customer)
    await test_db.flush()

    # Create some orders for the customer
    order1 = Order(
        customer_id=customer.id,
        number="ORD-001",
        status=OrderStatus.DOKONCENO,
    )
    order2 = Order(
        customer_id=customer.id,
        number="ORD-002",
        status=OrderStatus.VYROBA,
    )
    test_db.add(order1)
    test_db.add(order2)
    await test_db.flush()
    await test_db.refresh(customer)

    return customer


@pytest.mark.asyncio
async def test_gdpr_anonymize_customer(test_db: AsyncSession, customer_with_orders: Customer):
    """Test that GDPR anonymization removes all PII fields."""
    customer_id = customer_with_orders.id
    original_created_at = customer_with_orders.created_at

    service = CustomerService(test_db)
    result = await service.gdpr_anonymize(customer_id)

    assert result is not None
    assert result.id == customer_id
    assert result.company_name == "GDPR Anonymizováno"
    assert result.email == "gdpr-anonymized@invalid.local"
    assert result.phone is None
    assert result.address is None
    assert result.contact_name == "GDPR Anonymizováno"
    assert result.ico == "00000000"
    assert result.dic is None

    # Verify created_at is preserved
    assert result.created_at == original_created_at

    # Verify audit log was created
    audit_result = await test_db.execute(
        select(AuditLog)
        .where(AuditLog.entity_id == customer_id)
        .where(AuditLog.action == AuditAction.UPDATE)
    )
    audit_log = audit_result.scalar_one()
    assert audit_log is not None
    assert "gdpr_anonymization" in audit_log.changes
    assert "anonymized_fields" in audit_log.changes["gdpr_anonymization"]


@pytest.mark.asyncio
async def test_gdpr_anonymize_nonexistent_customer(test_db: AsyncSession):
    """Test that anonymizing a nonexistent customer returns None."""
    import uuid

    service = CustomerService(test_db)
    result = await service.gdpr_anonymize(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_gdpr_preserves_order_history(test_db: AsyncSession, customer_with_orders: Customer):
    """Test that order history is preserved after GDPR anonymization."""
    customer_id = customer_with_orders.id

    # Get order IDs before anonymization
    order_result = await test_db.execute(select(Order).where(Order.customer_id == customer_id))
    orders_before = list(order_result.scalars().all())
    assert len(orders_before) == 2

    # Anonymize customer
    service = CustomerService(test_db)
    await service.gdpr_anonymize(customer_id)
    await test_db.commit()

    # Verify orders still exist and belong to the customer
    order_result_after = await test_db.execute(
        select(Order).where(Order.customer_id == customer_id)
    )
    orders_after = list(order_result_after.scalars().all())
    assert len(orders_after) == 2
    assert orders_after[0].customer_id == customer_id
    assert orders_after[1].customer_id == customer_id


@pytest.mark.asyncio
async def test_gdpr_anonymization_idempotent(test_db: AsyncSession, customer_with_orders: Customer):
    """Test that GDPR anonymization can be run multiple times safely."""
    customer_id = customer_with_orders.id

    service = CustomerService(test_db)

    # First anonymization
    result1 = await service.gdpr_anonymize(customer_id)
    assert result1 is not None
    assert result1.company_name == "GDPR Anonymizováno"

    # Second anonymization (should work the same)
    result2 = await service.gdpr_anonymize(customer_id)
    assert result2 is not None
    assert result2.company_name == "GDPR Anonymizováno"
    assert result2.email == "gdpr-anonymized@invalid.local"
