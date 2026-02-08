"""Unit tests for operations (výrobní operace)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, OperationStatus, Order, OrderStatus
from app.schemas.operation import OperationCreate, OperationUpdate
from app.services.operation import OperationService


@pytest.fixture
async def sample_customer(test_db: AsyncSession) -> Customer:
    """Create a sample customer for testing."""
    customer = Customer(
        company_name="Test Company s.r.o.",
        ico="12345678",
        dic="CZ12345678",
        contact_name="Jan Novák",
        email="test@example.com",
        phone="+420123456789",
    )
    test_db.add(customer)
    await test_db.commit()
    await test_db.refresh(customer)
    return customer


@pytest.fixture
async def sample_order(test_db: AsyncSession, sample_customer: Customer) -> Order:
    """Create a sample order for testing."""
    order = Order(
        customer_id=sample_customer.id,
        number="ORD-2026-001",
        status=OrderStatus.VYROBA,
    )
    test_db.add(order)
    await test_db.commit()
    await test_db.refresh(order)
    return order


@pytest.fixture
def operation_service(test_db: AsyncSession) -> OperationService:
    """Create OperationService instance."""
    user_id = uuid4()
    return OperationService(db=test_db, user_id=user_id)


async def test_create_operation(
    test_db: AsyncSession,
    operation_service: OperationService,
    sample_order: Order,
) -> None:
    """Test creating a new operation."""
    data = OperationCreate(
        name="Řezání",
        description="Řezání materiálu podle výkresu",
        sequence=1,
        duration_hours=Decimal("2.5"),
        responsible="Jan Novák",
        notes="Použít pilu XYZ",
    )

    operation = await operation_service.create(sample_order.id, data)

    assert operation is not None
    assert operation.name == "Řezání"
    assert operation.description == "Řezání materiálu podle výkresu"
    assert operation.sequence == 1
    assert operation.duration_hours == Decimal("2.5")
    assert operation.responsible == "Jan Novák"
    assert operation.status == OperationStatus.PLANNED.value
    assert operation.order_id == sample_order.id
    assert operation.notes == "Použít pilu XYZ"


async def test_create_operation_with_dates(
    test_db: AsyncSession,
    operation_service: OperationService,
    sample_order: Order,
) -> None:
    """Test creating operation with planned dates."""
    now = datetime.now(UTC)
    planned_start = now + timedelta(days=1)
    planned_end = now + timedelta(days=2)

    data = OperationCreate(
        name="Svařování",
        sequence=2,
        planned_start=planned_start,
        planned_end=planned_end,
    )

    operation = await operation_service.create(sample_order.id, data)

    assert operation is not None
    # SQLite may strip timezone info, so compare timestamps
    assert operation.planned_start is not None
    assert operation.planned_end is not None
    assert abs((operation.planned_start.replace(tzinfo=UTC) - planned_start).total_seconds()) < 1
    assert abs((operation.planned_end.replace(tzinfo=UTC) - planned_end).total_seconds()) < 1


async def test_create_operation_order_not_found(
    test_db: AsyncSession,
    operation_service: OperationService,
) -> None:
    """Test creating operation for non-existent order."""
    fake_order_id = uuid4()
    data = OperationCreate(
        name="Test",
        sequence=1,
    )

    operation = await operation_service.create(fake_order_id, data)

    assert operation is None


async def test_list_operations_by_order(
    test_db: AsyncSession,
    operation_service: OperationService,
    sample_order: Order,
) -> None:
    """Test listing operations for an order, ordered by sequence."""
    # Create operations out of sequence order
    data2 = OperationCreate(name="Svařování", sequence=2)
    data1 = OperationCreate(name="Řezání", sequence=1)
    data3 = OperationCreate(name="NDT", sequence=3)

    await operation_service.create(sample_order.id, data2)
    await operation_service.create(sample_order.id, data1)
    await operation_service.create(sample_order.id, data3)

    operations = await operation_service.get_by_order(sample_order.id)

    assert len(operations) == 3
    # Should be sorted by sequence
    assert operations[0].name == "Řezání"
    assert operations[0].sequence == 1
    assert operations[1].name == "Svařování"
    assert operations[1].sequence == 2
    assert operations[2].name == "NDT"
    assert operations[2].sequence == 3


async def test_update_operation_status(
    test_db: AsyncSession,
    operation_service: OperationService,
    sample_order: Order,
) -> None:
    """Test updating operation status and actual times."""
    data = OperationCreate(name="Svařování", sequence=1)
    operation = await operation_service.create(sample_order.id, data)
    assert operation is not None

    # Start operation
    actual_start = datetime.now(UTC)
    update_data = OperationUpdate(
        status=OperationStatus.IN_PROGRESS.value,
        actual_start=actual_start,
    )

    updated = await operation_service.update(operation.id, update_data)

    assert updated is not None
    assert updated.status == OperationStatus.IN_PROGRESS.value
    assert updated.actual_start is not None
    # SQLite may strip timezone info
    assert abs((updated.actual_start.replace(tzinfo=UTC) - actual_start).total_seconds()) < 1
    assert updated.actual_end is None

    # Complete operation
    actual_end = datetime.now(UTC)
    complete_data = OperationUpdate(
        status=OperationStatus.COMPLETED.value,
        actual_end=actual_end,
    )

    completed = await operation_service.update(operation.id, complete_data)

    assert completed is not None
    assert completed.status == OperationStatus.COMPLETED.value
    assert completed.actual_end is not None
    assert abs((completed.actual_end.replace(tzinfo=UTC) - actual_end).total_seconds()) < 1


async def test_delete_operation(
    test_db: AsyncSession,
    operation_service: OperationService,
    sample_order: Order,
) -> None:
    """Test deleting an operation."""
    data = OperationCreate(name="Test", sequence=1)
    operation = await operation_service.create(sample_order.id, data)
    assert operation is not None

    deleted = await operation_service.delete(operation.id)
    assert deleted is True

    # Verify deletion
    operations = await operation_service.get_by_order(sample_order.id)
    assert len(operations) == 0


async def test_delete_operation_not_found(
    test_db: AsyncSession,
    operation_service: OperationService,
) -> None:
    """Test deleting non-existent operation."""
    fake_id = uuid4()
    deleted = await operation_service.delete(fake_id)
    assert deleted is False


async def test_reorder_operations(
    test_db: AsyncSession,
    operation_service: OperationService,
    sample_order: Order,
) -> None:
    """Test reordering operations."""
    # Create three operations
    op1 = await operation_service.create(
        sample_order.id, OperationCreate(name="First", sequence=1)
    )
    op2 = await operation_service.create(
        sample_order.id, OperationCreate(name="Second", sequence=2)
    )
    op3 = await operation_service.create(
        sample_order.id, OperationCreate(name="Third", sequence=3)
    )

    assert op1 and op2 and op3

    # Reorder: [op3, op1, op2]
    new_order = [op3.id, op1.id, op2.id]
    reordered = await operation_service.reorder(sample_order.id, new_order)

    assert len(reordered) == 3
    assert reordered[0].id == op3.id
    assert reordered[0].sequence == 1
    assert reordered[1].id == op1.id
    assert reordered[1].sequence == 2
    assert reordered[2].id == op2.id
    assert reordered[2].sequence == 3


async def test_reorder_operations_validation_error(
    test_db: AsyncSession,
    operation_service: OperationService,
    sample_order: Order,
) -> None:
    """Test reorder with mismatched operation IDs raises ValueError."""
    op1 = await operation_service.create(
        sample_order.id, OperationCreate(name="First", sequence=1)
    )
    op2 = await operation_service.create(
        sample_order.id, OperationCreate(name="Second", sequence=2)
    )

    assert op1 and op2

    # Try to reorder with missing operation and extra fake ID
    fake_id = uuid4()
    invalid_order = [op1.id, fake_id]  # Missing op2, has fake_id

    with pytest.raises(ValueError, match="Operation IDs mismatch"):
        await operation_service.reorder(sample_order.id, invalid_order)


async def test_operation_cascade_delete_with_order(
    test_db: AsyncSession,
    operation_service: OperationService,
    sample_order: Order,
) -> None:
    """Test that operations are deleted when order is deleted (CASCADE)."""
    # Create operations
    await operation_service.create(
        sample_order.id, OperationCreate(name="Op1", sequence=1)
    )
    await operation_service.create(
        sample_order.id, OperationCreate(name="Op2", sequence=2)
    )

    operations = await operation_service.get_by_order(sample_order.id)
    assert len(operations) == 2

    # Delete order
    await test_db.delete(sample_order)
    await test_db.commit()

    # Verify operations are gone
    operations_after = await operation_service.get_by_order(sample_order.id)
    assert len(operations_after) == 0
