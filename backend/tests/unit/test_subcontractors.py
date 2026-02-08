"""Unit tests for Subcontractor and Subcontract functionality."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Order, OrderStatus, Subcontract, Subcontractor
from app.schemas.subcontractor import (
    SubcontractCreate,
    SubcontractorCreate,
    SubcontractorUpdate,
    SubcontractUpdate,
)
from app.services.subcontractor import SubcontractorService


@pytest.fixture
async def subcontractor(test_db: AsyncSession) -> Subcontractor:
    """Create a subcontractor for testing."""
    subcontractor = Subcontractor(
        name="Test Subcontractor",
        ico="12345678",
        contact_email="test@subcontractor.cz",
        contact_phone="+420777888999",
        specialization="svařování",
        rating=4,
        is_active=True,
    )
    test_db.add(subcontractor)
    await test_db.flush()
    await test_db.refresh(subcontractor)
    return subcontractor


@pytest.fixture
async def order(test_db: AsyncSession) -> Order:
    """Create an order for testing subcontracts."""
    customer = Customer(
        company_name="Test Customer",
        ico="87654321",
        contact_name="Test Contact",
        email="test@customer.cz",
    )
    test_db.add(customer)
    await test_db.flush()

    order = Order(
        customer_id=customer.id,
        number="ORD-TEST-001",
        status=OrderStatus.VYROBA,
    )
    test_db.add(order)
    await test_db.flush()
    await test_db.refresh(order)
    return order


# --- Subcontractor tests ---


@pytest.mark.asyncio
async def test_create_subcontractor(test_db: AsyncSession):
    """Test creating a new subcontractor."""
    service = SubcontractorService(test_db)
    data = SubcontractorCreate(
        name="New Subcontractor",
        ico="11111111",
        contact_email="new@subcontractor.cz",
        specialization="povrchová úprava",
        rating=5,
        is_active=True,
    )

    result = await service.create_subcontractor(data)

    assert result.id is not None
    assert result.name == "New Subcontractor"
    assert result.ico == "11111111"
    assert result.specialization == "povrchová úprava"
    assert result.rating == 5
    assert result.is_active is True


@pytest.mark.asyncio
async def test_list_subcontractors(test_db: AsyncSession, subcontractor: Subcontractor):
    """Test listing subcontractors."""
    service = SubcontractorService(test_db)
    subcontractors, total = await service.get_all_subcontractors(skip=0, limit=10)

    assert total >= 1
    assert len(subcontractors) >= 1
    assert any(s.id == subcontractor.id for s in subcontractors)


@pytest.mark.asyncio
async def test_list_subcontractors_filter_active(test_db: AsyncSession):
    """Test filtering subcontractors by active status."""
    # Create active and inactive subcontractors
    active = Subcontractor(name="Active Sub", is_active=True)
    inactive = Subcontractor(name="Inactive Sub", is_active=False)
    test_db.add(active)
    test_db.add(inactive)
    await test_db.flush()

    service = SubcontractorService(test_db)

    # Filter for active only
    active_subs, active_total = await service.get_all_subcontractors(is_active=True)
    assert all(s.is_active for s in active_subs)
    assert active_total >= 1

    # Filter for inactive only
    inactive_subs, inactive_total = await service.get_all_subcontractors(is_active=False)
    assert all(not s.is_active for s in inactive_subs)
    assert inactive_total >= 1


@pytest.mark.asyncio
async def test_list_subcontractors_filter_specialization(test_db: AsyncSession):
    """Test filtering subcontractors by specialization."""
    # Create subcontractors with different specializations
    welding = Subcontractor(name="Welding Sub", specialization="svařování")
    ndt = Subcontractor(name="NDT Sub", specialization="NDT kontrola")
    test_db.add(welding)
    test_db.add(ndt)
    await test_db.flush()

    service = SubcontractorService(test_db)

    # Filter for welding
    welding_subs, welding_total = await service.get_all_subcontractors(
        specialization="svařování"
    )
    assert welding_total >= 1
    assert all("svařování" in (s.specialization or "").lower() for s in welding_subs)


@pytest.mark.asyncio
async def test_update_subcontractor(test_db: AsyncSession, subcontractor: Subcontractor):
    """Test updating a subcontractor."""
    service = SubcontractorService(test_db)
    update_data = SubcontractorUpdate(
        name="Updated Subcontractor",
        rating=5,
    )

    result = await service.update_subcontractor(subcontractor.id, update_data)

    assert result is not None
    assert result.name == "Updated Subcontractor"
    assert result.rating == 5
    # Other fields should remain unchanged
    assert result.ico == subcontractor.ico


@pytest.mark.asyncio
async def test_delete_subcontractor(test_db: AsyncSession, subcontractor: Subcontractor):
    """Test deleting a subcontractor."""
    service = SubcontractorService(test_db)
    subcontractor_id = subcontractor.id

    deleted = await service.delete_subcontractor(subcontractor_id)
    assert deleted is True

    # Verify it's gone
    result = await service.get_subcontractor_by_id(subcontractor_id)
    assert result is None


# --- Subcontract tests ---


@pytest.mark.asyncio
async def test_create_subcontract_for_order(
    test_db: AsyncSession, order: Order, subcontractor: Subcontractor
):
    """Test creating a subcontract for an order."""
    service = SubcontractorService(test_db)
    data = SubcontractCreate(
        subcontractor_id=subcontractor.id,
        description="Svařování dílů podle WPS-123",
        price=Decimal("15000.00"),
        status="requested",
    )

    result = await service.create_subcontract(order.id, data)

    assert result.id is not None
    assert result.order_id == order.id
    assert result.subcontractor_id == subcontractor.id
    assert result.description == "Svařování dílů podle WPS-123"
    assert result.price == Decimal("15000.00")
    assert result.status == "requested"


@pytest.mark.asyncio
async def test_list_subcontracts_by_order(
    test_db: AsyncSession, order: Order, subcontractor: Subcontractor
):
    """Test listing subcontracts for an order."""
    # Create multiple subcontracts
    subcontract1 = Subcontract(
        order_id=order.id,
        subcontractor_id=subcontractor.id,
        description="Subcontract 1",
        status="requested",
    )
    subcontract2 = Subcontract(
        order_id=order.id,
        subcontractor_id=subcontractor.id,
        description="Subcontract 2",
        status="confirmed",
    )
    test_db.add(subcontract1)
    test_db.add(subcontract2)
    await test_db.flush()

    service = SubcontractorService(test_db)
    subcontracts = await service.get_subcontracts_by_order(order.id)

    assert len(subcontracts) >= 2
    assert all(s.order_id == order.id for s in subcontracts)


@pytest.mark.asyncio
async def test_update_subcontract_status(
    test_db: AsyncSession, order: Order, subcontractor: Subcontractor
):
    """Test updating a subcontract status."""
    # Create a subcontract
    subcontract = Subcontract(
        order_id=order.id,
        subcontractor_id=subcontractor.id,
        description="Test subcontract",
        status="requested",
    )
    test_db.add(subcontract)
    await test_db.flush()
    await test_db.refresh(subcontract)

    service = SubcontractorService(test_db)
    update_data = SubcontractUpdate(
        status="confirmed",
        price=Decimal("25000.00"),
    )

    result = await service.update_subcontract(subcontract.id, update_data)

    assert result is not None
    assert result.status == "confirmed"
    assert result.price == Decimal("25000.00")


@pytest.mark.asyncio
async def test_delete_subcontract(
    test_db: AsyncSession, order: Order, subcontractor: Subcontractor
):
    """Test deleting a subcontract."""
    # Create a subcontract
    subcontract = Subcontract(
        order_id=order.id,
        subcontractor_id=subcontractor.id,
        description="Test subcontract",
        status="requested",
    )
    test_db.add(subcontract)
    await test_db.flush()
    await test_db.refresh(subcontract)
    subcontract_id = subcontract.id

    service = SubcontractorService(test_db)
    deleted = await service.delete_subcontract(subcontract_id)
    assert deleted is True

    # Verify it's gone
    result = await service.get_subcontract_by_id(subcontract_id)
    assert result is None


@pytest.mark.asyncio
async def test_cascade_delete_order_deletes_subcontracts(
    test_db: AsyncSession, order: Order, subcontractor: Subcontractor
):
    """Test that deleting an order cascades to delete its subcontracts."""
    # Create a subcontract
    subcontract = Subcontract(
        order_id=order.id,
        subcontractor_id=subcontractor.id,
        description="Test subcontract",
        status="requested",
    )
    test_db.add(subcontract)
    await test_db.flush()
    subcontract_id = subcontract.id

    # Delete the order
    await test_db.delete(order)
    await test_db.flush()

    # Verify subcontract is gone (CASCADE delete)
    service = SubcontractorService(test_db)
    result = await service.get_subcontract_by_id(subcontract_id)
    assert result is None
