"""Unit tests for Calculation module."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditAction,
    AuditLog,
    Calculation,
    CalculationItem,
    CalculationStatus,
    CostType,
    Customer,
    OfferStatus,
    Order,
    OrderStatus,
)
from app.schemas import (
    CalculationCreate,
    CalculationItemCreate,
    CalculationItemUpdate,
    CalculationResponse,
    CalculationSummary,
    CalculationUpdate,
)
from app.services import CalculationService


@pytest.fixture
async def test_customer(test_db: AsyncSession) -> Customer:
    """Create a test customer."""
    customer = Customer(
        company_name="Test Company s.r.o.",
        ico="12345678",
        contact_name="Jan Novák",
        email="test@example.com",
    )
    test_db.add(customer)
    await test_db.flush()
    await test_db.refresh(customer)
    return customer


@pytest.fixture
async def test_order(test_db: AsyncSession, test_customer: Customer) -> Order:
    """Create a test order."""
    order = Order(
        customer_id=test_customer.id,
        number="2024-001",
        status=OrderStatus.POPTAVKA,
    )
    test_db.add(order)
    await test_db.flush()
    await test_db.refresh(order)
    return order


class TestCalculationModel:
    """Tests for Calculation model."""

    async def test_create_calculation_minimal_fields(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test creating Calculation with minimal required fields."""
        calc = Calculation(
            order_id=test_order.id,
            name="Základní kalkulace",
        )
        test_db.add(calc)
        await test_db.flush()
        await test_db.refresh(calc)

        assert calc.id is not None
        assert calc.name == "Základní kalkulace"
        assert calc.status == CalculationStatus.DRAFT  # default
        assert calc.margin_percent == Decimal("15")  # default
        assert calc.material_total == Decimal("0")  # default
        assert calc.labor_total == Decimal("0")  # default
        assert calc.cooperation_total == Decimal("0")  # default
        assert calc.overhead_total == Decimal("0")  # default
        assert calc.total_price == Decimal("0")  # default
        assert calc.created_at is not None
        assert calc.updated_at is not None

    async def test_cost_type_enum_values(self) -> None:
        """Test CostType enum has expected values."""
        assert CostType.MATERIAL.value == "material"
        assert CostType.LABOR.value == "labor"
        assert CostType.COOPERATION.value == "cooperation"
        assert CostType.OVERHEAD.value == "overhead"

        cost_types = [CostType.MATERIAL, CostType.LABOR, CostType.COOPERATION, CostType.OVERHEAD]
        assert len(cost_types) == 4

    async def test_calculation_status_enum_values(self) -> None:
        """Test CalculationStatus enum has expected values."""
        assert CalculationStatus.DRAFT.value == "draft"
        assert CalculationStatus.APPROVED.value == "approved"
        assert CalculationStatus.OFFERED.value == "offered"

        statuses = [CalculationStatus.DRAFT, CalculationStatus.APPROVED, CalculationStatus.OFFERED]
        assert len(statuses) == 3

    async def test_default_values(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test default values for Calculation."""
        calc = Calculation(
            order_id=test_order.id,
            name="Test",
        )
        test_db.add(calc)
        await test_db.flush()

        assert calc.status == CalculationStatus.DRAFT
        assert calc.margin_percent == Decimal("15")
        assert calc.material_total == Decimal("0")
        assert calc.labor_total == Decimal("0")
        assert calc.cooperation_total == Decimal("0")
        assert calc.overhead_total == Decimal("0")
        assert calc.margin_amount == Decimal("0")
        assert calc.total_price == Decimal("0")

    async def test_calculation_item_creation(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test CalculationItem creation."""
        calc = Calculation(
            order_id=test_order.id,
            name="Test",
        )
        test_db.add(calc)
        await test_db.flush()

        item = CalculationItem(
            calculation_id=calc.id,
            cost_type=CostType.MATERIAL,
            name="Ocel 11523",
            quantity=Decimal("10.5"),
            unit="kg",
            unit_price=Decimal("25.50"),
            total_price=Decimal("267.75"),
        )
        test_db.add(item)
        await test_db.flush()
        await test_db.refresh(item)

        assert item.id is not None
        assert item.calculation_id == calc.id
        assert item.cost_type == CostType.MATERIAL
        assert item.name == "Ocel 11523"
        assert item.quantity == Decimal("10.5")
        assert item.unit == "kg"
        assert item.unit_price == Decimal("25.50")
        assert item.total_price == Decimal("267.75")

    async def test_relationship_items(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test Calculation-CalculationItem relationship."""
        calc = Calculation(
            order_id=test_order.id,
            name="Test",
        )
        test_db.add(calc)
        await test_db.flush()

        item1 = CalculationItem(
            calculation_id=calc.id,
            cost_type=CostType.MATERIAL,
            name="Item 1",
            unit_price=Decimal("100"),
        )
        item2 = CalculationItem(
            calculation_id=calc.id,
            cost_type=CostType.LABOR,
            name="Item 2",
            unit_price=Decimal("200"),
        )
        test_db.add_all([item1, item2])
        await test_db.flush()
        await test_db.refresh(calc, ["items"])

        assert len(calc.items) == 2
        assert item1 in calc.items
        assert item2 in calc.items


class TestCalculationService:
    """Tests for CalculationService."""

    async def test_create_empty_calculation(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test create - empty calculation (0 items)."""
        service = CalculationService(test_db, user_id=uuid.uuid4())
        data = CalculationCreate(
            order_id=test_order.id,
            name="Prázdná kalkulace",
            items=[],
        )

        calc = await service.create(data)
        await test_db.commit()

        # Re-fetch to ensure items are loaded
        calc = await service.get_by_id(calc.id)
        assert calc is not None
        assert calc.name == "Prázdná kalkulace"
        assert len(calc.items) == 0
        assert calc.total_price == Decimal("0")

    async def test_create_with_items_auto_recalc(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test create - calculation with items, automatic total recalculation."""
        service = CalculationService(test_db)
        data = CalculationCreate(
            order_id=test_order.id,
            name="Kalkulace s položkami",
            margin_percent=Decimal("20"),
            items=[
                CalculationItemCreate(
                    cost_type=CostType.MATERIAL,
                    name="Ocel",
                    quantity=Decimal("10"),
                    unit="kg",
                    unit_price=Decimal("50"),
                ),
                CalculationItemCreate(
                    cost_type=CostType.LABOR,
                    name="Svařování",
                    quantity=Decimal("5"),
                    unit="hod",
                    unit_price=Decimal("400"),
                ),
            ],
        )

        calc = await service.create(data)
        await test_db.commit()

        # Re-fetch to ensure items are loaded
        calc = await service.get_by_id(calc.id)
        assert calc is not None
        assert len(calc.items) == 2
        assert calc.material_total == Decimal("500")  # 10 * 50
        assert calc.labor_total == Decimal("2000")  # 5 * 400
        subtotal = Decimal("2500")
        expected_margin = (subtotal * Decimal("20") / Decimal("100")).quantize(Decimal("0.01"))
        assert calc.margin_amount == expected_margin
        assert calc.total_price == subtotal + expected_margin

    async def test_get_by_id_existing(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test get_by_id - existing calculation."""
        service = CalculationService(test_db)
        created = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Test",
            )
        )

        found = await service.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id
        assert found.name == "Test"

    async def test_get_by_id_nonexistent(self, test_db: AsyncSession) -> None:
        """Test get_by_id - nonexistent returns None."""
        service = CalculationService(test_db)
        result = await service.get_by_id(uuid.uuid4())
        assert result is None

    async def test_get_by_order_returns_calculations(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test get_by_order - returns calculations for order."""
        service = CalculationService(test_db)

        # Create 3 calculations for order
        for i in range(3):
            await service.create(
                CalculationCreate(
                    order_id=test_order.id,
                    name=f"Kalkulace {i}",
                )
            )

        # Create 1 calculation for different order (should not appear)
        other_customer = Customer(
            company_name="Other",
            ico="87654321",
            contact_name="Other",
            email="other@example.com",
        )
        test_db.add(other_customer)
        await test_db.flush()

        other_order = Order(
            customer_id=other_customer.id,
            number="2024-999",
            status=OrderStatus.POPTAVKA,
        )
        test_db.add(other_order)
        await test_db.flush()

        await service.create(
            CalculationCreate(
                order_id=other_order.id,
                name="Other calc",
            )
        )

        calcs = await service.get_by_order(test_order.id)
        assert len(calcs) == 3

    async def test_get_all_no_filters(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test get_all - without filters."""
        service = CalculationService(test_db)

        # Create 2 calculations
        await service.create(CalculationCreate(order_id=test_order.id, name="Calc 1"))
        await service.create(CalculationCreate(order_id=test_order.id, name="Calc 2"))

        calcs = await service.get_all()
        assert len(calcs) >= 2

    async def test_get_all_with_status_filter(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test get_all - with status filter."""
        service = CalculationService(test_db)

        # Create 2 drafts, 1 approved
        await service.create(CalculationCreate(order_id=test_order.id, name="Draft 1"))
        await service.create(CalculationCreate(order_id=test_order.id, name="Draft 2"))

        approved_calc = await service.create(
            CalculationCreate(order_id=test_order.id, name="Approved")
        )
        await service.update(
            approved_calc.id,
            CalculationUpdate(status=CalculationStatus.APPROVED),
        )

        draft_calcs = await service.get_all(status=CalculationStatus.DRAFT)
        assert len(draft_calcs) >= 2

        approved_calcs = await service.get_all(status=CalculationStatus.APPROVED)
        assert len(approved_calcs) >= 1

    async def test_update_name(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test update - change name."""
        service = CalculationService(test_db)
        calc = await service.create(CalculationCreate(order_id=test_order.id, name="Old Name"))

        updated = await service.update(
            calc.id,
            CalculationUpdate(name="New Name"),
        )

        assert updated is not None
        assert updated.name == "New Name"

    async def test_update_margin_recalculates_total(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test update - changing margin_percent triggers recalculation of total_price."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Test",
                margin_percent=Decimal("10"),
                items=[
                    CalculationItemCreate(
                        cost_type=CostType.MATERIAL,
                        name="Material",
                        quantity=Decimal("1"),
                        unit_price=Decimal("1000"),
                    ),
                ],
            )
        )

        # Initial: subtotal=1000, margin=10% -> 100, total=1100
        assert calc.total_price == Decimal("1100")

        # Update margin to 20%
        updated = await service.update(
            calc.id,
            CalculationUpdate(margin_percent=Decimal("20")),
        )

        assert updated is not None
        # New: subtotal=1000, margin=20% -> 200, total=1200
        assert updated.margin_percent == Decimal("20")
        assert updated.margin_amount == Decimal("200")
        assert updated.total_price == Decimal("1200")

    async def test_update_nonexistent(self, test_db: AsyncSession) -> None:
        """Test update - nonexistent returns None."""
        service = CalculationService(test_db)
        result = await service.update(
            uuid.uuid4(),
            CalculationUpdate(name="Won't work"),
        )
        assert result is None

    async def test_add_item_material(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test add_item - adding material item triggers recalculation."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Test",
                margin_percent=Decimal("10"),
            )
        )
        await test_db.commit()
        assert calc.total_price == Decimal("0")

        updated = await service.add_item(
            calc.id,
            CalculationItemCreate(
                cost_type=CostType.MATERIAL,
                name="Ocel",
                quantity=Decimal("5"),
                unit_price=Decimal("100"),
            ),
        )
        await test_db.commit()

        # Re-fetch to ensure items are loaded
        updated = await service.get_by_id(calc.id)
        assert updated is not None
        assert len(updated.items) == 1
        assert updated.material_total == Decimal("500")
        # subtotal=500, margin=10% -> 50, total=550
        assert updated.total_price == Decimal("550")

    async def test_add_item_labor(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test add_item - adding labor item triggers recalculation."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Test",
            )
        )

        updated = await service.add_item(
            calc.id,
            CalculationItemCreate(
                cost_type=CostType.LABOR,
                name="Svařování",
                quantity=Decimal("2"),
                unit_price=Decimal("500"),
            ),
        )

        assert updated is not None
        assert updated.labor_total == Decimal("1000")

    async def test_add_item_nonexistent(self, test_db: AsyncSession) -> None:
        """Test add_item - nonexistent calculation returns None."""
        service = CalculationService(test_db)
        result = await service.add_item(
            uuid.uuid4(),
            CalculationItemCreate(
                cost_type=CostType.MATERIAL,
                name="Test",
            ),
        )
        assert result is None

    async def test_update_item_quantity_recalculates(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test update_item - changing quantity triggers recalculation."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Test",
                margin_percent=Decimal("0"),  # no margin for simpler math
                items=[
                    CalculationItemCreate(
                        cost_type=CostType.MATERIAL,
                        name="Material",
                        quantity=Decimal("2"),
                        unit_price=Decimal("100"),
                    ),
                ],
            )
        )
        await test_db.commit()

        # Re-fetch to get items
        calc = await service.get_by_id(calc.id)
        assert calc is not None
        item_id = calc.items[0].id
        assert calc.total_price == Decimal("200")

        updated = await service.update_item(
            calc.id,
            item_id,
            CalculationItemUpdate(quantity=Decimal("5")),
        )
        await test_db.commit()

        # Re-fetch to ensure items are loaded
        updated = await service.get_by_id(calc.id)
        assert updated is not None
        assert updated.items[0].quantity == Decimal("5")
        assert updated.total_price == Decimal("500")

    async def test_update_item_unit_price_recalculates(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test update_item - changing unit_price triggers recalculation."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Test",
                margin_percent=Decimal("0"),
                items=[
                    CalculationItemCreate(
                        cost_type=CostType.MATERIAL,
                        name="Material",
                        quantity=Decimal("3"),
                        unit_price=Decimal("50"),
                    ),
                ],
            )
        )
        await test_db.commit()

        # Re-fetch to get items
        calc = await service.get_by_id(calc.id)
        assert calc is not None
        item_id = calc.items[0].id
        assert calc.total_price == Decimal("150")

        updated = await service.update_item(
            calc.id,
            item_id,
            CalculationItemUpdate(unit_price=Decimal("100")),
        )
        await test_db.commit()

        # Re-fetch to ensure items are loaded
        updated = await service.get_by_id(calc.id)
        assert updated is not None
        assert updated.items[0].unit_price == Decimal("100")
        assert updated.total_price == Decimal("300")

    async def test_update_item_nonexistent_item(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test update_item - nonexistent item returns None."""
        service = CalculationService(test_db)
        calc = await service.create(CalculationCreate(order_id=test_order.id, name="Test"))

        result = await service.update_item(
            calc.id,
            uuid.uuid4(),  # nonexistent item_id
            CalculationItemUpdate(quantity=Decimal("999")),
        )

        assert result is None

    async def test_remove_item_recalculates(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test remove_item - removing item triggers recalculation."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Test",
                margin_percent=Decimal("0"),
                items=[
                    CalculationItemCreate(
                        cost_type=CostType.MATERIAL,
                        name="Item 1",
                        unit_price=Decimal("100"),
                    ),
                    CalculationItemCreate(
                        cost_type=CostType.LABOR,
                        name="Item 2",
                        unit_price=Decimal("200"),
                    ),
                ],
            )
        )
        await test_db.commit()

        # Re-fetch to get items
        calc = await service.get_by_id(calc.id)
        assert calc is not None
        assert calc.total_price == Decimal("300")

        item_to_remove_id = calc.items[0].id
        updated = await service.remove_item(calc.id, item_to_remove_id)
        await test_db.commit()

        # Re-fetch to ensure items are loaded
        updated = await service.get_by_id(calc.id)
        assert updated is not None
        assert len(updated.items) == 1
        assert updated.total_price == Decimal("200")

    async def test_remove_item_nonexistent(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test remove_item - nonexistent item returns None."""
        service = CalculationService(test_db)
        calc = await service.create(CalculationCreate(order_id=test_order.id, name="Test"))

        result = await service.remove_item(calc.id, uuid.uuid4())
        assert result is None

    async def test_generate_offer_creates_offer_and_marks_offered(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test generate_offer - creates Offer and sets status to OFFERED."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Test",
                items=[
                    CalculationItemCreate(
                        cost_type=CostType.MATERIAL,
                        name="Material",
                        unit_price=Decimal("1000"),
                    ),
                ],
            )
        )

        offer = await service.generate_offer(calc.id, offer_number="N-2024-001")

        assert offer is not None
        assert offer.order_id == test_order.id
        assert offer.number == "N-2024-001"
        assert offer.total_price == calc.total_price
        assert offer.status == OfferStatus.DRAFT
        assert offer.valid_until is not None

        # Check calculation status changed to OFFERED
        updated_calc = await service.get_by_id(calc.id)
        assert updated_calc is not None
        assert updated_calc.status == CalculationStatus.OFFERED

    async def test_generate_offer_empty_calculation_raises(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test generate_offer - empty calculation raises ValueError."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(order_id=test_order.id, name="Empty", items=[])
        )

        with pytest.raises(ValueError, match="Cannot generate offer from empty calculation"):
            await service.generate_offer(calc.id, offer_number="N-2024-001")

    async def test_generate_offer_nonexistent(self, test_db: AsyncSession) -> None:
        """Test generate_offer - nonexistent calculation returns None."""
        service = CalculationService(test_db)
        result = await service.generate_offer(uuid.uuid4(), offer_number="N-2024-001")
        assert result is None

    async def test_delete_removes_calculation(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test delete - removes calculation."""
        service = CalculationService(test_db)
        calc = await service.create(CalculationCreate(order_id=test_order.id, name="Test"))

        result = await service.delete(calc.id)
        assert result is True

        # Verify deletion
        found = await service.get_by_id(calc.id)
        assert found is None

    async def test_delete_nonexistent(self, test_db: AsyncSession) -> None:
        """Test delete - nonexistent returns False."""
        service = CalculationService(test_db)
        result = await service.delete(uuid.uuid4())
        assert result is False

    async def test_recalculate_with_multiple_cost_types(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test recalculation logic - add 3 items of different types, verify totals."""
        service = CalculationService(test_db)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Multi-type test",
                margin_percent=Decimal("20"),
                items=[
                    CalculationItemCreate(
                        cost_type=CostType.MATERIAL,
                        name="Ocel",
                        quantity=Decimal("10"),
                        unit_price=Decimal("100"),
                    ),
                    CalculationItemCreate(
                        cost_type=CostType.LABOR,
                        name="Svařování",
                        quantity=Decimal("5"),
                        unit_price=Decimal("400"),
                    ),
                    CalculationItemCreate(
                        cost_type=CostType.COOPERATION,
                        name="NDT zkoušky",
                        quantity=Decimal("1"),
                        unit_price=Decimal("3000"),
                    ),
                    CalculationItemCreate(
                        cost_type=CostType.OVERHEAD,
                        name="Režie",
                        quantity=Decimal("1"),
                        unit_price=Decimal("500"),
                    ),
                ],
            )
        )

        # Verify individual totals
        assert calc.material_total == Decimal("1000")  # 10 * 100
        assert calc.labor_total == Decimal("2000")  # 5 * 400
        assert calc.cooperation_total == Decimal("3000")  # 1 * 3000
        assert calc.overhead_total == Decimal("500")  # 1 * 500

        # Verify total calculation
        subtotal = Decimal("1000") + Decimal("2000") + Decimal("3000") + Decimal("500")
        assert subtotal == Decimal("6500")

        expected_margin = (subtotal * Decimal("20") / Decimal("100")).quantize(Decimal("0.01"))
        assert calc.margin_amount == expected_margin
        assert calc.total_price == subtotal + expected_margin

    async def test_audit_trail_on_create(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test audit log created on calculation create."""
        user_id = uuid.uuid4()
        service = CalculationService(test_db, user_id=user_id)
        calc = await service.create(
            CalculationCreate(
                order_id=test_order.id,
                name="Audit Test",
                items=[
                    CalculationItemCreate(
                        cost_type=CostType.MATERIAL,
                        name="Material",
                        unit_price=Decimal("100"),
                    ),
                ],
            )
        )

        # Fetch audit log
        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "calculation",
                AuditLog.entity_id == calc.id,
                AuditLog.action == AuditAction.CREATE,
            )
        )
        audit = result.scalar_one_or_none()

        assert audit is not None
        assert audit.user_id == user_id
        assert audit.changes is not None
        assert audit.changes["name"] == "Audit Test"
        assert audit.changes["order_id"] == str(test_order.id)

    async def test_audit_trail_on_update(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test audit log created on calculation update."""
        user_id = uuid.uuid4()
        service = CalculationService(test_db, user_id=user_id)
        calc = await service.create(CalculationCreate(order_id=test_order.id, name="Original"))

        await service.update(calc.id, CalculationUpdate(name="Updated"))

        # Fetch audit log
        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "calculation",
                AuditLog.entity_id == calc.id,
                AuditLog.action == AuditAction.UPDATE,
            )
        )
        audit = result.scalar_one_or_none()

        assert audit is not None
        assert audit.user_id == user_id
        assert audit.changes is not None
        assert "name" in audit.changes
        assert audit.changes["name"]["old"] == "Original"
        assert audit.changes["name"]["new"] == "Updated"

    async def test_audit_trail_on_delete(self, test_db: AsyncSession, test_order: Order) -> None:
        """Test audit log created on calculation delete."""
        user_id = uuid.uuid4()
        service = CalculationService(test_db, user_id=user_id)
        calc = await service.create(CalculationCreate(order_id=test_order.id, name="To Delete"))

        calc_id = calc.id
        await service.delete(calc_id)

        # Fetch audit log
        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "calculation",
                AuditLog.entity_id == calc_id,
                AuditLog.action == AuditAction.DELETE,
            )
        )
        audit = result.scalar_one_or_none()

        assert audit is not None
        assert audit.user_id == user_id
        assert audit.changes is not None
        assert audit.changes["deleted_name"] == "To Delete"


