"""Tests for offer to order conversion workflow."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Offer, OfferStatus, Order, OrderItem, OrderStatus
from app.services import OrderService


@pytest.fixture
async def sample_customer(test_db: AsyncSession) -> Customer:
    """Create a sample customer."""
    customer = Customer(
        company_name="Test Company s.r.o.",
        ico="12345678",
        dic="CZ12345678",
        contact_name="Jan Novák",
        email="jan.novak@test.cz",
        phone="+420123456789",
        address="Test Street 123, Praha",
    )
    test_db.add(customer)
    await test_db.commit()
    await test_db.refresh(customer)
    return customer


@pytest.fixture
async def sample_order_with_offer(
    test_db: AsyncSession,
    sample_customer: Customer,
) -> tuple[Order, Offer]:
    """Create a sample order with offer."""
    # Create order in NABIDKA status
    order = Order(
        customer_id=sample_customer.id,
        number="OBJ-2024-001",
        status=OrderStatus.NABIDKA,
        priority="normal",
        due_date=date.today() + timedelta(days=30),
        note="Test order",
    )
    test_db.add(order)
    await test_db.flush()

    # Add items
    item1 = OrderItem(
        order_id=order.id,
        name="Potrubní díl DN100",
        material="S235JR",
        quantity=Decimal("10"),
        unit="ks",
        dn="DN100",
        pn="PN16",
    )
    item2 = OrderItem(
        order_id=order.id,
        name="Příruby DN50",
        material="S235JR",
        quantity=Decimal("20"),
        unit="ks",
        dn="DN50",
        pn="PN25",
    )
    test_db.add_all([item1, item2])
    await test_db.flush()

    # Create offer
    offer = Offer(
        order_id=order.id,
        number="NAB-2024-001",
        total_price=Decimal("125000.50"),
        valid_until=date.today() + timedelta(days=30),
        status=OfferStatus.SENT,
    )
    test_db.add(offer)
    await test_db.commit()

    await test_db.refresh(order, ["items"])
    await test_db.refresh(offer)

    return order, offer


@pytest.mark.asyncio
async def test_convert_offer_to_order_success(
    test_db: AsyncSession,
    sample_order_with_offer: tuple[Order, Offer],
):
    """Test successful conversion of offer to order."""
    source_order, offer = sample_order_with_offer
    user_id = uuid4()

    service = OrderService(test_db, user_id=user_id)
    new_order = await service.convert_offer_to_order(offer.id)

    assert new_order is not None
    assert new_order.id != source_order.id
    assert new_order.status == OrderStatus.OBJEDNAVKA
    assert new_order.customer_id == source_order.customer_id
    assert new_order.source_offer_id == offer.id
    assert new_order.created_by == user_id
    assert "Vytvořeno z nabídky" in new_order.note

    # Check items were copied
    assert len(new_order.items) == 2
    for new_item, source_item in zip(new_order.items, source_order.items, strict=False):
        assert new_item.name == source_item.name
        assert new_item.material == source_item.material
        assert new_item.quantity == source_item.quantity
        assert new_item.unit == source_item.unit
        assert new_item.dn == source_item.dn
        assert new_item.pn == source_item.pn

    # Check offer was updated
    await test_db.refresh(offer)
    assert offer.status == OfferStatus.ACCEPTED
    assert offer.converted_to_order_id == new_order.id


@pytest.mark.asyncio
async def test_convert_accepted_offer(
    test_db: AsyncSession,
    sample_order_with_offer: tuple[Order, Offer],
):
    """Test conversion of already accepted offer."""
    _, offer = sample_order_with_offer
    user_id = uuid4()

    # Set offer to accepted
    offer.status = OfferStatus.ACCEPTED
    await test_db.commit()

    service = OrderService(test_db, user_id=user_id)
    new_order = await service.convert_offer_to_order(offer.id)

    assert new_order is not None
    assert new_order.status == OrderStatus.OBJEDNAVKA


@pytest.mark.asyncio
async def test_convert_draft_offer_fails(
    test_db: AsyncSession,
    sample_order_with_offer: tuple[Order, Offer],
):
    """Test that draft offer cannot be converted."""
    _, offer = sample_order_with_offer
    user_id = uuid4()

    # Set offer to draft
    offer.status = OfferStatus.DRAFT
    await test_db.commit()

    service = OrderService(test_db, user_id=user_id)
    with pytest.raises(ValueError, match="Cannot convert offer with status"):
        await service.convert_offer_to_order(offer.id)


@pytest.mark.asyncio
async def test_convert_rejected_offer_fails(
    test_db: AsyncSession,
    sample_order_with_offer: tuple[Order, Offer],
):
    """Test that rejected offer cannot be converted."""
    _, offer = sample_order_with_offer
    user_id = uuid4()

    # Set offer to rejected
    offer.status = OfferStatus.REJECTED
    await test_db.commit()

    service = OrderService(test_db, user_id=user_id)
    with pytest.raises(ValueError, match="Cannot convert offer with status"):
        await service.convert_offer_to_order(offer.id)


@pytest.mark.asyncio
async def test_convert_nonexistent_offer_fails(test_db: AsyncSession):
    """Test conversion of non-existent offer."""
    user_id = uuid4()
    fake_offer_id = uuid4()

    service = OrderService(test_db, user_id=user_id)
    with pytest.raises(ValueError, match="Offer .* not found"):
        await service.convert_offer_to_order(fake_offer_id)


@pytest.mark.asyncio
async def test_convert_already_converted_offer_fails(
    test_db: AsyncSession,
    sample_order_with_offer: tuple[Order, Offer],
):
    """Test that already converted offer cannot be converted again."""
    _, offer = sample_order_with_offer
    user_id = uuid4()

    # First conversion
    service = OrderService(test_db, user_id=user_id)
    await service.convert_offer_to_order(offer.id)
    await test_db.commit()

    # Try to convert again
    with pytest.raises(ValueError, match="already converted"):
        await service.convert_offer_to_order(offer.id)


@pytest.mark.asyncio
async def test_conversion_preserves_priority_and_due_date(
    test_db: AsyncSession,
    sample_order_with_offer: tuple[Order, Offer],
):
    """Test that conversion preserves priority and due_date from source order."""
    source_order, offer = sample_order_with_offer
    user_id = uuid4()

    # Update source order
    source_order.priority = "urgent"
    specific_due_date = date.today() + timedelta(days=15)
    source_order.due_date = specific_due_date
    await test_db.commit()

    service = OrderService(test_db, user_id=user_id)
    new_order = await service.convert_offer_to_order(offer.id)

    assert new_order.priority == "urgent"
    assert new_order.due_date == specific_due_date


@pytest.mark.asyncio
async def test_conversion_creates_unique_order_number(
    test_db: AsyncSession,
    sample_order_with_offer: tuple[Order, Offer],
):
    """Test that conversion creates unique order number."""
    source_order, offer = sample_order_with_offer
    user_id = uuid4()

    service = OrderService(test_db, user_id=user_id)
    new_order = await service.convert_offer_to_order(offer.id)

    assert new_order.number != source_order.number
    assert source_order.number in new_order.number
    assert "OBJ" in new_order.number