class TestCalculationSchemas:
    """Tests for Calculation Pydantic schemas."""

    def test_calculation_create_validation(self) -> None:
        """Test CalculationCreate schema validation."""
        order_id = uuid.uuid4()
        create_schema = CalculationCreate(
            order_id=order_id,
            name="Test Calculation",
            margin_percent=Decimal("15"),
            items=[
                CalculationItemCreate(
                    cost_type=CostType.MATERIAL,
                    name="Material",
                    quantity=Decimal("5"),
                    unit="kg",
                    unit_price=Decimal("100"),
                ),
            ],
        )

        assert create_schema.order_id == order_id
        assert create_schema.name == "Test Calculation"
        assert create_schema.margin_percent == Decimal("15")
        assert len(create_schema.items) == 1
        assert create_schema.items[0].name == "Material"

    def test_calculation_item_create_validation(self) -> None:
        """Test CalculationItemCreate schema validation."""
        item = CalculationItemCreate(
            cost_type=CostType.LABOR,
            name="Svařování",
            description="Svařování potrubí",
            quantity=Decimal("8"),
            unit="hod",
            unit_price=Decimal("450"),
        )

        assert item.cost_type == CostType.LABOR
        assert item.name == "Svařování"
        assert item.description == "Svařování potrubí"
        assert item.quantity == Decimal("8")
        assert item.unit == "hod"
        assert item.unit_price == Decimal("450")

    async def test_calculation_response_from_attributes(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test CalculationResponse can be created from model instance."""
        calc = Calculation(
            order_id=test_order.id,
            name="Response Test",
            status=CalculationStatus.APPROVED,
            margin_percent=Decimal("18"),
            material_total=Decimal("1000"),
            total_price=Decimal("1180"),
        )
        test_db.add(calc)
        await test_db.flush()
        await test_db.refresh(calc, ["items"])

        response = CalculationResponse.model_validate(calc)
        assert response.name == "Response Test"
        assert response.status == CalculationStatus.APPROVED
        assert response.margin_percent == Decimal("18")
        assert response.material_total == Decimal("1000")
        assert response.total_price == Decimal("1180")

    def test_calculation_update_partial_update(self) -> None:
        """Test CalculationUpdate allows partial updates (all optional)."""
        # Update only name
        update1 = CalculationUpdate(name="New Name")
        assert update1.name == "New Name"
        assert update1.margin_percent is None
        assert update1.status is None

        # Update only margin
        update2 = CalculationUpdate(margin_percent=Decimal("25"))
        assert update2.name is None
        assert update2.margin_percent == Decimal("25")

        # Update multiple fields
        update3 = CalculationUpdate(
            name="Updated",
            status=CalculationStatus.APPROVED,
        )
        assert update3.name == "Updated"
        assert update3.status == CalculationStatus.APPROVED

    def test_margin_percent_validation_range(self) -> None:
        """Test margin_percent validates 0-100 range."""
        # Valid margins
        valid_create = CalculationCreate(
            order_id=uuid.uuid4(),
            name="Test",
            margin_percent=Decimal("0"),  # minimum
        )
        assert valid_create.margin_percent == Decimal("0")

        valid_create2 = CalculationCreate(
            order_id=uuid.uuid4(),
            name="Test",
            margin_percent=Decimal("100"),  # maximum
        )
        assert valid_create2.margin_percent == Decimal("100")

        # Invalid margin - negative
        with pytest.raises(ValueError):
            CalculationCreate(
                order_id=uuid.uuid4(),
                name="Test",
                margin_percent=Decimal("-5"),
            )

        # Invalid margin - over 100
        with pytest.raises(ValueError):
            CalculationCreate(
                order_id=uuid.uuid4(),
                name="Test",
                margin_percent=Decimal("101"),
            )

    async def test_calculation_summary_schema(
        self, test_db: AsyncSession, test_order: Order
    ) -> None:
        """Test CalculationSummary schema for dashboard views."""
        calc = Calculation(
            order_id=test_order.id,
            name="Summary Test",
            status=CalculationStatus.DRAFT,
            material_total=Decimal("500"),
            labor_total=Decimal("1000"),
            cooperation_total=Decimal("200"),
            overhead_total=Decimal("100"),
            margin_percent=Decimal("15"),
            total_price=Decimal("2070"),
        )
        test_db.add(calc)
        await test_db.flush()
        await test_db.refresh(calc)

        summary = CalculationSummary.model_validate(calc)
        assert summary.id == calc.id
        assert summary.name == "Summary Test"
        assert summary.total_price == Decimal("2070")
        assert summary.items_count == 0  # default
